"""Phase 8 sweep driver: helios vs ``cp -r`` vs ``tar -czf`` across size x redundancy.

For each (tool, size, redundancy) cell we run >=6 reps (rep 0 discarded as a
page-cache warm-up). Each rep uses a FRESH store/dest so ``store_bytes`` (measured
with ``du -sb`` -- NEVER helios ``stats``, which returns zeros) reflects exactly one
tree's footprint, and dedup across reps cannot inflate/deflate the number.

Store phase == commit; restore phase == materialize/copy-back/extract into a FRESH
EMPTY dir; then an sha256 round-trip integrity gate. helios uses
``materialize --id X --out <fresh empty dir>`` exclusively (never ``restore``, which
merges and never deletes). Large arms (size >= --docker-threshold) route the helios
commit/materialize through ``docker run --rm -m`` so an OOM kills only the container
(recorded ``oomed=1`` -- a legitimate measured result, not a harness crash).
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import statistics
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bench_time  # noqa: E402
from gen_corpus import gen_corpus, measured_redundancy, parse_size, sha256_tree  # noqa: E402

RESULTS_FIELDS = [
    "tool",
    "size_bytes",
    "redundancy",
    "n_nodes",
    "rep",
    "phase_commit_s",
    "phase_restore_s",
    "store_bytes",
    "peak_rss_kb",
    "round_trip_ok",
    "oomed",
    "skipped_reason",
]

TOOLS = ["helios", "cp_r", "tar_czf"]
REDUNDANCIES = ["low", "med", "high"]


def du_sb(path: str) -> int:
    out = subprocess.run(["du", "-sb", path], capture_output=True, text=True)
    if out.returncode != 0:
        return 0
    return int(out.stdout.split()[0])


def _log(logf, msg):
    line = f"[bench] {msg}"
    print(line, flush=True)
    if logf:
        logf.write(line + "\n")
        logf.flush()


# --------------------------------------------------------------------------- helios


def run_helios_cell(
    nodes, store_dir, helios_bin, engine, docker_mem, docker_image, scratch
):
    """Commit every node into ONE fresh store, then materialize each into a fresh dir.

    Returns (commit_s, restore_s, store_bytes, peak_rss_kb, round_trip_ok, oomed).
    """
    if os.path.isdir(store_dir):
        shutil.rmtree(store_dir)
    os.makedirs(store_dir, exist_ok=True)
    commit_total = 0.0
    peak = 0
    oomed = 0
    sids = []
    for nd in nodes:
        if engine == "docker":
            cont_work = "/work_" + os.path.basename(nd)
            res = bench_time.docker_helios(
                helios_bin,
                store_dir,
                ["commit", "--work", cont_work],
                image=docker_image,
                mem=docker_mem,
                extra_mounts=[(nd, cont_work, True)],
            )
        else:
            res = bench_time.run_native(
                [helios_bin, "commit", "--work", nd],
                env={"HELIOS_STORE_DIR": store_dir},
                capture=True,
            )
        commit_total += res.wall_s
        peak = max(peak, res.peak_rss_kb)
        oomed = oomed or res.oomed
        if res.oomed or res.exit_code != 0:
            return commit_total, 0.0, du_sb(store_dir), peak, 0, 1 if res.oomed else 0
        try:
            sid = json.loads(res.stdout.strip().splitlines()[-1])["snapshot_id"]
        except Exception:
            return commit_total, 0.0, du_sb(store_dir), peak, 0, oomed
        sids.append(sid)
    subprocess.run(["sync"])
    store_bytes = du_sb(store_dir)

    # restore phase: materialize each snapshot into a FRESH EMPTY dir, integrity-check.
    restore_total = 0.0
    ok = 1
    for nd, sid in zip(nodes, sids):
        out = os.path.join(scratch, "mat_" + os.path.basename(nd))
        if os.path.isdir(out):
            shutil.rmtree(out)
        # Create the FRESH EMPTY out dir on the HOST *before* docker mounts it, so it is
        # host-owned and the --user helios process inside the container can write to it
        # (docker auto-creating an absent mount source would make it root-owned).
        os.makedirs(out, exist_ok=True)
        if engine == "docker":
            cont_out = "/mat_" + os.path.basename(nd)
            res = bench_time.docker_helios(
                helios_bin,
                store_dir,
                ["materialize", "--id", sid, "--out", cont_out],
                image=docker_image,
                mem=docker_mem,
                extra_mounts=[(out, cont_out, False)],
            )
        else:
            res = bench_time.run_native(
                [helios_bin, "materialize", "--id", sid, "--out", out],
                env={"HELIOS_STORE_DIR": store_dir},
                capture=True,
            )
        restore_total += res.wall_s
        peak = max(peak, res.peak_rss_kb)
        if res.exit_code != 0 or sha256_tree(out) != sha256_tree(nd):
            ok = 0
        shutil.rmtree(out, ignore_errors=True)
    shutil.rmtree(store_dir, ignore_errors=True)
    return commit_total, restore_total, store_bytes, peak, ok, oomed


# ----------------------------------------------------------------------------- cp -r


def run_cp_cell(nodes, dest_dir, scratch):
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    commit_total = 0.0
    peak = 0
    for nd in nodes:
        d = os.path.join(dest_dir, os.path.basename(nd))
        res = bench_time.run_native(["cp", "-r", nd, d])
        commit_total += res.wall_s
        peak = max(peak, res.peak_rss_kb)
    subprocess.run(["sync"])
    store_bytes = du_sb(dest_dir)
    restore_total = 0.0
    ok = 1
    for nd in nodes:
        src = os.path.join(dest_dir, os.path.basename(nd))
        back = os.path.join(scratch, "cpback_" + os.path.basename(nd))
        if os.path.isdir(back):
            shutil.rmtree(back)
        res = bench_time.run_native(["cp", "-r", src, back])
        restore_total += res.wall_s
        peak = max(peak, res.peak_rss_kb)
        if res.exit_code != 0 or sha256_tree(back) != sha256_tree(nd):
            ok = 0
        shutil.rmtree(back, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)
    return commit_total, restore_total, store_bytes, peak, ok, 0


# --------------------------------------------------------------------------- tar -czf


def run_tar_cell(nodes, dest_dir, scratch):
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    commit_total = 0.0
    peak = 0
    tgzs = []
    for nd in nodes:
        tgz = os.path.join(dest_dir, os.path.basename(nd) + ".tgz")
        res = bench_time.run_native(["tar", "-czf", tgz, "-C", nd, "."])
        commit_total += res.wall_s
        peak = max(peak, res.peak_rss_kb)
        tgzs.append(tgz)
    subprocess.run(["sync"])
    store_bytes = sum(os.path.getsize(t) for t in tgzs)
    restore_total = 0.0
    ok = 1
    for nd, tgz in zip(nodes, tgzs):
        out = os.path.join(scratch, "tarx_" + os.path.basename(nd))
        if os.path.isdir(out):
            shutil.rmtree(out)
        os.makedirs(out, exist_ok=True)
        res = bench_time.run_native(["tar", "-xzf", tgz, "-C", out])
        restore_total += res.wall_s
        peak = max(peak, res.peak_rss_kb)
        if res.exit_code != 0 or sha256_tree(out) != sha256_tree(nd):
            ok = 0
        shutil.rmtree(out, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)
    return commit_total, restore_total, store_bytes, peak, ok, 0


# ----------------------------------------------------------------------------- driver


def p90(vals):
    if not vals:
        return ""
    s = sorted(vals)
    idx = min(len(s) - 1, int(round(0.9 * (len(s) - 1))))
    return s[idx]


def summarize(rows):
    """Group completed rep rows into per-cell median/p90 summary dicts."""
    cells = {}
    for r in rows:
        if r["skipped_reason"]:
            continue
        key = (r["tool"], r["size_bytes"], r["redundancy"])
        cells.setdefault(key, []).append(r)
    summ = []
    for (tool, size, red), rs in cells.items():
        commits = [float(r["phase_commit_s"]) for r in rs]
        restores = [float(r["phase_restore_s"]) for r in rs]
        store = [int(r["store_bytes"]) for r in rs]
        rss = [int(r["peak_rss_kb"]) for r in rs if r["peak_rss_kb"] not in ("", None)]
        summ.append(
            {
                "tool": tool,
                "size_bytes": size,
                "redundancy": red,
                "n_reps": len(rs),
                "commit_s_median": round(statistics.median(commits), 4),
                "commit_s_p90": round(float(p90(commits)), 4),
                "restore_s_median": round(statistics.median(restores), 4),
                "restore_s_p90": round(float(p90(restores)), 4),
                "store_bytes_median": int(statistics.median(store)),
                "peak_rss_kb_median": int(statistics.median(rss)) if rss else "",
                "round_trip_ok": min(int(r["round_trip_ok"]) for r in rs),
                "oomed": max(int(r["oomed"]) for r in rs),
            }
        )
    return summ


def add_helios_tar_ratios(summ):
    """Add helios/tar store_bytes and commit_s ratios keyed by (size, redundancy)."""
    tar = {
        (s["size_bytes"], s["redundancy"]): s for s in summ if s["tool"] == "tar_czf"
    }
    for s in summ:
        key = (s["size_bytes"], s["redundancy"])
        t = tar.get(key)
        if s["tool"] == "helios" and t and t["store_bytes_median"]:
            s["helios_over_tar_store"] = round(
                s["store_bytes_median"] / t["store_bytes_median"], 4
            )
            if t["commit_s_median"]:
                s["helios_over_tar_commit"] = round(
                    s["commit_s_median"] / t["commit_s_median"], 4
                )
    return summ


def default_grid():
    """Per-size execution plan; caps are LOGGED, never silently applied."""
    return {
        "5MB": {
            "nodes": 6,
            "reps": 6,
            "engine": "native",
            "redundancies": REDUNDANCIES,
        },
        "50MB": {
            "nodes": 6,
            "reps": 6,
            "engine": "native",
            "redundancies": REDUNDANCIES,
        },
        "500MB": {
            "nodes": 3,
            "reps": 6,
            "engine": "docker",
            "redundancies": REDUNDANCIES,
        },
        "5GB": {
            "nodes": 2,
            "reps": 6,
            "engine": "docker",
            "redundancies": ["high"],  # sampled: high only (capped; see run.log)
            "capped": "low,med dropped at 5GB (wall-clock/disk); high-redundancy sampled",
        },
    }


def smoke_grid():
    return {
        "5MB": {
            "nodes": 3,
            "reps": 6,
            "engine": "native",
            "redundancies": REDUNDANCIES,
        },
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--grid", default="full", choices=["full", "smoke"])
    ap.add_argument("--helios-bin", required=True)
    ap.add_argument("--scratch", required=True)
    ap.add_argument(
        "--native-cap-bytes",
        type=int,
        required=True,
        help="0.5 x MemAvailable single-file native ceiling (from run_bench.sh)",
    )
    ap.add_argument("--docker-mem", default="6g")
    ap.add_argument("--docker-image", default="debian:stable-slim")
    ap.add_argument(
        "--no-docker",
        action="store_true",
        help="force native even for large arms (unsafe; test only)",
    )
    ap.add_argument("--logfile", default=None)
    args = ap.parse_args(argv)

    os.makedirs(args.out, exist_ok=True)
    os.makedirs(args.scratch, exist_ok=True)
    logf = open(args.logfile, "a") if args.logfile else None

    grid = smoke_grid() if args.grid == "smoke" else default_grid()
    all_sizes = list(grid.keys())
    rows = []

    for size_str in all_sizes:
        cfg = grid[size_str]
        size_bytes = parse_size(size_str)
        n_nodes = cfg["nodes"]
        reps = cfg["reps"]
        engine = cfg["engine"]
        # Largest single file this corpus will produce (<=128MB unless single-huge).
        from gen_corpus import MAX_FILE_BYTES

        largest_file = min(size_bytes, MAX_FILE_BYTES)
        # MemAvailable-based native single-file guard (0.5 x MemAvailable).
        if (
            engine == "native"
            and largest_file > args.native_cap_bytes
            and not args.no_docker
        ):
            _log(
                logf,
                f"{size_str}: largest file {largest_file} > native cap "
                f"{args.native_cap_bytes} -> re-dispatch to docker",
            )
            engine = "docker"
        if engine == "docker" and args.no_docker:
            engine = "native"
        _log(
            logf,
            f"=== size={size_str} bytes={size_bytes} nodes={n_nodes} reps={reps} "
            f"engine={engine} redundancies={cfg['redundancies']} ===",
        )
        if cfg.get("capped"):
            _log(logf, f"CAP[{size_str}]: {cfg['capped']}")

        for red in REDUNDANCIES:
            if red not in cfg["redundancies"]:
                # Emit a skipped_reason row per tool so the grid stays covered.
                reason = cfg.get("capped", "capped")
                for tool in TOOLS:
                    rows.append(_skip_row(tool, size_bytes, red, n_nodes, reason))
                _log(logf, f"SKIP size={size_str} red={red}: {reason}")
                continue

            # Generate the corpus ONCE per (size,redundancy) cell; reuse across reps+tools.
            corpus = os.path.join(args.scratch, f"corpus_{size_str}_{red}")
            if os.path.isdir(corpus):
                shutil.rmtree(corpus)
            gen_corpus(size_bytes, red, n_nodes, args.seed, corpus)
            meas = measured_redundancy(corpus, n_nodes)
            _log(
                logf,
                f"corpus {size_str}/{red}: measured_redundancy={meas:.4f} "
                f"(target {red}) nodes={n_nodes}",
            )
            nodes = [os.path.join(corpus, f"node_{i:03d}") for i in range(n_nodes)]

            for tool in TOOLS:
                for rep in range(reps):
                    subprocess.run(["sync"])
                    store_dir = os.path.join(
                        args.scratch, f"store_{size_str}_{red}_{tool}"
                    )
                    try:
                        if tool == "helios":
                            c, r_, sb, rss, ok, oom = run_helios_cell(
                                nodes,
                                store_dir,
                                args.helios_bin,
                                engine,
                                args.docker_mem,
                                args.docker_image,
                                args.scratch,
                            )
                        elif tool == "cp_r":
                            c, r_, sb, rss, ok, oom = run_cp_cell(
                                nodes, store_dir, args.scratch
                            )
                        else:
                            c, r_, sb, rss, ok, oom = run_tar_cell(
                                nodes, store_dir, args.scratch
                            )
                    except Exception as e:  # pragma: no cover
                        _log(logf, f"ERROR {tool} {size_str}/{red} rep{rep}: {e}")
                        rows.append(
                            _skip_row(tool, size_bytes, red, n_nodes, f"error:{e}")
                        )
                        continue
                    # An in-container OOM is RECORDED DATA (the cli.go:118 whole-file
                    # RAM ceiling), not an integrity failure: tag it skipped_reason so
                    # it is exempt from the round_trip_ok=1 gate while its oomed=1 /
                    # peak_rss_kb evidence stays in the row.
                    skip_reason = ""
                    if oom:
                        skip_reason = (
                            "oomed: helios whole-file-into-RAM ceiling "
                            "(cli.go:118); docker -m 6g OOM at this size"
                        )
                    rows.append(
                        {
                            "tool": tool,
                            "size_bytes": size_bytes,
                            "redundancy": red,
                            "n_nodes": n_nodes,
                            "rep": rep,
                            "phase_commit_s": round(c, 4),
                            "phase_restore_s": round(r_, 4),
                            "store_bytes": sb,
                            "peak_rss_kb": rss,
                            "round_trip_ok": ok,
                            "oomed": oom,
                            "skipped_reason": skip_reason,
                        }
                    )
                    _log(
                        logf,
                        f"{tool} {size_str}/{red} rep{rep}: commit={c:.2f}s "
                        f"restore={r_:.2f}s store={sb} rss={rss}kb ok={ok} oom={oom}",
                    )
            shutil.rmtree(corpus, ignore_errors=True)

    # Write results.csv (raw, includes rep 0) and summary.csv (rep>=1 only).
    results_path = os.path.join(args.out, "results.csv")
    with open(results_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=RESULTS_FIELDS)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    completed = [r for r in rows if not r["skipped_reason"] and int(r["rep"]) >= 1]
    summ = add_helios_tar_ratios(summarize(completed))
    summary_path = os.path.join(args.out, "summary.csv")
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
    with open(summary_path, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=summ_fields)
        w.writeheader()
        for s in sorted(
            summ, key=lambda x: (x["size_bytes"], x["redundancy"], x["tool"])
        ):
            w.writerow({k: s.get(k, "") for k in summ_fields})

    _log(
        logf,
        f"wrote {results_path} ({len(rows)} rows) and {summary_path} ({len(summ)} cells)",
    )
    if logf:
        logf.close()
    return 0


def _skip_row(tool, size_bytes, red, n_nodes, reason):
    return {
        "tool": tool,
        "size_bytes": size_bytes,
        "redundancy": red,
        "n_nodes": n_nodes,
        "rep": 0,
        "phase_commit_s": "",
        "phase_restore_s": "",
        "store_bytes": "",
        "peak_rss_kb": "",
        "round_trip_ok": "",
        "oomed": "",
        "skipped_reason": reason,
    }


if __name__ == "__main__":
    raise SystemExit(main())
