"""Synthetic tests for gate/fill_remote_checkpoint_slot.py — remote capsule
fill path with non-mixability enforcement, ordering guard, and attempt policy.

Every fixture is hand-built (no real capsules, no real signatures). Tests use
unittest.mock to isolate the capsule loader and avoid filesystem dependencies.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pytest

from gate import slot_resolution_txn as srt
from gate import step2_attempt_policy as ap

# ---- helpers ----

SCHEMA = "remote-checkpoint-slot-fill/v1"
REMOTE_CONTEXT = "arena-1-remote-with-attestation"
EXPECTED_TOOL_SHA256 = "a" * 64


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _sha256_file(p: Path) -> str:
    d = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def _canonical(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()


def _canonical_compact(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _minimal_terminal_record(**overrides) -> dict:
    """A minimal valid terminal_record for a remote capsule."""
    rec = {
        "phase": "commit",
        "slot_id": "gbm-cf-s08",
        "slice_id": "s08",
        "train_seed": 42,
        "family": "gbm",
        "host": "arena-1-node-01",
        "exit_code": 0,
        "config_sha256": "b" * 64,
        "argv_sha256": "c" * 64,
        "anchor_capsule_id": "test-anchor-1",
        "anchor_core_sha256": "d" * 64,
        "freeze_sha256": "e" * 64,
        "split_sha256": "f" * 64,
        "artifact_sha256": "a9" * 32,  # hex-only; valid 64-char sha256
        "attempt_id": "capsule-attempt-1",
        "attempt_number": 1,
        "wrapper_tool_sha256": "ac" * 32,  # hex-only
    }
    rec.update(overrides)
    return rec


def _minimal_capsule_core(**overrides) -> dict:
    """A minimal valid remote result capsule core."""
    terminal = overrides.pop("terminal_record", None)
    if terminal is None:
        terminal = _minimal_terminal_record()
    core = {
        "schema": "remote-result-capsule/v1",
        "kind": "remote-result",
        "execution_context": REMOTE_CONTEXT,
        "terminal_record": terminal,
        "capsule_id": "test-capsule-1",
    }
    core.update(overrides)
    if "terminal_record" not in overrides and terminal is not None:
        core["terminal_record"] = terminal
    return core


def _write_capsule_file(core: dict, tmp_path: Path, name: str = "capsule.json") -> Path:
    """Write a minimal capsule file (core + core_sha256) to tmp_path.
    This creates a file that passes load_remote_result_capsule's existence
    check, though the test provides its own mock return value."""
    core_sha = _sha256_bytes(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
    )
    capsule = {
        "core": core,
        "core_sha256": core_sha,
    }
    path = tmp_path / name
    path.write_text(json.dumps(capsule, indent=1, sort_keys=True) + "\n")
    return path


def _minimal_freeze(**overrides) -> dict:
    """A minimal executable freeze dict."""
    fam_contract = {
        "execution_context": REMOTE_CONTEXT,
        "trainer_sha256": "a1" * 32,
        "config_sha256": "b2" * 32,
        "producer_wrapper_sha256": "c3" * 32,
        "validator_sha256": EXPECTED_TOOL_SHA256,
        "resolution_engine_sha256": "d4" * 32,
        "liveness_validator_sha256": "e5" * 32,
        "archive_encoder_sha256": "f6" * 32,
        "argv_contract": {
            "interpreter": "/usr/bin/python3",
            "trainer": "train_gbm.py",
            "interpreter_sha256": "a7" * 32,
            "slot_bound_options": {},
        },
        "slice_pairs_pattern": "pairs/{slice_id}.json",
        "output_path_pattern": "output/{slot_id}/",
        "execution_env": {},
    }
    freeze = {
        "checkpoint_command_contract": {
            "gbm": dict(fam_contract),
            "nn": {
                **dict(fam_contract),
                "execution_context": REMOTE_CONTEXT,
                "trainer_sha256": "b8" * 32,
                "config_sha256": "c9" * 32,
                "argv_contract": {
                    "interpreter": "/usr/bin/python3",
                    "trainer": "train_nn.py",
                    "interpreter_sha256": "d0" * 32,
                    "slot_bound_options": {},
                },
            },
        },
        "tool_runtime": {
            "training_tools": {
                "arena-1:gbm-training-env": {
                    "attested_host": "arena-1-node-01",
                },
                "arena-1:nn-training-env (p3-train)": {
                    "attested_host": "arena-1-node-01",
                },
            },
        },
        "files": {},
    }
    freeze.update(overrides)
    return freeze


def _minimal_split_section(
    slot_id: str = "gbm-cf-s08",
    family: str = "gbm",
    trains_on: str = "arena-1",
) -> dict:
    """A minimal rotation_freeze section for testing."""
    return {
        "frozen": True,
        "immutable_projection_sha256": None,
        "bound_manifests": {
            "executable_freeze_manifest_sha256": "e" * 64,
        },
        "checkpoint_slots": [
            {
                "slot_id": slot_id,
                "family": family,
                "slice_id": "s08",
                "train_seed": 42,
                "trains_on": trains_on,
                "staged_pairs_sha256": None,
                "artifact_sha256": None,
                "slot_status": "PENDING",
            },
        ],
    }


def _minimal_slot_row(slot_id="gbm-cf-s08", family="gbm") -> dict:
    return {
        "slot_id": slot_id,
        "family": family,
        "slice_id": "s08",
        "train_seed": 42,
        "trains_on": "arena-1",
        "staged_pairs_sha256": None,
        "artifact_sha256": None,
        "slot_status": "PENDING",
    }


def _minimal_decision(verdict="FILLED", sid="gbm-cf-s07") -> ap.AttemptDecision:
    return ap.AttemptDecision(
        schema=ap.SCHEMA,
        verdict=verdict,
        n_attempts=1,
        binding_attempt_id=f"{sid}-a1",
        failure_class=None,
        reason="synthetic",
    )


# ---- Fixtures ----


@pytest.fixture
def mock_capsule_loader():
    """Mock load_remote_result_capsule.load_remote_result_capsule."""
    with patch("gate.load_remote_result_capsule.load_remote_result_capsule") as mock_fn:
        yield mock_fn


@pytest.fixture
def mock_flr_self_verify():
    """Mock self_verify_tool to skip sha256 pin check."""
    with patch("gate.fill_remote_checkpoint_slot.self_verify_tool") as mock_sv:
        mock_sv.return_value = EXPECTED_TOOL_SHA256
        yield mock_sv


# ---- Tests ----


class TestRemoteFillHappyPath:
    """test_remote_fill_success: full happy path with mock capsule."""

    def test_filled_happy_path(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """Remote capsule with exit_code=0 leads to FILLED resolution."""
        capsule_core = _minimal_capsule_core()
        terminal = capsule_core["terminal_record"]
        mock_capsule_loader.return_value = capsule_core
        self_sha = EXPECTED_TOOL_SHA256

        # Write a real capsule file so the existence check passes
        _write_capsule_file(capsule_core, tmp_path)

        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = None
            slot_decisions_file = None

        section["immutable_projection_sha256"] = srt.immutable_projection(section)

        evidence, updates = parse_remote_evidence(
            slot, section, freeze, "f" * 64, MockArgs, self_sha
        )

        assert evidence["schema"] == "verified-slot-evidence/v1"
        assert evidence["transport"] == "remote"
        assert evidence["slot_id"] == "gbm-cf-s08"
        assert evidence["evidence_schema"] == SCHEMA
        assert evidence["parser_tool_sha256"] == self_sha

        facts = evidence["resolution_facts"]
        assert facts["evidence_source"] == "remote"
        assert facts["execution_context"] == REMOTE_CONTEXT
        assert facts["slot_id"] == "gbm-cf-s08"
        assert facts["terminal_record_hash"] is not None
        assert facts["terminal_record"] == terminal
        assert facts["attempt_decision"]["verdict"] == "FILLED"

        assert updates["slot_status"] == "FILLED"
        assert updates["artifact_sha256"] == terminal["artifact_sha256"]

    def test_failed_happy_path(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """FAILED resolution via capsule with exit_code!=0 and
        deterministic category requires 2 identical failure signatures
        across 2 attempts. We mock the attempt history evaluation to
        return FAILED_DETERMINISTIC since the real capsule has only one
        attempt."""
        capsule_core = _minimal_capsule_core(
            terminal_record=_minimal_terminal_record(
                exit_code=1,
                artifact_sha256=None,
                failure_category="engine-crash",
                failure_signature=_sha256_bytes(b"stderr content"),
            )
        )
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        # Patch evaluate_attempt_history to simulate a 2-attempt history
        # that resolves to FAILED_DETERMINISTIC (since a single capsule
        # only carries one attempt, the real policy returns RETRY).
        with patch("gate.step2_attempt_policy.evaluate_attempt_history") as mock_eval:
            mock_eval.return_value = ap.AttemptDecision(
                schema=ap.SCHEMA,
                verdict="FAILED_DETERMINISTIC",
                n_attempts=2,
                binding_attempt_id=None,
                failure_class="deterministic",
                reason="capsule test: 2 identical deterministic failures",
            )

            from gate.fill_remote_checkpoint_slot import parse_remote_evidence

            slot = _minimal_slot_row()
            freeze = _minimal_freeze()
            section = _minimal_split_section()
            section["immutable_projection_sha256"] = srt.immutable_projection(section)

            class MockArgs:
                capsule_path = tmp_path / "capsule.json"
                resolution = "FAILED"
                freeze_sha = "e" * 64
                split_sha = "f" * 64
                anchor_manifest = None
                slot_decisions_file = None

            evidence, updates = parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )

        facts = evidence["resolution_facts"]
        assert facts["evidence_source"] == "remote"
        assert facts["attempt_decision"]["verdict"] == "FAILED_DETERMINISTIC"

        assert updates["slot_status"] == "FAILED"
        assert updates["artifact_sha256"] is None


class TestRemoteNonMixability:
    """test_remote_non_mixability_local_evidence_refused: remote path
    refuses local-context evidence."""

    def test_wrong_execution_context(self, tmp_path, mock_flr_self_verify):
        """Capsule with execution_context != remote is refused."""
        from gate.fill_remote_checkpoint_slot import (
            _verify_remote_evidence_non_mixability,
        )

        capsule_core = _minimal_capsule_core(
            execution_context="local",
            terminal_record=_minimal_terminal_record(),
        )

        with pytest.raises(SystemExit, match="remote evidence refused"):
            _verify_remote_evidence_non_mixability(
                capsule_core, REMOTE_CONTEXT, "gbm-cf-s08"
            )

    def test_frozen_context_mismatch(self, tmp_path, mock_flr_self_verify):
        """Capsule has remote context but the frozen contract says local."""
        from gate.fill_remote_checkpoint_slot import (
            _verify_remote_evidence_non_mixability,
        )

        capsule_core = _minimal_capsule_core(
            execution_context=REMOTE_CONTEXT,
            terminal_record=_minimal_terminal_record(),
        )

        with pytest.raises(SystemExit, match="does not match"):
            _verify_remote_evidence_non_mixability(capsule_core, "local", "gbm-cf-s08")

    def test_capsule_missing_context(self, tmp_path, mock_flr_self_verify):
        """Capsule without execution_context is refused."""
        from gate.fill_remote_checkpoint_slot import (
            _verify_remote_evidence_non_mixability,
        )

        capsule_core = _minimal_capsule_core(
            terminal_record=_minimal_terminal_record(),
        )
        capsule_core.pop("execution_context", None)

        with pytest.raises(SystemExit, match="remote evidence refused"):
            _verify_remote_evidence_non_mixability(
                capsule_core, REMOTE_CONTEXT, "gbm-cf-s08"
            )

    def test_full_parse_rejects_local_context(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """The evidence parser die()s when the capsule carries a local context."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        capsule_core = _minimal_capsule_core(
            execution_context="local",
            terminal_record=_minimal_terminal_record(),
        )
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = None
            slot_decisions_file = None

        with pytest.raises(SystemExit, match="remote evidence refused"):
            parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )


class TestRemoteInvalidCapsule:
    """test_remote_invalid_capsule: missing/invalid capsule fails."""

    def test_missing_capsule(self, tmp_path, mock_capsule_loader, mock_flr_self_verify):
        """A non-existent capsule path is caught before the loader is called."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        nonexistent = tmp_path / "does_not_exist.json"
        assert not nonexistent.is_file()

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()

        class MockArgs:
            capsule_path = nonexistent
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = None
            slot_decisions_file = None

        with pytest.raises(SystemExit, match="does not exist"):
            parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )

    def test_loader_dies_on_missing_fields(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """When the capsule loader dies (raises SystemExit), the fill fails."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence
        from gate.load_remote_result_capsule import die as loader_die

        def failing_loader(*args, **kwargs):
            loader_die("capsule missing terminal_record phase=commit")

        mock_capsule_loader.side_effect = failing_loader

        capsule_core = _minimal_capsule_core()
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = None
            slot_decisions_file = None

        with pytest.raises(SystemExit, match="capsule"):
            parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )


class TestCapsuleSlotMismatch:
    """test_capsule_slot_mismatch: capsule for wrong slot is rejected."""

    def test_slot_id_mismatch(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """Capsule terminal_record has a different slot_id.
        The real load_remote_result_capsule validates slot_id binding
        and dies with ``not for this slot/freeze``. The mock simulates
        this by raising SystemExit with a matching message."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence
        from gate.load_remote_result_capsule import die as loader_die

        def slot_aware_loader(capsule_path=None, slot=None, **kwargs):
            capsule_core = _minimal_capsule_core(
                terminal_record=_minimal_terminal_record(slot_id="lin-cf-s01"),
            )
            # Replicate the real load_remote_result_capsule check
            record = capsule_core.get("terminal_record") or {}
            for field, expect in (("slot_id", slot["slot_id"]),):
                if record.get(field) != expect:
                    loader_die(
                        f"terminal_record {field}={record.get(field)!r} != "
                        f"expected {expect!r} — capsule is not for this slot/freeze"
                    )
            return capsule_core

        mock_capsule_loader.side_effect = slot_aware_loader

        _write_capsule_file(
            _minimal_capsule_core(
                terminal_record=_minimal_terminal_record(slot_id="lin-cf-s01"),
            ),
            tmp_path,
        )

        slot = _minimal_slot_row(slot_id="gbm-cf-s08")
        freeze = _minimal_freeze()
        section = _minimal_split_section()

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = None
            slot_decisions_file = None

        with pytest.raises(SystemExit, match="not for this slot"):
            parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )


class TestRemoteFillFailed:
    """test_remote_fill_failed: remote evidence with FAILED outcome."""

    def test_failed_capsule_accepted(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """FAILED resolution accepted when the attempt policy verdict
        matches FAILED_DETERMINISTIC."""
        capsule_core = _minimal_capsule_core(
            terminal_record=_minimal_terminal_record(
                exit_code=1,
                artifact_sha256=None,
                failure_category="engine-crash",
                failure_signature=_sha256_bytes(b"crash stderr"),
            )
        )
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        with patch("gate.step2_attempt_policy.evaluate_attempt_history") as mock_eval:
            mock_eval.return_value = ap.AttemptDecision(
                schema=ap.SCHEMA,
                verdict="FAILED_DETERMINISTIC",
                n_attempts=2,
                binding_attempt_id=None,
                failure_class="deterministic",
                reason="test: 2 failures, deterministic",
            )

            from gate.fill_remote_checkpoint_slot import parse_remote_evidence

            slot = _minimal_slot_row()
            freeze = _minimal_freeze()
            section = _minimal_split_section()
            section["immutable_projection_sha256"] = srt.immutable_projection(section)

            class MockArgs:
                capsule_path = tmp_path / "capsule.json"
                resolution = "FAILED"
                freeze_sha = "e" * 64
                split_sha = "f" * 64
                anchor_manifest = None
                slot_decisions_file = None

            evidence, updates = parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )

            assert evidence["transport"] == "remote"
            assert updates["slot_status"] == "FAILED"
            assert updates["artifact_sha256"] is None

    def test_failed_verdict_mismatch(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """Capsule with FAILED outcome but --resolution=FILLED is rejected."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        capsule_core = _minimal_capsule_core(
            terminal_record=_minimal_terminal_record(
                exit_code=1,
                artifact_sha256=None,
                failure_category="engine-crash",
                failure_signature=_sha256_bytes(b"crash stderr"),
            )
        )
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = None
            slot_decisions_file = None

        with pytest.raises(SystemExit, match="does not entitle"):
            parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )


class TestOrderingGuard:
    """test_ordering_guard_refuses_before_all_terminal: missing slot histories."""

    def test_missing_slot_decisions(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """When not all authorized slots have decisions, ordering guard raises."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        capsule_core = _minimal_capsule_core()
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()
        section["immutable_projection_sha256"] = srt.immutable_projection(section)

        anchor_dir = tmp_path / "anchor"
        anchor_dir.mkdir()
        anchor_path = anchor_dir / "baseline.json"
        baseline_slots = [
            {
                "slot_id": "gbm-cf-s07",
                "family": "gbm",
                "artifact_sha256": None,
                "slot_status": "PENDING",
            },
            {
                "slot_id": "gbm-cf-s08",
                "family": "gbm",
                "artifact_sha256": None,
                "slot_status": "PENDING",
            },
        ]
        anchor_data = {
            "rotation_freeze": {
                "checkpoint_slots": baseline_slots,
            }
        }
        anchor_path.write_text(json.dumps(anchor_data, indent=1) + "\n")

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = anchor_path
            slot_decisions_file = None

        with pytest.raises(SystemExit, match="fill ordering violation"):
            parse_remote_evidence(
                slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
            )

    def test_all_terminal_passes(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """When all authorized slots have decisions, ordering guard passes."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        capsule_core = _minimal_capsule_core()
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()
        section["immutable_projection_sha256"] = srt.immutable_projection(section)

        anchor_dir = tmp_path / "anchor"
        anchor_dir.mkdir()
        anchor_path = anchor_dir / "baseline.json"
        baseline_slots = [
            {
                "slot_id": "gbm-cf-s07",
                "family": "gbm",
                "artifact_sha256": None,
                "slot_status": "PENDING",
            },
            {
                "slot_id": "gbm-cf-s08",
                "family": "gbm",
                "artifact_sha256": None,
                "slot_status": "PENDING",
            },
        ]
        anchor_data = {
            "rotation_freeze": {
                "checkpoint_slots": baseline_slots,
            }
        }
        anchor_path.write_text(json.dumps(anchor_data, indent=1) + "\n")

        decisions_file = tmp_path / "slot_decisions.json"
        decisions_data = {
            "gbm-cf-s07": {
                "verdict": "FILLED",
                "n_attempts": 1,
                "binding_attempt_id": "s07-a1",
                "failure_class": None,
                "reason": "synthetic",
            },
        }
        decisions_file.write_text(json.dumps(decisions_data, indent=1) + "\n")

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = anchor_path
            slot_decisions_file = decisions_file

        evidence, updates = parse_remote_evidence(
            slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
        )

        assert updates["slot_status"] == "FILLED"
        assert evidence["transport"] == "remote"


class TestRemoteFillVerifiedEvidence:
    """test_remote_fill_with_verified_evidence: verify verified_evidence schema."""

    def test_evidence_schema_is_valid(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """The verified_evidence object satisfies
        slot_resolution_txn.validate_verified_evidence."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        capsule_core = _minimal_capsule_core()
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()
        section["immutable_projection_sha256"] = srt.immutable_projection(section)

        anchor_dir = tmp_path / "anchor"
        anchor_dir.mkdir()
        anchor_path = anchor_dir / "baseline.json"
        anchor_data = {
            "rotation_freeze": {
                "checkpoint_slots": [
                    {
                        "slot_id": "gbm-cf-s08",
                        "family": "gbm",
                        "artifact_sha256": None,
                        "slot_status": "PENDING",
                    },
                ],
            }
        }
        anchor_path.write_text(json.dumps(anchor_data, indent=1) + "\n")

        decisions_file = tmp_path / "slot_decisions.json"
        decisions_file.write_text(json.dumps({}, indent=1) + "\n")

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = anchor_path
            slot_decisions_file = decisions_file

        evidence, updates = parse_remote_evidence(
            slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
        )

        # validate_verified_evidence should not raise
        srt.validate_verified_evidence(evidence)

        assert evidence["transport"] == "remote"
        assert evidence["evidence_schema"] == SCHEMA

        facts = evidence["resolution_facts"]
        assert isinstance(facts["terminal_record"], dict)
        assert isinstance(facts["terminal_record_hash"], str)
        assert len(facts["terminal_record_hash"]) == 64
        assert facts["evidence_source"] == "remote"

    def test_terminal_record_embedded_in_facts(
        self, tmp_path, mock_capsule_loader, mock_flr_self_verify
    ):
        """The terminal_record core/hash is embedded in resolution_facts."""
        from gate.fill_remote_checkpoint_slot import parse_remote_evidence

        terminal = _minimal_terminal_record()
        capsule_core = _minimal_capsule_core(terminal_record=terminal)
        mock_capsule_loader.return_value = capsule_core
        _write_capsule_file(capsule_core, tmp_path)

        slot = _minimal_slot_row()
        freeze = _minimal_freeze()
        section = _minimal_split_section()
        section["immutable_projection_sha256"] = srt.immutable_projection(section)

        anchor_dir = tmp_path / "anchor"
        anchor_dir.mkdir()
        anchor_path = anchor_dir / "baseline.json"
        anchor_data = {
            "rotation_freeze": {
                "checkpoint_slots": [
                    {
                        "slot_id": "gbm-cf-s08",
                        "family": "gbm",
                        "artifact_sha256": None,
                        "slot_status": "PENDING",
                    },
                ],
            }
        }
        anchor_path.write_text(json.dumps(anchor_data, indent=1) + "\n")

        decisions_file = tmp_path / "slot_decisions.json"
        decisions_file.write_text(json.dumps({}, indent=1) + "\n")

        class MockArgs:
            capsule_path = tmp_path / "capsule.json"
            resolution = "FILLED"
            freeze_sha = "e" * 64
            split_sha = "f" * 64
            anchor_manifest = anchor_path
            slot_decisions_file = decisions_file

        evidence, updates = parse_remote_evidence(
            slot, section, freeze, "f" * 64, MockArgs, EXPECTED_TOOL_SHA256
        )

        facts = evidence["resolution_facts"]
        expected_hash = _sha256_bytes(
            json.dumps(terminal, sort_keys=True, separators=(",", ":")).encode()
        )
        assert facts["terminal_record_hash"] == expected_hash
        assert facts["terminal_record"] == terminal


class TestSelfVerify:
    """Tests for the tool's own self-verification."""

    def test_self_verify_rejects_placeholder(self):
        """The all-zeros placeholder should cause early failure."""
        with patch(
            "gate.fill_remote_checkpoint_slot._EXPECTED_TOOL_SHA256",
            "0" * 64,
        ):
            with pytest.raises(SystemExit, match="all-zeros placeholder"):
                from gate.fill_remote_checkpoint_slot import self_verify_tool

                self_verify_tool()

    def test_self_verify_rejects_wrong_sha(self):
        """A sha256 that does not match the file bytes is refused."""
        with patch(
            "gate.fill_remote_checkpoint_slot._EXPECTED_TOOL_SHA256",
            "f" * 64,
        ):
            with pytest.raises(SystemExit, match="self-verify FAILED"):
                from gate.fill_remote_checkpoint_slot import self_verify_tool

                self_verify_tool()
