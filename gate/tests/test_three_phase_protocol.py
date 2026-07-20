"""Tests for the P0-2 three-phase protocol: TRAIN_COMMIT → LIVENESS_COMMIT
→ SLOT_RESOLUTION_COMMIT.

#3902 P0-2: break the training/liveness causal cycle.  Every phase file must be
in the freeze's file census to pass pre-exec identity checks.

Tests use minimal in-memory fixtures rather than real manifests:
  * train_fixture builds the train-ledger.jsonl
  * liveness_fixture builds the liveness-ledger.jsonl
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from gate import phase_train_commit as ptc
from gate import phase_liveness_commit as plc
from gate import phase_slot_resolution_commit as psrc

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

SLOT_ID = "gbm-cf-s01"
SLICE_ID = "S01"
TRAIN_SEED = 42
FAMILY = "gbm"
ARTIFACT_SHA = "a" * 64
FAMILY_CONFIG_SHA = "c" * 64
TRAINER_SHA = "t" * 64

# Real sha of the actual produce_checkpoint.py on disk (freeze-verified)
_REAL_PRODUCER_WRAPPER_SHA = (
    "d0821e8b5b23ba2aa321da7f05edee3b07ae1fc90b022e12e5ae021b1d1926e5"
)

# The artifact content used in fixtures and its known SHA256
_FIXTURE_ARTIFACT_CONTENT = b"fake checkpoint data"
ARTIFACT_SHA = hashlib.sha256(_FIXTURE_ARTIFACT_CONTENT).hexdigest()


def _sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()


def _canonical_compact(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


# ---------------------------------------------------------------------------
# fixtures: minimal freeze + split manifests
# ---------------------------------------------------------------------------
# The executor-freeze-manifest must contain the phase file in its
# "files" census so the pinned-identity validation in each phase script
# can succeed (or be bypassed by not setting a pin).
#
# Each test needs isolated temp dirs so ledger entries do not leak across
# tests.  The three fixture scopes below produce disposable manifests and
# ledgers per test function.


@pytest.fixture
def tmp_gate(tmp_path: Path) -> Path:
    """Build a temporary gate/ directory with the phase scripts symlinked in,
    plus minimal freeze/split manifests and empty ledgers."""
    gate_dir = tmp_path / "gate"
    gate_dir.mkdir()
    receipts = gate_dir / "receipts"
    receipts.mkdir()

    # record real sha of the phase scripts for freeze pins
    _this_dir = Path(__file__).resolve().parent.parent

    ptc_real = _this_dir / "phase_train_commit.py"
    plc_real = _this_dir / "phase_liveness_commit.py"
    psrc_real = _this_dir / "phase_slot_resolution_commit.py"

    ptc_sha = _sha256_file(ptc_real)
    plc_sha = _sha256_file(plc_real)
    psrc_sha = _sha256_file(psrc_real)

    # symlink the phase scripts into the temp gate
    for src, name in [
        (ptc_real, "phase_train_commit.py"),
        (plc_real, "phase_liveness_commit.py"),
        (psrc_real, "phase_slot_resolution_commit.py"),
    ]:
        (gate_dir / name).symlink_to(src)

    # minimal freeze: file census entries for each phase script
    freeze = {
        "files": {
            "fac:gate/phase_train_commit.py": {
                "sha256": ptc_sha,
                "size": ptc_real.stat().st_size,
            },
            "fac:gate/phase_liveness_commit.py": {
                "sha256": plc_sha,
                "size": plc_real.stat().st_size,
            },
            "fac:gate/phase_slot_resolution_commit.py": {
                "sha256": psrc_sha,
                "size": psrc_real.stat().st_size,
            },
        },
        "checkpoint_command_contract": {
            FAMILY: {
                "producer_wrapper_sha256": _REAL_PRODUCER_WRAPPER_SHA,
                "trainer_sha256": TRAINER_SHA,
                "config_sha256": FAMILY_CONFIG_SHA,
                "argv_contract": {
                    "interpreter": "/usr/bin/python3",
                    "interpreter_sha256": "i" * 64,
                    "trainer": f"scripts/{FAMILY}_imitation.py",
                },
                "execution_context": "local",
                "validator_sha256": "v" * 64,
                "liveness_validator_sha256": "l" * 64,
                "archive_encoder_sha256": "e" * 64,
            }
        },
    }
    freeze_manifest = gate_dir / "executable-freeze-manifest.json"
    freeze_manifest.write_text(json.dumps(freeze, indent=1, sort_keys=True) + "\n")
    freeze_sha = _sha256_file(freeze_manifest)

    # minimal split: one frozen slot
    split = {
        "rotation_freeze": {
            "frozen": True,
            "immutable_projection_sha256": None,  # computed below
            "bound_manifests": {
                "executable_freeze_manifest_sha256": freeze_sha,
            },
            "checkpoint_slots": [
                {
                    "slot_id": SLOT_ID,
                    "slice_id": SLICE_ID,
                    "train_seed": TRAIN_SEED,
                    "family": FAMILY,
                    "slot_status": "PENDING",
                    "artifact_sha256": None,
                }
            ],
        }
    }

    # compute immutable projection
    from gate import slot_resolution_txn

    section = split["rotation_freeze"]
    proj = slot_resolution_txn.immutable_projection(section)
    section["immutable_projection_sha256"] = proj

    split_manifest = gate_dir / "split-manifest.json"
    split_manifest.write_text(json.dumps(split, indent=1, sort_keys=True) + "\n")

    # populate patch-monkey for phase scripts: the modules reference
    # hard-coded Path(__file__).resolve().parent for their ledger/lock
    # paths.  We monkey-patch the module-level constants below.
    return gate_dir


def _patch_train_ledger(gate_dir: Path, monkeypatch) -> None:
    """Redirect train-ledger paths to the temp gate."""
    monkeypatch.setattr(ptc, "_GATE_DIR", gate_dir)


def _patch_liveness_ledger(gate_dir: Path, monkeypatch) -> None:
    """Redirect liveness-ledger paths to the temp gate."""
    monkeypatch.setattr(plc, "_GATE_DIR", gate_dir)


def _patch_slot_resolution_ledger(gate_dir: Path, monkeypatch) -> None:
    """Redirect slot-resolution-ledger paths to the temp gate."""
    monkeypatch.setattr(psrc, "_GATE_DIR", gate_dir)


def _write_train_commit(
    gate_dir: Path,
    *,
    slot_id: str = SLOT_ID,
    artifact_sha: str | None = ARTIFACT_SHA,
) -> str:
    """Write a synthetic TRAIN_COMMIT row to the train ledger and return its
    receipt_core_sha256."""
    ledger = gate_dir / "receipts" / "train-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    core = {
        "phase": "TRAIN_COMMIT",
        "schema": ptc.SCHEMA,
        "slot_id": slot_id,
        "attempt_id": "a1",
        "artifact_sha256": artifact_sha,
        "receipt_core_sha256": _sha256_bytes(b"fake-train-core"),
        "utc": "2026-07-19T00:00:00Z",
    }
    with open(ledger, "a") as fh:
        fh.write(json.dumps(core, sort_keys=True) + "\n")
    return core["receipt_core_sha256"]


def _write_liveness_commit(
    gate_dir: Path,
    *,
    slot_id: str = SLOT_ID,
    train_ledger_id: str = "train-ledger-1",
) -> str:
    """Write a synthetic LIVENESS_COMMIT row to the liveness ledger."""
    ledger = gate_dir / "receipts" / "liveness-ledger.jsonl"
    ledger.parent.mkdir(parents=True, exist_ok=True)
    core = {
        "phase": "LIVENESS_COMMIT",
        "schema": plc.SCHEMA,
        "slot_id": slot_id,
        "train_ledger_id": train_ledger_id,
        "artifact_sha256": ARTIFACT_SHA,
        "receipt_core_sha256": _sha256_bytes(b"fake-liveness-core"),
        "utc": "2026-07-19T00:00:01Z",
    }
    with open(ledger, "a") as fh:
        fh.write(json.dumps(core, sort_keys=True) + "\n")
    return core["receipt_core_sha256"]


# ============================================================================
# Phase 1: TRAIN_COMMIT
# ============================================================================


def test_train_commit_writes_receipt_no_liveness_reference(tmp_gate, monkeypatch):
    """TRAIN_COMMIT with valid execution writes a receipt.  No liveness
    reference appears anywhere in the receipt or ledger entry."""
    gate = tmp_gate
    _patch_train_ledger(gate, monkeypatch)

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"
    artifact = gate / "artifacts" / "checkpoint.pt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"fake checkpoint data")

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_train_commit.py",
            "--slot-id",
            SLOT_ID,
            "--attempt-id",
            "a1",
            "--artifact-path",
            str(artifact),
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        rc = ptc.main()
    finally:
        sys.argv = old_argv

    assert rc == 0

    # Check the ledger
    ledger_path = gate / "receipts" / "train-ledger.jsonl"
    assert ledger_path.is_file()
    rows = [json.loads(l) for l in ledger_path.read_text().splitlines() if l.strip()]
    assert len(rows) >= 1
    last = rows[-1]
    assert last["phase"] == "TRAIN_COMMIT"
    assert last["slot_id"] == SLOT_ID
    assert last["schema"] == ptc.SCHEMA
    assert last["artifact_sha256"] is not None

    # Serialise the whole ledger to check no liveness reference
    ledger_text = ledger_path.read_text().lower()
    assert "liveness" not in ledger_text, (
        "TRAIN_COMMIT ledger entry must not reference liveness"
    )


# ============================================================================
# Phase 2: LIVENESS_COMMIT
# ============================================================================


def test_liveness_commit_references_train_artifact(tmp_gate, monkeypatch):
    """LIVENESS_COMMIT references train ledger ID + artifact path and SHA.
    Produces an independent liveness receipt."""
    gate = tmp_gate
    _patch_liveness_ledger(gate, monkeypatch)

    # Pre-populate train ledger
    _write_train_commit(gate, slot_id=SLOT_ID, artifact_sha=ARTIFACT_SHA)

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"
    artifact = gate / "artifacts" / "checkpoint.pt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"fake checkpoint data")

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_liveness_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--artifact-path",
            str(artifact),
            "--artifact-sha256",
            ARTIFACT_SHA,
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        rc = plc.main()
    finally:
        sys.argv = old_argv

    assert rc == 0

    ledger_path = gate / "receipts" / "liveness-ledger.jsonl"
    assert ledger_path.is_file()
    rows = [json.loads(l) for l in ledger_path.read_text().splitlines() if l.strip()]
    last = rows[-1]
    assert last["phase"] == "LIVENESS_COMMIT"
    assert last["slot_id"] == SLOT_ID
    assert last["train_ledger_id"] == "train-ledger-1"
    assert last["artifact_sha256"] == ARTIFACT_SHA


def test_liveness_commit_missing_artifact_fails(tmp_gate, monkeypatch):
    """LIVENESS_COMMIT with a non-existent artifact path fails closed."""
    gate = tmp_gate
    _patch_liveness_ledger(gate, monkeypatch)
    _write_train_commit(gate, slot_id=SLOT_ID, artifact_sha=ARTIFACT_SHA)

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"
    missing_path = gate / "no-such-artifact.pt"

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_liveness_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--artifact-path",
            str(missing_path),
            "--artifact-sha256",
            ARTIFACT_SHA,
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        with pytest.raises(SystemExit, match="does not exist"):
            plc.main()
    finally:
        sys.argv = old_argv


def test_liveness_commit_mismatched_sha_fails(tmp_gate, monkeypatch):
    """LIVENESS_COMMIT with a SHA256 that does not match the artifact on disk
    fails closed."""
    gate = tmp_gate
    _patch_liveness_ledger(gate, monkeypatch)
    _write_train_commit(gate, slot_id=SLOT_ID, artifact_sha=ARTIFACT_SHA)

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"
    artifact = gate / "artifacts" / "checkpoint.pt"
    artifact.parent.mkdir(parents=True, exist_ok=True)
    artifact.write_bytes(b"different data than the claimed sha")

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_liveness_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--artifact-path",
            str(artifact),
            "--artifact-sha256",
            ARTIFACT_SHA,
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        with pytest.raises(SystemExit, match="sha"):
            plc.main()
    finally:
        sys.argv = old_argv


# ============================================================================
# Phase 3: SLOT_RESOLUTION_COMMIT
# ============================================================================


def test_slot_resolution_commit_requires_both(tmp_gate, monkeypatch):
    """SLOT_RESOLUTION_COMMIT with both TRAIN_COMMIT and LIVENESS_COMMIT
    present succeeds."""
    gate = tmp_gate
    _patch_slot_resolution_ledger(gate, monkeypatch)

    # Pre-populate both ledgers
    _write_train_commit(gate, slot_id=SLOT_ID, artifact_sha=ARTIFACT_SHA)
    _write_liveness_commit(gate, slot_id=SLOT_ID, train_ledger_id="train-ledger-1")

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_slot_resolution_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--liveness-ledger-id",
            "liveness-ledger-1",
            "--resolution",
            "FILLED",
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        rc = psrc.main()
    finally:
        sys.argv = old_argv

    assert rc == 0

    # Verify the slot-resolution ledger was written
    srl = gate / "receipts" / "slot-resolution-ledger.jsonl"
    assert srl.is_file()
    rows = [json.loads(l) for l in srl.read_text().splitlines() if l.strip()]
    last = rows[-1]
    assert last["phase"] == "SLOT_RESOLUTION_COMMIT"
    assert last["slot_id"] == SLOT_ID
    assert last["resolution"] == "FILLED"


def test_slot_resolution_commit_without_liveness_refuses(tmp_gate, monkeypatch):
    """SLOT_RESOLUTION_COMMIT without a prior LIVENESS_COMMIT refuses."""
    gate = tmp_gate
    _patch_slot_resolution_ledger(gate, monkeypatch)

    # Only write train commit, no liveness
    _write_train_commit(gate, slot_id=SLOT_ID, artifact_sha=ARTIFACT_SHA)

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_slot_resolution_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--liveness-ledger-id",
            "liveness-ledger-1",
            "--resolution",
            "FILLED",
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        with pytest.raises(SystemExit, match="no LIVENESS_COMMIT|LIVENESS_COMMIT"):
            psrc.main()
    finally:
        sys.argv = old_argv


def test_slot_resolution_commit_without_train_refuses(tmp_gate, monkeypatch):
    """SLOT_RESOLUTION_COMMIT without a prior TRAIN_COMMIT refuses."""
    gate = tmp_gate
    _patch_slot_resolution_ledger(gate, monkeypatch)

    # Write liveness but no train
    _write_liveness_commit(gate, slot_id=SLOT_ID, train_ledger_id="train-ledger-1")

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_slot_resolution_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--liveness-ledger-id",
            "liveness-ledger-1",
            "--resolution",
            "FILLED",
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        with pytest.raises(SystemExit, match="no TRAIN_COMMIT"):
            psrc.main()
    finally:
        sys.argv = old_argv


def test_slot_resolution_commit_no_artifact_sha_refuses_filled(tmp_gate, monkeypatch):
    """SLOT_RESOLUTION_COMMIT with resolution=FILLED but a train commit that
    has no artifact_sha256 refuses."""
    gate = tmp_gate
    _patch_slot_resolution_ledger(gate, monkeypatch)

    # Write train commit WITHOUT artifact_sha
    _write_train_commit(gate, slot_id=SLOT_ID, artifact_sha=None)
    _write_liveness_commit(gate, slot_id=SLOT_ID, train_ledger_id="train-ledger-1")

    fm = gate / "executable-freeze-manifest.json"
    sm = gate / "split-manifest.json"

    import sys

    old_argv = sys.argv
    try:
        sys.argv = [
            "phase_slot_resolution_commit.py",
            "--slot-id",
            SLOT_ID,
            "--train-ledger-id",
            "train-ledger-1",
            "--liveness-ledger-id",
            "liveness-ledger-1",
            "--resolution",
            "FILLED",
            "--freeze-manifest",
            str(fm),
            "--split-manifest",
            str(sm),
        ]
        with pytest.raises(SystemExit, match="no artifact_sha"):
            psrc.main()
    finally:
        sys.argv = old_argv
