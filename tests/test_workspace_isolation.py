"""Unit tests for the Phase-6 per-node isolation helper.

Fast and dependency-free: imports ONLY
``ai_scientist.treesearch.workspace_isolation`` (pure stdlib) — no torch, no numpy,
no parallel_agent — so these never skip for import reasons on a GPU-less host.

Covers the four load-bearing guarantees:

* baseline keying is BYTE-IDENTICAL to the pre-Phase-6 expression
  ``os.path.join(cfg.workspace_dir, f"process_{name}")`` (flag OFF => zero delta);
* isolated keying uses ``node_<id>`` and never ``process_``;
* the stale-detection predicate is empty on a fresh dir and finds a leftover ``.npy``;
* GC is double-gated (``isolated`` AND a durable snapshot) and bounded (a K-node loop
  drives the ``node_*`` dir count to 0; a count/age sweep caps unbounded growth).
"""

from __future__ import annotations

import os

from ai_scientist.treesearch.workspace_isolation import (
    detect_saved_npy,
    gc_bounded_node_workdirs,
    gc_node_workdir,
    resolve_node_workdir,
)

_GOOD_SNAP = "blake3:" + "a" * 64


# --------------------------------------------------------------------------- #
# AC3 / AC9 -- keying                                                          #
# --------------------------------------------------------------------------- #
def test_isolated_keying_uses_node_id(tmp_path):
    root = str(tmp_path)
    ws, wd = resolve_node_workdir(root, "abc", "W", isolated=True)
    assert ws.endswith("node_abc")
    assert os.path.basename(ws) == "node_abc"
    assert "process_" not in os.path.basename(ws)
    assert wd == os.path.join(ws, "working")
    assert os.path.isdir(wd)  # resolve creates it


def test_baseline_keying_byte_identical(tmp_path):
    root = str(tmp_path)
    ws, wd = resolve_node_workdir(root, "abc", "W", isolated=False)
    # The EXACT pre-Phase-6 expression from parallel_agent.py.
    assert ws == os.path.join(root, "process_W")
    assert wd == os.path.join(root, "process_W", "working")
    assert os.path.isdir(wd)


def test_flag_off_matches_literal_table(tmp_path):
    """Flag OFF => zero delta: the string equals the literal old expression for a
    table of worker names (AC9). ``child_node_id`` must not influence the OFF path."""
    root = str(tmp_path)
    for name in ["SpawnPoolWorker-1", "MainProcess", "ForkPoolWorker-3", "W"]:
        ws, _ = resolve_node_workdir(root, "IGNORED-NODE-ID", name, isolated=False)
        assert ws == os.path.join(root, f"process_{name}"), name


# --------------------------------------------------------------------------- #
# stale-detection predicate                                                   #
# --------------------------------------------------------------------------- #
def test_detect_saved_npy_empty_and_present(tmp_path):
    _, wd = resolve_node_workdir(str(tmp_path), "n", "W", isolated=True)
    assert detect_saved_npy(wd) == []
    open(os.path.join(wd, "experiment_data.npy"), "wb").close()
    open(os.path.join(wd, "note.txt"), "w").close()  # non-npy ignored
    assert detect_saved_npy(wd) == ["experiment_data.npy"]


# --------------------------------------------------------------------------- #
# AC8 -- GC double-gated                                                       #
# --------------------------------------------------------------------------- #
def _make_ws(root, node_id):
    ws, _ = resolve_node_workdir(str(root), node_id, "W", isolated=True)
    return ws


def test_gc_deletes_only_when_isolated_and_snapshot(tmp_path):
    # (isolated=True, snapshot set) -> True, dir gone.
    ws = _make_ws(tmp_path, "n_del")
    assert gc_node_workdir(ws, isolated=True, snapshot_id=_GOOD_SNAP) is True
    assert not os.path.isdir(ws)

    # (isolated=False, snapshot set) -> False, dir survives (baseline never resets).
    ws2, _ = resolve_node_workdir(str(tmp_path), "off", "W", isolated=False)
    assert gc_node_workdir(ws2, isolated=False, snapshot_id=_GOOD_SNAP) is False
    assert os.path.isdir(ws2)

    # (isolated=True, snapshot None) -> False, dir survives (no durable copy yet).
    ws3 = _make_ws(tmp_path, "n_nosnap")
    assert gc_node_workdir(ws3, isolated=True, snapshot_id=None) is False
    assert os.path.isdir(ws3)


def test_gc_loop_k10_drives_dir_count_to_zero(tmp_path):
    """K nodes on one worker, isolated + snapshot each -> 0 node_* dirs after GC
    (unbounded per-node growth is bounded back to 0 post-snapshot)."""
    root = str(tmp_path)
    K = 10
    for i in range(K):
        ws = _make_ws(root, f"loop_{i}")
        assert os.path.isdir(ws)
        assert gc_node_workdir(ws, isolated=True, snapshot_id=_GOOD_SNAP) is True
    leftover = [d for d in os.listdir(root) if d.startswith("node_")]
    assert leftover == [], leftover


# --------------------------------------------------------------------------- #
# bounded safety-net sweep (count + age caps)                                 #
# --------------------------------------------------------------------------- #
def test_gc_bounded_caps_by_count(tmp_path):
    root = str(tmp_path)
    for i in range(20):
        _make_ws(root, f"c_{i:02d}")
    removed = gc_bounded_node_workdirs(root, isolated=True, max_keep=5)
    remaining = [d for d in os.listdir(root) if d.startswith("node_")]
    assert len(remaining) == 5, remaining
    assert len(removed) == 15, removed


def test_gc_bounded_caps_by_age(tmp_path):
    root = str(tmp_path)
    old = _make_ws(root, "old")
    new = _make_ws(root, "new")
    # Age `old` far into the past; keep `new` fresh.
    past = os.path.getmtime(new) - 10_000
    os.utime(old, (past, past))
    removed = gc_bounded_node_workdirs(
        root, isolated=True, max_keep=None, max_age_s=100
    )
    assert os.path.basename(old) in removed
    assert not os.path.isdir(old)
    assert os.path.isdir(new)


def test_gc_bounded_inert_under_baseline(tmp_path):
    root = str(tmp_path)
    for i in range(20):
        _make_ws(root, f"b_{i:02d}")
    removed = gc_bounded_node_workdirs(root, isolated=False, max_keep=1)
    assert removed == []
    remaining = [d for d in os.listdir(root) if d.startswith("node_")]
    assert len(remaining) == 20
