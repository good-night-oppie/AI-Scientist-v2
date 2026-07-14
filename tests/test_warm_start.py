"""Phase 7 warm-start unit tests — one deterministic test per criterion.

Dependency-light on purpose: these exercise the SHIPPED helper
(``ai_scientist.treesearch.helios_store.maybe_warm_start``) and the SHIPPED prompt
method (rendered via ``tests/_guideline_render.py`` — an AST extraction, since
``parallel_agent`` is un-importable on this GPU/pandas-less host) directly. No LLM, no
GPU, no helios binary is required: the single materialize entry point
(``helios_store._materialize``) is monkeypatched where a real store is not the thing
under test, so every assertion is about control flow, gating, and byte-identity.

Coverage: AC1 (typed default), AC2 (none-safe, ``-k none_safe``), AC3 (prompt gated),
AC4 (flag-OFF byte-identity vs golden), AC8 (buggy-parent guard), AC11 (materialize
failure -> cold). AC5/AC6/AC7/AC9/AC10/AC12 are proven by the harness + replay evidence.
"""

from __future__ import annotations

import dataclasses
import os
import sys
from types import SimpleNamespace

_HERE = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(_HERE)
for _p in (_REPO_ROOT, _HERE):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from ai_scientist.treesearch import helios_store  # noqa: E402
from _guideline_render import render_guideline  # noqa: E402

_PARALLEL_AGENT = os.path.join(
    _REPO_ROOT, "ai_scientist", "treesearch", "parallel_agent.py"
)
_GOLDEN = os.path.join(_HERE, "fixtures", "impl_guideline_golden.txt")
_MARKER = "Warm-start / cached-artifact reuse"
_GOOD_SID = "blake3:" + "a" * 64


def _cfg_on():
    return SimpleNamespace(helios=SimpleNamespace(enabled=True, warm_start=True))


def _mkwd(tmp_path):
    wd = str(tmp_path / "wd")
    os.makedirs(wd, exist_ok=True)
    return wd


# --------------------------------------------------------------------------- #
# AC1 — warm_start typed + default False                                       #
# --------------------------------------------------------------------------- #
def test_warm_start_field_typed_default_false():
    from ai_scientist.treesearch.utils.config import HeliosConfig

    fields = {f.name: f for f in dataclasses.fields(HeliosConfig)}
    assert "warm_start" in fields
    assert fields["warm_start"].type in (bool, "bool")
    assert fields["warm_start"].default is False


# --------------------------------------------------------------------------- #
# AC2 — none-safe: no helios call when cfg.helios is None                      #
# --------------------------------------------------------------------------- #
def test_none_safe_no_helios_calls(monkeypatch, tmp_path):
    calls = []

    def _must_not_run(cfg, sid, out_dir):
        calls.append(sid)
        raise AssertionError("_materialize must never run when helios is None")

    monkeypatch.setattr(helios_store, "_materialize", _must_not_run)
    wd = _mkwd(tmp_path)
    parent = SimpleNamespace(is_buggy=False, snapshot_id=_GOOD_SID)

    # Both disabled shapes must short-circuit to cold with zero materialize calls.
    assert (
        helios_store.maybe_warm_start(SimpleNamespace(helios=None), parent, wd)
        == "cold"
    )
    assert (
        helios_store.maybe_warm_start(
            SimpleNamespace(helios=SimpleNamespace(enabled=False, warm_start=True)),
            parent,
            wd,
        )
        == "cold"
    )
    assert (
        helios_store.maybe_warm_start(
            SimpleNamespace(helios=SimpleNamespace(enabled=True, warm_start=False)),
            parent,
            wd,
        )
        == "cold"
    )
    assert calls == []
    assert os.listdir(wd) == []


# --------------------------------------------------------------------------- #
# AC3 — prompt reuse block gated on the flag                                   #
# --------------------------------------------------------------------------- #
def test_prompt_gated_on_flag():
    off = render_guideline(_PARALLEL_AGENT, helios=None)
    on = render_guideline(
        _PARALLEL_AGENT, helios=SimpleNamespace(enabled=True, warm_start=True)
    )
    # enabled but warm_start False must ALSO stay off (needs BOTH).
    enabled_only = render_guideline(
        _PARALLEL_AGENT, helios=SimpleNamespace(enabled=True, warm_start=False)
    )
    assert _MARKER not in off
    assert _MARKER in on
    assert _MARKER not in enabled_only


# --------------------------------------------------------------------------- #
# AC4 — flag-OFF guideline byte-identical to baseline 96bd516 golden           #
# --------------------------------------------------------------------------- #
def test_prompt_off_byte_identical():
    with open(_GOLDEN, "r", encoding="utf-8") as fh:
        golden = fh.read()
    rendered_none = render_guideline(_PARALLEL_AGENT, helios=None)
    assert rendered_none == golden
    # An explicitly-disabled helios cfg is likewise byte-identical to baseline.
    rendered_off = render_guideline(
        _PARALLEL_AGENT, helios=SimpleNamespace(enabled=False, warm_start=False)
    )
    assert rendered_off == golden


# --------------------------------------------------------------------------- #
# AC8 — buggy-parent guard (debug branch re-enters buggy parents)             #
# --------------------------------------------------------------------------- #
def test_buggy_parent_guard(monkeypatch, tmp_path):
    def _must_not_run(cfg, sid, out_dir):
        raise AssertionError("a buggy parent must never be materialized (poison guard)")

    monkeypatch.setattr(helios_store, "_materialize", _must_not_run)
    wd = _mkwd(tmp_path)
    buggy_parent = SimpleNamespace(is_buggy=True, snapshot_id=_GOOD_SID)
    assert helios_store.maybe_warm_start(_cfg_on(), buggy_parent, wd) == "cold"
    assert os.listdir(wd) == []


# --------------------------------------------------------------------------- #
# AC11 — materialize failure ⇒ cold, node survives, no exception escapes       #
# --------------------------------------------------------------------------- #
def test_materialize_failure_falls_back_cold(monkeypatch, tmp_path):
    def _raise(cfg, sid, out_dir):
        raise RuntimeError("helios materialize exited 1 (unknown snapshot in L2)")

    monkeypatch.setattr(helios_store, "_materialize", _raise)
    wd = _mkwd(tmp_path)
    parent = SimpleNamespace(is_buggy=False, snapshot_id="blake3:" + "f" * 64)
    # Must NOT raise; must degrade to cold; must leave the dir empty.
    assert helios_store.maybe_warm_start(_cfg_on(), parent, wd) == "cold"
    assert os.listdir(wd) == []


# --------------------------------------------------------------------------- #
# Extra — happy path + draft guard (strengthens AC5 control flow)              #
# --------------------------------------------------------------------------- #
def test_warm_path_returns_warm(monkeypatch, tmp_path):
    def _fake(cfg, sid, out_dir):
        with open(os.path.join(out_dir, "preprocessed.npy"), "wb") as fh:
            fh.write(b"cached")

    monkeypatch.setattr(helios_store, "_materialize", _fake)
    wd = _mkwd(tmp_path)
    parent = SimpleNamespace(is_buggy=False, snapshot_id=_GOOD_SID)
    assert helios_store.maybe_warm_start(_cfg_on(), parent, wd) == "warm"
    assert os.path.exists(os.path.join(wd, "preprocessed.npy"))


def test_draft_node_parent_none_is_cold(monkeypatch, tmp_path):
    def _must_not_run(cfg, sid, out_dir):
        raise AssertionError("a draft (parent=None) must never materialize")

    monkeypatch.setattr(helios_store, "_materialize", _must_not_run)
    wd = _mkwd(tmp_path)
    assert helios_store.maybe_warm_start(_cfg_on(), None, wd) == "cold"
    assert os.listdir(wd) == []


def test_parent_without_snapshot_is_cold(monkeypatch, tmp_path):
    def _must_not_run(cfg, sid, out_dir):
        raise AssertionError("no snapshot_id -> nothing to materialize")

    monkeypatch.setattr(helios_store, "_materialize", _must_not_run)
    wd = _mkwd(tmp_path)
    parent = SimpleNamespace(is_buggy=False, snapshot_id=None)
    assert helios_store.maybe_warm_start(_cfg_on(), parent, wd) == "cold"
    assert os.listdir(wd) == []
