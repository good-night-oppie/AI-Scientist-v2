"""Hermetic guard suite — RR#3 item 2.

C2 was "zero committed tests": every guard in this chain was verified by me
running an ad-hoc probe once, in a shell, and reporting the result. That is not
evidence a reviewer can re-run, and it is not a regression barrier — the T1
argv-blindness regression happened precisely because a fix removed a guard and
nothing re-checked it.

This suite covers EXACTLY the six adversarial probes now proven to matter —
every one of them is a real exploit that a reviewer or the coordinator actually
executed against a real commit of this chain — plus the Q-A binding replacement.

  1. argv-garbage exit 2 on all 7 CLIs        (T1 class; coordinator's finding)
  2. FAC dirty-CONTENT mutation is caught     (E1.1; reviewer proved the old
                                               status-hash form fail-open)
  3. an arbitrary --manifest is refused       (reviewer got PASS on an unfrozen
                                               bundle via a temp manifest)
  4. the fake liveness receipt is refused     (reviewer's deadbeef/0-invocations/
                                               non-empty-branches receipt was
                                               ACCEPTED by the old loader)
  5. the 000…0 slot fill is refused           (coordinator reproduced FILLED,
                                               exit 0, on a non-existent artifact)
  6. grandfather set == measured census       (equality, so the census can never
                                               silently drift again)
  Q-A. B/C resolve to the SAME function object, and a DETERMINISTIC STUB battery
       driven through both arms' call paths produces EQUAL counts (no real
       engine => no std::random_device problem, so this is assertable where
       numeric equality on real batteries is not).

Hermetic: no network, no real engine, no writes outside tmp_path. Every test
that touches split-manifest.json operates on a COPY.

Run:  <pinned venv>/python -m pytest gate/tests/ -q
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parent.parent
FAC = GATE.parent
PY = sys.executable
sys.path.insert(0, str(GATE))

VENV_PY = "/home/admin/gh/ready-player-one-ptcg/.venv/bin/python"
SYS_PY = "/usr/bin/python3"

# REAL FINDING surfaced by writing this suite: the chain spans TWO interpreters,
# and an argv guard inside main() is only reachable under the interpreter whose
# module-level imports resolve. rdiv_mine imports zstandard (system python has
# it, the pinned venv does NOT); armc_liveness_preflight imports
# kaggle_environments (pinned venv has it, system python does not). Under the
# wrong interpreter each dies at import with rc=1 BEFORE argparse runs. So each
# CLI is probed with the interpreter it is actually invoked with — probing them
# all under one interpreter would silently prove nothing for one of them.
ARGV_BLIND_CLIS = [
    ("tfreeze_snapshot.py", SYS_PY),
    ("rdiv_mine.py", SYS_PY),
    ("make_executable_freeze_manifest.py", SYS_PY),
    ("make_rotation_freeze.py", SYS_PY),
    ("make_slice_definition.py", SYS_PY),
    ("parent_diff_receipt.py", SYS_PY),
    ("armc_liveness_preflight.py", VENV_PY),
    # RR#4 item 7: the test-receipt generator is a chain CLI like any other —
    # garbage argv must exit 2 BEFORE any suite runs (no recursion risk: the
    # probe never reaches the pytest invocations).
    ("make_test_receipt.py", VENV_PY),
]


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def core_sha(core: dict) -> str:
    return sha256_bytes(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    )


# ---------------------------------------------------------------------------
# PROBE 1 — argv garbage must exit 2 on every chain CLI (T1 class)
# ---------------------------------------------------------------------------
@pytest.mark.parametrize("tool,interp", ARGV_BLIND_CLIS)
def test_probe1_argv_garbage_rejected(tool, interp):
    """The coordinator's exact garbage. A swallowed flag makes any historical
    invocation record permanently ambiguous — that is the provenance defect."""
    r = subprocess.run(
        [
            interp,  # each CLI under ITS OWN interpreter — see ARGV_BLIND_CLIS
            str(GATE / tool),
            "--this-flag-is-nonsense",
            "--allow-gaps",
            "--roots",
            "/tmp/nope",
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2, (
        f"{tool} did not reject unknown args under {interp} (rc={r.returncode}): "
        f"{r.stderr[-160:]}"
    )
    assert "unrecognized arguments" in r.stderr


# ---------------------------------------------------------------------------
# PROBE 2 — FAC projection must catch a dirty-CONTENT mutation (E1.1)
# ---------------------------------------------------------------------------
def test_probe2_fac_projection_catches_dirty_content_mutation():
    """The REJECTED status-hash form hashed `git status` TEXT, so mutating a
    dirty file dirty1 -> dirty2 left it identical. The content projection must
    move when file CONTENT moves, with paths/status unchanged.

    RR#5.6 update: the projection's file set is now the TRACKED set (the
    untracked-probe variant of this test is structurally out of scope — that
    exclusion is itself asserted by the rr56 cache-invariance regression), so
    the probe mutates a real TRACKED generator input: one byte flipped, SAME
    path, SAME size, SAME tracked status — only content_sha256 can catch it —
    then restores the original bytes and proves the projection returns to
    baseline.

    RR#5.7 update (navigator-ruled): the probe must check the checkout it
    LIVES IN. The module's FAC was host-pinned, so on any non-canonical
    checkout/worktree the byte-flip below hit the checkout copy while the
    projection read the canonical tree — this probe verified NOTHING there.
    The alignment assert is the machine edge: module root and test root must
    agree in EVERY run, so the flip provably lands on the projection's own
    input on whatever checkout is under audit."""
    import make_executable_freeze_manifest as m

    assert m.FAC == FAC and m.GATE == GATE, (
        f"probe target misbound: projection reads {m.FAC}, flip lands under "
        f"{FAC} — a worktree run would verify nothing (the RR#5.7 defect)"
    )
    target = GATE / "armb-pilot" / "config.json"  # tracked generator input
    original = target.read_bytes()
    try:
        baseline = m.fac_source_projection()["fac_source_projection_sha256"]
        mutated_bytes = original[:-1] + bytes([original[-1] ^ 1])
        assert len(mutated_bytes) == len(original)
        target.write_bytes(mutated_bytes)  # dirty1 -> dirty2, size-preserving
        second = m.fac_source_projection()["fac_source_projection_sha256"]
    finally:
        target.write_bytes(original)
    assert second != baseline, (
        "projection did not move on a content-only mutation — this is exactly "
        "the fail-open the reviewer reproduced against the status-hash form"
    )
    restored = m.fac_source_projection()["fac_source_projection_sha256"]
    assert restored == baseline, "projection did not return after byte restore"


def test_probe2_projection_excludes_only_generator_outputs():
    import make_executable_freeze_manifest as m

    assert "gate/executable-freeze-manifest.json" in m._FAC_PROJECTION_EXCLUDE
    # slice-definition is an INPUT and must be projected, never excluded
    assert not any("slice-definition" in x for x in m._FAC_PROJECTION_EXCLUDE)


# ---------------------------------------------------------------------------
# PROBE 3 — an arbitrary --manifest must be refused (launch validator)
# ---------------------------------------------------------------------------
def test_probe3_launch_validator_has_no_manifest_surface():
    """The reviewer built a temp manifest naming an unfrozen bundle and got PASS.
    The surface must not exist at all — validating it harder is not enough."""
    r = subprocess.run(
        [PY, str(GATE / "validate_launch_bundles.py"), "--manifest", "/tmp/evil.json"],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "unrecognized arguments" in r.stderr
    # assert the SURFACE is gone, not the word — the docstrings deliberately
    # explain the removal, and naming it there is correct.
    src = (GATE / "validate_launch_bundles.py").read_text()
    assert 'add_argument("--manifest"' not in src, (
        "an operator-facing --manifest surface reappeared"
    )


def test_probe3_launch_validator_takes_pools_from_the_freeze():
    import validate_launch_bundles as v

    pools = v.pool_manifests_from_freeze()
    freeze = json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    for path, sha in pools.items():
        key = "fac:" + str(Path(path).relative_to(FAC))
        assert freeze["files"][key]["sha256"] == sha


# ---------------------------------------------------------------------------
# PROBE 4 — the reviewer's fake liveness receipt must be refused
# ---------------------------------------------------------------------------
def _stage_fake(tmp_path, monkeypatch, fake: dict):
    """Sandbox that has BOTH the receipt and the real tools: patching GATE alone
    also moves the tools whose shas the loader pins, so the test would pass for
    the wrong reason (FileNotFoundError instead of the fail-closed rejection)."""
    import make_executable_freeze_manifest as m

    (tmp_path / "receipts").mkdir(parents=True, exist_ok=True)
    (tmp_path / "receipts" / "armc-liveness-receipt.json").write_text(json.dumps(fake))
    for tool in ("armc_liveness_preflight.py", "make_executable_freeze_manifest.py"):
        (tmp_path / tool).write_bytes((GATE / tool).read_bytes())
    monkeypatch.setattr(m, "GATE", tmp_path)


def _loader_args(m) -> tuple[dict, dict]:
    """(files, fac_projection) as the freeze generator passes them: the REAL
    on-disk pins for the counting-path files + a fixed projection token the
    fake receipts either match (to reach deeper checks) or not."""
    files = {
        f"fac:gate/armb-pilot/{n}": {
            "sha256": sha256_bytes((GATE / "armb-pilot" / n).read_bytes())
        }
        for n in ("harness_bridge.py", "cutoff.py")
    }
    return files, {"fac_source_projection_sha256": "p" * 64}


def _upgrade_fake_to_v2(m, core: dict) -> dict:
    """Give the reviewer's fake every RR#4 binding it needs to reach the
    checks that existed BEFORE this round — so those checks still fire."""
    core["schema"] = "armc-liveness-receipt/v2"
    for fname in ("harness_bridge.py", "cutoff.py"):
        core["arm_symmetry"].setdefault(fname, {})["sha256"] = sha256_bytes(
            (GATE / "armb-pilot" / fname).read_bytes()
        )
    core["source_bindings"] = {
        "rpo_head": m.EXPECTED_RPO_HEAD,
        "generator_source_projection_sha256": "p" * 64,
        "freeze_generator_sha256": sha256_bytes(
            (GATE / "make_executable_freeze_manifest.py").read_bytes()
        ),
    }
    # RR#5 item 5: the loader recomputes the nested pool_integrity_core sha and
    # requires legal_for_preflight — give the fake a self-consistent, legal one
    # so it reaches the OLDER branch check this test targets.
    pic = {
        "schema": "battery-pool-integrity/v2",
        "trust_chain": {"legal_for_preflight": True, "ok": True},
    }
    pic_sha = sha256_bytes(
        json.dumps(pic, sort_keys=True, separators=(",", ":")).encode()
    )
    core["search_counter_liveness"]["launch_context"] = {
        "mode": "instrumentation-preflight",
        "pool_integrity_pass": True,
        "pool_integrity_core": pic,
        "pool_integrity_core_sha256": pic_sha,
    }
    return core


def _fake_liveness_core() -> dict:
    """The reviewer's exact shape: bad tool sha, zero invocations, NON-empty
    arm_conditional_branches, pass=true. The old loader accepted this and then
    hardcoded branch-count 0 into its own output."""
    return {
        "schema": "armc-liveness-receipt/v1",
        "tool_sha256": "deadbeef" * 8,
        "armc_branch_liveness": {
            "run_epoch_invocations": 0,
            "transitions": {
                "proposal_fired": True,
                "guard_stage_fired": True,
                "selection_fired": True,
                "d_gate_select_computed": True,
                "alignment_computed": True,
                "confirmation_fired": True,
                "adoption_decided": True,
                "w_next_produced": True,
                "deterministic_given_seed": True,
            },
        },
        "search_counter_liveness": {
            "positive_search_bundles_fired": {"s18": 1},
            "negative_control": {
                "opponent": "linear_armA",
                "search_begin": 0,
                "expected": 0,
            },
            "decision_totals": {"total": 1},
        },
        "arm_symmetry": {
            "harness_bridge.py": {
                "arm_conditional_branches": [{"line": 1, "test": "arm=='C'"}]
            },
            "cutoff.py": {"arm_conditional_branches": []},
        },
        "pass": True,
    }


def test_probe4_fake_liveness_receipt_refused(tmp_path, monkeypatch):
    """The reviewer's ORIGINAL fake, verbatim — under the v2 loader it now dies
    at the schema gate (v1 receipts cannot prove they describe the final tree),
    which is an equally fail-closed refusal of the same artifact."""
    import make_executable_freeze_manifest as m

    core = _fake_liveness_core()
    fake = {"core": core, "core_sha256": core_sha(core), "volatile": {}}
    _stage_fake(tmp_path, monkeypatch, fake)
    files, proj = _loader_args(m)
    with pytest.raises(SystemExit) as e:
        m.load_liveness_receipt(files, proj)
    assert "FAIL-CLOSED" in str(e.value) and "schema" in str(e.value)


def test_probe4_stale_receipt_refused(tmp_path, monkeypatch):
    """RR#4 L1, the round's meta-pattern as a committed probe: a receipt whose
    source hashes describe an OLDER revision of the counting-path files must be
    refused — old-bridge evidence may never vouch for new-bridge code."""
    import make_executable_freeze_manifest as m

    core = _upgrade_fake_to_v2(m, _fake_liveness_core())
    core["arm_symmetry"]["harness_bridge.py"]["sha256"] = "deadbeef" * 8
    core["arm_symmetry"]["harness_bridge.py"]["arm_conditional_branches"] = []
    core["tool_sha256"] = m.sha256_file(GATE / "armc_liveness_preflight.py")
    core["armc_branch_liveness"]["run_epoch_invocations"] = 2
    fake = {"core": core, "core_sha256": core_sha(core), "volatile": {}}
    _stage_fake(tmp_path, monkeypatch, fake)
    files, proj = _loader_args(m)
    with pytest.raises(SystemExit) as e:
        m.load_liveness_receipt(files, proj)
    assert "STALE" in str(e.value)


def test_probe4_loader_reads_branches_from_receipt_not_hardcoded(tmp_path, monkeypatch):
    """Even with a valid-looking v2 receipt (bindings all correct), a NON-empty
    branch list must kill it — the old loader ignored the field and wrote a
    hardcoded 0."""
    import make_executable_freeze_manifest as m

    core = _upgrade_fake_to_v2(m, _fake_liveness_core())
    core["tool_sha256"] = m.sha256_file(GATE / "armc_liveness_preflight.py")
    core["armc_branch_liveness"]["run_epoch_invocations"] = 2
    fake = {"core": core, "core_sha256": core_sha(core), "volatile": {}}
    _stage_fake(tmp_path, monkeypatch, fake)
    files, proj = _loader_args(m)
    with pytest.raises(SystemExit) as e:
        m.load_liveness_receipt(files, proj)
    assert "arm-conditional branches present" in str(e.value)


def test_probe4_real_receipt_accepted(monkeypatch, _test_anchor_signers):
    """The receipt on disk must satisfy the FULL v2 loader against the REAL
    pins and the CURRENT projection — this is exactly the check the freeze
    generator runs, so it doubles as the staleness canary: it fails the moment
    any counting-path file changes without a receipt re-run.

    RR#5.5 B2: the committed receipt's captured chain is ok=false (branch-2
    cycle-break form), so the loader re-derives legality against the REAL
    coordinator-signed preflight anchor — which also requires restoring the
    REAL pinned allowed-signers (the autouse fixture swaps in the test key)."""
    import make_executable_freeze_manifest as m
    import validate_launch_bundles as v

    monkeypatch.setattr(v, "COORDINATOR_ALLOWED_SIGNERS", _test_anchor_signers)
    monkeypatch.setenv(v.ANCHOR_ENV, "/home/admin/.harness/rr5-anchors/preflight.json")
    files, _ = _loader_args(m)
    proj = m.fac_source_projection()
    out = m.load_liveness_receipt(files, proj)
    assert out["arm_conditional_branches_in_counting_path"] == 0
    assert out["negative_control"]["search_begin"] == 0
    assert out["source_bindings"]["rpo_head"] == m.EXPECTED_RPO_HEAD


# ---------------------------------------------------------------------------
# PROBE 5 — the 000…0 slot fill must be refused
# ---------------------------------------------------------------------------
def test_probe5_zero_hash_fill_surface_is_gone():
    """The coordinator drove --artifact-sha256 000…0 into a good slot: FILLED,
    exit 0. The operator-supplied-hash surface must not exist."""
    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    r = subprocess.run(
        [
            PY,
            str(GATE / "fill_checkpoint_slot.py"),
            "--slot",
            "lin-cf-s01",
            "--status",
            "FILLED",
            "--artifact-sha256",
            "0" * 64,
            "--expect-parent-sha",
            cur,
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode == 2
    assert "unrecognized arguments" in r.stderr
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


def test_probe5_nonexistent_artifact_path_refused():
    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    r = subprocess.run(
        [
            PY,
            str(GATE / "fill_checkpoint_slot.py"),
            "--slot",
            "lin-cf-s01",
            "--status",
            "FILLED",
            "--artifact-path",
            "/tmp/nope.tar.gz",
            "--production-receipt",
            "/tmp/nope.json",
            "--expect-parent-sha",
            cur,
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0 and "does not exist" in r.stdout + r.stderr
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


def test_probe5_failed_by_choice_refused():
    """FAILED after seeing quality, with no reproduced deterministic failure, is
    the completion-conditioned selection the failed-slot rule forbids."""
    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    r = subprocess.run(
        [
            PY,
            str(GATE / "fill_checkpoint_slot.py"),
            "--slot",
            "lin-cf-s01",
            "--status",
            "FAILED",
            "--reason",
            "the number looked bad",
            "--expect-parent-sha",
            cur,
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "bounded attempt receipts" in r.stdout + r.stderr
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


def test_probe5_wrong_parent_sha_refused():
    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    r = subprocess.run(
        [
            PY,
            str(GATE / "fill_checkpoint_slot.py"),
            "--slot",
            "lin-cf-s01",
            "--status",
            "FAILED",
            "--reason",
            "x",
            "--expect-parent-sha",
            "0" * 64,
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0 and "unexpected base" in r.stdout + r.stderr
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


# ---------------------------------------------------------------------------
# PROBE 6 — grandfather set == measured engine-vendoring census
# ---------------------------------------------------------------------------
def test_probe6_grandfather_set_equals_measured_census():
    """Equality, not containment: an entry that no longer corresponds to a
    measured engine-vendoring frozen bundle makes the census unauditable (the
    set had 14 entries, 4 matching, 10 orphans). And the census population is
    the 17 PINNED entries — never a filesystem glob, which is what produced the
    false '8 including both S1' claim."""
    import engine_guard

    freeze = json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    measured = {
        v["sha256"]
        for v in freeze["frozen_bundles"].values()
        if engine_guard.vendored_engines(Path(v["path"]))
    }
    assert engine_guard.GRANDFATHERED_BUNDLE_SHA256 == measured, (
        "grandfather set drifted from the measured census"
    )


def test_probe6_s1_sealed_vendor_nothing():
    freeze = json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    for bid in ("metamon_router_r1", "pokechamp_macro_minimax_r1"):
        assert not freeze["frozen_bundles"][bid].get("vendored_engines")


def test_probe6_renamed_bundle_still_bound_by_content(tmp_path):
    """Filename-prefix matching was the original defect: a rename defeated it."""
    import engine_guard

    freeze = json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    src = Path(freeze["frozen_bundles"]["search_s18_oppmodel"]["path"])
    renamed = tmp_path / "totally_innocent_checkpoint.tar.gz"
    renamed.write_bytes(src.read_bytes())
    assert engine_guard.check_bundle(renamed) == []  # grandfathered by CONTENT sha


# ---------------------------------------------------------------------------
# Q-A — the binding replacement for the withdrawn numeric-equality requirement
# (RR#4: the prior version compared the same expression to itself and drove an
# isolated local stub — it exercised no production resolution at all. These
# tests drive the REAL dispatch: harness_bridge.resolve_curriculum_battery /
# run_arm_{b,c}_with_stub_harness, the exact functions pilot_run uses.)
# ---------------------------------------------------------------------------
def _hb():
    sys.path.insert(0, str(GATE / "armb-pilot"))
    import harness_bridge

    return harness_bridge


def test_qa_both_arms_resolve_to_the_same_battery_function_object():
    """Through the PRODUCTION resolver, arm-parameterized — not the same
    expression written twice. An alias/match/dict-dispatch fork anywhere in
    the dispatch breaks the identity this asserts."""
    pytest.importorskip("kaggle_environments")  # requires pinned venv
    hb = _hb()
    rb = hb.resolve_curriculum_battery("B")
    rc = hb.resolve_curriculum_battery("C")
    assert rb is rc is hb.HarnessBridge.curriculum_battery
    with pytest.raises(ValueError):
        hb.resolve_curriculum_battery("D")
    # and ARM-C's module must never own a counting path of its own
    import armc_evolution

    src = Path(armc_evolution.__file__).read_text()
    for token in ("search_begin", "search_calls", "curriculum_battery"):
        assert token not in src, (
            f"armc_evolution references {token!r} — ARM-C must not touch the counter"
        )


def test_qa_pilot_runner_battery_goes_through_the_dispatch():
    """Wiring proof (the RR#3 lesson: a dispatch nobody calls is not a
    dispatch): the ARM-B runner obtains its battery via run_arm_generation and
    no method-literal battery call remains in the runner."""
    src = (GATE / "armb-pilot" / "pilot_run.py").read_text()
    assert "run_arm_generation(" in src
    assert ".curriculum_battery(" not in src, (
        "pilot_run bypasses resolve_curriculum_battery with a method literal"
    )


class _StubHarness:
    """Injected battery/counter object: deterministic, engine-free, and shaped
    like the production accounting so receipts are comparable."""

    def __init__(self):
        self.counter = {"search_begin": 0}
        self.dispatch_targets: list[int] = []

    def curriculum_battery(
        self,
        q,
        child_seed,
        target_decisions,
        min_eval_games,
        gen,
        max_games_hard_cap,
    ):
        self.dispatch_targets.append(id(self))
        n_games = min(max_games_hard_cap, target_decisions // 10)
        for _ in range(n_games):
            self.counter["search_begin"] += 1
        return {
            "target_decisions": target_decisions,
            "realized_decisions": n_games * 10,
            "completed_games": n_games,
            "search_calls": {
                "learner_search_begin": self.counter["search_begin"],
                "per_opponent_search_begin": dict.fromkeys(sorted(q), n_games),
            },
            "decision_totals": {"total": n_games * 10},
            "child_seed": child_seed,
            "gen": gen,
        }


def test_qa_stub_harness_through_real_dispatch_identical_accounting():
    """run_arm_b/c_with_stub_harness — the REAL dispatch — must end in the
    SAME injected battery/counter object for both arms and produce IDENTICAL
    accounting receipts. Deterministic stub => assertable equality, which
    numeric equality on real engine batteries can never support
    (std::random_device)."""
    pytest.importorskip("kaggle_environments")  # requires pinned venv
    hb = _hb()
    stub = _StubHarness()
    kw = dict(
        q={"opp_a": 0.5, "opp_b": 0.5},
        child_seed=7,
        target_decisions=200,
        min_eval_games=1,
        gen=0,
        max_games_hard_cap=50,
    )
    rb = hb.run_arm_b_with_stub_harness(stub, **kw)
    stub.counter["search_begin"] = 0
    rc = hb.run_arm_c_with_stub_harness(stub, **kw)
    assert rb["arm"] == "B" and rc["arm"] == "C"
    assert (
        rb["dispatch"]
        == rc["dispatch"]
        == ("harness_bridge.resolve_curriculum_battery")
    )
    # identical accounting receipts through the one shared path
    assert rb["battery"] == rc["battery"]
    # both dispatches landed on the SAME injected object — no per-arm target
    assert stub.dispatch_targets == [id(stub), id(stub)]


# ---------------------------------------------------------------------------
# RR#4 adversarial probes — the three holes found in Round 4, reproduced
# exactly as the reviewer drove them, asserted refused. (The 23-test suite
# was ruled "good direction, NOT a complete verification receipt" precisely
# because it missed these.)
# ---------------------------------------------------------------------------
def _split_section() -> dict:
    return json.loads((GATE / "split-manifest.json").read_bytes())["rotation_freeze"]


def _slot_row(slot_id: str) -> dict:
    return next(
        s for s in _split_section()["checkpoint_slots"] if s["slot_id"] == slot_id
    )


def _run_fill(args: list[str]) -> subprocess.CompletedProcess:
    return subprocess.run(
        [PY, str(GATE / "fill_checkpoint_slot.py"), *args],
        capture_output=True,
        text=True,
    )


def test_adv_fabricated_filled_receipt_refused(tmp_path):
    """RR#4 F1 verbatim: {config_sha256:'fabricated',
    executable_manifest_sha256:'fabricated', host:'wrong-host',
    liveness_bar:{pass:true,quality_blind:true}} + a REAL but arbitrary
    artifact file got a FILLED at exit 0 from the truthy-check version. Every
    provenance field is now verified, so this dies at the freeze-identity
    check — before host, config, or interpreter are even reached."""
    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    slot = _slot_row("lin-cf-s01")
    artifact = tmp_path / "innocent-checkpoint.tar.gz"
    artifact.write_bytes(b"real bytes with zero production story")
    core = {
        "schema": "checkpoint-production-receipt/v1",
        "slot_id": slot["slot_id"],
        "slice_id": slot["slice_id"],
        "train_seed": slot["train_seed"],
        "config_sha256": "fabricated",
        "executable_manifest_sha256": "fabricated",
        "training_command_sha256": "fabricated",
        "host": "wrong-host",
        "artifact_sha256": sha256_bytes(artifact.read_bytes()),
        "liveness_bar": {"pass": True, "quality_blind": True},
    }
    rec = tmp_path / "fabricated-production.json"
    rec.write_text(json.dumps({"core": core, "core_sha256": core_sha(core)}))
    r = _run_fill(
        [
            "--slot",
            slot["slot_id"],
            "--status",
            "FILLED",
            "--artifact-path",
            str(artifact),
            "--production-receipt",
            str(rec),
            "--expect-parent-sha",
            cur,
        ]
    )
    assert r.returncode != 0, "fabricated FILLED receipt was ACCEPTED"
    # RR#5: a v1-schema fabricated receipt is now refused at the schema gate
    # (the deeper field checks still apply to v2 fakes — see the RR#5 item-6
    # tests below which build structurally-complete v2 fakes).
    assert "schema" in r.stdout + r.stderr
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


def test_adv_unsigned_fabricated_failed_refused(tmp_path):
    """RR#4 F2 verbatim: {outcome:'FAILED', deterministic_failure:true,
    failure_signature:'fake'} with NO core_sha256 and NO provenance killed
    lin-cf-s01 at exit 0 — the completion-conditioned selection leak in a new
    door. Unsigned attempt evidence must be refused before its content is
    even considered."""
    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    slot = _slot_row("lin-cf-s01")
    paths = []
    for i in range(2):
        p = tmp_path / f"fake-attempt-{i}.json"
        p.write_text(
            json.dumps(
                {
                    "core": {
                        "slot_id": slot["slot_id"],
                        "slice_id": slot["slice_id"],
                        "train_seed": slot["train_seed"],
                        "outcome": "FAILED",
                        "deterministic_failure": True,
                        "failure_signature": "fake",
                    }
                }
            )
        )
        paths.append(str(p))
    r = _run_fill(
        [
            "--slot",
            slot["slot_id"],
            "--status",
            "FAILED",
            "--attempt-receipts",
            *paths,
            "--reason",
            "operator saw the number and preferred FAILED",
            "--expect-parent-sha",
            cur,
        ]
    )
    assert r.returncode != 0, "unsigned fabricated FAILED was ACCEPTED"
    assert "core_sha256" in r.stdout + r.stderr or "schema" in r.stdout + r.stderr
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


def test_adv_dispatch_has_no_per_arm_fork_surface():
    """RR#4 Q-A hole, adversarial form: the dispatch layer must contain no
    per-arm branching beyond the membership guard — a fork of ANY shape
    (if/match/dict-dispatch/alias) would surface as either an arm-conditional
    node inside the dispatch functions or a broken identity in
    test_qa_both_arms_resolve_to_the_same_battery_function_object."""
    import ast

    src = (GATE / "armb-pilot" / "harness_bridge.py").read_text()
    tree = ast.parse(src)
    for fn in ast.walk(tree):
        if not isinstance(fn, ast.FunctionDef):
            continue
        if fn.name not in ("resolve_curriculum_battery", "run_arm_generation"):
            continue
        for node in ast.walk(fn):
            # the ONLY admissible test on `arm` is the membership guard
            if isinstance(node, (ast.If, ast.IfExp)):
                seg = ast.get_source_segment(src, node.test) or ""
                assert "not in ARMS" in seg or "arm" not in seg.lower(), (
                    f"{fn.name}: arm-conditional branch {seg!r}"
                )
            assert not isinstance(node, ast.Match), (
                f"{fn.name}: match statement — a fork surface"
            )
            if isinstance(node, ast.Subscript):
                seg = ast.get_source_segment(src, node) or ""
                assert "arm" not in seg.lower(), (
                    f"{fn.name}: arm-keyed subscript {seg!r} — dict-dispatch fork"
                )


# ---------------------------------------------------------------------------
# RR#5 item 6 — the three new adversarial probes for the round-5 attacks.
# (i) nested-instrumentation / no top-level stamp lives in the armb-pilot suite
#     (test_validate_receipt.py::TestLaunchStampRR5Item1); (ii) and (iii) here.
#
# RR#5.5 B4: anchors now require a REAL detached ssh signature over the
# canonical core bytes. Tests sign with a session-scoped throwaway ed25519
# key; an autouse fixture points the verifier's pinned allowed-signers at
# that key (the REAL coordinator key never enters tests — its refusal of
# test-signed anchors is itself a committed probe below).
# ---------------------------------------------------------------------------
_SIGN_DIR: Path | None = None


def _test_signing_dir() -> Path:
    global _SIGN_DIR
    if _SIGN_DIR is None:
        d = Path(tempfile.mkdtemp(prefix="anchor-test-signing-"))
        subprocess.run(
            [
                "ssh-keygen",
                "-t",
                "ed25519",
                "-f",
                str(d / "key"),
                "-N",
                "",
                "-q",
                "-C",
                "test-anchor-signing",
            ],
            check=True,
        )
        _SIGN_DIR = d
    return _SIGN_DIR


def _test_allowed_signers_line() -> str:
    pub = (_test_signing_dir() / "key.pub").read_text().strip()
    return f'rq-tcg-coordinator namespaces="rq-tcg-anchor" {pub}\n'


@pytest.fixture(autouse=True)
def _test_anchor_signers(monkeypatch):
    """Every test verifies anchor signatures against the session TEST key;
    tests that probe the real pinned key restore the saved original."""
    import validate_launch_bundles as v

    original = v.COORDINATOR_ALLOWED_SIGNERS
    monkeypatch.setattr(v, "COORDINATOR_ALLOWED_SIGNERS", _test_allowed_signers_line())
    yield original


def _sign_anchor_core(core: dict, sig_path: Path) -> None:
    d = _test_signing_dir()
    cb = json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    tmp = sig_path.parent / (sig_path.name + ".corebytes")
    tmp.write_bytes(cb)
    subprocess.run(
        [
            "ssh-keygen",
            "-Y",
            "sign",
            "-f",
            str(d / "key"),
            "-n",
            "rq-tcg-anchor",
            str(tmp),
        ],
        check=True,
        capture_output=True,
    )
    (tmp.parent / (tmp.name + ".sig")).rename(sig_path)
    tmp.unlink()


def _anchor_file(
    tmp_path, core: dict, name: str = "anchor.json", sign: bool = True
) -> str:
    p = tmp_path / name
    p.write_text(json.dumps({"core": core, "core_sha256": core_sha(core)}))
    if sign:
        _sign_anchor_core(core, Path(str(p) + ".sig"))
    return str(p)


def _section5a_launch_anchor(
    *,
    split_path: Path | None = None,
    freeze_path: Path | None = None,
    authorized_slot_ids: list[str] | None = None,
    **overrides,
) -> dict:
    """A complete RR#7 §5A launch core over the supplied sandbox bytes."""
    import produce_checkpoint as pc

    split_path = split_path or (GATE / "split-manifest.json")
    freeze_path = freeze_path or (GATE / "executable-freeze-manifest.json")
    section = json.loads(split_path.read_bytes())["rotation_freeze"]
    core = {
        "kind": "launch",
        "capsule_id": "rr7-section5a-test",
        "coordinator": "test",
        "root_verifier_sha256": sha256_bytes(
            (GATE / "validate_launch_bundles.py").read_bytes()
        ),
        "expected_split_sha256": sha256_bytes(split_path.read_bytes()),
        "executable_freeze_manifest_sha256": sha256_bytes(freeze_path.read_bytes()),
        "split_immutable_projection_sha256": pc._immutable_projection(section),
        "authorized_slot_ids": (
            sorted(row["slot_id"] for row in section["checkpoint_slots"])
            if authorized_slot_ids is None
            else authorized_slot_ids
        ),
        "not_after_utc": "2099-01-01T00:00:00Z",
        "producer_wrapper_sha256": sha256_bytes(
            (GATE / "produce_checkpoint.py").read_bytes()
        ),
        "fill_validator_sha256": sha256_bytes(
            (GATE / "fill_checkpoint_slot.py").read_bytes()
        ),
        "liveness_validator_sha256": sha256_bytes(
            (GATE / "validate_liveness_receipt.py").read_bytes()
        ),
        "archive_encoder_sha256": sha256_bytes(
            (GATE / "canonical_ustar.py").read_bytes()
        ),
    }
    core.update(overrides)
    return core


def _verified_section5a_anchor(tmp_path, *, name="section5a-anchor.json", **kwargs):
    import validate_launch_bundles as v

    core = _section5a_launch_anchor(**kwargs)
    return v.load_anchor(_anchor_file(tmp_path, core, name))


def _section5a_sandbox_manifests(tmp_path):
    """Regenerated-in-memory manifest pair for source-first producer tests.

    The committed manifest intentionally stays stale until receipts-last.  A
    positive unit test therefore uses explicit sandbox bytes with the new
    census/contract pins instead of weakening the production check.
    """
    import produce_checkpoint as pc

    freeze = json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    source_rows = {
        "fac:gate/produce_checkpoint.py": GATE / "produce_checkpoint.py",
        "fac:gate/fill_checkpoint_slot.py": GATE / "fill_checkpoint_slot.py",
        "fac:gate/validate_liveness_receipt.py": GATE / "validate_liveness_receipt.py",
        "fac:gate/canonical_ustar.py": GATE / "canonical_ustar.py",
    }
    files = freeze.setdefault("files", {})
    for key, path in source_rows.items():
        row = files.setdefault(
            key,
            {
                "role": "section5a sandbox census",
                "tier": "interface-pinned",
            },
        )
        row["sha256"] = sha256_bytes(path.read_bytes())
        row["bytes"] = path.stat().st_size
    for contract in freeze["checkpoint_command_contract"].values():
        if not isinstance(contract, dict):
            continue
        contract["producer_wrapper_sha256"] = files["fac:gate/produce_checkpoint.py"][
            "sha256"
        ]
        contract["validator_sha256"] = files["fac:gate/fill_checkpoint_slot.py"][
            "sha256"
        ]
        contract["liveness_validator_sha256"] = files[
            "fac:gate/validate_liveness_receipt.py"
        ]["sha256"]
        contract["archive_encoder_sha256"] = files["fac:gate/canonical_ustar.py"][
            "sha256"
        ]
    freeze_path = tmp_path / "section5a-freeze.json"
    freeze_path.write_bytes(pc._canonical(freeze))

    split = json.loads((GATE / "split-manifest.json").read_bytes())
    section = split["rotation_freeze"]
    section["bound_manifests"]["executable_freeze_manifest_sha256"] = sha256_bytes(
        freeze_path.read_bytes()
    )
    section["immutable_projection_sha256"] = pc._immutable_projection(section)
    split_path = tmp_path / "section5a-split.json"
    split_path.write_bytes(pc._canonical(split))
    return split_path, freeze_path


def test_adv_rr5_structurally_complete_fake_filled_refused(tmp_path):
    """RR#5 F1: a v2 receipt that is structurally complete AND core-hash
    self-consistent (pinned interpreter, correct slot/slice/seed, current
    freeze, self-hashed config, real artifact) is STILL refused, because it was
    not emitted by the pinned producer wrapper and has no independent
    launch-ledger entry — hash is integrity, not authenticity."""
    import fill_checkpoint_slot as fcs
    import json as _json

    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    slot = _slot_row("lin-cf-s01")
    freeze = _json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    contract = freeze["checkpoint_command_contract"]["linear"]
    argv = fcs.expected_argv_for_slot(contract, slot)
    artifact = tmp_path / "cp.tar.gz"
    artifact.write_bytes(b"a structurally complete but unauthentic checkpoint")
    core = {
        "schema": "checkpoint-production-receipt/v2",
        "slot_id": slot["slot_id"],
        "slice_id": slot["slice_id"],
        "train_seed": slot["train_seed"],
        "executable_manifest_sha256": sha256_bytes(
            (GATE / "executable-freeze-manifest.json").read_bytes()
        ),
        "config_sha256": contract["config_sha256"],
        "interpreter_sha256": contract["argv_contract"]["interpreter_sha256"],
        "host": __import__("platform").node(),
        "argv": argv,
        "training_command_sha256": sha256_bytes(
            _json.dumps(argv, separators=(",", ":")).encode()
        ),
        "artifact_sha256": sha256_bytes(artifact.read_bytes()),
        "exit_code": 0,
        # forged wrapper sha + no ledger entry + inline liveness booleans
        "wrapper_tool_sha256": "f" * 64,
        "cwd": "/home/admin/gh/ready-player-one-ptcg",
        "start_utc": "2026-07-17T00:00:00Z",
        "end_utc": "2026-07-17T00:05:00Z",
        "stdout_sha256": "a" * 64,
        "stderr_sha256": "b" * 64,
        "launch_ledger_id": "no-such-entry",
    }
    rec = tmp_path / "fake-v2-production.json"
    rec.write_text(_json.dumps({"core": core, "core_sha256": core_sha(core)}))
    r = _run_fill(
        [
            "--slot",
            slot["slot_id"],
            "--status",
            "FILLED",
            "--artifact-path",
            str(artifact),
            "--production-receipt",
            str(rec),
            "--expect-parent-sha",
            cur,
        ]
    )
    assert r.returncode != 0, "structurally-complete fake v2 FILLED was ACCEPTED"
    out = r.stdout + r.stderr
    assert "wrapper" in out or "ledger" in out
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


def test_adv_rr5_jointly_replaced_chain_fails_external_anchor(tmp_path, monkeypatch):
    """RR#5 V1: a modifier who jointly replaces split content + its own
    projection hash + bound freeze sha + freeze content + pools keeps the chain
    internally consistent, so a self-referential check accepts it. The external
    anchor kills this: the EXPECTED split sha comes from the anchor, and the
    on-disk (jointly-replaced) split will not match it."""
    import validate_launch_bundles as v

    # a self-consistent but UNAUTHORIZED split is whatever is on disk; the
    # anchor names a DIFFERENT expected split sha, so the chain must refuse.
    real_split_sha = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    verifier_sha = sha256_bytes((GATE / "validate_launch_bundles.py").read_bytes())
    wrong = _section5a_launch_anchor(
        capsule_id="test-capsule",
        root_verifier_sha256=verifier_sha,
        expected_split_sha256="0" * 64,  # NOT the on-disk split
    )
    anchor = v.load_anchor(_anchor_file(tmp_path, wrong), kind="launch")
    with pytest.raises(SystemExit) as e:
        v.split_root_of_trust(anchor)
    assert "anchor's expected split sha" in str(e.value)

    # and with the CORRECT expected split sha + authorized verifier, the chain
    # gets PAST the anchor gate (it then proceeds to the projection/freeze
    # checks — which hold on the real tree).
    ok = dict(wrong, expected_split_sha256=real_split_sha)
    good = v.load_anchor(_anchor_file(tmp_path, ok, "ok.json"), kind="launch")
    # should not raise on the anchor gate itself
    try:
        v.split_root_of_trust(good)
    except SystemExit as e:
        # any failure here must be DOWNSTREAM of the anchor gate, never the
        # anchor mismatch we just proved fires on a wrong sha. (mid-chain,
        # with code edited but the freeze not yet regenerated, the chain
        # legitimately dies on the freeze's self-pins — still downstream.)
        assert "anchor's expected split sha" not in str(e)


@pytest.mark.parametrize(
    "field",
    [
        "expected_split_sha256",
        "executable_freeze_manifest_sha256",
        "split_immutable_projection_sha256",
        "authorized_slot_ids",
        "producer_wrapper_sha256",
        "fill_validator_sha256",
        "liveness_validator_sha256",
        "archive_encoder_sha256",
        "not_after_utc",
    ],
)
def test_rr7_section5a_launch_anchor_superset_is_mandatory(tmp_path, field):
    """Signature authenticity is checked first; then every production field
    is mandatory instead of present-if-supplied."""
    import validate_launch_bundles as v

    core = _section5a_launch_anchor()
    del core[field]
    with pytest.raises(SystemExit, match=field):
        v.load_anchor(_anchor_file(tmp_path, core, f"missing-{field}.json"))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("expected_split_sha256", "A" * 64),
        ("producer_wrapper_sha256", "0" * 63),
        ("authorized_slot_ids", []),
        ("authorized_slot_ids", ["lin-cf-s01", "lin-cf-s01"]),
        ("authorized_slot_ids", ["lin-cf-s02", "lin-cf-s01"]),
        ("not_after_utc", "2026-07-18 00:00:00"),
        ("not_after_utc", "2000-01-01T00:00:00Z"),
    ],
)
def test_rr7_section5a_launch_anchor_malformed_or_expired_refused(
    tmp_path, field, value
):
    import validate_launch_bundles as v

    core = _section5a_launch_anchor(**{field: value})
    with pytest.raises(SystemExit):
        v.load_anchor(_anchor_file(tmp_path, core, f"bad-{field}.json"))


@pytest.mark.parametrize(
    "field",
    [
        "expected_split_sha256",
        "executable_freeze_manifest_sha256",
        "split_immutable_projection_sha256",
        "producer_wrapper_sha256",
        "fill_validator_sha256",
        "liveness_validator_sha256",
        "archive_encoder_sha256",
        "root_verifier_sha256",
    ],
)
def test_rr7_section5a_producer_rechecks_every_anchor_hash(
    tmp_path, monkeypatch, field
):
    import produce_checkpoint as pc

    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    slot = _slot_row("lin-cf-s01")
    core = _section5a_launch_anchor(split_path=split_path, freeze_path=freeze_path)
    core[field] = "0" * 64
    import validate_launch_bundles as v

    anchor = v.load_anchor(_anchor_file(tmp_path, core, f"bad-{field}.json"))
    with pytest.raises(SystemExit):
        pc.verify_launch_anchor_object(anchor, slot)


def test_rr7_section5a_wrong_slot_refused_before_intent(tmp_path, monkeypatch):
    """Acceptance test 13: authorization failure leaves no ledger INTENT."""
    import produce_checkpoint as pc

    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    slot = dict(_slot_row("lin-cf-s01"), slot_id="not-a-frozen-slot")
    freeze = json.loads(freeze_path.read_bytes())
    contract = freeze["checkpoint_command_contract"][slot["family"]]
    anchor = _verified_section5a_anchor(
        tmp_path, split_path=split_path, freeze_path=freeze_path
    )
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(pc, "LAUNCH_LEDGER", ledger)
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    monkeypatch.setattr(pc, "recover_open_intents", lambda: [])
    with pytest.raises(SystemExit, match="does not authorize slot"):
        pc.run_terminal_execution(
            slot,
            contract,
            phase="test",
            attempt_id="a1",
            launch_anchor=anchor,
            jail_dir=tmp_path / "jail",
            receipt_out=tmp_path / "receipt.json",
        )
    assert not ledger.exists()


def test_rr7_section5a_plain_dict_never_authorizes():
    import produce_checkpoint as pc

    with pytest.raises(SystemExit, match="signature-verified value"):
        pc.verify_launch_anchor_object(
            _section5a_launch_anchor(), _slot_row("lin-cf-s01")
        )


def test_rr7_section5a_verified_anchor_value_is_immutable(tmp_path):
    anchor = _verified_section5a_anchor(tmp_path, name="immutable-anchor.json")
    original_core = anchor.core
    original_sha = anchor.core_sha256

    with pytest.raises(AttributeError):
        anchor.core_sha256 = "0" * 64
    with pytest.raises(AttributeError):
        anchor._core_bytes = b"{}"
    with pytest.raises(TypeError):
        anchor[0] = b"{}"

    # The exposed core is a fresh parse, not mutable backing storage.
    forged_view = anchor.core
    forged_view["capsule_id"] = "forged"
    assert anchor.core == original_core
    assert anchor.core_sha256 == original_sha


def test_rr7_section5a_partial_frozen_slot_set_refused(tmp_path, monkeypatch):
    import produce_checkpoint as pc

    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    slot = _slot_row("lin-cf-s01")
    anchor = _verified_section5a_anchor(
        tmp_path,
        name="partial-slots.json",
        split_path=split_path,
        freeze_path=freeze_path,
        authorized_slot_ids=[slot["slot_id"]],
    )
    with pytest.raises(SystemExit, match="exactly the sorted frozen"):
        pc.verify_launch_anchor_object(anchor, slot)


def test_rr7_section5a_expiry_is_rechecked_before_intent(tmp_path, monkeypatch):
    import produce_checkpoint as pc

    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    anchor = _verified_section5a_anchor(
        tmp_path,
        name="future-then-expired.json",
        split_path=split_path,
        freeze_path=freeze_path,
        not_after_utc="2099-01-01T00:00:00Z",
    )
    monkeypatch.setattr(pc.time, "time", lambda: 4_102_444_800)  # 2100-01-01 UTC
    with pytest.raises(SystemExit, match="expired"):
        pc.verify_launch_anchor_object(anchor, _slot_row("lin-cf-s01"))


def test_rr7_section5a_archive_source_drift_refused_before_intent(
    tmp_path, monkeypatch
):
    """The anchor's archive pin is rooted in the freeze census, and changing
    the source bytes after that freeze refuses before a ledger row exists."""
    import produce_checkpoint as pc

    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    ledger = tmp_path / "ledger.jsonl"
    monkeypatch.setattr(pc, "LAUNCH_LEDGER", ledger)
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    monkeypatch.setattr(pc, "recover_open_intents", lambda: [])
    drifted = tmp_path / "canonical_ustar.py"
    drifted.write_bytes((GATE / "canonical_ustar.py").read_bytes() + b"\n# drift\n")
    monkeypatch.setitem(
        pc.PRODUCTION_ANCHOR_HASH_PATHS, "archive_encoder_sha256", drifted
    )
    anchor = _verified_section5a_anchor(
        tmp_path,
        name="archive-drift.json",
        split_path=split_path,
        freeze_path=freeze_path,
    )
    slot = _slot_row("lin-cf-s01")
    contract = json.loads(freeze_path.read_bytes())["checkpoint_command_contract"][
        slot["family"]
    ]
    with pytest.raises(SystemExit, match="archive_encoder_sha256"):
        pc.run_terminal_execution(
            slot,
            contract,
            phase="test",
            attempt_id="a1",
            launch_anchor=anchor,
            jail_dir=tmp_path / "jail",
            receipt_out=tmp_path / "receipt.json",
        )
    assert not ledger.exists()


def test_adv_rr5_validated_launch_requires_anchor(monkeypatch):
    """A validated launch with no external anchor must fail-closed — the split
    may not authenticate itself (RR#5 V1)."""
    import validate_launch_bundles as v

    monkeypatch.delenv(v.ANCHOR_ENV, raising=False)
    with pytest.raises(SystemExit) as e:
        v.validate()
    assert v.ANCHOR_ENV in str(e.value)


def test_adv_rr5_projection_impls_agree():
    """The inline projection in validate_launch_bundles (which killed the
    import-fill_checkpoint_slot hole) must stay byte-identical to the fill
    tool's and the rotation-freeze generator's."""
    import json as _json

    import fill_checkpoint_slot as fcs
    import make_rotation_freeze as mrf
    import validate_launch_bundles as v

    section = _json.loads((GATE / "split-manifest.json").read_bytes())[
        "rotation_freeze"
    ]
    a = v.immutable_projection(section)
    b = fcs.immutable_projection(section)
    c = mrf.immutable_projection(section)
    assert a == b == c


# ---------------------------------------------------------------------------
# RR#5.5 B1 — the round-5 audit's committed adversarial batch:
# (1) the structurally-complete fake-FAILED forgery (the missing half of
#     verdict test 2); (2) the cycle-break refusal paths, executed rather
#     than code-read; (3) the B3 liveness-validator byte-pin; (4) the B4
#     anchor-signature teeth; (5) the A2 execution_context fail-closed gate;
#     (6) the rpo launch verifier's wrong-fac-verifier-sha refusal branch
#     (fac-side subprocess test, temp-dir jail with a TEST signers file).
# ---------------------------------------------------------------------------
def _attempt_core(slot, contract, argv, attempt_id: str, ledger_id: str) -> dict:
    """A structurally COMPLETE attempt core: every schema/provenance field
    present and self-consistent — only wrapper authenticity + ledger backing
    are forged. Mirrors the fake-FILLED construction (RR#5 F1) for FAILED."""
    import json as _json
    import platform as _platform

    sig = sha256_bytes(b"reproduced deterministic import failure stderr")
    return {
        "schema": "checkpoint-attempt-receipt/v2",
        "slot_id": slot["slot_id"],
        "slice_id": slot["slice_id"],
        "train_seed": slot["train_seed"],
        "executable_manifest_sha256": sha256_bytes(
            (GATE / "executable-freeze-manifest.json").read_bytes()
        ),
        "config_sha256": contract["config_sha256"],
        "interpreter_sha256": contract["argv_contract"]["interpreter_sha256"],
        "host": _platform.node(),
        "argv": argv,
        "training_command_sha256": sha256_bytes(
            _json.dumps(argv, separators=(",", ":")).encode()
        ),
        "outcome": "FAILED",
        "exit_code": 1,
        "failure_category": "import-failure",
        "failure_signature": sig,
        "attempt_id": attempt_id,
        "wrapper_tool_sha256": "f" * 64,  # forged — not the pinned producer
        "cwd": "/home/admin/gh/ready-player-one-ptcg",
        "start_utc": "2026-07-17T00:00:00Z",
        "end_utc": "2026-07-17T00:05:00Z",
        "stdout_sha256": "a" * 64,
        "stderr_sha256": sig,
        "launch_ledger_id": ledger_id,  # no such ledger entry exists
    }


def test_adv_rr55_structurally_complete_fake_failed_refused(tmp_path):
    """RR#5.5 B1(1): TWO attempt receipts that are structurally complete,
    core-hash self-consistent, same argv, same derived failure signature,
    distinct attempt ids, frozen failure category — STILL refused, because
    neither was emitted by the pinned producer wrapper and neither has an
    independent launch-ledger entry. A fabricated deterministic failure is
    the completion-conditioned selection leak in a new door."""
    import json as _json

    import fill_checkpoint_slot as fcs

    cur = sha256_bytes((GATE / "split-manifest.json").read_bytes())
    slot = _slot_row("lin-cf-s01")
    freeze = _json.loads((GATE / "executable-freeze-manifest.json").read_bytes())
    contract = freeze["checkpoint_command_contract"]["linear"]
    argv = fcs.expected_argv_for_slot(contract, slot)
    paths = []
    for i in (1, 2):
        core = _attempt_core(slot, contract, argv, f"attempt-{i}", f"no-entry-{i}")
        p = tmp_path / f"fake-attempt-{i}.json"
        p.write_text(_json.dumps({"core": core, "core_sha256": core_sha(core)}))
        paths.append(str(p))
    r = _run_fill(
        [
            "--slot",
            slot["slot_id"],
            "--status",
            "FAILED",
            "--attempt-receipts",
            *paths,
            "--reason",
            "reproduced deterministic import failure (forged)",
            "--expect-parent-sha",
            cur,
        ]
    )
    assert r.returncode != 0, "structurally-complete fake FAILED was ACCEPTED"
    out = r.stdout + r.stderr
    assert "wrapper" in out or "ledger" in out
    # the split manifest must be untouched by the refused fill
    assert sha256_bytes((GATE / "split-manifest.json").read_bytes()) == cur


# --- (2) cycle-break refusal paths — executed, not code-read ----------------
def _lc_with_chain(tc: dict) -> dict:
    """A captured launch_context whose nested pool-integrity core sha
    RECOMPUTES (so only the trust-chain logic is under test)."""
    pic = {"pass": True, "trust_chain": tc}
    return {
        "pool_integrity_pass": True,
        "pool_integrity_core": pic,
        "pool_integrity_core_sha256": core_sha(pic),
    }


def test_adv_rr55_cyclebreak_tampered_nested_core_refused():
    import make_executable_freeze_manifest as mefm

    lc = _lc_with_chain({"ok": True, "legal_for_preflight": True})
    lc["pool_integrity_core_sha256"] = "0" * 64  # tampered
    with pytest.raises(SystemExit) as e:
        mefm.rederive_preflight_legality(lc)
    assert "does not recompute" in str(e.value)


def test_adv_rr55_cyclebreak_ok_false_no_anchor_refused(monkeypatch):
    import make_executable_freeze_manifest as mefm
    import validate_launch_bundles as v

    monkeypatch.delenv(v.ANCHOR_ENV, raising=False)
    lc = _lc_with_chain(
        {
            "ok": False,
            "legal_for_preflight": True,  # captured word — must NOT be trusted
            "predecessor_freeze_sha256": "b" * 64,
        }
    )
    with pytest.raises(SystemExit) as e:
        mefm.rederive_preflight_legality(lc)
    assert "no preflight anchor" in str(e.value)


def test_adv_rr55_cyclebreak_nonallowlisted_root_refused(tmp_path, monkeypatch):
    """THE must-fix 2 laundering probe: captured legal_for_preflight=True and
    a self-consistent nested core, but the captured predecessor root is NOT
    in the external anchor's allowlist and the chain is ok=false. The old
    loader trusted the boolean; the re-derivation must refuse."""
    import make_executable_freeze_manifest as mefm
    import validate_launch_bundles as v

    anchor_core = {
        "kind": "preflight",
        "capsule_id": "rr55-test-preflight",
        "coordinator": "test",
        "root_verifier_sha256": sha256_bytes(
            (GATE / "validate_launch_bundles.py").read_bytes()
        ),
        "allowlisted_predecessor_freeze_sha256": ["a" * 64],
    }
    monkeypatch.setenv(v.ANCHOR_ENV, _anchor_file(tmp_path, anchor_core))
    lc = _lc_with_chain(
        {
            "ok": False,
            "legal_for_preflight": True,  # laundered word
            "predecessor_freeze_sha256": "b" * 64,  # NOT allowlisted
        }
    )
    with pytest.raises(SystemExit) as e:
        mefm.rederive_preflight_legality(lc)
    assert "not in the external preflight anchor's allowlist" in str(e.value)


def test_adv_rr55_cyclebreak_allowlisted_root_accepted(tmp_path, monkeypatch):
    import make_executable_freeze_manifest as mefm
    import validate_launch_bundles as v

    root = sha256_bytes((GATE / "executable-freeze-manifest.json").read_bytes())
    anchor_core = {
        "kind": "preflight",
        "capsule_id": "rr55-test-preflight",
        "coordinator": "test",
        "root_verifier_sha256": sha256_bytes(
            (GATE / "validate_launch_bundles.py").read_bytes()
        ),
        "allowlisted_predecessor_freeze_sha256": [root],
    }
    monkeypatch.setenv(v.ANCHOR_ENV, _anchor_file(tmp_path, anchor_core))
    lc = _lc_with_chain(
        {
            "ok": False,
            "legal_for_preflight": True,
            "predecessor_freeze_sha256": root,
        }
    )
    basis = mefm.rederive_preflight_legality(lc)
    assert "external anchor allowlist" in basis


def test_adv_rr55_cyclebreak_contradictory_boolean_refused():
    """Derivation succeeds (ok=true) but the receipt's own captured verdict
    says illegal — a contradictory receipt is refused, not 'corrected'."""
    import make_executable_freeze_manifest as mefm

    lc = _lc_with_chain({"ok": True, "legal_for_preflight": False})
    with pytest.raises(SystemExit) as e:
        mefm.rederive_preflight_legality(lc)
    assert "contradictory" in str(e.value)


# --- (3) B3: liveness-validator byte pin ------------------------------------
def test_adv_rr55_liveness_validator_byte_pin(tmp_path):
    import fill_checkpoint_slot as fcs

    real_sha = sha256_bytes((GATE / "validate_liveness_receipt.py").read_bytes())
    # correct pin -> returns the callable from EXACTLY those bytes
    fn = fcs.pinned_liveness_validator({"liveness_validator_sha256": real_sha})
    assert callable(fn)
    # wrong pin -> refused BEFORE any code from the module executes
    with pytest.raises(SystemExit) as e:
        fcs.pinned_liveness_validator({"liveness_validator_sha256": "0" * 64})
    assert "liveness_validator_sha256 pin" in str(e.value)
    # no pin -> refused
    with pytest.raises(SystemExit) as e:
        fcs.pinned_liveness_validator({})
    assert "no liveness_validator_sha256 pin" in str(e.value)


# --- (4) B4: anchor signature teeth ------------------------------------------
def test_adv_rr55_unsigned_anchor_refused(tmp_path):
    import validate_launch_bundles as v

    core = {
        "kind": "preflight",
        "capsule_id": "t",
        "coordinator": "test",
        "root_verifier_sha256": "a" * 64,
        "allowlisted_predecessor_freeze_sha256": ["b" * 64],
    }
    with pytest.raises(SystemExit) as e:
        v.load_anchor(_anchor_file(tmp_path, core, sign=False), kind="preflight")
    assert "signature" in str(e.value) and "missing" in str(e.value)


def test_adv_rr55_real_pinned_key_refuses_test_signature(
    tmp_path, monkeypatch, _test_anchor_signers
):
    """The production constant actually gates: an anchor signed by the TEST
    key must be REFUSED once the real coordinator allowed-signers line is
    restored. (If this ever passes with a test signature, the pin is dead.)"""
    import validate_launch_bundles as v

    monkeypatch.setattr(v, "COORDINATOR_ALLOWED_SIGNERS", _test_anchor_signers)
    core = {
        "kind": "preflight",
        "capsule_id": "t",
        "coordinator": "test",
        "root_verifier_sha256": "a" * 64,
        "allowlisted_predecessor_freeze_sha256": ["b" * 64],
    }
    with pytest.raises(SystemExit) as e:
        v.load_anchor(_anchor_file(tmp_path, core), kind="preflight")
    assert "signature verification FAILED" in str(e.value)


def test_adv_rr55_core_swap_after_signing_refused(tmp_path):
    """Integrity-vs-authenticity: swap the core AFTER signing and re-checksum
    it correctly — core_sha256 recomputes, so only the signature can catch
    the swap."""
    import json as _json

    import validate_launch_bundles as v

    core = {
        "kind": "preflight",
        "capsule_id": "t",
        "coordinator": "test",
        "root_verifier_sha256": "a" * 64,
        "allowlisted_predecessor_freeze_sha256": ["b" * 64],
    }
    path = _anchor_file(tmp_path, core)  # signed over THESE core bytes
    evil = dict(core, capsule_id="evil")
    Path(path).write_text(_json.dumps({"core": evil, "core_sha256": core_sha(evil)}))
    with pytest.raises(SystemExit) as e:
        v.load_anchor(path, kind="preflight")
    assert "signature verification FAILED" in str(e.value)


# --- (5) A2: execution_context fail-closed gate ------------------------------
def _remote_family_freeze() -> dict:
    return {
        "checkpoint_command_contract": {
            "gbm": {
                "trainer_path": "fac:gate/arena1-recovery/scripts/gbm_imitation.py",
                "trainer_sha256": "c" * 64,  # REAL-looking attested hash
                "execution_context": "arena-1-remote-with-attestation",
            }
        }
    }


def test_adv_rr55_remote_family_local_fill_refused(tmp_path):
    """A2: once gbm/nn carry real trainer hashes, the null-trainer_sha256
    refusal no longer fires — the execution_context gate must refuse a LOCAL
    fill of a remote family (attested identity is not local executability)."""
    import fill_checkpoint_slot as fcs

    with pytest.raises(SystemExit) as e:
        fcs.family_contract(
            _remote_family_freeze(), {"family": "gbm"}, tmp_path / "r.json"
        )
    assert "execution_context" in str(e.value)


def test_adv_rr55_remote_family_local_produce_refused(tmp_path, monkeypatch):
    """Same gate on the producer wrapper: a remote family may not be launched
    locally even with a fully-filled contract."""
    import json as _json

    import produce_checkpoint as pc

    freeze_p = tmp_path / "freeze.json"
    freeze_p.write_text(_json.dumps(_remote_family_freeze()))
    split_p = tmp_path / "split.json"
    split_p.write_text(
        _json.dumps(
            {
                "rotation_freeze": {
                    "bound_manifests": {
                        "executable_freeze_manifest_sha256": sha256_bytes(
                            freeze_p.read_bytes()
                        )
                    }
                }
            }
        )
    )
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_p)
    monkeypatch.setattr(pc, "SPLIT", split_p)
    with pytest.raises(SystemExit) as e:
        pc.load_contract("gbm")
    assert "execution_context" in str(e.value)


# --- (6) rpo launch verifier: wrong-fac-verifier-sha refusal branch ----------
RPO_VERIFIER = Path(
    "/home/admin/gh/ready-player-one-ptcg/scripts/step2_launch_verifier.py"
)


def test_adv_rr55_step2_verifier_wrong_fac_verifier_sha_refused(tmp_path):
    """The rpo launcher must refuse to DELEGATE to a fac verifier whose sha
    the anchor did not authorize — executed as a subprocess in a temp-dir
    jail (verifier copy + TEST allowed_signers pinned next to it), with a
    correctly-signed anchor so the refusal is unambiguously the verifier-sha
    branch, and proof the unauthorized verifier never executed."""
    import json as _json

    jail = tmp_path / "jail"
    jail.mkdir()
    (jail / "step2_launch_verifier.py").write_bytes(RPO_VERIFIER.read_bytes())
    (jail / "step2_allowed_signers").write_text(_test_allowed_signers_line())
    fake_verifier = jail / "fake_fac_verifier.py"
    fake_verifier.write_text("print('UNAUTHORIZED VERIFIER EXECUTED')\n")
    core = {
        "kind": "launch",
        "capsule_id": "rr55-test-launch",
        "coordinator": "test",
        "expected_split_sha256": "e" * 64,
        "root_verifier_sha256": "a" * 64,  # NOT the fake verifier's sha
    }
    anchor_path = jail / "anchor.json"
    anchor_path.write_text(_json.dumps({"core": core, "core_sha256": core_sha(core)}))
    _sign_anchor_core(core, Path(str(anchor_path) + ".sig"))
    r = subprocess.run(
        [
            PY,
            str(jail / "step2_launch_verifier.py"),
            "--anchor",
            str(anchor_path),
            "--fac-verifier",
            str(fake_verifier),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "root_verifier_sha256" in r.stderr
    assert "UNAUTHORIZED VERIFIER EXECUTED" not in r.stdout


def test_adv_rr55_step2_verifier_unsigned_anchor_refused(tmp_path):
    """The rpo launcher's own signature gate: unsigned anchor -> refuse
    before any delegation."""
    import json as _json

    jail = tmp_path / "jail"
    jail.mkdir()
    (jail / "step2_launch_verifier.py").write_bytes(RPO_VERIFIER.read_bytes())
    (jail / "step2_allowed_signers").write_text(_test_allowed_signers_line())
    fake_verifier = jail / "fake_fac_verifier.py"
    fake_verifier.write_text("print('UNAUTHORIZED VERIFIER EXECUTED')\n")
    core = {
        "kind": "launch",
        "capsule_id": "rr55-test-launch",
        "coordinator": "test",
        "expected_split_sha256": "e" * 64,
        "root_verifier_sha256": "a" * 64,
    }
    anchor_path = jail / "anchor.json"
    anchor_path.write_text(_json.dumps({"core": core, "core_sha256": core_sha(core)}))
    r = subprocess.run(
        [
            PY,
            str(jail / "step2_launch_verifier.py"),
            "--anchor",
            str(anchor_path),
            "--fac-verifier",
            str(fake_verifier),
        ],
        capture_output=True,
        text=True,
    )
    assert r.returncode != 0
    assert "signature" in r.stderr and "missing" in r.stderr
    assert "UNAUTHORIZED VERIFIER EXECUTED" not in r.stdout


# ---------------------------------------------------------------------------
# RR#5.5 self-review teeth (adversarial review of the fold-in diff): the
# fail-safe, wiring, and binding paths that had no committed regression.
# ---------------------------------------------------------------------------
def test_adv_rr55_fail_safe_blocks_unruled_contract():
    """The A4 fail-safe is a real gate: ANY nested PENDING-COORDINATOR-RULING
    marker in a family row blocks the freeze; a ruled contract passes."""
    import make_executable_freeze_manifest as mefm

    unruled = {
        "gbm": {
            "argv_contract": {"note": "deeply nested PENDING-COORDINATOR-RULING marker"}
        }
    }
    with pytest.raises(SystemExit) as e:
        mefm.assert_no_unruled_design_points(unruled)
    assert "unruled design point" in str(e.value)
    ruled = {"gbm": {"slice_mechanism": "per-slot cwd jail (ruled)"}}
    assert mefm.assert_no_unruled_design_points(ruled) is None


def test_adv_rr55_b3_pin_wired_into_fill_path():
    """The B3 byte-pin must be WIRED where receipts are verified, not just
    exist as a helper: load_production_receipt calls
    pinned_liveness_validator, and no module-level import of
    validate_liveness_receipt exists to bypass it."""
    import ast

    src = (GATE / "fill_checkpoint_slot.py").read_text()
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            assert node.module != "validate_liveness_receipt", (
                "module-level import of validate_liveness_receipt bypasses "
                "the B3 byte-pin"
            )
        if isinstance(node, ast.Import):
            assert all(a.name != "validate_liveness_receipt" for a in node.names)
    fill_fn = next(
        n
        for n in ast.walk(tree)
        if isinstance(n, ast.FunctionDef) and n.name == "load_production_receipt"
    )
    fn_src = ast.get_source_segment(src, fill_fn)
    assert "pinned_liveness_validator(" in fn_src, (
        "load_production_receipt does not verify the liveness validator's "
        "bytes against the contract pin before use"
    )


def test_adv_rr55_arena_slot_host_binding(tmp_path):
    """verify_execution_provenance's arena branch: the expected host comes
    from the attested tool_runtime row (TRAINING_TOOL_BY_FAMILY), a wrong
    host is refused, and a correct host still cannot reach a local fill of a
    remote family (execution_context fires next)."""
    import fill_checkpoint_slot as fcs

    slot = {
        "slot_id": "gbm-cf-s06",
        "family": "gbm",
        "slice_id": "slice-06",
        "train_seed": 7,
        "trains_on": "arena-1 (provenance procedure binding)",
    }
    freeze = {
        "tool_runtime": {
            "training_tools": {
                "arena-1:gbm-training-env": {"attested_host": "ip-172-26-8-252"}
            }
        },
        "checkpoint_command_contract": {
            "gbm": {
                "trainer_sha256": "c" * 64,
                "execution_context": "arena-1-remote-with-attestation",
            }
        },
    }
    core = {
        "slot_id": slot["slot_id"],
        "slice_id": slot["slice_id"],
        "train_seed": slot["train_seed"],
        "executable_manifest_sha256": sha256_bytes(
            (GATE / "executable-freeze-manifest.json").read_bytes()
        ),
        "host": "attacker-laptop",
    }
    with pytest.raises(SystemExit) as e:
        fcs.verify_execution_provenance(core, slot, {}, freeze, tmp_path / "r")
    assert "not in the expected host set" in str(e.value)
    # with the ATTESTED host the host gate passes — and the very next gate
    # (execution_context) still refuses a local fill of a remote family
    core["host"] = "ip-172-26-8-252"
    with pytest.raises(SystemExit) as e:
        fcs.verify_execution_provenance(core, slot, {}, freeze, tmp_path / "r")
    assert "execution_context" in str(e.value)


def test_adv_rr55_subcommand_none_and_builder_mirror():
    """The two argv builders (fill's expected_argv_for_slot and the producer
    wrapper's build_argv) must MIRROR each other exactly, including the
    arena-trainer shape where subcommand is None (no None in argv)."""
    import fill_checkpoint_slot as fcs
    import produce_checkpoint as pc

    slot = {"slot_id": "s", "slice_id": "sl", "train_seed": 3}
    for subcommand in (None, "train"):
        contract = {
            "argv_contract": {
                "interpreter": "/x/bin/python",
                "trainer": "scripts/t.py",
                "subcommand": subcommand,
                "required_options": {"--val-every": "5"},
                "slot_bound_options": {"--pairs": "x", "--out": "y", "--seed": "z"},
            },
            "slice_pairs_pattern": "runs/step2/slices/{slice_id}/p.jsonl",
            "output_path_pattern": "runs/step2/{slot_id}/",
        }
        a = fcs.expected_argv_for_slot(contract, slot)
        b = pc.build_argv(contract, slot)
        assert a == b, f"builder mirror broken for subcommand={subcommand!r}"
        assert None not in a
        if subcommand is None:
            assert a[:2] == ["/x/bin/python", "scripts/t.py"]
        else:
            assert a[:3] == ["/x/bin/python", "scripts/t.py", "train"]


def test_adv_rr55_attestation_binding_refusals(tmp_path, monkeypatch):
    """checkpoint_command_contract binds the attestation receipt by PINNED
    core sha — missing, tampered, and self-consistent-but-unpinned receipts
    are each refused before any contract row is built."""
    import json as _json

    import make_executable_freeze_manifest as mefm

    fake_fac = tmp_path
    rec_dir = fake_fac / "gate" / "receipts"
    rec_dir.mkdir(parents=True)
    monkeypatch.setattr(mefm, "FAC", fake_fac)
    rec = rec_dir / "arena1-runtime-attestation.json"

    # missing
    with pytest.raises(SystemExit) as e:
        mefm.checkpoint_command_contract({})
    assert "missing" in str(e.value)

    # tampered: stored core_sha256 does not recompute
    core = {"schema": "arena1-runtime-attestation/v1", "host": mefm.ARENA1_HOST}
    rec.write_text(_json.dumps({"core": core, "core_sha256": "0" * 64}))
    with pytest.raises(SystemExit) as e:
        mefm.checkpoint_command_contract({})
    assert "does not recompute" in str(e.value)

    # wholesale forgery: self-consistent core sha, right schema/host — but
    # NOT the pinned expected core
    rec.write_text(_json.dumps({"core": core, "core_sha256": core_sha(core)}))
    with pytest.raises(SystemExit) as e:
        mefm.checkpoint_command_contract({})
    assert "pinned expected core" in str(e.value)


def test_adv_rr55_generation_counter_seed_machine_checkable():
    """B6: the counter seed is reproducible from git history alone — the
    predecessor pin equals sha256(git show 66f97dd:gate/executable-freeze-
    manifest.json) and the version/ordinal relationship holds."""
    import make_rotation_freeze as mrf

    blob = subprocess.run(
        [
            "git",
            "-C",
            str(GATE.parent),
            "show",
            "66f97dd:gate/executable-freeze-manifest.json",
        ],
        capture_output=True,
        check=True,
    ).stdout
    assert mrf.PREDECESSOR_FREEZE_MANIFEST_SHA256 == sha256_bytes(blob)
    assert mrf.COMMITTED_ROTATION_FREEZE_VERSION == mrf.REGEN_ORDINAL + 1, (
        "each committed version is exactly one regen past its predecessor"
    )


# ---------------------------------------------------------------------------
# RR#5.6 — the projection-reproducibility BLOCK's committed regression: the
# generator-source projection must be deterministic on a clean checkout and
# INVARIANT to volatile local cache state (the rglob form ingested
# .pytest_cache/.ruff_cache — created by THIS suite while it runs — so the
# pinned value reproduced on no external checkout and probe4 was
# structurally red outside the generation pass).
# ---------------------------------------------------------------------------
def test_rr56_projection_tracked_set_and_cache_invariant():
    import make_executable_freeze_manifest as m

    p1 = m.fac_source_projection()
    # 1) reproducible: an immediate recompute in the SAME tree state agrees
    #    (rglob never guaranteed even this once a cache mutated between runs)
    assert (
        m.fac_source_projection()["fac_source_projection_sha256"]
        == (p1["fac_source_projection_sha256"])
    )
    # 2) cache-invariant: dummy volatile-cache files must not move it — this
    #    is exactly the mutation pytest itself performs while probe4 runs
    dummies = [
        GATE / ".pytest_cache" / "__rr56_regression_dummy__.txt",
        GATE / ".ruff_cache" / "__rr56_regression_dummy__.txt",
        GATE / "armb-pilot" / ".pytest_cache" / "__rr56_regression_dummy__.txt",
    ]
    try:
        for d in dummies:
            d.parent.mkdir(exist_ok=True)
            d.write_text("volatile cache noise")
        p2 = m.fac_source_projection()
    finally:
        for d in dummies:
            if d.exists():
                d.unlink()
    assert p2["fac_source_projection_sha256"] == p1["fac_source_projection_sha256"], (
        "projection ingested untracked cache state — the RR#5.6 defect is back"
    )
    # 3) the file set is the TRACKED set: every projected path is git-tracked
    #    (deterministic on any clean checkout), none is a cache path
    tracked = set(
        subprocess.run(
            ["git", "-C", str(GATE.parent), "ls-files", "--", "gate/"],
            capture_output=True,
            text=True,
            check=True,
        ).stdout.splitlines()
    )
    assert p1["n_files"] <= len(tracked)
    assert "git ls-files" in p1["rule"] or "GIT-TRACKED" in p1["rule"]


# ---------------------------------------------------------------------------
# RR#5.7 — the projection must reproduce on a FRESH NON-CANONICAL CHECKOUT
# (the coordinator's independent reproduction of the probe2-fixed tree found
# probe4 red on a real worktree: the row bound raw st_mode&0o777, and 74
# files carried host-umask group-write noise — 664-canonical vs 644-fresh —
# that git does not track. The mode now comes from the INDEX, so the pinned
# value must be recomputable from committed bytes alone, anywhere.)
# ---------------------------------------------------------------------------
def test_rr57_projection_reproduces_on_fresh_checkout(tmp_path):
    import shutil
    import types

    import make_executable_freeze_manifest as m

    live = m.fac_source_projection()

    # 1) on-disk umask noise cannot move it (mode is read from the index)
    probe_file = GATE / "armb-pilot" / "config.json"
    orig_mode = probe_file.stat().st_mode & 0o777
    try:
        probe_file.chmod(0o664)
        assert (
            m.fac_source_projection()["fac_source_projection_sha256"]
            == live["fac_source_projection_sha256"]
        ), "projection ingested host-umask mode noise — the RR#5.7 defect is back"
    finally:
        probe_file.chmod(orig_mode)

    # 2) a fresh clone at a non-canonical path reproduces the value exactly:
    #    copy the WORKING TREE's tracked gate/ set (this is what the receipts
    #    pin mid-chain), commit it in a scratch repo, clone THAT (git
    #    materializes modes fresh, whatever the runner's umask), and compute
    #    the projection with the CLONE's own generator module — the module
    #    binds its own checkout (RR#5.7 probe2 fix), so this is exactly the
    #    external reviewer's run.
    tracked = subprocess.run(
        ["git", "-C", str(FAC), "ls-files", "--", "gate/"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout.splitlines()
    src = tmp_path / "src"
    for rel in tracked:
        dst = src / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(FAC / rel, dst)

    def g(*args, cwd):
        subprocess.run(["git", *args], cwd=cwd, capture_output=True, check=True)

    g("init", "-q", cwd=src)
    g("add", "gate", cwd=src)
    g(
        "-c",
        "user.name=guard",
        "-c",
        "user.email=guard@local",
        "commit",
        "-qm",
        "rr57 fresh-checkout regression",
        cwd=src,
    )
    clone = tmp_path / "clone"
    g("clone", "-q", str(src), str(clone), cwd=tmp_path)

    mod_path = clone / "gate" / "make_executable_freeze_manifest.py"
    mod = types.ModuleType("mefm_rr57_fresh_checkout")
    mod.__file__ = str(mod_path)
    exec(compile(mod_path.read_bytes(), str(mod_path), "exec"), mod.__dict__)
    fresh = mod.fac_source_projection()
    assert fresh["n_files"] == live["n_files"]
    assert (
        fresh["fac_source_projection_sha256"] == live["fac_source_projection_sha256"]
    ), (
        "projection does not reproduce on a fresh non-canonical checkout — it "
        "binds something git does not materialize (the RR#5.7 probe4 defect)"
    )


# ---------------------------------------------------------------------------
# Navigator F2 / RR#6 item 5 — execution_context is MANDATORY: the v9-era
# "missing reads as local" default is retired (every committed freeze since
# v10 carries the field on every family row, so absence is provenance loss,
# not legacy). Three ruled classes, each through BOTH consumers (producer
# load_contract + fill family_contract).
# ---------------------------------------------------------------------------
def _ctx_freeze(ctx):
    row = {"trainer_sha256": "t" * 64}
    if ctx is not None:
        row["execution_context"] = ctx
    return {"checkpoint_command_contract": {"linear": row}}


def _stage_producer_freeze(tmp_path, monkeypatch, freeze):
    """produce_checkpoint reads SPLIT/FREEZE_MANIFEST from disk and requires
    the split->freeze sha binding — stage a self-consistent pair in tmp."""
    import produce_checkpoint as pc

    fz = tmp_path / "executable-freeze-manifest.json"
    fz.write_text(json.dumps(freeze))
    sp = tmp_path / "split-manifest.json"
    sp.write_text(
        json.dumps(
            {
                "rotation_freeze": {
                    "bound_manifests": {
                        "executable_freeze_manifest_sha256": sha256_bytes(
                            fz.read_bytes()
                        )
                    }
                }
            }
        )
    )
    monkeypatch.setattr(pc, "SPLIT", sp)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", fz)
    return pc


def test_rr6_doc_counts_match_machine_truth():
    """RR#6 documentation MUST-FIX, machine-enforced: the human-maintained
    executable-freeze-manifest.md carried test counts that disagreed with the
    machine manifest (reviewer finding). Reconciling once fixes today; THIS
    test makes drift impossible — the doc's numeric evidence claims must
    equal what pytest actually collects and what the freeze actually pins,
    or the suite (and therefore the guard receipt the final-audit anchor
    binds) goes red."""
    import re

    md = (GATE / "executable-freeze-manifest.md").read_text()

    def collected(target: str, cwd: Path) -> int:
        r = subprocess.run(
            [VENV_PY, "-m", "pytest", target, "--collect-only", "-q"],
            cwd=cwd,
            capture_output=True,
            text=True,
        )
        m = re.search(r"(\d+) tests collected", r.stdout)
        assert m, f"could not collect {target}: {r.stdout[-200:]}"
        return int(m.group(1))

    guards = collected("gate/tests/", FAC)
    armb = collected("tests/", GATE / "armb-pilot")
    n_files = len(
        json.loads((GATE / "executable-freeze-manifest.json").read_bytes())["files"]
    )
    assert f"armb-pilot suite {armb}/{armb} passed" in md, (
        f"doc's armb-pilot suite count != collected {armb} — reconcile the "
        "human doc to the machine truth (RR#6 MUST-FIX)"
    )
    assert f"({armb} tests)" in md, f"doc's armb test-count != collected {armb}"
    assert f"{guards} committed tests" in md, (
        f"doc's guard-suite count != collected {guards}"
    )
    assert f"{n_files} files hashed" in md, (
        f"doc's hashed-file count != the freeze's {n_files} pins"
    )


def test_adv_f2_execution_context_missing_fails_closed(tmp_path, monkeypatch):
    """Ruled class 1: field ABSENT -> BOTH consumers refuse deterministically
    with the distinct machine-branchable token; no local default exists."""
    import fill_checkpoint_slot as fcs

    pc = _stage_producer_freeze(tmp_path, monkeypatch, _ctx_freeze(None))
    with pytest.raises(SystemExit) as e:
        pc.load_contract("linear")
    assert "EXECUTION-CONTEXT-MISSING" in str(e.value)

    with pytest.raises(SystemExit) as e:
        fcs.family_contract(_ctx_freeze(None), {"family": "linear"}, Path("probe"))
    assert "EXECUTION-CONTEXT-MISSING" in str(e.value)


def test_adv_f2_execution_context_unknown_refused(tmp_path, monkeypatch):
    """Ruled class 2: field PRESENT but unknown/unverified -> refused through
    the not-local branch (distinct from the missing-field token)."""
    import fill_checkpoint_slot as fcs

    pc = _stage_producer_freeze(tmp_path, monkeypatch, _ctx_freeze("mystery-host"))
    with pytest.raises(SystemExit) as e:
        pc.load_contract("linear")
    assert "mystery-host" in str(e.value)
    assert "EXECUTION-CONTEXT-MISSING" not in str(e.value)

    with pytest.raises(SystemExit) as e:
        fcs.family_contract(
            _ctx_freeze("mystery-host"), {"family": "linear"}, Path("probe")
        )
    assert "mystery-host" in str(e.value)
    assert "EXECUTION-CONTEXT-MISSING" not in str(e.value)


# ---------------------------------------------------------------------------
# RR#6 — the ledger authenticity chain must not stop at INTENT. The reviewer
# reproduced on committed bytes: intent-only ledger + fabricated FILLED ->
# ACCEPTED; 2x intent-only + fabricated FAILED -> ACCEPTED. These are the six
# verdict-mandated adversarial probes plus the consequence probe and the
# built-wrapper / signed-capsule stub demonstrations (items-1/4 ruling: BUILD
# and stub-test everything, execute NO real trainer).
# ---------------------------------------------------------------------------
def _rr6_fixture():
    """A self-consistent (contract, slot, receipt-core, intent, commit) set —
    every RR#6 probe perturbs exactly one element of it."""
    wrapper_sha = "w" * 64
    contract = {
        "producer_wrapper_sha256": wrapper_sha,
        "argv_contract": {
            "interpreter": "/usr/bin/python3",
            "trainer": "trainer.py",
            "interpreter_sha256": "i" * 64,
        },
    }
    slot = {"slot_id": "lin-cf-s01", "slice_id": "sl-a", "train_seed": 7}
    argv = ["/usr/bin/python3", "trainer.py"]
    cmd_sha = sha256_bytes(json.dumps(argv, separators=(",", ":")).encode())
    core = {
        "wrapper_tool_sha256": wrapper_sha,
        "argv": argv,
        "training_command_sha256": cmd_sha,
        "cwd": "/jail",
        "start_utc": "2026-07-17T00:00:00Z",
        "end_utc": "2026-07-17T00:00:01Z",
        "stdout_sha256": "o" * 64,
        "stderr_sha256": "e" * 64,
        "interpreter_sha256": "i" * 64,
        "host": "host-1",
        "exit_code": 0,
        "artifact_sha256": "a" * 64,
        "attempt_id": None,
        "launch_ledger_id": "lid-1",
        "jail_member_resolutions": None,
        "jail_member_resolutions_sha256": None,
    }
    intent = {
        "ledger_id": "lid-1",
        "phase": "intent",
        "slot_id": slot["slot_id"],
        "argv_sha256": cmd_sha,
        "attempt_id": None,
        "jail_member_resolutions_sha256": None,
    }

    def commit(**overrides):
        rec = {
            "ledger_id": "lid-1",
            "phase": "commit",
            "slot_id": slot["slot_id"],
            "attempt_id": None,
            "wrapper_sha256": wrapper_sha,
            "anchor_capsule_id": "cap-1",
            "anchor_core_sha256": "c" * 64,
            "anchor_root_verifier_sha256": "v" * 64,
            "split_sha256": "s" * 64,
            "freeze_sha256": "f" * 64,
            "argv": argv,
            "argv_sha256": cmd_sha,
            "cwd": "/jail",
            "jail_manifest_sha256": "j" * 64,
            "jail_member_resolutions_sha256": None,
            "host": "host-1",
            "interpreter_sha256": "i" * 64,
            "start_utc": "2026-07-17T00:00:00Z",
            "end_utc": "2026-07-17T00:00:01Z",
            "exit_code": 0,
            "stdout_sha256": "o" * 64,
            "stderr_sha256": "e" * 64,
            "artifact_path": "/jail/out.bin",
            "artifact_sha256": "a" * 64,
            "receipt_core_sha256": core_sha(core),
            "liveness_receipt_core_sha256": "l" * 64,
        }
        rec.update(overrides)
        return rec

    return contract, slot, core, cmd_sha, intent, commit


def _stage_ledger(tmp_path, monkeypatch, rows):
    import fill_checkpoint_slot as fcs

    led = tmp_path / "launch-ledger.jsonl"
    led.write_text("".join(json.dumps(r, sort_keys=True) + "\n" for r in rows))
    monkeypatch.setattr(fcs, "LAUNCH_LEDGER", led)
    return fcs


def test_rr7_option_a_receipt_resolution_digest_recomputed_and_terminal_bound(
    tmp_path, monkeypatch
):
    """#3671 producer binding teeth: the receipt's full resolution records
    recompute to jail_member_resolutions_sha256, and that digest must match
    BOTH the intent and terminal. Tampering any one surface is refused."""
    contract, slot, core, _, intent, commit = _rr6_fixture()
    records = [
        {
            "schema": "slot-symbols/v1",
            "form": "ref",
            "symbol": "slot.staged_pairs_sha256",
            "member_source": {"ref": "slot.staged_pairs_sha256"},
            "resolved_sha256": "a" * 64,
            "slot_id": slot["slot_id"],
            "slot_row_projection_sha256": "b" * 64,
        }
    ]
    digest = sha256_bytes(
        json.dumps(records, sort_keys=True, separators=(",", ":")).encode()
    )
    core["jail_member_resolutions"] = records
    core["jail_member_resolutions_sha256"] = digest
    intent["jail_member_resolutions_sha256"] = digest
    good_commit = commit(
        jail_member_resolutions_sha256=digest,
        receipt_core_sha256=core_sha(core),
    )
    fcs = _stage_ledger(tmp_path, monkeypatch, [intent, good_commit])
    ledger = fcs.load_launch_ledger()
    fcs.verify_wrapper_authenticity(core, slot, contract, ledger, Path("probe"))

    forged = json.loads(json.dumps(core))
    forged["jail_member_resolutions"][0]["resolved_sha256"] = "c" * 64
    with pytest.raises(SystemExit, match="does not recompute"):
        fcs.verify_wrapper_authenticity(
            forged, slot, contract, ledger, Path("forged-receipt")
        )

    bad_term = commit(
        jail_member_resolutions_sha256="d" * 64,
        receipt_core_sha256=core_sha(core),
    )
    fcs = _stage_ledger(tmp_path, monkeypatch, [intent, bad_term])
    with pytest.raises(SystemExit, match="disagrees with its intent"):
        fcs.load_launch_ledger()


def test_rr6_intent_only_filled_rejected(tmp_path, monkeypatch):
    """Verdict probe 1: intent-only ledger + valid-looking FILLED -> reject.
    The reviewer's exact exploit: every hash self-consistent, one wrapper-
    generated intent row, no execution."""
    contract, slot, core, _, intent, _ = _rr6_fixture()
    fcs = _stage_ledger(tmp_path, monkeypatch, [intent])
    with pytest.raises(SystemExit) as e:
        fcs.verify_wrapper_authenticity(
            core, slot, contract, fcs.load_launch_ledger(), Path("probe")
        )
    assert "OPEN (intent-only)" in str(e.value)


def test_rr6_intent_only_liveness_rejected(tmp_path, monkeypatch):
    """Verdict probe 2: intent-only ledger + valid liveness -> reject. The
    validator receives only COMMITTED transaction ids now."""
    import validate_liveness_receipt as vlr

    contract, slot, core, _, intent, _ = _rr6_fixture()
    fcs = _stage_ledger(tmp_path, monkeypatch, [intent])
    committed = fcs.committed_ledger_ids(fcs.load_launch_ledger())
    assert committed == set()
    lv_core = {"launch_ledger_id": "lid-1"}
    violations = vlr.validate_liveness_receipt(
        {"core": lv_core, "core_sha256": core_sha(lv_core)},
        slot,
        contract["producer_wrapper_sha256"],
        expected_ledger_id="lid-1",
        committed_ledger_ids=committed,
    )
    assert any("no COMMITTED launch-ledger transaction" in v for v in violations)


def test_rr6_two_intent_only_attempts_rejected(tmp_path, monkeypatch):
    """Verdict probe 3: two distinct intent-only attempts (the fabricated
    FAILED channel) -> each refused at the transaction boundary."""
    contract, slot, core, cmd_sha, intent, _ = _rr6_fixture()
    intents, cores = [], []
    for i, lid in enumerate(("lid-1", "lid-2")):
        it = dict(intent, ledger_id=lid, attempt_id=f"a{i}")
        intents.append(it)
        c = dict(
            core,
            launch_ledger_id=lid,
            attempt_id=f"a{i}",
            exit_code=3,
            outcome="FAILED",
            failure_signature="e" * 64,
        )
        c.pop("artifact_sha256")
        cores.append(c)
    fcs = _stage_ledger(tmp_path, monkeypatch, intents)
    for c in cores:
        with pytest.raises(SystemExit) as e:
            fcs.verify_wrapper_authenticity(
                c, slot, contract, fcs.load_launch_ledger(), Path("probe")
            )
        assert "OPEN (intent-only)" in str(e.value)


def test_rr6_terminal_commit_mismatched_receipt_sha_rejected(tmp_path, monkeypatch):
    """Verdict probe 4: a terminal commit whose bound receipt core sha is not
    THE receipt presented -> reject (evidence divergence)."""
    contract, slot, core, _, intent, commit = _rr6_fixture()
    fcs = _stage_ledger(
        tmp_path, monkeypatch, [intent, commit(receipt_core_sha256="0" * 64)]
    )
    with pytest.raises(SystemExit) as e:
        fcs.verify_wrapper_authenticity(
            core, slot, contract, fcs.load_launch_ledger(), Path("probe")
        )
    assert "receipt_core_sha256" in str(e.value)


def test_rr6_terminal_commit_mismatched_artifact_sha_rejected(tmp_path, monkeypatch):
    """Verdict probe 5: a terminal commit whose artifact sha is not the
    artifact the receipt names -> reject (artifact substitution)."""
    contract, slot, core, _, intent, commit = _rr6_fixture()
    fcs = _stage_ledger(
        tmp_path, monkeypatch, [intent, commit(artifact_sha256="b" * 64)]
    )
    with pytest.raises(SystemExit) as e:
        fcs.verify_wrapper_authenticity(
            core, slot, contract, fcs.load_launch_ledger(), Path("probe")
        )
    assert "artifact" in str(e.value)


def test_rr7_option_a_resolution_digest_triple_binding(tmp_path, monkeypatch):
    """Option-A resolution evidence is one transaction-bound fact: the
    receipt records recompute to the digest carried by both INTENT and the
    terminal COMMIT. Any divergence at any edge is refused."""
    contract, slot, core, _, intent, commit = _rr6_fixture()
    resolutions = [
        {
            "dest_relpath": "runs/step2/slices/S01/imitation_pairs.jsonl",
            "form": "ref",
            "member_source": {"ref": "slot.staged_pairs_sha256"},
            "resolved_sha256": "a" * 64,
            "slot_id": slot["slot_id"],
            "slot_row_projection_sha256": "b" * 64,
            "symbol": "slot.staged_pairs_sha256",
        }
    ]
    digest = sha256_bytes(
        json.dumps(resolutions, sort_keys=True, separators=(",", ":")).encode()
    )
    core.update(
        jail_member_resolutions=resolutions,
        jail_member_resolutions_sha256=digest,
    )
    intent["jail_member_resolutions_sha256"] = digest
    terminal = commit(
        jail_member_resolutions_sha256=digest,
        receipt_core_sha256=core_sha(core),
    )
    fcs = _stage_ledger(tmp_path, monkeypatch, [intent, terminal])
    ledger = fcs.load_launch_ledger()
    fcs.verify_wrapper_authenticity(core, slot, contract, ledger, Path("probe"))

    tampered_receipt = dict(core)
    tampered_receipt["jail_member_resolutions"] = [
        {**resolutions[0], "resolved_sha256": "c" * 64}
    ]
    with pytest.raises(SystemExit, match="does not recompute"):
        fcs.verify_wrapper_authenticity(
            tampered_receipt, slot, contract, ledger, Path("tampered-receipt")
        )

    fcs = _stage_ledger(
        tmp_path,
        monkeypatch,
        [intent, {**terminal, "jail_member_resolutions_sha256": "d" * 64}],
    )
    with pytest.raises(SystemExit, match="disagrees with its intent"):
        fcs.load_launch_ledger()

    divergent_intent = {**intent, "jail_member_resolutions_sha256": "e" * 64}
    fcs = _stage_ledger(tmp_path, monkeypatch, [divergent_intent, terminal])
    with pytest.raises(SystemExit, match="disagrees with its intent"):
        fcs.load_launch_ledger()


def test_rr6_duplicate_contradictory_phases_rejected(tmp_path, monkeypatch):
    """Verdict probe 6: duplicate/contradictory phases -> the LEDGER ITSELF
    dies fail-closed (the pinned wrapper can write none of these states)."""
    contract, slot, core, _, intent, commit = _rr6_fixture()
    bad_ledgers = (
        [intent, commit(), commit()],  # two commits
        [intent, commit(), commit(phase="abort")],  # commit AND abort
        [intent, intent],  # duplicate intent
        [commit()],  # terminal with no prior intent
        [intent, commit(slot_id="other-slot")],  # terminal disagrees w/ intent
    )
    for rows in bad_ledgers:
        fcs = _stage_ledger(tmp_path, monkeypatch, rows)
        with pytest.raises(SystemExit):
            fcs.load_launch_ledger()


def test_rr6_consequence_aborted_and_absent_never_fill(tmp_path, monkeypatch):
    """The ruled CONSEQUENCE, committed: with zero real executions there are
    no terminal commits, so ALL FILLED/FAILED evidence refuses — including a
    HOLD-era transaction the producer itself closed with an abort."""
    contract, slot, core, _, intent, commit = _rr6_fixture()
    fcs = _stage_ledger(
        tmp_path,
        monkeypatch,
        [intent, commit(phase="abort", abort_reason="step2-hold")],
    )
    ledger = fcs.load_launch_ledger()
    assert fcs.committed_ledger_ids(ledger) == set()
    with pytest.raises(SystemExit) as e:
        fcs.verify_wrapper_authenticity(core, slot, contract, ledger, Path("probe"))
    assert "ABORTED" in str(e.value)


def test_rr6_wrapper_terminal_execution_stub_e2e(tmp_path, monkeypatch):
    """items-1/4 ruling: the terminal-execution wrapper is BUILT and proven
    with a FROZEN STUB (a real subprocess, not a trainer): intent->commit
    transaction lands, and the emitted receipt passes the fail-closed
    consumer end-to-end — wrapper-produced evidence fills, hand-written
    evidence cannot. No trainer executes; no checkpoint outcome exists."""
    import fill_checkpoint_slot as fcs
    import produce_checkpoint as pc

    jail = tmp_path / "jail"
    jail.mkdir()
    stub = jail / "stub_trainer.py"
    out_path = jail / "out.bin"
    stub.write_text(
        "import sys\n"
        "args = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
        "open(args['--out'], 'w').write('stub artifact bytes')\n"
        "print('stub ok')\n"
    )
    interp_sha = sha256_bytes(Path(sys.executable).resolve().read_bytes())
    contract = {
        "producer_wrapper_sha256": sha256_bytes(
            (GATE / "produce_checkpoint.py").read_bytes()
        ),
        "config_sha256": "c" * 64,
        "output_path_pattern": str(out_path),
        "argv_contract": {
            "interpreter": sys.executable,
            "trainer": str(stub),
            "interpreter_sha256": interp_sha,
            "slot_bound_options": {"--out": "x"},
        },
    }
    slot = _slot_row("lin-cf-s01")
    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    led = tmp_path / "ledger.jsonl"
    for mod in (pc, fcs):
        monkeypatch.setattr(mod, "SPLIT", split_path)
        monkeypatch.setattr(mod, "FREEZE_MANIFEST", freeze_path)
    monkeypatch.setattr(pc, "LAUNCH_LEDGER", led)
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    monkeypatch.setattr(pc, "STDERR_SIDECAR_DIR", tmp_path / "runtime")
    monkeypatch.setattr(fcs, "LAUNCH_LEDGER", led)

    # RR#7 §5: the producer takes a VERIFIED anchor OBJECT, never a bare
    # capsule-id string.
    launch_anchor = _verified_section5a_anchor(
        tmp_path,
        split_path=split_path,
        freeze_path=freeze_path,
        name="wrapper-e2e-anchor.json",
    )

    # RR#7 §4.1: the pinned quality-blind probe writes an independent
    # liveness receipt bound to THIS execution's in-flight ledger id; the
    # producer's own pre-commit pass re-verifies it with the real validator.
    def liveness_probe(ledger_id, artifact_file):
        core = {
            "schema": "checkpoint-liveness-receipt/v1",
            "slot_id": slot["slot_id"],
            "slice_id": slot["slice_id"],
            "train_seed": slot["train_seed"],
            "wrapper_tool_sha256": sha256_bytes(
                (GATE / "produce_checkpoint.py").read_bytes()
            ),
            "positive_control": {"fired": 3},
            "negative_control": {"observed": 0, "expected": 0},
            "quality_blind": True,
            "launch_ledger_id": ledger_id,
        }
        core_sha = sha256_bytes(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        )
        lv_path = tmp_path / "liveness-receipt.json"
        lv_path.write_text(json.dumps({"core": core, "core_sha256": core_sha}))
        return lv_path

    res = pc.run_terminal_execution(
        slot,
        contract,
        "FILLED",
        None,
        launch_anchor,
        jail,
        receipt_out=tmp_path / "receipt.json",
        liveness_probe=liveness_probe,
    )
    ledger = fcs.load_launch_ledger()
    term = fcs.committed_ledger_txn(ledger, res["ledger_id"])
    assert term is not None and term["exit_code"] == 0
    rec = json.loads((tmp_path / "receipt.json").read_text())
    assert rec["core_sha256"] == res["receipt_core_sha256"]
    assert term["receipt_core_sha256"] == res["receipt_core_sha256"]
    intent = ledger[res["ledger_id"]]["intent"]
    expected_anchor_fields = {
        "anchor_capsule_id": launch_anchor["capsule_id"],
        "anchor_core_sha256": launch_anchor.core_sha256,
        "anchor_root_verifier_sha256": launch_anchor["root_verifier_sha256"],
    }
    for field, expected in expected_anchor_fields.items():
        assert intent[field] == expected
        assert rec["core"][field] == expected
        assert term[field] == expected
    # the wrapper's own receipt passes the fail-closed consumer boundary
    fcs.verify_wrapper_authenticity(
        rec["core"], slot, contract, ledger, Path("stub-receipt")
    )
    # ...and a byte-tampered variant of it does not
    forged = dict(rec["core"], artifact_sha256="b" * 64)
    with pytest.raises(SystemExit):
        fcs.verify_wrapper_authenticity(forged, slot, contract, ledger, Path("forged"))


def test_rr6_remote_capsule_stub_signed_roundtrip_and_refusals(tmp_path, monkeypatch):
    """items-1/4 ruling: the GBM/NN signed remote-capsule path is BUILT and
    stub-tested, never executed. A capsule signed by the pinned key in the
    CAPSULE namespace loads; the SAME bytes signed in the ANCHOR namespace
    are refused at the crypto layer (coordinator design amendment: cross-
    protocol replay fails before schema parsing); tamper/open-transaction/
    wrong-host each refuse."""
    import load_remote_result_capsule as lrc

    key = tmp_path / "id_ed25519"
    subprocess.run(
        ["ssh-keygen", "-t", "ed25519", "-N", "", "-q", "-f", str(key)], check=True
    )
    pub = (tmp_path / "id_ed25519.pub").read_text().strip()
    monkeypatch.setattr(
        lrc,
        "CAPSULE_ALLOWED_SIGNERS",
        f'rq-tcg-coordinator namespaces="rq-tcg-remote-result" {pub}\n',
    )
    _, _, _, _, _, commit = _rr6_fixture()
    record = commit(
        slot_id="gbm-cf-s08",
        host="arena-1-host",
        freeze_sha256="f" * 64,
        split_sha256="s" * 64,
    )
    core = {
        "schema": "remote-result-capsule/v1",
        "kind": "remote-result",
        "execution_context": "arena-1-remote-with-attestation",
        "terminal_record": record,
    }
    slot = {"slot_id": "gbm-cf-s08", "family": "gbm"}
    freeze = {
        "checkpoint_command_contract": {
            "gbm": {"execution_context": "arena-1-remote-with-attestation"}
        },
        "tool_runtime": {
            "training_tools": {
                "arena-1:gbm-training-env": {"attested_host": "arena-1-host"}
            }
        },
    }

    def write_capsule(c, namespace):
        p = tmp_path / "capsule.json"
        raw = json.dumps(c, sort_keys=True, separators=(",", ":")).encode()
        p.write_text(json.dumps({"core": c, "core_sha256": sha256_bytes(raw)}))
        blob = tmp_path / "core.bytes"
        blob.write_bytes(raw)
        # ssh-keygen -Y sign PROMPTS instead of overwriting an existing .sig
        # (with stdin closed it keeps the stale file and exits 0) — a stale
        # signature would make the cross-namespace refusal below pass for the
        # wrong reason, so remove it first.
        blob.with_suffix(".bytes.sig").unlink(missing_ok=True)
        subprocess.run(
            ["ssh-keygen", "-Y", "sign", "-f", str(key), "-n", namespace, str(blob)],
            check=True,
            capture_output=True,
            stdin=subprocess.DEVNULL,
        )
        (tmp_path / "capsule.json.sig").write_bytes(
            (tmp_path / "core.bytes.sig").read_bytes()
        )
        return p

    # signed in the CAPSULE namespace -> loads
    p = write_capsule(core, "rq-tcg-remote-result")
    got = lrc.load_remote_result_capsule(p, slot, freeze, "f" * 64, "s" * 64)
    assert got["terminal_record"]["slot_id"] == "gbm-cf-s08"

    # SAME bytes signed in the ANCHOR namespace -> crypto-layer refusal
    p = write_capsule(core, "rq-tcg-anchor")
    with pytest.raises(SystemExit) as e:
        lrc.load_remote_result_capsule(p, slot, freeze, "f" * 64, "s" * 64)
    assert "namespace" in str(e.value)

    # tampered core -> refused before/at signature
    p = write_capsule(core, "rq-tcg-remote-result")
    tampered = json.loads(p.read_text())
    tampered["core"]["terminal_record"]["artifact_sha256"] = "b" * 64
    p.write_text(json.dumps(tampered))
    with pytest.raises(SystemExit):
        lrc.load_remote_result_capsule(p, slot, freeze, "f" * 64, "s" * 64)

    # open transaction (phase intent) -> refused
    open_core = json.loads(json.dumps(core))
    open_core["terminal_record"]["phase"] = "intent"
    p = write_capsule(open_core, "rq-tcg-remote-result")
    with pytest.raises(SystemExit) as e:
        lrc.load_remote_result_capsule(p, slot, freeze, "f" * 64, "s" * 64)
    assert "COMMIT" in str(e.value)

    # host != attested arena-1 host -> refused
    bad_host = json.loads(json.dumps(core))
    bad_host["terminal_record"]["host"] = "laptop"
    p = write_capsule(bad_host, "rq-tcg-remote-result")
    with pytest.raises(SystemExit) as e:
        lrc.load_remote_result_capsule(p, slot, freeze, "f" * 64, "s" * 64)
    assert "attested" in str(e.value)


def test_adv_f2_execution_context_remote_no_local_fallback(tmp_path, monkeypatch):
    """Ruled class 3: field present and remotely attested -> local production
    and local fill BOTH refuse (identity is not executability); the remote
    path is the coordinator-signed capsule flow, never an implicit
    local-interpreter fallback."""
    import fill_checkpoint_slot as fcs

    ctx = "arena-1-remote-with-attestation"
    pc = _stage_producer_freeze(tmp_path, monkeypatch, _ctx_freeze(ctx))
    with pytest.raises(SystemExit) as e:
        pc.load_contract("linear")
    assert "not local executability" in str(e.value)
    assert "EXECUTION-CONTEXT-MISSING" not in str(e.value)

    with pytest.raises(SystemExit) as e:
        fcs.family_contract(_ctx_freeze(ctx), {"family": "linear"}, Path("probe"))
    assert "not local executability" in str(e.value)
    assert "EXECUTION-CONTEXT-MISSING" not in str(e.value)


# ---------------------------------------------------------------------------
# RR#7 — full local-linear directory-output FILLED e2e (design v2 section 9,
# acceptance-matrix items 1-3). mroute-15 closed the crash regression (fill's
# FILLED branch reading retired core["liveness_bar"]) and wired the linear
# family's canonical-directory-archive contract into the freeze generator,
# but left no dedicated test driving the full producer -> fill path with a
# DIRECTORY-form artifact through _locked_fill itself.
# ---------------------------------------------------------------------------
def test_rr7_linear_directory_output_producer_to_filled_e2e(tmp_path, monkeypatch):
    """Acceptance-matrix items 1-3: a wrapper-produced local success (linear
    family, DIRECTORY-form output) traverses producer -> independent liveness
    -> production receipt -> the full production loader -> a real sandboxed
    _locked_fill FILLED — with the canonical-directory-archive packaged from
    that directory, and fill's canonical_ustar re-verification (not merely a
    whole-file hash compare) exercised on the real archive bytes."""
    import types

    import fill_checkpoint_slot as fcs
    import produce_checkpoint as pc

    jail = tmp_path / "jail"
    jail.mkdir()
    stub = jail / "stub_trainer.py"
    stub.write_text(
        "import os, sys\n"
        "args = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
        "out_dir = args['--out']\n"
        "os.makedirs(out_dir, exist_ok=True)\n"
        "with open(os.path.join(out_dir, 'imitation_weights.json'), 'w') as fh:\n"
        "    fh.write('stub-weights')\n"
        "with open(os.path.join(out_dir, 'imitation_report.json'), 'w') as fh:\n"
        "    fh.write('stub-report')\n"
        "print('stub ok')\n"
    )
    interp_sha = sha256_bytes(Path(sys.executable).resolve().read_bytes())
    trainer_sha = sha256_bytes(stub.read_bytes())
    wrapper_sha = sha256_bytes((GATE / "produce_checkpoint.py").read_bytes())
    validator_sha = sha256_bytes((GATE / "validate_liveness_receipt.py").read_bytes())

    out_pattern = str(jail / "runs" / "{slot_id}")
    contract = {
        "producer_wrapper_sha256": wrapper_sha,
        "liveness_validator_sha256": validator_sha,
        "trainer_sha256": trainer_sha,
        "execution_context": "local",
        "config_sha256": "c" * 64,
        "output_path_pattern": out_pattern,
        "artifact_kind": "canonical-directory-archive",
        "required_artifact_members": [
            "imitation_weights.json",
            "imitation_report.json",
        ],
        "argv_contract": {
            "interpreter": sys.executable,
            "trainer": str(stub),
            "interpreter_sha256": interp_sha,
            "slot_bound_options": {"--out": "x"},
        },
    }
    slot = {
        "slot_id": "lin-rr7-e2e-s01",
        "slice_id": "sl-a",
        "family": "linear",
        "train_seed": 7,
        "artifact_sha256": None,
        "slot_status": "PENDING",
    }

    archive_sha = sha256_bytes((GATE / "canonical_ustar.py").read_bytes())
    fill_sha = sha256_bytes((GATE / "fill_checkpoint_slot.py").read_bytes())
    resolution_engine_sha = sha256_bytes((GATE / "slot_resolution_txn.py").read_bytes())
    contract["validator_sha256"] = fill_sha
    contract["resolution_engine_sha256"] = resolution_engine_sha
    contract["archive_encoder_sha256"] = archive_sha
    freeze_path = tmp_path / "executable-freeze-manifest.json"
    freeze = {
        "checkpoint_command_contract": {"linear": contract},
        "files": {
            "fac:gate/produce_checkpoint.py": {"sha256": wrapper_sha},
            "fac:gate/fill_checkpoint_slot.py": {"sha256": fill_sha},
            "fac:gate/slot_resolution_txn.py": {"sha256": resolution_engine_sha},
            "fac:gate/validate_liveness_receipt.py": {"sha256": validator_sha},
            "fac:gate/canonical_ustar.py": {"sha256": archive_sha},
        },
    }
    freeze_path.write_text(json.dumps(freeze))
    freeze_sha = sha256_bytes(freeze_path.read_bytes())

    section = {
        "frozen": True,
        "bound_manifests": {"executable_freeze_manifest_sha256": freeze_sha},
        "checkpoint_slots": [dict(slot)],
    }
    section["immutable_projection_sha256"] = fcs.immutable_projection(section)
    split_manifest = {"rotation_freeze": section}
    split_path = tmp_path / "split-manifest.json"
    split_path.write_bytes(fcs.canonical(split_manifest))
    parent_sha = sha256_bytes(split_path.read_bytes())

    led = tmp_path / "ledger.jsonl"
    for mod in (pc, fcs):
        monkeypatch.setattr(mod, "SPLIT", split_path)
        monkeypatch.setattr(mod, "FREEZE_MANIFEST", freeze_path)
        monkeypatch.setattr(mod, "LAUNCH_LEDGER", led)
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    monkeypatch.setattr(pc, "STDERR_SIDECAR_DIR", tmp_path / "runtime")
    monkeypatch.setattr(fcs, "RESOLUTION_LOG", tmp_path / "slot-resolution-log.jsonl")
    monkeypatch.setattr(fcs, "FILL_JOURNAL", tmp_path / "slot-fill-journal.jsonl")
    monkeypatch.setattr(fcs, "FILL_LOCK", tmp_path / ".slot-fill.lock")

    launch_anchor = _verified_section5a_anchor(
        tmp_path,
        split_path=split_path,
        freeze_path=freeze_path,
        capsule_id="rr7-e2e-capsule",
        name="local-linear-e2e-anchor.json",
    )

    def liveness_probe(ledger_id, artifact_file):
        core = {
            "schema": "checkpoint-liveness-receipt/v1",
            "slot_id": slot["slot_id"],
            "slice_id": slot["slice_id"],
            "train_seed": slot["train_seed"],
            "wrapper_tool_sha256": wrapper_sha,
            "positive_control": {"fired": 3},
            "negative_control": {"observed": 0, "expected": 0},
            "quality_blind": True,
            "launch_ledger_id": ledger_id,
        }
        core_sha = sha256_bytes(
            json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
        )
        lv_path = tmp_path / "liveness-receipt.json"
        lv_path.write_text(json.dumps({"core": core, "core_sha256": core_sha}))
        return lv_path

    receipt_path = tmp_path / "receipt.json"
    res = pc.run_terminal_execution(
        slot,
        contract,
        "FILLED",
        None,
        launch_anchor,
        jail,
        receipt_out=receipt_path,
        liveness_probe=liveness_probe,
    )

    # the producer packaged a DIRECTORY output into a canonical archive, not
    # a bare file — confirm before driving fill.
    out_dir = jail / "runs" / slot["slot_id"]
    assert out_dir.is_dir()
    archive_path = jail / "artifacts" / "slot-artifact.tar"
    assert archive_path.is_file()

    rec = json.loads(receipt_path.read_text())
    assert rec["core_sha256"] == res["receipt_core_sha256"]
    assert rec["core"]["archive_member_manifest_sha256"]

    # item 1 — the wrapper success receipt passes the FULL production
    # loader (not just verify_wrapper_authenticity, as the RR#6 scaffold
    # does): family_contract lookup, provenance, liveness rerun, all of it.
    freeze_loaded = json.loads(freeze_path.read_bytes())
    core, liveness_summary = fcs.load_production_receipt(
        receipt_path, slot, section, freeze_loaded
    )
    assert core["artifact_sha256"] == sha256_bytes(archive_path.read_bytes())
    assert liveness_summary["phase"] == "fill-rerun"
    assert liveness_summary["violations"] == []

    # item 2/3 — a real sandboxed _locked_fill drives FILLED end-to-end, and
    # the transferred archive is canonical-verified, not merely whole-file
    # hashed.
    args = types.SimpleNamespace(
        slot=slot["slot_id"],
        status="FILLED",
        artifact_path=archive_path,
        production_receipt=receipt_path,
        attempt_receipts=[],
        reason="",
        expect_parent_sha=parent_sha,
    )
    substituted_artifact = tmp_path / "substituted-artifact.tar"
    substituted_artifact.write_bytes(archive_path.read_bytes())
    with pytest.raises(SystemExit, match="three-way equal"):
        fcs._locked_fill(
            types.SimpleNamespace(
                **{**vars(args), "artifact_path": substituted_artifact}
            )
        )
    rc = fcs._locked_fill(args)
    assert rc == 0

    updated = json.loads(split_path.read_bytes())
    updated_slot = updated["rotation_freeze"]["checkpoint_slots"][0]
    assert updated_slot["slot_status"] == "FILLED"
    assert updated_slot["artifact_sha256"] == sha256_bytes(archive_path.read_bytes())

    resolution_rows = (tmp_path / "slot-resolution-log.jsonl").read_text().splitlines()
    assert len(resolution_rows) == 1
    evidence = json.loads(resolution_rows[0])["evidence"]
    assert "liveness_earned_summary" in evidence
    assert "liveness_bar" not in evidence
    assert evidence["liveness_earned_summary"]["phase"] == "fill-rerun"
    assert (
        evidence["archive_member_manifest_sha256"]
        == rec["core"]["archive_member_manifest_sha256"]
    )
    resolution = json.loads(resolution_rows[0])
    assert resolution["schema"] == "slot-resolution/v3"
    assert resolution["verified_evidence"]["transport"] == "local"
    assert resolution["verified_evidence_sha256"] == sha256_bytes(
        json.dumps(
            resolution["verified_evidence"], sort_keys=True, separators=(",", ":")
        ).encode()
    )


# ---------------------------------------------------------------------------
# RR#7 §2.2 WIRING — pre_exec_barrier verifies the contract's pinned
# runtime_contract/v1 block against the interpreter that will ACTUALLY
# execute (argv[0]), before any intent lands. The audit digest's gap was
# "pre_exec_barrier verifies interpreter + env + jail only — the
# runtime-closure half is simply not there"; these tests pin the wiring, the
# fail-closed refusals, and the observed-identity binding. The projection
# algorithms themselves are covered in test_rr7_primitives.py — here the
# closure tool is stubbed via sys.modules so no host stdlib is ever hashed.
# ---------------------------------------------------------------------------
def _rr7_barrier_fixture(tmp_path):
    jail = tmp_path / "jail"
    jail.mkdir(parents=True)
    (jail / "trainer.py").write_text("print('stub')\n")
    contract = {
        "argv_contract": {"trainer": "trainer.py"},
        "output_path_pattern": "out/{slot_id}/",
    }
    slot = {"slot_id": "SLOT-RC", "slice_id": "S01"}
    argv = [sys.executable, "trainer.py"]
    return jail, contract, slot, argv


def _rr7_closure_stub(monkeypatch, fake_verify):
    """Intercept produce_checkpoint's ``import runtime_closure`` with a stub
    whose __file__ still points at the REAL on-disk tool (so the caller-side
    tool-pin check hashes real bytes) but whose verification is canned."""
    import types

    import runtime_closure as real_rc

    stub = types.SimpleNamespace(
        __file__=real_rc.__file__, verify_runtime_contract=fake_verify
    )
    monkeypatch.setitem(sys.modules, "runtime_closure", stub)


def test_rr7_pre_exec_barrier_verifies_runtime_contract_and_binds_observed(
    tmp_path, monkeypatch
):
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)
    calls = []

    def fake_verify(block, *, python):
        calls.append((block, python))
        return {"stdlib_projection_sha256": "aa" * 32}

    _rr7_closure_stub(monkeypatch, fake_verify)
    block = {"schema": "runtime_contract/v1"}
    contract["runtime_contract"] = block
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    # verified against the interpreter that will ACTUALLY execute — argv[0],
    # never a contract string
    assert calls == [(block, argv[0])]
    expected = sha256_bytes(
        json.dumps(
            {"stdlib_projection_sha256": "aa" * 32},
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    assert barrier["runtime_closure_observed_sha256"] == expected


def test_rr7_pre_exec_barrier_refuses_runtime_closure_divergence(tmp_path, monkeypatch):
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)

    def fake_verify(block, *, python):
        raise ValueError("stdlib projection deadbeef != pinned cafebabe")

    _rr7_closure_stub(monkeypatch, fake_verify)
    contract["runtime_contract"] = {"schema": "runtime_contract/v1"}
    with pytest.raises(SystemExit, match="runtime closure diverges"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


def test_rr7_pre_exec_barrier_refuses_unpinned_closure_tool(tmp_path, monkeypatch):
    """The block's closure_tool_sha256 pins the tool whose verification code
    is about to be TRUSTED — mismatching on-disk tool bytes are refused
    BEFORE any of its verification runs (same pattern as the pinned liveness
    validator)."""
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)
    calls = []

    def fake_verify(block, *, python):
        calls.append(block)
        return {}

    _rr7_closure_stub(monkeypatch, fake_verify)
    contract["runtime_contract"] = {
        "schema": "runtime_contract/v1",
        "closure_tool_sha256": "0" * 64,
    }
    with pytest.raises(SystemExit, match="unpinned closure tool"):
        pc.pre_exec_barrier(slot, contract, jail, argv)
    assert calls == []


def test_rr7_pre_exec_barrier_without_runtime_contract_binds_none(
    tmp_path, monkeypatch
):
    """Contracts predating the runtime_contract/v1 pin (and the remote
    families, whose closure is attestation-territory) carry no block: the
    barrier binds an explicit None — never a fabricated identity — and the
    closure tool is never consulted."""
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)

    def fake_verify(block, *, python):  # pragma: no cover — must not run
        raise AssertionError("verify_runtime_contract called without a block")

    _rr7_closure_stub(monkeypatch, fake_verify)
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    assert barrier["runtime_closure_observed_sha256"] is None


# ---------------------------------------------------------------------------
# RR#7 §2.1 residual pins + §2.4 member-set/manifest hardening (audit digest
# section-3 gaps 1/3/4): live-observed interpreter runtime identity, mode/
# role/order enforcement on the closed member set, and the canonical-JSON
# jail manifest that binds mode+role into the transaction.
# ---------------------------------------------------------------------------
def test_rr7_observed_interpreter_identity_is_live_observed():
    """sys.version/ABI/pyvenv.cfg are OBSERVED by executing the invocation
    path, never copied from a contract or read off the orchestrator."""
    import sysconfig

    import produce_checkpoint as pc

    ident = pc.observed_interpreter_identity(sys.executable)
    assert ident["sys_version"] == sys.version.replace("\n", " ")
    assert ident["abi_platform"] == {
        "platform": sysconfig.get_platform(),
        "cache_tag": sys.implementation.cache_tag,
        "abiflags": getattr(sys, "abiflags", ""),
    }
    # pyvenv fields are consistent: both None (non-venv) or both recorded
    assert (ident["pyvenv_cfg_path"] is None) == (ident["pyvenv_cfg_sha256"] is None)
    if ident["pyvenv_cfg_sha256"] is not None:
        assert len(ident["pyvenv_cfg_sha256"]) == 64


def test_rr7_pre_exec_barrier_refuses_runtime_identity_drift(tmp_path):
    """A matching resolved-binary sha must NOT be enough: drifted
    sys.version, ABI/platform, or pyvenv.cfg pins each refuse before
    intent."""
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)
    contract["argv_contract"]["interpreter_sys_version"] = "9.9.9 (frozen, fake)"
    with pytest.raises(SystemExit, match="sys.version"):
        pc.pre_exec_barrier(slot, contract, jail, argv)

    jail2, contract2, slot2, argv2 = _rr7_barrier_fixture(tmp_path / "b")
    contract2["argv_contract"]["interpreter_abi_platform"] = {
        "platform": "win-amd64",
        "cache_tag": "cpython-99",
        "abiflags": "",
    }
    with pytest.raises(SystemExit, match="ABI/platform"):
        pc.pre_exec_barrier(slot2, contract2, jail2, argv2)

    jail3, contract3, slot3, argv3 = _rr7_barrier_fixture(tmp_path / "c")
    # sys.executable is not the pinned venv: observed pyvenv sha (None or the
    # host's) cannot equal this pin — the frozen-venv claim must refuse
    contract3["argv_contract"]["interpreter_pyvenv_cfg_sha256"] = "0" * 64
    with pytest.raises(SystemExit, match="pyvenv.cfg"):
        pc.pre_exec_barrier(slot3, contract3, jail3, argv3)


def test_rr7_pre_exec_barrier_verifies_dependency_lock(tmp_path):
    import produce_checkpoint as pc

    lock = tmp_path / "uv.lock"
    lock.write_text("[lock]\nversion = 1\n")
    lock_sha = sha256_bytes(lock.read_bytes())

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)
    contract["argv_contract"]["dependency_lock_path"] = str(lock)
    contract["argv_contract"]["dependency_lock_sha256"] = lock_sha
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    assert barrier["jail_manifest_sha256"]  # reached the end: pins accepted

    contract["argv_contract"]["dependency_lock_sha256"] = "f" * 64
    with pytest.raises(SystemExit, match="dependency lock sha"):
        pc.pre_exec_barrier(slot, contract, jail, argv)

    contract["argv_contract"]["dependency_lock_sha256"] = lock_sha
    lock.unlink()
    with pytest.raises(SystemExit, match="dependency lock .* missing"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


def test_rr7_jail_manifest_is_canonical_json_binding_mode_and_role(tmp_path):
    """Digest gap 4 verbatim: two jails differing ONLY in file mode (or
    member role) must not hash identically; the manifest is canonical JSON
    rows {relpath, mode, size, sha256, role} sorted by relpath."""
    import produce_checkpoint as pc

    a = tmp_path / "a"
    b = tmp_path / "b"
    for root in (a, b):
        (root / "scripts").mkdir(parents=True)
        (root / "scripts" / "t.py").write_text("print(1)\n")
    plain = pc.jail_manifest_sha256(a)
    (b / "scripts" / "t.py").chmod(0o755)
    assert pc.jail_manifest_sha256(b) != plain  # mode is bound
    assert pc.jail_manifest_sha256(a, {"scripts/t.py": "trainer"}) != plain  # role too

    # exact canonical form, recomputed independently
    body = (a / "scripts" / "t.py").read_bytes()
    rows = [
        {
            "relpath": "scripts/t.py",
            "mode": 0o100644,
            "size": len(body),
            "sha256": sha256_bytes(body),
            "role": None,
        }
    ]
    expected = sha256_bytes(
        json.dumps(rows, sort_keys=True, separators=(",", ":")).encode()
    )
    assert plain == expected


def _rr7_pinned_jail_contract(rows):
    return {
        "schema": "jail-contract/v1",
        "resolver_tool_sha256": sha256_bytes((GATE / "slot_symbols.py").read_bytes()),
        "required_members": rows,
    }


def test_rr7_pre_exec_barrier_enforces_member_mode_role_and_order(tmp_path):
    """Digest gap 3: required_members is an exact ORDERED mapping with sha,
    normalized mode, and role — wrong mode, unsorted/duplicated rows, or a
    partial row each refuse; a full match binds the roles into the jail
    manifest."""
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)
    trainer_sha = sha256_bytes((jail / "trainer.py").read_bytes())
    good_row = {
        "dest_relpath": "trainer.py",
        "content": {"sha256": trainer_sha},
        "mode": 0o100644,
        "role": "trainer",
    }

    contract["jail_contract"] = _rr7_pinned_jail_contract([good_row])
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    assert barrier["jail_manifest_sha256"] == pc.jail_manifest_sha256(
        jail, {"trainer.py": "trainer"}
    )

    # right bytes, wrong permissions — not the frozen member
    (jail / "trainer.py").chmod(0o755)
    with pytest.raises(SystemExit, match="mode diverges"):
        pc.pre_exec_barrier(slot, contract, jail, argv)
    (jail / "trainer.py").chmod(0o644)

    # unsorted mapping is a malformed freeze, refused before any hashing
    (jail / "aaa.txt").write_text("x")
    row2 = {
        "dest_relpath": "aaa.txt",
        "content": {"sha256": sha256_bytes(b"x")},
        "mode": 0o100644,
        "role": "side-input",
    }
    contract["jail_contract"] = _rr7_pinned_jail_contract([good_row, row2])
    with pytest.raises(SystemExit, match="sorted by ASCII"):
        pc.pre_exec_barrier(slot, contract, jail, argv)
    contract["jail_contract"] = _rr7_pinned_jail_contract([row2, good_row])
    assert pc.pre_exec_barrier(slot, contract, jail, argv)["jail_manifest_sha256"]

    # duplicated dest is refused
    contract["jail_contract"] = _rr7_pinned_jail_contract([row2, row2, good_row])
    with pytest.raises(SystemExit, match="reordered/duplicated"):
        pc.pre_exec_barrier(slot, contract, jail, argv)

    # a partial row (missing role) is refused, never defaulted
    partial = {k: v for k, v in good_row.items() if k != "role"}
    contract["jail_contract"] = _rr7_pinned_jail_contract([row2, partial])
    with pytest.raises(SystemExit, match="partial member pin"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


def _rr7_option_a_fixture(tmp_path):
    """Linear-shaped jail_contract fixture: staged pairs at the family's
    slice_pairs_pattern (SYMBOLIC row) + a static trainer (LITERAL row),
    ASCII-sorted; the slot row is the resolver's only resolution source."""
    import produce_checkpoint as pc

    jail, contract, slot, argv = _rr7_barrier_fixture(tmp_path)
    pairs_bytes = b'{"ep":"e1"}\n'
    (jail / "slices" / "S01").mkdir(parents=True)
    (jail / "slices" / "S01" / "pairs.jsonl").write_bytes(pairs_bytes)
    contract["slice_pairs_pattern"] = "slices/{slice_id}/pairs.jsonl"
    trainer_sha = sha256_bytes((jail / "trainer.py").read_bytes())
    contract["jail_contract"] = {
        "schema": "jail-contract/v1",
        "resolver_tool_sha256": sha256_bytes((GATE / "slot_symbols.py").read_bytes()),
        "required_members": [
            {
                "dest_relpath": "slices/{slice_id}/pairs.jsonl",
                "content": {"ref": "slot.staged_pairs_sha256"},
                "mode": 0o100644,
                "role": "staged-pairs",
            },
            {
                "dest_relpath": "trainer.py",
                "content": {"sha256": trainer_sha},
                "mode": 0o100644,
                "role": "trainer",
            },
        ],
    }
    slot = dict(slot)
    slot["staged_pairs_sha256"] = sha256_bytes(pairs_bytes)
    slot["artifact_sha256"] = None
    slot["slot_status"] = "PENDING"
    return pc, jail, contract, slot, argv, trainer_sha


def test_rr7_option_a_symbolic_member_resolves_and_records_triple(tmp_path):
    """Option-A happy path: the symbolic staged-pairs row resolves through
    the shared resolver from the FROZEN slot row, the literal trainer row
    resolves alongside it, and the barrier returns the #3671 resolution
    records (symbolic contract + resolved SHA + slot-row immutable identity)
    for BOTH members."""
    import slot_symbols

    pc, jail, contract, slot, argv, trainer_sha = _rr7_option_a_fixture(tmp_path)
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    recs = barrier["jail_member_resolutions"]
    assert [r["dest_relpath"] for r in recs] == [
        "slices/S01/pairs.jsonl",
        "trainer.py",
    ]
    sym, lit = recs
    assert (sym["form"], sym["symbol"]) == ("ref", "slot.staged_pairs_sha256")
    assert sym["resolved_sha256"] == slot["staged_pairs_sha256"]
    assert (lit["form"], lit["symbol"]) == ("literal", None)
    assert lit["resolved_sha256"] == trainer_sha
    expected_identity = slot_symbols.slot_row_immutable_identity(slot)
    for r in recs:
        assert r["slot_id"] == expected_identity["slot_id"]
        assert (
            r["slot_row_projection_sha256"]
            == expected_identity["slot_row_projection_sha256"]
        )
    # roles from the closed set flow into the manifest binding
    assert barrier["jail_manifest_sha256"] == pc.jail_manifest_sha256(
        jail,
        {"slices/S01/pairs.jsonl": "staged-pairs", "trainer.py": "trainer"},
    )


def test_rr7_option_a_wrong_slot_pin_refuses_through_the_resolver_path(tmp_path):
    """Constraint 4b, producer half: a wrong staged_pairs_sha256 in the
    (sandboxed) frozen slot row propagates to refusal through the barrier's
    member-set comparison — the resolver resolved the WRONG frozen value, so
    the staged bytes no longer match. (Fixture has no --pairs option, so the
    legacy step-3 check is bypassed: the refusal is the Option-A path's own.)"""
    pc, jail, contract, slot, argv, _ = _rr7_option_a_fixture(tmp_path)
    slot["staged_pairs_sha256"] = "e" * 64
    with pytest.raises(SystemExit, match="jail member set diverges"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


def test_rr7_option_a_wrong_slot_pin_refuses_in_local_fill_reconciliation(tmp_path):
    """Constraint 4b, local-fill half: fill calls the SAME shared resolver
    against the fresh frozen slot row and refuses before neutral mutation."""
    import fill_checkpoint_slot as fcs

    pc, jail, contract, slot, argv, _ = _rr7_option_a_fixture(tmp_path)
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    core = {
        "cwd": str(jail),
        "jail_manifest_sha256": barrier["jail_manifest_sha256"],
        "jail_member_resolutions": barrier["jail_member_resolutions"],
        "staged_pairs_sha256": barrier["staged_pairs_sha256"],
    }
    wrong_frozen_row = {**slot, "staged_pairs_sha256": "e" * 64}
    with pytest.raises(SystemExit, match="shared slot-symbol resolution.*wrong-bytes"):
        fcs._reconcile_jail_and_pairs(
            core, wrong_frozen_row, contract, Path("fill-reconciliation")
        )


def test_rr7_local_fill_rehashes_sidecar_and_reruns_pinned_classifier(tmp_path):
    import failure_classifier
    import fill_checkpoint_slot as fcs

    pc, jail, contract, slot, argv, trainer_sha = _rr7_option_a_fixture(tmp_path)
    barrier = pc.pre_exec_barrier(slot, contract, jail, argv)
    classifier_path = GATE / "failure_classifier.py"
    classifier_sha = sha256_bytes(classifier_path.read_bytes())
    stderr = b"ModuleNotFoundError: no module named frozen_probe\n"
    classified = failure_classifier.classify(
        stage="subprocess", exit_code=3, stderr=stderr
    )
    sidecar = tmp_path / "ledger-failed.stderr"
    sidecar.write_bytes(stderr)
    sidecar.chmod(0o600)
    contract["validator_sha256"] = sha256_bytes(
        (GATE / "fill_checkpoint_slot.py").read_bytes()
    )
    contract["resolution_engine_sha256"] = sha256_bytes(
        (GATE / "slot_resolution_txn.py").read_bytes()
    )
    contract["trainer_sha256"] = trainer_sha
    env_sha = sha256_bytes(
        json.dumps(
            fcs._expected_execution_env(contract),
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    )
    core = {
        "launch_ledger_id": "ledger-failed",
        "cwd": str(jail),
        "exit_code": 3,
        "stderr_sidecar_path": str(sidecar),
        "stderr_sidecar_size": len(stderr),
        "stderr_total_bytes": len(stderr),
        "stderr_sha256": sha256_bytes(stderr),
        "failure_signature": classified["failure_signature"],
        "failure_category": classified["failure_category"],
        "failure_rule_id": classified["rule_id"],
        "failure_classifier_sha256": classifier_sha,
        "argv": argv,
        "interpreter_invocation_path": argv[0],
        "interpreter_realpath": str(Path(argv[0]).resolve()),
        "interpreter_sha256": sha256_bytes(Path(argv[0]).resolve().read_bytes()),
        "trainer_sha256": trainer_sha,
        "execution_env_sha256": env_sha,
        "runtime_closure_observed_sha256": None,
        "jail_manifest_sha256": barrier["jail_manifest_sha256"],
        "jail_member_resolutions": barrier["jail_member_resolutions"],
        "staged_pairs_sha256": barrier["staged_pairs_sha256"],
    }
    freeze = {
        "files": {
            "fac:gate/failure_classifier.py": {"sha256": classifier_sha},
        }
    }
    facts = fcs.reconcile_local_execution(
        core, slot, contract, freeze, Path("attempt.json")
    )
    assert facts["failure_classification"] == classified
    assert facts["stderr_sidecar_sha256"] == sha256_bytes(stderr)

    forged = {**core, "failure_category": "engine-crash"}
    with pytest.raises(SystemExit, match="pinned fill-side classifier rerun"):
        fcs.reconcile_local_execution(
            forged, slot, contract, freeze, Path("forged-attempt.json")
        )


def test_rr7_local_fill_rederives_staged_pairs_from_projected_inputs(
    tmp_path, monkeypatch
):
    import fill_checkpoint_slot as fcs
    import slice_pairs

    repo = tmp_path / "fac"
    gate = repo / "gate"
    corpus = gate / "corpus.gz"
    gate.mkdir(parents=True)
    corpus.write_bytes(b"projected-corpus")
    materialized = b'{"ep":"e1"}\n'
    definition = {
        "schema": "slice-definition/v2",
        "derivation_schema": "slice-pairs-derivation/v1",
        "derivation_tool_sha256": sha256_bytes((GATE / "slice_pairs.py").read_bytes()),
        "corpus_path": "gate/corpus.gz",
        "slices": {
            "S01": {
                "episodes": ["e1"],
                "pairs_sha256": sha256_bytes(materialized),
                "pairs_n_bytes": len(materialized),
                "pairs_n_records": 1,
            }
        },
    }
    definition_path = gate / "slice-definition.json"
    definition_path.write_text(json.dumps(definition))
    monkeypatch.setattr(fcs, "SLICE_DEFINITION", definition_path)
    monkeypatch.setattr(
        slice_pairs,
        "materialize_slice_bytes",
        lambda slice_id, slices, path: (
            materialized
            if slice_id == "S01" and slices == definition["slices"] and path == corpus
            else b"wrong"
        ),
    )
    freeze = {
        "files": {
            "fac:gate/slice_pairs.py": {
                "sha256": definition["derivation_tool_sha256"],
            },
            "fac:gate/slice-definition.json": {
                "sha256": sha256_bytes(definition_path.read_bytes()),
            },
            "fac:gate/corpus.gz": {"sha256": sha256_bytes(corpus.read_bytes())},
        }
    }
    slot = {
        "slot_id": "lin-cf-s01",
        "slice_id": "S01",
        "slice_derivation_schema": "slice-pairs-derivation/v1",
        "staged_pairs_sha256": sha256_bytes(materialized),
        "staged_pairs_n_bytes": len(materialized),
        "staged_pairs_n_records": 1,
    }
    observed = fcs._rederive_frozen_slice(slot, freeze, Path("receipt.json"))
    assert observed["staged_pairs_sha256"] == sha256_bytes(materialized)
    assert observed["staged_pairs_n_records"] == 1

    with pytest.raises(SystemExit, match="staged_pairs_n_bytes"):
        fcs._rederive_frozen_slice(
            {**slot, "staged_pairs_n_bytes": len(materialized) + 1},
            freeze,
            Path("wrong-slot.json"),
        )


def test_rr7_option_a_form_position_mismatches_refused(tmp_path):
    """A ref where the position requires a literal (trainer dest) and a
    literal where it requires a ref (the slice_pairs_pattern dest) both die
    inside the ONE shared resolver — the ruled positional matrix."""
    pc, jail, contract, slot, argv, trainer_sha = _rr7_option_a_fixture(tmp_path)
    rows = contract["jail_contract"]["required_members"]

    rows[1]["content"] = {"ref": "slot.staged_pairs_sha256"}
    with pytest.raises(SystemExit, match="requires 'literal'"):
        pc.pre_exec_barrier(slot, contract, jail, argv)
    rows[1]["content"] = {"sha256": trainer_sha}

    rows[0]["content"] = {"sha256": slot["staged_pairs_sha256"]}
    with pytest.raises(SystemExit, match="requires 'ref'"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


@pytest.mark.parametrize(
    ("case", "bad_pin"),
    [
        ("absent", None),
        ("null", None),
        ("empty", ""),
        ("short", "f" * 63),
        ("uppercase", "F" * 64),
        ("nonhex", "z" * 64),
    ],
)
def test_rr7_option_a_missing_or_malformed_resolver_pin_refused(
    tmp_path, case, bad_pin
):
    """The resolver pin is mandatory whenever required_members exists and
    must be exactly 64 lowercase hex — absent/null/malformed values die
    before any resolver code can be trusted or called."""
    pc, jail, contract, slot, argv, _ = _rr7_option_a_fixture(tmp_path)
    if case == "absent":
        contract["jail_contract"].pop("resolver_tool_sha256")
    else:
        contract["jail_contract"]["resolver_tool_sha256"] = bad_pin
    with pytest.raises(SystemExit, match="absent/null/malformed resolver pin"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


def test_rr7_option_a_unpinned_resolver_refused_before_resolution(tmp_path):
    """A jail_contract that pins resolver_tool_sha256 refuses when the
    on-disk slot_symbols.py does not match — BEFORE any member resolution
    runs (same caller-side class as the runtime_contract closure-tool pin)."""
    import slot_symbols

    pc, jail, contract, slot, argv, _ = _rr7_option_a_fixture(tmp_path)
    contract["jail_contract"]["resolver_tool_sha256"] = "f" * 64
    with pytest.raises(SystemExit, match="unpinned resolver"):
        pc.pre_exec_barrier(slot, contract, jail, argv)
    # the REAL on-disk resolver bytes pass
    contract["jail_contract"]["resolver_tool_sha256"] = sha256_bytes(
        Path(slot_symbols.__file__).resolve().read_bytes()
    )
    assert pc.pre_exec_barrier(slot, contract, jail, argv)["jail_member_resolutions"]


def test_rr7_option_a_unknown_symbol_refused_at_barrier(tmp_path):
    """Constraint 4a at the wiring level: an unknown symbolic key in a frozen
    contract is a hard load-time failure through the barrier, never a
    literal."""
    pc, jail, contract, slot, argv, _ = _rr7_option_a_fixture(tmp_path)
    contract["jail_contract"]["required_members"][0]["content"] = {
        "ref": "slot.train_seed"
    }
    with pytest.raises(SystemExit, match="enum is CLOSED"):
        pc.pre_exec_barrier(slot, contract, jail, argv)


def test_rr7_option_a_linear_emission_deterministic_and_valid():
    """Constraint 4c: the emitted linear jail_contract round-trips the
    generator deterministically (byte-identical canonical JSON across
    builds) and every row validates through the shared resolver with the
    form its position requires."""
    import make_executable_freeze_manifest as m
    import slot_symbols

    b1 = m.linear_jail_contract("ab" * 32)
    b2 = m.linear_jail_contract("ab" * 32)
    canon = json.dumps(b1, sort_keys=True, separators=(",", ":"))
    assert canon == json.dumps(b2, sort_keys=True, separators=(",", ":"))
    assert b1["schema"] == "jail-contract/v1"
    # the emitted block pins the resolver's own on-disk bytes
    assert b1["resolver_tool_sha256"] == sha256_bytes(
        (GATE / "slot_symbols.py").read_bytes()
    )
    dests = [r["dest_relpath"] for r in b1["required_members"]]
    assert dests == sorted(dests) and len(set(dests)) == len(dests)
    pairs_row, trainer_row = b1["required_members"]
    # the symbolic member IS the linear slice_pairs_pattern dest
    assert (
        pairs_row["dest_relpath"]
        == "runs/step2/slices/{slice_id}/imitation_pairs.jsonl"
    )
    assert slot_symbols.parse_member_source(pairs_row["content"]) == (
        "ref",
        "slot.staged_pairs_sha256",
    )
    assert slot_symbols.parse_member_source(trainer_row["content"]) == (
        "literal",
        "ab" * 32,
    )
    assert {r["mode"] for r in b1["required_members"]} == {0o100644}
    assert [r["role"] for r in b1["required_members"]] == [
        "staged-pairs",
        "trainer",
    ]


# ---------------------------------------------------------------------------
# RR#7 §4.2/§4.3 DEDICATED tests (audit digest section 2, blocking gap):
# close_once / recover_open_intents / write_stderr_sidecar were exercised
# only incidentally through one e2e — these pin their design teeth directly.
# ---------------------------------------------------------------------------
def _rr7_ledger(monkeypatch, tmp_path):
    import produce_checkpoint as pc

    monkeypatch.setattr(pc, "LAUNCH_LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    return pc


def _rr7_ledger_rows(tmp_path):
    path = tmp_path / "ledger.jsonl"
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text().splitlines() if line]


def _rr7_abort_row(pc, ledger_id, reason="stage=test: injected abort"):
    row = {k: None for k in pc.TERMINAL_REQUIRED_FIELDS}
    row.update(
        {
            "ledger_id": ledger_id,
            "slot_id": "SLOT-X",
            "phase": "abort",
            "abort_reason": reason,
            "argv": [],
        }
    )
    return row


def _rr7_commit_row(pc, ledger_id, *, exit_code=1, artifact_sha256=None):
    return {
        "ledger_id": ledger_id,
        "slot_id": "SLOT-X",
        "attempt_id": "a1",
        "phase": "commit",
        "wrapper_sha256": "w" * 64,
        "anchor_capsule_id": "cap-1",
        "anchor_core_sha256": "c" * 64,
        "anchor_root_verifier_sha256": "v" * 64,
        "split_sha256": "s" * 64,
        "freeze_sha256": "f" * 64,
        "argv": ["/usr/bin/python3", "t.py"],
        "argv_sha256": "a" * 64,
        "cwd": "/tmp/jail",
        "jail_manifest_sha256": "j" * 64,
        "jail_member_resolutions_sha256": None,
        "host": "testhost",
        "interpreter_sha256": "i" * 64,
        "start_utc": "2026-07-17T00:00:00Z",
        "end_utc": "2026-07-17T00:00:01Z",
        "exit_code": exit_code,
        "stdout_sha256": "o" * 64,
        "stderr_sha256": "e" * 64,
        "artifact_path": None,
        "artifact_sha256": artifact_sha256,
        "receipt_core_sha256": "r" * 64,
        "liveness_receipt_core_sha256": None,
    }


def test_rr7_close_once_dedup_and_landed_commit_protection(tmp_path, monkeypatch):
    """Two closers, a racing recovery, or a recovery running after the real
    terminal landed all yield EXACTLY ONE terminal — and a landed COMMIT is
    never re-closed into an abort."""
    pc = _rr7_ledger(monkeypatch, tmp_path)
    assert pc.close_once(_rr7_abort_row(pc, "L1")) is True
    assert pc.close_once(_rr7_abort_row(pc, "L1", "stage=test: second closer")) is False
    terminals = [
        r
        for r in _rr7_ledger_rows(tmp_path)
        if r["ledger_id"] == "L1" and r["phase"] in pc.TERMINAL_PHASES
    ]
    assert len(terminals) == 1
    assert terminals[0]["abort_reason"] == "stage=test: injected abort"

    # reverse race: the commit reached disk; a late abort closer is a no-op
    assert pc.close_once(_rr7_commit_row(pc, "L2")) is True
    assert pc.close_once(_rr7_abort_row(pc, "L2")) is False
    l2 = [
        r
        for r in _rr7_ledger_rows(tmp_path)
        if r["ledger_id"] == "L2" and r["phase"] in pc.TERMINAL_PHASES
    ]
    assert [r["phase"] for r in l2] == ["commit"]


def test_rr7_close_once_refuses_malformed_terminals(tmp_path, monkeypatch):
    """Validation happens BEFORE append — a malformed terminal row never
    lands, and the refusals are field-precise."""
    pc = _rr7_ledger(monkeypatch, tmp_path)
    bad_phase = _rr7_abort_row(pc, "L3")
    bad_phase["phase"] = "intent"
    with pytest.raises(SystemExit, match="terminal ledger phase"):
        pc.close_once(bad_phase)
    incomplete = _rr7_abort_row(pc, "L3")
    del incomplete["stderr_sha256"]
    with pytest.raises(SystemExit, match="missing bound fields"):
        pc.close_once(incomplete)
    empty_commit = _rr7_commit_row(pc, "L3")
    empty_commit["freeze_sha256"] = None
    with pytest.raises(SystemExit, match="empty bound fields"):
        pc.close_once(empty_commit)
    no_exit = _rr7_commit_row(pc, "L3")
    no_exit["exit_code"] = None
    with pytest.raises(SystemExit, match="without an observed exit_code"):
        pc.close_once(no_exit)
    zero_no_artifact = _rr7_commit_row(pc, "L3", exit_code=0, artifact_sha256=None)
    with pytest.raises(SystemExit, match="no artifact_sha256"):
        pc.close_once(zero_no_artifact)
    assert _rr7_ledger_rows(tmp_path) == []  # nothing malformed ever landed


def test_rr7_recover_open_intents_abort_only_and_idempotent(tmp_path, monkeypatch):
    """Acceptance test 15's core: an open intent closes as ABORT ONLY with
    the recovery stage stamped; a ledger id whose commit landed is skipped
    entirely; a second recovery pass is a no-op."""
    pc = _rr7_ledger(monkeypatch, tmp_path)
    pc.ledger_append(
        {
            "ledger_id": "OPEN1",
            "slot_id": "S1",
            "phase": "intent",
            "attempt_id": None,
            "argv_sha256": "a" * 64,
            "host": "h",
            "interpreter_sha256": "i" * 64,
            "jail_manifest_sha256": "j" * 64,
            "anchor_capsule_id": "cap",
        }
    )
    pc.ledger_append({"ledger_id": "DONE1", "slot_id": "S1", "phase": "intent"})
    assert pc.close_once(_rr7_commit_row(pc, "DONE1")) is True

    assert pc.recover_open_intents() == ["OPEN1"]
    rows = _rr7_ledger_rows(tmp_path)
    open1 = [
        r
        for r in rows
        if r["ledger_id"] == "OPEN1" and r["phase"] in pc.TERMINAL_PHASES
    ]
    assert len(open1) == 1
    assert open1[0]["phase"] == "abort"
    assert pc.RECOVERY_STAGE in open1[0]["abort_reason"]
    # recovery observed nothing — it may never invent execution evidence
    assert open1[0]["exit_code"] is None
    assert open1[0]["artifact_sha256"] is None
    assert open1[0]["receipt_core_sha256"] is None
    done1 = [
        r
        for r in rows
        if r["ledger_id"] == "DONE1" and r["phase"] in pc.TERMINAL_PHASES
    ]
    assert [r["phase"] for r in done1] == ["commit"]  # never re-closed
    assert pc.recover_open_intents() == []  # idempotent


def test_rr7_write_stderr_sidecar_mode_excl_and_sha(tmp_path, monkeypatch):
    """§4.2: mode-0600 sidecar, O_EXCL collision refusal (original evidence
    untouched), and returned sha == exactly the captured bytes."""
    import produce_checkpoint as pc

    monkeypatch.setattr(pc, "STDERR_SIDECAR_DIR", tmp_path / "runtime")
    body = b"Traceback (most recent call last): boom\n"
    out = pc.write_stderr_sidecar("LID1", body)
    path = Path(out["stderr_sidecar_path"])
    assert path == tmp_path / "runtime" / "LID1.stderr"
    assert path.read_bytes() == body
    assert (path.stat().st_mode & 0o777) == 0o600
    assert out["stderr_sidecar_sha256"] == sha256_bytes(body)
    assert out["stderr_sidecar_size"] == len(body)
    with pytest.raises(FileExistsError):
        pc.write_stderr_sidecar("LID1", b"a stray retry's different bytes")
    assert path.read_bytes() == body


def test_rr7_injected_post_intent_stage_failure_yields_exactly_one_abort(
    tmp_path, monkeypatch
):
    """§8 test-5 property (representative): a post-intent stage failure
    inside run_terminal_execution closes the transaction with EXACTLY ONE
    abort naming its stage, then re-raises — never a commit, never a second
    terminal."""
    import produce_checkpoint as pc

    jail = tmp_path / "jail"
    jail.mkdir()
    stub = jail / "stub_trainer.py"
    out_path = jail / "out.bin"
    stub.write_text(
        "import sys\n"
        "args = dict(zip(sys.argv[1::2], sys.argv[2::2]))\n"
        "open(args['--out'], 'w').write('stub artifact bytes')\n"
    )
    contract = {
        "producer_wrapper_sha256": sha256_bytes(
            (GATE / "produce_checkpoint.py").read_bytes()
        ),
        "config_sha256": "c" * 64,
        "output_path_pattern": str(out_path),
        "argv_contract": {
            "interpreter": sys.executable,
            "trainer": str(stub),
            "slot_bound_options": {"--out": "x"},
        },
    }
    slot = _slot_row("lin-cf-s01")
    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    monkeypatch.setattr(pc, "LAUNCH_LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    monkeypatch.setattr(pc, "STDERR_SIDECAR_DIR", tmp_path / "runtime")

    def broken_package(slot_arg, contract_arg, jail_arg):
        raise RuntimeError("injected artifact-stage failure")

    monkeypatch.setattr(pc, "_package_artifact", broken_package)
    with pytest.raises(RuntimeError, match="injected artifact-stage failure"):
        pc.run_terminal_execution(
            slot,
            contract,
            phase="test",
            attempt_id="att-1",
            launch_anchor=_verified_section5a_anchor(
                tmp_path,
                split_path=split_path,
                freeze_path=freeze_path,
                name="injected-failure-anchor.json",
            ),
            jail_dir=jail,
            receipt_out=tmp_path / "receipt.json",
        )
    rows = _rr7_ledger_rows(tmp_path)
    intents = [r for r in rows if r["phase"] == "intent"]
    terminals = [r for r in rows if r["phase"] in pc.TERMINAL_PHASES]
    assert len(intents) == 1
    assert len(terminals) == 1
    assert terminals[0]["phase"] == "abort"
    assert terminals[0]["ledger_id"] == intents[0]["ledger_id"]
    assert "stage=artifact" in terminals[0]["abort_reason"]
    assert "injected artifact-stage failure" in terminals[0]["abort_reason"]
    # the receipt was never written; no execution evidence was manufactured
    assert not (tmp_path / "receipt.json").exists()
    assert pc.recover_open_intents() == []  # the abort already closed it


# ---------------------------------------------------------------------------
# RR#7 §4.2 BOUNDED CAPTURE (audit digest section-2 gap: "the sidecar file is
# never bounded ... a genuinely resource-exhausting subprocess OOM-kills the
# capturing wrapper BEFORE the classifier can run"). The frozen capture
# policy is now enforced at capture time: at most cap+1 bytes are retained
# per stream (draining fully, counting the true total), so overflow reaches
# classify() as len > MAX — the SAME frozen constant — and the
# stderr-capture-overflow rule fires deterministically instead of the
# wrapper dying first.
# ---------------------------------------------------------------------------
def test_rr7_bounded_capture_retains_cap_plus_one_and_true_totals(tmp_path):
    import produce_checkpoint as pc

    rc_code, out_b, out_total, err_b, err_total = pc._bounded_capture_run(
        [
            sys.executable,
            "-c",
            "import sys; sys.stdout.write('o'*1000); "
            "sys.stderr.write('e'*1000); sys.exit(3)",
        ],
        tmp_path,
        {"PATH": "/usr/bin:/bin"},
        cap=100,
    )
    assert rc_code == 3
    assert out_b == b"o" * 101 and out_total == 1000
    assert err_b == b"e" * 101 and err_total == 1000

    # under the cap: retained == full stream, total == len(retained)
    rc_code, out_b, out_total, err_b, err_total = pc._bounded_capture_run(
        [sys.executable, "-c", "import sys; sys.stderr.write('ok')"],
        tmp_path,
        {"PATH": "/usr/bin:/bin"},
        cap=100,
    )
    assert rc_code == 0
    assert err_b == b"ok" and err_total == 2
    assert out_b == b"" and out_total == 0


def test_rr7_stderr_overflow_is_deterministic_resource_exhaustion_evidence(
    tmp_path, monkeypatch
):
    """The design's exact guarantee, end-to-end: a failing trainer with an
    oversized stderr commits an ATTEMPT receipt classified
    stderr-capture-overflow/resource-exhaustion, with a BOUNDED sidecar whose
    sha equals the receipt's stderr sha, and the true byte count recorded as
    an observed total — the wrapper survives to testify."""
    import failure_classifier
    import produce_checkpoint as pc

    jail = tmp_path / "jail"
    jail.mkdir()
    stub = jail / "stub_trainer.py"
    out_path = jail / "out.bin"
    stub.write_text("import sys\nsys.stderr.write('x' * 1000)\nsys.exit(1)\n")
    contract = {
        "producer_wrapper_sha256": sha256_bytes(
            (GATE / "produce_checkpoint.py").read_bytes()
        ),
        "config_sha256": "c" * 64,
        "output_path_pattern": str(out_path),
        "argv_contract": {
            "interpreter": sys.executable,
            "trainer": str(stub),
            "slot_bound_options": {"--out": "x"},
        },
    }
    slot = _slot_row("lin-cf-s01")
    split_path, freeze_path = _section5a_sandbox_manifests(tmp_path)
    monkeypatch.setattr(pc, "SPLIT", split_path)
    monkeypatch.setattr(pc, "FREEZE_MANIFEST", freeze_path)
    monkeypatch.setattr(pc, "LAUNCH_LEDGER", tmp_path / "ledger.jsonl")
    monkeypatch.setattr(pc, "LEDGER_LOCK", tmp_path / ".ledger.lock")
    monkeypatch.setattr(pc, "STDERR_SIDECAR_DIR", tmp_path / "runtime")
    monkeypatch.setattr(failure_classifier, "MAX_STDERR_BYTES", 64)

    receipt_out = tmp_path / "receipt.json"
    pc.run_terminal_execution(
        slot,
        contract,
        phase="test",
        attempt_id="att-ovf",
        launch_anchor=_verified_section5a_anchor(
            tmp_path,
            split_path=split_path,
            freeze_path=freeze_path,
            name="bounded-stderr-anchor.json",
        ),
        jail_dir=jail,
        receipt_out=receipt_out,
    )
    core = json.loads(receipt_out.read_bytes())["core"]
    retained = b"x" * 65  # cap+1 — overflow is self-evident, bytes bounded
    assert core["exit_code"] == 1
    assert core["outcome"] == "FAILED"
    assert core["failure_rule_id"] == "stderr-capture-overflow"
    assert core["failure_category"] == "resource-exhaustion"
    assert core["stderr_total_bytes"] == 1000  # the TRUE size, observed
    assert core["stderr_sidecar_size"] == 65  # the sidecar is BOUNDED
    assert core["stderr_sha256"] == sha256_bytes(retained)
    sidecar = Path(core["stderr_sidecar_path"])
    assert sidecar.read_bytes() == retained  # receipt/sidecar: SAME bytes
    rows = [
        json.loads(line)
        for line in (tmp_path / "ledger.jsonl").read_text().splitlines()
    ]
    terminals = [r for r in rows if r["phase"] in pc.TERMINAL_PHASES]
    assert [r["phase"] for r in terminals] == ["commit"]  # survived to testify
    intents = [r for r in rows if r["phase"] == "intent"]
    # §4.3: the receipt destination is bound into the intent so recovery can
    # locate the orphan a crash would leave behind
    assert intents[0]["receipt_path"] == str(receipt_out)


def test_rr7_recovery_quarantines_orphans_after_abort(tmp_path, monkeypatch):
    """§4.3 explicit cleanup (audit digest: previously absent, docstring
    disavowed it): after the abort record lands, the intent's recorded
    receipt and the ledger-id-keyed sidecar are MOVED to quarantine — bytes
    preserved, originals gone, never deleted, never read as evidence. A
    ledger id whose commit landed is never touched; a second pass is a
    no-op."""
    pc = _rr7_ledger(monkeypatch, tmp_path)
    monkeypatch.setattr(pc, "STDERR_SIDECAR_DIR", tmp_path / "runtime")
    monkeypatch.setattr(pc, "QUARANTINE_DIR", tmp_path / "quarantine")
    orphan_receipt = tmp_path / "orphan-receipt.json"
    orphan_receipt.write_text('{"core": {"unverified": true}}')
    (tmp_path / "runtime").mkdir()
    orphan_sidecar = tmp_path / "runtime" / "OPEN1.stderr"
    orphan_sidecar.write_bytes(b"crash-time stderr")
    pc.ledger_append(
        {
            "ledger_id": "OPEN1",
            "slot_id": "S1",
            "phase": "intent",
            "receipt_path": str(orphan_receipt),
        }
    )
    done_receipt = tmp_path / "done-receipt.json"
    done_receipt.write_text('{"core": {}}')
    pc.ledger_append(
        {
            "ledger_id": "DONE1",
            "slot_id": "S1",
            "phase": "intent",
            "receipt_path": str(done_receipt),
        }
    )
    assert pc.close_once(_rr7_commit_row(pc, "DONE1")) is True

    assert pc.recover_open_intents() == ["OPEN1"]
    # originals moved, bytes preserved under quarantine names
    assert not orphan_receipt.exists()
    assert not orphan_sidecar.exists()
    q = tmp_path / "quarantine"
    assert (q / "OPEN1.orphan-receipt.json.quarantined").read_text() == (
        '{"core": {"unverified": true}}'
    )
    assert (q / "OPEN1.OPEN1.stderr.quarantined").read_bytes() == b"crash-time stderr"
    # the landed-commit transaction's receipt is never touched
    assert done_receipt.exists()
    assert pc.recover_open_intents() == []  # idempotent no-op
