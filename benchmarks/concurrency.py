"""Concurrent-writer scaling with REAL processes (never threads).

BFTS workers are separate processes that fork (constraint 4/9), so a
``threading.Lock``/shared fd would mis-model Pebble's single-writer contention.
For K in {1,2,4,8} we spawn K OS processes that each commit a distinct node dir
into ONE shared store, under three configs:

  * ``helios+flock``  -- the shipped Phase-2 wrapper (fcntl.flock serialises the
    cold worker processes). Predicate: 0 failures at every K.
  * ``helios-flock``  -- raw CLI, no serialisation. Predicate: >=1
    ``resource temporarily unavailable`` exit-1 failure at some K>=2 (Pebble's
    exclusive OS lock, objstore.go:62) -- proving the flock is load-bearing.
  * ``tar``           -- K parallel ``tar -czf``, embarrassingly parallel.

Each worker is this module re-invoked with ``--worker`` (a real subprocess), so
the contention is genuine cross-process contention.
"""

from __future__ import annotations

import argparse
import csv
import os
import subprocess
import sys
import time

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, REPO_ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from gen_corpus import det_bytes  # noqa: E402

KS = [1, 2, 4, 8]
CONFIGS = ["helios+flock", "helios-flock", "tar"]


def _make_node(path, seed, size_bytes):
    os.makedirs(path, exist_ok=True)
    with open(os.path.join(path, "experiment_data.npy"), "wb") as fh:
        fh.write(det_bytes(seed, size_bytes))


def worker_helios_flock(helios_bin, store_dir, work_dir, lock_path):
    from ai_scientist.treesearch.helios_store import HeliosStore

    store = HeliosStore(helios_bin, store_dir, lock_path=lock_path)
    store.snapshot(work_dir)


def worker_helios_raw(helios_bin, store_dir, work_dir):
    env = dict(os.environ)
    env["HELIOS_STORE_DIR"] = store_dir
    cp = subprocess.run(
        [helios_bin, "commit", "--work", work_dir],
        capture_output=True,
        text=True,
        env=env,
    )
    if cp.returncode != 0:
        sys.stderr.write(cp.stderr)
        raise SystemExit(1)


def worker_tar(work_dir, out_tgz):
    cp = subprocess.run(["tar", "-czf", out_tgz, "-C", work_dir, "."])
    if cp.returncode != 0:
        raise SystemExit(1)


def run_config(config, K, helios_bin, scratch, size_bytes, seed):
    """Spawn K real worker processes for one (config, K) and tally ok/failed + wall."""
    store_dir = os.path.join(scratch, f"cc_store_{config.replace('+', '_')}_{K}")
    lock_path = store_dir.rstrip("/") + ".flock"
    for p in (store_dir,):
        if os.path.isdir(p):
            import shutil

            shutil.rmtree(p)
    os.makedirs(store_dir, exist_ok=True)
    nodes = []
    for i in range(K):
        nd = os.path.join(scratch, f"cc_node_{config.replace('+', '_')}_{K}_{i}")
        import shutil

        if os.path.isdir(nd):
            shutil.rmtree(nd)
        _make_node(nd, f"{seed}:cc:{config}:{K}:{i}", size_bytes)
        nodes.append(nd)

    procs = []
    t0 = time.time()
    for i, nd in enumerate(nodes):
        if config == "helios+flock":
            argv = [
                sys.executable,
                __file__,
                "--worker",
                "helios_flock",
                "--helios-bin",
                helios_bin,
                "--store",
                store_dir,
                "--work",
                nd,
                "--lock",
                lock_path,
            ]
        elif config == "helios-flock":
            argv = [
                sys.executable,
                __file__,
                "--worker",
                "helios_raw",
                "--helios-bin",
                helios_bin,
                "--store",
                store_dir,
                "--work",
                nd,
            ]
        else:
            argv = [
                sys.executable,
                __file__,
                "--worker",
                "tar",
                "--work",
                nd,
                "--out",
                os.path.join(store_dir, f"n{i}.tgz"),
            ]
        procs.append(subprocess.Popen(argv))
    ok = failed = 0
    for p in procs:
        rc = p.wait()
        if rc == 0:
            ok += 1
        else:
            failed += 1
    wall = time.time() - t0
    import shutil

    shutil.rmtree(store_dir, ignore_errors=True)
    for nd in nodes:
        shutil.rmtree(nd, ignore_errors=True)
    throughput = ok / wall if wall > 0 else 0.0
    return {
        "config": config,
        "K": K,
        "wall_s": round(wall, 4),
        "commits_ok": ok,
        "commits_failed": failed,
        "throughput_cps": round(throughput, 4),
    }


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--worker", choices=["helios_flock", "helios_raw", "tar"])
    ap.add_argument("--helios-bin")
    ap.add_argument("--store")
    ap.add_argument("--work")
    ap.add_argument("--lock")
    ap.add_argument("--out")
    ap.add_argument("--scratch")
    ap.add_argument("--out-csv")
    ap.add_argument("--size", default="8MB")
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args(argv)

    if args.worker:
        if args.worker == "helios_flock":
            worker_helios_flock(args.helios_bin, args.store, args.work, args.lock)
        elif args.worker == "helios_raw":
            worker_helios_raw(args.helios_bin, args.store, args.work)
        else:
            worker_tar(args.work, args.out)
        return 0

    from gen_corpus import parse_size

    size_bytes = parse_size(args.size)
    rows = []
    for config in CONFIGS:
        for K in KS:
            row = run_config(
                config, K, args.helios_bin, args.scratch, size_bytes, args.seed
            )
            rows.append(row)
            print(
                f"[cc] {config} K={K}: wall={row['wall_s']}s ok={row['commits_ok']} "
                f"failed={row['commits_failed']} tput={row['throughput_cps']}",
                flush=True,
            )

    fields = ["config", "K", "wall_s", "commits_ok", "commits_failed", "throughput_cps"]
    with open(args.out_csv, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    print(f"[cc] wrote {args.out_csv} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
