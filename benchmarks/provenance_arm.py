"""AC13 -- the "why helios at all" skeptic gate.

The integration's NON-speed justification (Phases 5-6) is durable recovery of a
buggy node's post-exec dir. A 3-line ``tar -czf node.tgz -C working .`` +
``sha256sum`` delivers the same recovery with zero helios dependency. This arm
measures, at the realistic anchor size read from ``.supergoal/evidence/M5/``,
whether helios adds provenance value over tar+hash.

Two scenarios are recorded so the verdict can be grounded honestly:

  * ``single_node``  -- ONE anchor-sized buggy node recovered byte-for-byte by
    each tool. This is the actual Phases 5-6 justification. tar+hash matches
    helios here => the provenance feature alone does not justify the dependency.
  * ``multinode_high_redundancy`` -- a 6-node anchor-sized tree at high cross-node
    redundancy, the ONE regime where helios's dedup can beat tar on store_bytes.
    Recorded for transparency: any advantage here is the DEDUP regime already
    credited by the crossover verdict, not provenance per se.

Both tools must recover byte-identically (``recovered_ok=1``) or the arm is
invalid. A YES verdict requires a named, measured >=2x helios advantage in a
specific column; NO (tar+hash matches on single-node provenance) is the
sanctioned honest outcome.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import shutil
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bench_time  # noqa: E402
from gen_corpus import gen_corpus, sha256_tree  # noqa: E402


def read_anchor_bytes(m5_dir: str) -> int:
    """Read ANCHOR_BYTES from the M5 per-node-dir-size evidence file."""
    path = os.path.join(m5_dir, "per-node-dir-size.txt")
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if line.startswith("ANCHOR_BYTES="):
                return int(line.split("=", 1)[1])
    raise SystemExit(f"ANCHOR_BYTES not found in {path}")


def du_sb(path: str) -> int:
    out = subprocess.run(["du", "-sb", path], capture_output=True, text=True)
    return int(out.stdout.split()[0]) if out.returncode == 0 else 0


def helios_scenario(nodes, helios_bin, store_dir, scratch):
    if os.path.isdir(store_dir):
        shutil.rmtree(store_dir)
    os.makedirs(store_dir, exist_ok=True)
    commit_s = restore_s = 0.0
    sids = []
    ok = 1
    for nd in nodes:
        res = bench_time.run_native(
            [helios_bin, "commit", "--work", nd],
            env={"HELIOS_STORE_DIR": store_dir},
            capture=True,
        )
        commit_s += res.wall_s
        if res.exit_code != 0:
            return 0, du_sb(store_dir), commit_s, restore_s
        sids.append(json.loads(res.stdout.strip().splitlines()[-1])["snapshot_id"])
    subprocess.run(["sync"])
    store_bytes = du_sb(store_dir)
    for nd, sid in zip(nodes, sids):
        out = os.path.join(scratch, "hmat_" + os.path.basename(nd))
        if os.path.isdir(out):
            shutil.rmtree(out)
        os.makedirs(out, exist_ok=True)
        res = bench_time.run_native(
            [helios_bin, "materialize", "--id", sid, "--out", out],
            env={"HELIOS_STORE_DIR": store_dir},
            capture=True,
        )
        restore_s += res.wall_s
        if res.exit_code != 0 or sha256_tree(out) != sha256_tree(nd):
            ok = 0
        shutil.rmtree(out, ignore_errors=True)
    shutil.rmtree(store_dir, ignore_errors=True)
    return ok, store_bytes, commit_s, restore_s


def tar_hash_scenario(nodes, dest_dir, scratch):
    """tar -czf + sha256sum manifest; recover via tar -xzf and verify hashes."""
    if os.path.isdir(dest_dir):
        shutil.rmtree(dest_dir)
    os.makedirs(dest_dir, exist_ok=True)
    commit_s = restore_s = 0.0
    tgzs = []
    ok = 1
    for nd in nodes:
        tgz = os.path.join(dest_dir, os.path.basename(nd) + ".tgz")
        # commit == archive + record sha256 manifest (the tar+hash provenance recipe)
        res = bench_time.run_native(["tar", "-czf", tgz, "-C", nd, "."])
        commit_s += res.wall_s
        manifest = sha256_tree(nd)
        with open(tgz + ".sha256", "w") as fh:
            json.dump(manifest, fh)
        tgzs.append((nd, tgz))
    subprocess.run(["sync"])
    store_bytes = sum(
        os.path.getsize(t) + os.path.getsize(t + ".sha256") for _, t in tgzs
    )
    for nd, tgz in tgzs:
        out = os.path.join(scratch, "tarx_" + os.path.basename(nd))
        if os.path.isdir(out):
            shutil.rmtree(out)
        os.makedirs(out, exist_ok=True)
        res = bench_time.run_native(["tar", "-xzf", tgz, "-C", out])
        restore_s += res.wall_s
        with open(tgz + ".sha256") as fh:
            recorded = json.load(fh)
        if (
            res.exit_code != 0
            or sha256_tree(out) != recorded
            or sha256_tree(out) != sha256_tree(nd)
        ):
            ok = 0
        shutil.rmtree(out, ignore_errors=True)
    shutil.rmtree(dest_dir, ignore_errors=True)
    return ok, store_bytes, commit_s, restore_s


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--anchor", required=True, help="M5 evidence dir (reads ANCHOR_BYTES)"
    )
    ap.add_argument("--out", required=True, help="provenance.csv output path")
    ap.add_argument("--helios-bin", default=None)
    ap.add_argument("--seed", type=int, default=1234)
    args = ap.parse_args(argv)

    helios_bin = args.helios_bin or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        ".supergoal",
        "bin",
        "helios",
    )
    anchor = read_anchor_bytes(args.anchor)
    scratch = tempfile.mkdtemp(prefix="prov_")
    rows = []
    try:
        # Scenario 1: single anchor-sized buggy node (the Phases 5-6 provenance question).
        c1 = os.path.join(scratch, "single")
        gen_corpus(anchor, "low", 1, args.seed, c1)
        n1 = [os.path.join(c1, "node_000")]
        ok, sb, cs, rs = helios_scenario(
            n1, helios_bin, os.path.join(scratch, "s1"), scratch
        )
        rows.append(
            dict(
                tool="helios",
                scenario="single_node",
                recovered_ok=ok,
                store_bytes=sb,
                commit_s=round(cs, 4),
                restore_s=round(rs, 4),
            )
        )
        ok, sb, cs, rs = tar_hash_scenario(n1, os.path.join(scratch, "t1"), scratch)
        rows.append(
            dict(
                tool="tar_hash",
                scenario="single_node",
                recovered_ok=ok,
                store_bytes=sb,
                commit_s=round(cs, 4),
                restore_s=round(rs, 4),
            )
        )
        shutil.rmtree(c1, ignore_errors=True)

        # Scenario 2: 6-node high-redundancy tree (helios's dedup steelman).
        c2 = os.path.join(scratch, "multi")
        gen_corpus(anchor, "high", 6, args.seed, c2)
        n2 = [os.path.join(c2, f"node_{i:03d}") for i in range(6)]
        ok, sb, cs, rs = helios_scenario(
            n2, helios_bin, os.path.join(scratch, "s2"), scratch
        )
        rows.append(
            dict(
                tool="helios",
                scenario="multinode_high_redundancy",
                recovered_ok=ok,
                store_bytes=sb,
                commit_s=round(cs, 4),
                restore_s=round(rs, 4),
            )
        )
        ok, sb, cs, rs = tar_hash_scenario(n2, os.path.join(scratch, "t2"), scratch)
        rows.append(
            dict(
                tool="tar_hash",
                scenario="multinode_high_redundancy",
                recovered_ok=ok,
                store_bytes=sb,
                commit_s=round(cs, 4),
                restore_s=round(rs, 4),
            )
        )
        shutil.rmtree(c2, ignore_errors=True)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)

    fields = [
        "tool",
        "scenario",
        "recovered_ok",
        "store_bytes",
        "commit_s",
        "restore_s",
    ]
    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        for r in rows:
            w.writerow(r)

    # Report the single-node provenance comparison (the actual justification).
    h = next(
        r for r in rows if r["tool"] == "helios" and r["scenario"] == "single_node"
    )
    t = next(
        r for r in rows if r["tool"] == "tar_hash" and r["scenario"] == "single_node"
    )
    print(f"anchor_bytes={anchor}")
    print(
        f"single_node helios store={h['store_bytes']} tar_hash store={t['store_bytes']} "
        f"ratio_helios_over_tar={h['store_bytes'] / max(1, t['store_bytes']):.3f}"
    )
    hm = next(
        r
        for r in rows
        if r["tool"] == "helios" and r["scenario"] == "multinode_high_redundancy"
    )
    tm = next(
        r
        for r in rows
        if r["tool"] == "tar_hash" and r["scenario"] == "multinode_high_redundancy"
    )
    print(
        f"multinode_high_redundancy helios store={hm['store_bytes']} tar store={tm['store_bytes']} "
        f"tar_over_helios={tm['store_bytes'] / max(1, hm['store_bytes']):.3f}x"
    )
    print(f"wrote {args.out} ({len(rows)} rows)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
