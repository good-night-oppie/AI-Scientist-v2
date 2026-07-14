"""Falsifiable tests for the helios_store wrapper -- one per acceptance criterion.

Pure-Python tests need no helios binary and always run. Tests marked ``helios``
require a freshly built CLI (skipped only if go is genuinely unavailable). The
concurrent test is additionally marked ``slow``.
"""

from __future__ import annotations

import hashlib
import json
import multiprocessing as mp
import os
import re
import sys
import types
from pathlib import Path

import pytest

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

import ai_scientist.treesearch.helios_store as helios_store  # noqa: E402
from ai_scientist.treesearch.helios_store import (  # noqa: E402
    HeliosCommandError,
    HeliosStore,
    HeliosUnavailableError,
    _parse_snapshot_id,
    _SNAPSHOT_ID_RE,
)

_EVIDENCE_DIR = os.path.join(_REPO_ROOT, ".supergoal", "evidence", "M2")
os.makedirs(_EVIDENCE_DIR, exist_ok=True)

_GOOD_ID = "blake3:" + "a" * 64
_BOGUS_ID = "blake3:" + "0" * 64  # regex-valid but not a real snapshot


# --------------------------------------------------------------------------- #
# fixtures / helpers                                                          #
# --------------------------------------------------------------------------- #
@pytest.fixture
def fake_bin(tmp_path):
    """An executable stand-in so HeliosStore can be constructed without a real CLI."""
    p = tmp_path / "fakehelios"
    p.write_text("#!/bin/sh\nexit 0\n")
    p.chmod(0o755)
    return str(p)


def _fake_subprocess(run_fn):
    """A SimpleNamespace replacing helios_store.subprocess (isolated, no globals)."""
    import subprocess as _sp

    return types.SimpleNamespace(run=run_fn, TimeoutExpired=_sp.TimeoutExpired)


def _tree_shas(root):
    out = {}
    for dp, _dirs, fns in os.walk(root):
        for fn in fns:
            fp = os.path.join(dp, fn)
            rel = os.path.relpath(fp, root)
            with open(fp, "rb") as fh:
                out[rel] = hashlib.sha256(fh.read()).hexdigest()
    return out


# --------------------------------------------------------------------------- #
# AC1 -- import-safe, stdlib-only                                             #
# --------------------------------------------------------------------------- #
def test_import_is_stdlib_only():
    code = (
        "import sys\n"
        "import ai_scientist.treesearch.helios_store as h\n"
        "heavy = {'torch','numpy','anthropic','omegaconf'} & set(sys.modules)\n"
        "assert not heavy, ('heavy modules leaked: %r' % (heavy,))\n"
        "print(h.__file__)\n"
    )
    env = dict(os.environ)
    env["PYTHONPATH"] = _REPO_ROOT + os.pathsep + env.get("PYTHONPATH", "")
    proc = mp_subprocess(code, env)
    assert proc.returncode == 0, proc.stderr


def mp_subprocess(code, env):
    import subprocess

    return subprocess.run(
        [sys.executable, "-c", code],
        capture_output=True,
        text=True,
        env=env,
        cwd=_REPO_ROOT,
    )


# --------------------------------------------------------------------------- #
# AC2 -- missing binary raises at construction, never at import               #
# --------------------------------------------------------------------------- #
def test_construct_missing_binary_raises_not_at_import(tmp_path):
    # The module import at the top of this file already succeeded with no binary.
    with pytest.raises(HeliosUnavailableError):
        HeliosStore("/nonexistent/helios", str(tmp_path / "store"))


# --------------------------------------------------------------------------- #
# AC3 -- snapshot_id from the JSON key, not from .strip()                     #
# --------------------------------------------------------------------------- #
def test_parse_snapshot_id_extracts_key_not_line():
    raw = '{"snapshot_id":"blake3:%s"}\n' % ("a" * 64)
    sid = _parse_snapshot_id(raw)
    assert sid == "blake3:" + "a" * 64
    assert sid != raw.strip()
    assert "{" not in sid and "}" not in sid and "snapshot_id" not in sid


# --------------------------------------------------------------------------- #
# AC7 -- HELIOS_STORE_DIR pinned absolute on every subprocess call            #
# --------------------------------------------------------------------------- #
def test_store_dir_pinned_on_every_call(fake_bin, tmp_path, monkeypatch):
    store_dir = tmp_path / "store"
    store = HeliosStore(fake_bin, str(store_dir))
    captured = []

    def fake_run(cmd, capture_output=None, text=None, env=None, timeout=None, **kw):
        captured.append({"argv": list(cmd), "env": dict(env)})
        return types.SimpleNamespace(
            returncode=0, stdout='{"snapshot_id":"%s"}' % _GOOD_ID, stderr=""
        )

    monkeypatch.setattr(helios_store, "subprocess", _fake_subprocess(fake_run))

    work = tmp_path / "work"
    work.mkdir()
    store.snapshot(str(work))
    store.materialize(_GOOD_ID, str(tmp_path / "out"))

    assert len(captured) == 2
    expected = os.path.abspath(str(store_dir))
    for c in captured:
        assert c["env"]["HELIOS_STORE_DIR"] == expected
    assert captured[0]["argv"][1] == "commit" and "--work" in captured[0]["argv"]
    assert captured[1]["argv"][1] == "materialize"
    assert "--id" in captured[1]["argv"] and "--out" in captured[1]["argv"]


# --------------------------------------------------------------------------- #
# AC9 -- materialize refuses a dirty out dir before any subprocess            #
# --------------------------------------------------------------------------- #
def test_materialize_refuses_dirty_out(fake_bin, tmp_path, monkeypatch):
    store = HeliosStore(fake_bin, str(tmp_path / "store"))
    out = tmp_path / "out"
    out.mkdir()
    (out / "stray.txt").write_text("i was here first")

    called = []
    monkeypatch.setattr(
        helios_store,
        "subprocess",
        _fake_subprocess(lambda *a, **k: called.append(1)),
    )
    with pytest.raises(ValueError):
        store.materialize(_GOOD_ID, str(out))
    assert called == []  # no subprocess was spawned


# --------------------------------------------------------------------------- #
# AC10 -- module never calls restore                                          #
# --------------------------------------------------------------------------- #
def test_module_never_calls_restore():
    src = Path(helios_store.__file__).read_text()
    assert "restore" not in src


# --------------------------------------------------------------------------- #
# AC12 -- store-outside-workspace guard, both directions                      #
# --------------------------------------------------------------------------- #
def test_assert_store_outside_workspace():
    assert HeliosStore.assert_store_outside_workspace("/a/logs/store", "/a/ws") is None
    with pytest.raises(ValueError):
        HeliosStore.assert_store_outside_workspace("/a/ws/store", "/a/ws")


# --------------------------------------------------------------------------- #
# AC4 -- returned id is a plain, well-formed str                              #
# --------------------------------------------------------------------------- #
@pytest.mark.helios
def test_snapshot_returns_plain_str_id(store, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "a.txt").write_text("hello world\n")
    sid = store.snapshot(str(src))
    assert type(sid) is str
    assert re.match(r"^blake3:[0-9a-f]{64}$", sid)
    # Re-commit (content-addressed -> identical id) and confirm we returned the
    # JSON key, not the raw stdout line.
    cp = store._run(["commit", "--work", str(src)])
    assert json.loads(cp.stdout)["snapshot_id"] == sid


# --------------------------------------------------------------------------- #
# AC5 -- exit 1 never triggers JSONDecodeError; stderr surfaced               #
# --------------------------------------------------------------------------- #
@pytest.mark.helios
def test_exit1_empty_stdout_no_jsondecode(store, tmp_path):
    with pytest.raises(HeliosCommandError) as ei:
        store.materialize(_BOGUS_ID, str(tmp_path / "out"))
    exc = ei.value
    assert not isinstance(exc, json.JSONDecodeError)
    assert exc.returncode == 1
    assert _BOGUS_ID in str(exc)  # the bogus-id stderr text is surfaced


# --------------------------------------------------------------------------- #
# AC6 -- exit 2 fails loudly as a programming error                           #
# --------------------------------------------------------------------------- #
@pytest.mark.helios
def test_exit2_programming_error_loud(store):
    with pytest.raises(HeliosCommandError) as ei:
        store._run(["bogusverb"])
    assert ei.value.returncode == 2


# --------------------------------------------------------------------------- #
# AC8 -- round-trip resolves independent of process cwd                       #
# --------------------------------------------------------------------------- #
@pytest.mark.helios
def test_cwd_independent_roundtrip(store, tmp_path):
    src = tmp_path / "src"
    src.mkdir()
    (src / "data.txt").write_text("payload-xyz")
    cwd_a = tmp_path / "cwd_a"
    cwd_a.mkdir()
    cwd_b = tmp_path / "cwd_b"
    cwd_b.mkdir()
    origin = os.getcwd()
    try:
        os.chdir(str(cwd_a))
        sid = store.snapshot(str(src))
        os.chdir(str(cwd_b))
        out = tmp_path / "out"
        store.materialize(sid, str(out))
    finally:
        os.chdir(origin)
    assert (out / "data.txt").read_text() == "payload-xyz"


# --------------------------------------------------------------------------- #
# AC11 -- flock is released on error (no self-deadlock)                        #
# --------------------------------------------------------------------------- #
@pytest.mark.helios
def test_flock_released_on_error(store, tmp_path):
    # An in-lock CLI failure must release the flock via the finally: clause.
    with pytest.raises(HeliosCommandError):
        store.materialize(_BOGUS_ID, str(tmp_path / "o1"))
    # A snapshot with an invalid work_dir also raises.
    with pytest.raises((ValueError, HeliosCommandError)):
        store.snapshot(str(tmp_path / "does_not_exist"))
    # The next real snapshot from the SAME process must not deadlock.
    src = tmp_path / "src"
    src.mkdir()
    (src / "f.txt").write_text("payload")
    sid = store.snapshot(str(src))
    assert _SNAPSHOT_ID_RE.match(sid)


# --------------------------------------------------------------------------- #
# AC14 -- byte-identical materialize round-trip                               #
# --------------------------------------------------------------------------- #
@pytest.mark.helios
def test_roundtrip_byte_identical(store, tmp_path):
    src = tmp_path / "src"
    (src / "sub").mkdir(parents=True)
    (src / "a.txt").write_text("ascii content, non-empty\n")
    (src / "sub" / "b.txt").write_text("nested non-empty payload\n")
    (src / "blob.bin").write_bytes(os.urandom(1 << 20))  # 1 MiB binary

    sid = store.snapshot(str(src))
    out = tmp_path / "out"
    store.materialize(sid, str(out))

    src_shas = _tree_shas(str(src))
    out_shas = _tree_shas(str(out))
    identical = set(src_shas) == set(out_shas) and all(
        src_shas[k] == out_shas.get(k) for k in src_shas
    )

    lines = [
        "snapshot_id: %s" % sid,
        "",
        "%-14s %-64s %s" % ("path", "src_sha256", "out_sha256"),
    ]
    for k in sorted(set(src_shas) | set(out_shas)):
        lines.append(
            "%-14s %-64s %s"
            % (k, src_shas.get(k, "<missing>"), out_shas.get(k, "<missing>"))
        )
    lines.append("")
    lines.append("VERDICT: %s" % ("IDENTICAL" if identical else "MISMATCH"))
    Path(_EVIDENCE_DIR, "roundtrip.txt").write_text("\n".join(lines) + "\n")

    assert set(src_shas) == set(out_shas)
    for k in src_shas:
        assert src_shas[k] == out_shas[k], k
    for required in ("a.txt", os.path.join("sub", "b.txt"), "blob.bin"):
        assert required in out_shas


# --------------------------------------------------------------------------- #
# AC13 -- flock prevents the Pebble exit-1 under real process contention      #
# --------------------------------------------------------------------------- #
def _contention_worker(
    helios_bin, store_dir, lock_path, root, idx, barrier, use_lock, q
):
    """Top-level, fork-safe worker: a fresh COLD HeliosStore per process."""
    try:
        from ai_scientist.treesearch.helios_store import (
            HeliosCommandError as _HCE,
            HeliosStore as _HS,
        )

        st = _HS(helios_bin, store_dir, lock_path=lock_path)
        work = os.path.join(root, "work_%d" % idx)
        os.makedirs(work, exist_ok=True)
        with open(os.path.join(work, "f.txt"), "w") as fh:
            fh.write("worker-%d-distinct-content" % idx)
        try:
            barrier.wait(timeout=60)
        except Exception:
            pass
        if use_lock:
            sid = st.snapshot(work)
            q.put(("ok", sid))
        else:
            cp = st._run(["commit", "--work", work])  # bypasses the flock
            q.put(("ok", json.loads(cp.stdout)["snapshot_id"]))
    except _HCE as e:  # noqa: F821 -- imported in the try above
        q.put(("err", e.returncode, e.stderr or ""))
    except Exception as e:  # pragma: no cover - defensive
        q.put(("err", -1, repr(e)))


def _run_arm(ctx, helios_bin, store_dir, root, n, use_lock):
    os.makedirs(root, exist_ok=True)
    lock_path = store_dir.rstrip("/") + ".flock"
    barrier = ctx.Barrier(n)
    q = ctx.Queue()
    procs = []
    for i in range(n):
        p = ctx.Process(
            target=_contention_worker,
            args=(helios_bin, store_dir, lock_path, root, i, barrier, use_lock, q),
        )
        p.start()
        procs.append(p)
    results = [q.get(timeout=110) for _ in range(n)]
    for p in procs:
        p.join(timeout=10)
    return results


@pytest.mark.helios
@pytest.mark.slow
def test_concurrent_writers_flock(helios_bin, tmp_path):
    ctx = mp.get_context("fork")
    n = 16

    # Locked arm -- the hard, deterministic gate.
    locked = _run_arm(
        ctx,
        helios_bin,
        str(tmp_path / "locked_store"),
        str(tmp_path / "locked_work"),
        n,
        use_lock=True,
    )
    locked_ok = sum(1 for r in locked if r[0] == "ok")
    locked_err1 = sum(1 for r in locked if r[0] == "err" and r[1] == 1)
    for r in locked:
        if r[0] == "ok":
            assert _SNAPSHOT_ID_RE.match(r[1]), r

    # Unlocked arm -- up to R rounds to try to induce Pebble contention.
    rounds = 5
    u_ok = u_err1 = 0
    rounds_run = 0
    sample = None
    for rnd in range(rounds):
        rounds_run += 1
        res = _run_arm(
            ctx,
            helios_bin,
            str(tmp_path / ("unlocked_store_%d" % rnd)),
            str(tmp_path / ("unlocked_work_%d" % rnd)),
            n,
            use_lock=False,
        )
        u_ok += sum(1 for r in res if r[0] == "ok")
        for r in res:
            if r[0] == "err" and r[1] == 1:
                u_err1 += 1
                if "resource temporarily unavailable" in (r[2] or ""):
                    sample = (r[2] or "").strip().splitlines()[-1]
        if u_err1 >= 1 and sample:
            break

    lines = [
        "locked:   ok=%d err1=%d" % (locked_ok, locked_err1),
        "unlocked: ok=%d err1=%d (rounds=%d)" % (u_ok, u_err1, rounds_run),
    ]
    if u_err1 >= 1:
        lines.append("stderr-sample: %s" % (sample or "<exit-1, phrase not captured>"))
    else:
        lines.append("unlocked: SKIP (could not induce Pebble contention)")
    Path(_EVIDENCE_DIR, "concurrent.txt").write_text("\n".join(lines) + "\n")

    # The hard gate: the locked arm never produces a Pebble exit-1.
    assert locked_ok == n, locked
    assert locked_err1 == 0, locked

    if u_err1 == 0:
        pytest.skip("could not induce Pebble contention")
