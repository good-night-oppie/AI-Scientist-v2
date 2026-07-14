"""Independent grid-coverage + concurrency checker for the Phase 8 evidence.

Default: validate ``results.csv`` (and sibling ``summary.csv`` /
``dedup_granularity.txt``) -- full tool x size x redundancy coverage, >=5 usable
reps per completed cell (rep 0 discarded), non-null peak RSS, round-trip integrity,
p90 columns, and the measured dedup-granularity delta supporting its verdict line.

``--concurrency <csv>``: validate the concurrent-writer predicate (AC7).

Exits 0 iff every assertion holds; prints ``FAIL: ...`` and exits 1 otherwise.
"""

from __future__ import annotations

import argparse
import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_corpus import parse_size  # noqa: E402

TOOLS = ["helios", "cp_r", "tar_czf"]
SIZES = ["5MB", "50MB", "500MB", "5GB"]
REDS = ["low", "med", "high"]
MIN_REPS = 5


def load_csv(path):
    with open(path) as fh:
        return list(csv.DictReader(fh))


def check_results(results_path, fails):
    rows = load_csv(results_path)
    {str(parse_size(s)): s for s in SIZES}
    # index by (tool, size_bytes, red)
    by_cell = {}
    for r in rows:
        key = (r["tool"], r["size_bytes"], r["redundancy"])
        by_cell.setdefault(key, []).append(r)

    for tool in TOOLS:
        for s in SIZES:
            sb = str(parse_size(s))
            for red in REDS:
                key = (tool, sb, red)
                cell = by_cell.get(key, [])
                if not cell:
                    fails.append(f"missing cell {tool}/{s}/{red} (no rows, no skip)")
                    continue
                skipped = [r for r in cell if r.get("skipped_reason")]
                completed = [r for r in cell if not r.get("skipped_reason")]
                usable = [r for r in completed if int(r["rep"]) >= 1]
                if skipped:
                    continue  # a non-empty skipped_reason satisfies coverage
                if len(usable) < MIN_REPS:
                    fails.append(
                        f"cell {tool}/{s}/{red}: {len(usable)} usable reps < {MIN_REPS} "
                        "and no skipped_reason"
                    )
                    continue
                if not any(int(r["rep"]) == 0 for r in completed):
                    fails.append(f"cell {tool}/{s}/{red}: no rep 0 (warm-up) present")
                for r in completed:
                    if r["peak_rss_kb"] in ("", None):
                        fails.append(
                            f"cell {tool}/{s}/{red} rep{r['rep']}: null peak_rss_kb"
                        )
                    if str(r["round_trip_ok"]) != "1":
                        fails.append(
                            f"cell {tool}/{s}/{red} rep{r['rep']}: round_trip_ok="
                            f"{r['round_trip_ok']} (integrity fail / disqualified)"
                        )
    return rows


def check_summary(summary_path, fails):
    if not os.path.exists(summary_path):
        fails.append(f"missing summary.csv at {summary_path}")
        return
    rows = load_csv(summary_path)
    need = ["commit_s_median", "commit_s_p90", "restore_s_median", "restore_s_p90"]
    for r in rows:
        try:
            nreps = int(r["n_reps"])
        except (ValueError, KeyError):
            fails.append(
                f"summary cell {r.get('tool')}/{r.get('size_bytes')}: bad n_reps"
            )
            continue
        if nreps < MIN_REPS:
            fails.append(
                f"summary cell {r['tool']}/{r['size_bytes']}/{r['redundancy']}: "
                f"n_reps={nreps} < {MIN_REPS}"
            )
        for col in need:
            if r.get(col) in ("", None):
                fails.append(
                    f"summary cell {r['tool']}/{r['size_bytes']}/{r['redundancy']}: "
                    f"missing {col}"
                )


def check_dedup(dedup_path, fails):
    if not os.path.exists(dedup_path):
        fails.append(f"missing dedup_granularity.txt at {dedup_path}")
        return
    txt = open(dedup_path).read()
    gran = None
    delta = filesize = None
    for line in txt.splitlines():
        line = line.strip()
        if line.startswith("GRANULARITY="):
            gran = line.split("=", 1)[1].strip()
        elif line.startswith("DELTA_BYTES="):
            delta = int(line.split("=", 1)[1])
        elif line.startswith("FILESIZE_BYTES="):
            filesize = int(line.split("=", 1)[1])
    if gran not in ("whole-file", "sub-file"):
        fails.append(
            f"dedup_granularity.txt: GRANULARITY={gran!r} not in whole-file|sub-file"
        )
        return
    if delta is None or filesize is None:
        fails.append("dedup_granularity.txt: missing DELTA_BYTES/FILESIZE_BYTES")
        return
    # Numeric support: whole-file => delta >= 0.9*filesize; sub-file => delta <= 0.1*filesize.
    if gran == "whole-file" and delta < 0.9 * filesize:
        fails.append(
            f"dedup: GRANULARITY=whole-file but delta {delta} < 0.9*{filesize}"
        )
    if gran == "sub-file" and delta > 0.1 * filesize:
        fails.append(f"dedup: GRANULARITY=sub-file but delta {delta} > 0.1*{filesize}")


def check_concurrency(cc_path, fails):
    rows = load_csv(cc_path)
    ks = {1, 2, 4, 8}
    configs = {"helios+flock", "helios-flock", "tar"}
    present = {(r["config"], int(r["K"])) for r in rows}
    for c in configs:
        for k in ks:
            if (c, k) not in present:
                fails.append(f"concurrency: missing row config={c} K={k}")
    # helios-flock must fail (>=1) at some K>=2
    raw_fail = any(
        r["config"] == "helios-flock"
        and int(r["K"]) >= 2
        and int(r["commits_failed"]) >= 1
        for r in rows
    )
    if not raw_fail:
        fails.append(
            "concurrency: helios-flock never records commits_failed>=1 at K>=2 "
            "(flock would not be load-bearing)"
        )
    # helios+flock must be 0 failures at every K
    for r in rows:
        if r["config"] == "helios+flock" and int(r["commits_failed"]) != 0:
            fails.append(
                f"concurrency: helios+flock K={r['K']} commits_failed="
                f"{r['commits_failed']} (expected 0)"
            )


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "results", help="results.csv (or concurrency.csv with --concurrency)"
    )
    ap.add_argument("--concurrency", action="store_true")
    ap.add_argument("--summary", default=None)
    ap.add_argument("--dedup", default=None)
    args = ap.parse_args(argv)

    fails = []
    if args.concurrency:
        check_concurrency(args.results, fails)
    else:
        check_results(args.results, fails)
        d = os.path.dirname(os.path.abspath(args.results))
        check_summary(args.summary or os.path.join(d, "summary.csv"), fails)
        check_dedup(args.dedup or os.path.join(d, "dedup_granularity.txt"), fails)

    if fails:
        for f in fails:
            print(f"FAIL: {f}")
        print(f"check_grid: {len(fails)} failure(s)")
        return 1
    print("check_grid: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
