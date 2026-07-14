#!/usr/bin/env python3
"""Deterministic replay harness for the Phase-5 helios write-only snapshot hook.

Drives the REAL production seam --
``ai_scientist.treesearch.helios_store.snapshot_node_working_dir`` -- over a canned tree
of BFTS-like nodes (``tests/replay/fixtures.py``) WITHOUT importing ``parallel_agent`` or
``journal`` (both un-importable on this host: ``humanize`` / ``dataclasses_json``). The
production call-site wiring is proven separately and purely structurally by
``tests/ast_checks/check_seam.py``.

For each fixture node it:
  1. makes a fresh working dir (``mkdtemp``, OUTSIDE the store dir),
  2. really executes the node's canned code there (numpy present, no torch); buggy nodes
     exit non-zero AFTER writing their ``.npy`` -- standing in for a crashed BFTS node,
  3. calls ``snapshot_node_working_dir`` with a duck-typed ``SimpleNamespace`` cfg,
  4. records ``{id, node_type, is_buggy, snapshot_id, npy_sha256}``.

Then it emits (to ``--out``): ``journal.json`` (enabled run), ``journal-flagoff.json``
(disabled run, every id null), ``flagoff-subprocess-count.txt`` (commit calls during the
disabled pass -- must be 0), ``coverage-report.txt`` (100% coverage incl. buggy), and
``materialize-diff.txt`` (a buggy node's ``experiment_data.npy`` reconstructed
byte-for-byte via ``materialize`` -- NEVER ``restore``).

Output uses ``sys.stdout.write`` / file writes only (no ``print`` calls) for cleanliness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
from types import SimpleNamespace

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
for _p in (_REPO_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import fixtures  # noqa: E402  (tests/replay/fixtures.py, added to sys.path above)
from ai_scientist.treesearch import helios_store  # noqa: E402
from ai_scientist.treesearch.helios_store import (  # noqa: E402
    materialize,
    snapshot_node_working_dir,
)

_BLAKE3_RE = re.compile(r"blake3:[0-9a-f]{64}\Z")


def _log(msg: str) -> None:
    sys.stdout.write(msg + "\n")


def _sha256_file(path: str):
    if not os.path.isfile(path):
        return None
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _exec_node(code: str, working_dir: str) -> None:
    """Run a fixture node's canned code in ``working_dir``; ignore its exit status.

    A buggy node exits non-zero on purpose (after writing its ``.npy``); the point of
    the hook is that its files are snapshotted regardless.
    """
    subprocess.run(
        [sys.executable, "-c", code],
        cwd=working_dir,
        capture_output=True,
        text=True,
    )


def _cfg(*, enabled, store_dir, binary, lock_file):
    return SimpleNamespace(
        helios=SimpleNamespace(
            enabled=enabled,
            store_dir=store_dir,
            binary_path=binary,
            lock_file=lock_file,
        )
    )


def _resolve_binary() -> str:
    binary = os.environ.get("HELIOS_CLI_BIN")
    if not binary:
        cand = os.path.join(_REPO_ROOT, ".supergoal", "bin", "helios")
        if os.path.isfile(cand):
            binary = cand
    if not binary or not (os.path.isfile(binary) and os.access(binary, os.X_OK)):
        raise SystemExit(
            "HELIOS_CLI_BIN not set to an executable helios built from HEAD "
            "(never the tracked ./helios-cli); got %r" % binary
        )
    return os.path.abspath(binary)


def _enabled_pass(cfg):
    """Snapshot every node with helios enabled. Returns (records, work_dirs)."""
    records = []
    work_dirs = {}
    for rec in fixtures.FIXTURE_TREE:
        wd = tempfile.mkdtemp(prefix="helios_wd_")  # OUTSIDE the store dir
        _exec_node(rec.code, wd)
        sid = snapshot_node_working_dir(cfg, wd, node_id=rec.id)
        records.append(
            {
                "id": rec.id,
                "node_type": rec.node_type,
                "is_buggy": rec.is_buggy,
                "snapshot_id": sid,
                "npy_sha256": _sha256_file(os.path.join(wd, "experiment_data.npy")),
            }
        )
        work_dirs[rec.id] = wd
    return records, work_dirs


def _flagoff_pass(store_dir, binary, lock_file):
    """Rerun the tree with helios OFF, counting real commit (snapshot) invocations.

    Exercises BOTH disabled shapes: ``cfg.helios = None`` and ``cfg.helios.enabled =
    False``. ``HeliosStore.snapshot`` IS the commit chokepoint (it shells out to
    ``commit --work``); we wrap it with a counter. The disabled guard returns before any
    ``HeliosStore`` is even constructed, so the counter must stay 0.
    """
    counter = {"n": 0}
    original_snapshot = helios_store.HeliosStore.snapshot

    def _counting_snapshot(self, work_dir):
        counter["n"] += 1
        return original_snapshot(self, work_dir)

    helios_store.HeliosStore.snapshot = _counting_snapshot
    try:
        cfg_none = SimpleNamespace(helios=None)
        cfg_off = _cfg(
            enabled=False, store_dir=store_dir, binary=binary, lock_file=lock_file
        )
        records = []
        for i, rec in enumerate(fixtures.FIXTURE_TREE):
            wd = tempfile.mkdtemp(prefix="helios_off_")
            _exec_node(rec.code, wd)
            cfg = cfg_none if (i % 2 == 0) else cfg_off  # exercise both disabled shapes
            sid = snapshot_node_working_dir(cfg, wd, node_id=rec.id)
            records.append(
                {
                    "id": rec.id,
                    "node_type": rec.node_type,
                    "is_buggy": rec.is_buggy,
                    "snapshot_id": sid,
                    "npy_sha256": _sha256_file(os.path.join(wd, "experiment_data.npy")),
                }
            )
        return records, counter["n"]
    finally:
        helios_store.HeliosStore.snapshot = original_snapshot


def _write_json(path, obj):
    with open(path, "w") as fh:
        json.dump(obj, fh, indent=2, sort_keys=True)
        fh.write("\n")


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--store-dir", required=True)
    ap.add_argument("--out", required=True)
    args = ap.parse_args(argv)

    store_dir = os.path.abspath(args.store_dir)
    out_dir = os.path.abspath(args.out)
    os.makedirs(out_dir, exist_ok=True)
    binary = _resolve_binary()
    lock_file = store_dir.rstrip("/") + ".flock"

    cfg = _cfg(enabled=True, store_dir=store_dir, binary=binary, lock_file=lock_file)

    # --- enabled pass: 100% coverage incl. buggy ----------------------------------
    records, work_dirs = _enabled_pass(cfg)
    _write_json(os.path.join(out_dir, "journal.json"), records)

    # --- flag-off pass: zero subprocess, snapshot_id all null ---------------------
    off_records, off_count = _flagoff_pass(store_dir, binary, lock_file)
    _write_json(os.path.join(out_dir, "journal-flagoff.json"), off_records)
    with open(os.path.join(out_dir, "flagoff-subprocess-count.txt"), "w") as fh:
        fh.write("%d\n" % off_count)

    by_id = {r["id"]: r for r in records}

    # --- materialize a BUGGY node byte-for-byte (materialize, never restore) -------
    debug_rec = by_id["n_debug"]
    debug_sid = debug_rec["snapshot_id"]
    mat_out = tempfile.mkdtemp(prefix="helios_mat_")  # fresh empty, outside the store
    # mkdtemp returns an empty dir; HeliosStore.materialize refuses a non-empty out dir.
    os.rmdir(mat_out)  # hand materialize a not-yet-existing path -> it makedirs it
    materialize(debug_sid, mat_out, cfg=cfg)
    orig_npy = os.path.join(work_dirs["n_debug"], "experiment_data.npy")
    mat_npy = os.path.join(mat_out, "experiment_data.npy")
    orig_sha = _sha256_file(orig_npy)
    mat_sha = _sha256_file(mat_npy)
    arrays_equal = bool(np.array_equal(np.load(orig_npy), np.load(mat_npy)))
    identical = (orig_sha is not None) and (orig_sha == mat_sha) and arrays_equal
    with open(os.path.join(out_dir, "materialize-diff.txt"), "w") as fh:
        fh.write("node id: %s\n" % debug_rec["id"])
        fh.write("snapshot_id: %s\n" % debug_sid)
        fh.write("sha256(original): %s\n" % orig_sha)
        fh.write("sha256(materialized): %s\n" % mat_sha)
        fh.write("numpy.array_equal=%s\n" % arrays_equal)
        fh.write("verdict: %s\n" % ("IDENTICAL" if identical else "MISMATCH"))

    # --- coverage report ----------------------------------------------------------
    node_types = sorted({r["node_type"] for r in records})
    buggy = [r for r in records if r["is_buggy"]]
    null_snap = [r for r in records if r["snapshot_id"] is None]
    all_match = all(
        r["snapshot_id"] and _BLAKE3_RE.fullmatch(r["snapshot_id"]) for r in records
    )
    debug_eq_ablation = (
        by_id["n_debug"]["snapshot_id"] == by_id["n_ablation"]["snapshot_id"]
    )
    with open(os.path.join(out_dir, "coverage-report.txt"), "w") as fh:
        fh.write("total nodes: %d\n" % len(records))
        fh.write("distinct node_types: %d %s\n" % (len(node_types), node_types))
        fh.write("buggy count: %d\n" % len(buggy))
        fh.write("null-snapshot count: %d\n" % len(null_snap))
        fh.write("ALL snapshot_id match ^blake3:[0-9a-f]{64}$: %s\n" % bool(all_match))
        fh.write(
            "n_debug.snapshot_id == n_ablation.snapshot_id: %s\n" % debug_eq_ablation
        )
        fh.write("flag-off commit-call count: %d\n" % off_count)

    # --- fail loudly if any headline invariant is violated ------------------------
    problems = []
    if len(records) < 6:
        problems.append("fewer than 6 nodes")
    if len(node_types) < 5:
        problems.append("fewer than 5 node_types")
    if len(buggy) < 2:
        problems.append("fewer than 2 buggy nodes")
    if null_snap:
        problems.append("null snapshot_id(s): %s" % [r["id"] for r in null_snap])
    if not all_match:
        problems.append("some snapshot_id did not match blake3 pattern")
    if not debug_eq_ablation:
        problems.append("n_debug/n_ablation snapshot ids differ (content-addressing)")
    if off_count != 0:
        problems.append("flag-off commit count != 0 (was %d)" % off_count)
    if not identical:
        problems.append("buggy materialize not byte-identical")
    if problems:
        raise SystemExit("REPLAY FAILED: " + "; ".join(problems))

    _log(
        "REPLAY_OK nodes=%d types=%d buggy=%d nulls=0 flagoff_commits=%d"
        % (len(records), len(node_types), len(buggy), off_count)
    )
    _log("out=%s store=%s binary=%s" % (out_dir, store_dir, binary))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
