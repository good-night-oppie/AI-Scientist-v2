"""Coverage assertions over the deterministic replay harness (Phase 5).

Invokes ``tests/replay/replay_tree.py`` in a tmp store/out dir (using the ``helios_bin``
fixture from ``tests/conftest.py`` -- a binary built from HEAD, never the tracked
./helios-cli), then asserts over the emitted journals: 100% snapshot coverage incl.
buggy nodes, byte-identical materialize of a buggy node, and a flag-off delta that
changes provenance only.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys

import pytest

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_HERE))
_BLAKE3_RE = re.compile(r"blake3:[0-9a-f]{64}\Z")


@pytest.fixture(scope="module")
def replay_out(helios_bin, tmp_path_factory):
    out = tmp_path_factory.mktemp("replay_out")
    store = tmp_path_factory.mktemp("replay_store")
    env = os.environ.copy()
    env["HELIOS_CLI_BIN"] = helios_bin
    proc = subprocess.run(
        [
            sys.executable,
            os.path.join(_HERE, "replay_tree.py"),
            "--store-dir",
            str(store),
            "--out",
            str(out),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    assert proc.returncode == 0, "replay harness failed:\n%s\n%s" % (
        proc.stdout,
        proc.stderr,
    )
    return str(out)


def _load(out, name):
    with open(os.path.join(out, name)) as fh:
        return json.load(fh)


def test_full_coverage_incl_buggy(replay_out):
    nodes = _load(replay_out, "journal.json")
    assert len(nodes) >= 6
    assert len({n["node_type"] for n in nodes}) >= 5
    assert sum(1 for n in nodes if n["is_buggy"]) >= 2
    # Every node -- buggy included -- has a well-formed content-hash snapshot id.
    assert all(
        n["snapshot_id"] and _BLAKE3_RE.fullmatch(n["snapshot_id"]) for n in nodes
    )
    assert sum(1 for n in nodes if n["snapshot_id"] is None) == 0


def test_buggy_materialize_byte_identical(replay_out):
    with open(os.path.join(replay_out, "materialize-diff.txt")) as fh:
        text = fh.read()
    assert "IDENTICAL" in text
    shas = re.findall(r"sha256\([^)]*\):\s*([0-9a-f]{64})", text)
    assert len(shas) == 2, shas
    assert shas[0] == shas[1], "materialized sha256 differs from original"
    assert "numpy.array_equal=True" in text


def test_content_addressing_identical_dirs(replay_out):
    nodes = {n["id"]: n for n in _load(replay_out, "journal.json")}
    # Byte-identical working dirs (n_debug, n_ablation) -> identical snapshot id.
    assert nodes["n_debug"]["snapshot_id"] == nodes["n_ablation"]["snapshot_id"]


def test_flagoff_journal_delta_is_snapshot_only(replay_out):
    on = _load(replay_out, "journal.json")
    off = _load(replay_out, "journal-flagoff.json")
    assert len(on) == len(off)
    for a, b in zip(on, off):
        assert b["snapshot_id"] is None
        # Every non-provenance key is unchanged by the seam.
        assert a["id"] == b["id"]
        assert a["node_type"] == b["node_type"]
        assert a["is_buggy"] == b["is_buggy"]
    # And the commit chokepoint was never invoked while disabled.
    with open(os.path.join(replay_out, "flagoff-subprocess-count.txt")) as fh:
        assert fh.read().strip() == "0"
