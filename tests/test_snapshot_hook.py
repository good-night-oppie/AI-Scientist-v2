"""Behavioral tests for the Phase-5 write-only snapshot hook.

Imports ONLY ``helios_store`` (import-safe, pure stdlib) -- never ``parallel_agent`` /
``journal`` (un-importable on this host). Proves the four load-bearing behaviors of
``snapshot_node_working_dir``: disabled = no-op + zero subprocess, never-raises on a
failing binary, missing dir = None, and a real enabled round-trip that materializes
byte-for-byte.
"""

from __future__ import annotations

import re
from types import SimpleNamespace

from ai_scientist.treesearch import helios_store
from ai_scientist.treesearch.helios_store import (
    materialize,
    snapshot_node_working_dir,
)

_BLAKE3_RE = re.compile(r"blake3:[0-9a-f]{64}\Z")


def _cfg(*, enabled, store_dir, binary, lock_file=None):
    return SimpleNamespace(
        helios=SimpleNamespace(
            enabled=enabled,
            store_dir=store_dir,
            binary_path=binary,
            lock_file=lock_file,
        )
    )


def _populate(dir_path):
    dir_path.mkdir(parents=True, exist_ok=True)
    (dir_path / "experiment_data.npy").write_bytes(b"\x93NUMPY-fake-but-nonempty")
    return dir_path


def test_disabled_returns_none_no_subprocess(tmp_path, monkeypatch):
    """cfg.helios=None AND cfg.helios.enabled=False both -> None, 0 commit calls."""
    calls = {"n": 0}
    original = helios_store.HeliosStore.snapshot

    def _counting(self, work_dir):  # would run `commit --work` -> a subprocess
        calls["n"] += 1
        return original(self, work_dir)

    monkeypatch.setattr(helios_store.HeliosStore, "snapshot", _counting)

    wd = _populate(tmp_path / "working")

    cfg_none = SimpleNamespace(helios=None)
    assert snapshot_node_working_dir(cfg_none, str(wd)) is None

    cfg_off = _cfg(
        enabled=False, store_dir=str(tmp_path / "store"), binary="/bin/false"
    )
    assert snapshot_node_working_dir(cfg_off, str(wd)) is None

    assert calls["n"] == 0


def test_never_raises_on_commit_failure(tmp_path):
    """enabled=True + binary=/bin/false (exit 1, empty stdout) -> None, no exception."""
    wd = _populate(tmp_path / "working")
    cfg = _cfg(enabled=True, store_dir=str(tmp_path / "store"), binary="/bin/false")
    # A bare call: if any exception escapes, the test errors out (no pytest.raises).
    result = snapshot_node_working_dir(cfg, str(wd), node_id="n_fail")
    assert result is None


def test_missing_working_dir_returns_none(tmp_path):
    """A nonexistent working_dir -> None, no raise, no subprocess."""
    cfg = _cfg(enabled=True, store_dir=str(tmp_path / "store"), binary="/bin/false")
    assert snapshot_node_working_dir(cfg, str(tmp_path / "nope")) is None


def test_enabled_roundtrip(helios_bin, tmp_path):
    """Real pinned binary: snapshot -> blake3 id; materialize -> byte-identical files."""
    wd = tmp_path / "working"
    wd.mkdir()
    (wd / "experiment_data.npy").write_bytes(b"roundtrip-experiment-bytes")
    (wd / "sub").mkdir()
    (wd / "sub" / "note.txt").write_text("hello-helios")

    cfg = _cfg(enabled=True, store_dir=str(tmp_path / "store"), binary=helios_bin)
    sid = snapshot_node_working_dir(cfg, str(wd), node_id="n_roundtrip")
    assert sid is not None
    assert _BLAKE3_RE.fullmatch(sid), sid

    out = tmp_path / "out"  # not-yet-existing -> materialize makedirs it
    materialize(sid, str(out), cfg=cfg)
    assert (out / "experiment_data.npy").read_bytes() == b"roundtrip-experiment-bytes"
    assert (out / "sub" / "note.txt").read_text() == "hello-helios"
