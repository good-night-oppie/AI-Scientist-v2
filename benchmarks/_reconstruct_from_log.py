"""One-shot reconstruction of results.csv + summary.csv from the FROZEN sweep log.

The full-grid sweep RAN but was intentionally CAPPED (killed) at the final cell to
save ~45 min of zero-signal 5 GB reps (explicitly licensed by the phase spec). bench.py
writes results.csv only at loop-end, so it was never written. This parses every
``[bench] <tool> <size>/<red> rep<N>: ...`` line (each printed twice -> dedup), maps
ok->round_trip_ok / oom->oomed, pulls n_nodes from the ``=== size=... nodes=N ===``
headers, marks oomed reps skipped (bench.py's own behaviour), and adds explicit
skipped_reason rows for the design-capped and wall-clock-capped cells. It fabricates
NO measured numbers -- capped reps carry empty metric fields and a reason string only.

summary.csv is produced by feeding the reconstructed completed (non-skipped, rep>=1)
rows through bench.summarize + add_helios_tar_ratios, then dropping any cell with
n_reps < 5 (a capped/under-sampled cell is represented in results.csv, not summarised).
"""

from __future__ import annotations

import csv
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bench  # noqa: E402

FROZEN = os.path.join(HERE, "..", ".supergoal", "evidence", "M8", "run.log.frozen")
OUT_DIR = os.path.join(HERE, "..", ".supergoal", "evidence", "M8")

OOM_REASON = (
    "oomed: helios whole-file-into-RAM ceiling (cli.go:118); "
    "docker -m 6g OOM at this size"
)
DESIGN_CAP = "design-cap: 5GB low/med dropped for wall-clock/disk; high sampled"
WALLCLOCK_CAP = (
    "capped: 5GB/high cp_r+tar_czf reps beyond sample dropped for wall-clock "
    "— decisive datapoint helios OOM + cp_r sample retained"
)

HDR = re.compile(r"=== size=(\S+) bytes=(\d+) nodes=(\d+) ")
ROW = re.compile(
    r"\[bench\] (helios|cp_r|tar_czf) (\S+)/(low|med|high) rep(\d+): "
    r"commit=([\d.]+)s restore=([\d.]+)s store=(\d+) rss=(\d+)kb "
    r"ok=([01]) oom=([01])"
)

SIZE_ORDER = {"5MB": 0, "50MB": 1, "500MB": 2, "5GB": 3}
RED_ORDER = {"low": 0, "med": 1, "high": 2}
TOOL_ORDER = {"helios": 0, "cp_r": 1, "tar_czf": 2}
TOOLS = ["helios", "cp_r", "tar_czf"]


def main():
    size_bytes = {}
    size_nodes = {}
    seen = {}
    rows = []
    with open(FROZEN) as fh:
        for line in fh:
            mh = HDR.search(line)
            if mh:
                size_bytes[mh.group(1)] = int(mh.group(2))
                size_nodes[mh.group(1)] = int(mh.group(3))
                continue
            mr = ROW.search(line)
            if not mr:
                continue
            tool, size, red, rep = (
                mr.group(1),
                mr.group(2),
                mr.group(3),
                int(mr.group(4)),
            )
            key = (tool, size, red, rep)
            if key in seen:  # dedup (every line printed twice)
                continue
            seen[key] = True
            commit, restore = float(mr.group(5)), float(mr.group(6))
            store, rss = int(mr.group(7)), int(mr.group(8))
            ok, oom = int(mr.group(9)), int(mr.group(10))
            rows.append(
                {
                    "tool": tool,
                    "size_bytes": size_bytes[size],
                    "redundancy": red,
                    "n_nodes": size_nodes[size],
                    "rep": rep,
                    "phase_commit_s": round(commit, 4),
                    "phase_restore_s": round(restore, 4),
                    "store_bytes": store,
                    "peak_rss_kb": rss,
                    "round_trip_ok": ok,
                    "oomed": oom,
                    "skipped_reason": OOM_REASON if oom == 1 else "",
                    "_size": size,
                }
            )

    # ---- capped rows (no fabricated numbers) ----
    gb = size_bytes["5GB"]
    gb_nodes = size_nodes["5GB"]  # 2

    def skip(tool, red, reason, rep):
        rows.append(
            {
                "tool": tool,
                "size_bytes": gb,
                "redundancy": red,
                "n_nodes": gb_nodes,
                "rep": rep,
                "phase_commit_s": "",
                "phase_restore_s": "",
                "store_bytes": "",
                "peak_rss_kb": "",
                "round_trip_ok": "",
                "oomed": "",
                "skipped_reason": reason,
                "_size": "5GB",
            }
        )

    # 5GB/low + 5GB/med: design-capped, all tools, all 6 reps.
    for red in ("low", "med"):
        for tool in TOOLS:
            for rep in range(6):
                skip(tool, red, DESIGN_CAP, rep)
    # 5GB/high tar_czf: 0 reps ran (killed) -> all 6 reps wall-clock-capped.
    for rep in range(6):
        skip("tar_czf", "high", WALLCLOCK_CAP, rep)
    # 5GB/high cp_r: reps 0-1 ran (kept above); reps 2-5 wall-clock-capped.
    for rep in range(2, 6):
        skip("cp_r", "high", WALLCLOCK_CAP, rep)

    rows.sort(
        key=lambda r: (
            SIZE_ORDER[r["_size"]],
            RED_ORDER[r["redundancy"]],
            TOOL_ORDER[r["tool"]],
            int(r["rep"]),
        )
    )
    for r in rows:
        del r["_size"]

    results_path = os.path.join(OUT_DIR, "results.csv")
    with open(results_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=bench.RESULTS_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # ---- summary (completed, rep>=1); drop under-sampled/capped cells (n_reps<5) ----
    completed = [r for r in rows if not r["skipped_reason"] and int(r["rep"]) >= 1]
    summ = bench.add_helios_tar_ratios(bench.summarize(completed))
    summ = [s for s in summ if s["n_reps"] >= 5]
    summ_fields = [
        "tool",
        "size_bytes",
        "redundancy",
        "n_reps",
        "commit_s_median",
        "commit_s_p90",
        "restore_s_median",
        "restore_s_p90",
        "store_bytes_median",
        "peak_rss_kb_median",
        "round_trip_ok",
        "oomed",
        "helios_over_tar_store",
        "helios_over_tar_commit",
    ]
    summary_path = os.path.join(OUT_DIR, "summary.csv")
    with open(summary_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=summ_fields)
        w.writeheader()
        for s in sorted(
            summ, key=lambda x: (x["size_bytes"], RED_ORDER[x["redundancy"]], x["tool"])
        ):
            w.writerow({k: s.get(k, "") for k in summ_fields})

    print(f"wrote {results_path} ({len(rows)} rows)")
    print(f"wrote {summary_path} ({len(summ)} cells)")
    # crossover recompute for verdict authoring
    import check_verdict

    xs, xr = check_verdict.recompute_crossover(
        [dict(r) for r in csv.DictReader(open(summary_path))]
    )
    print(f"RECOMPUTED_CROSSOVER size={xs} red={xr}")


if __name__ == "__main__":
    main()
