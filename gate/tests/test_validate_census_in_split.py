"""Tests for gate/validate_census_in_split.py — per-slice vocabulary in split."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import validate_census_in_split as vc


def _sha256(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# Slices covering all frozen GBM slices (need >=7 for the validator's guard)
_ALL_SLICES = [
    {"slice_id": "S06", "vocab_size": 137},
    {"slice_id": "S07", "vocab_size": 139},
    {"slice_id": "S08", "vocab_size": 145},
    {"slice_id": "S09", "vocab_size": 152},
    {"slice_id": "S10", "vocab_size": 144},
    {"slice_id": "S11", "vocab_size": 153},
    {"slice_id": "S12", "vocab_size": 128},
]


@pytest.fixture(autouse=True)
def _patch_constants(monkeypatch):
    """Patch SHA pin and slice map for all tests."""
    monkeypatch.setattr(vc, "EXPECTED_CENSUS_RECEIPT_SHA256", _sha256(b"test"))
    monkeypatch.setattr(
        vc,
        "_SLICE_VOCAB_MAP",
        {
            "S06": 137,
            "S07": 139,
            "S08": 145,
            "S09": 152,
            "S10": 144,
            "S11": 153,
            "S12": 128,
        },
    )


def _mock_load_core(core: dict):
    """Return a load_census_receipt replacement that returns the given core dict."""
    return lambda _path: core


def _setup_valid_env(tmp_path):
    """Write a matching census + split with all GBM slots, patch GATE."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(vc, "GATE", tmp_path)

    # census receipt
    core = {"slices": _ALL_SLICES, "gbm_slots_censused": 7}
    (tmp_path / "receipts" / "gbm-slice-vocab-census.json").parent.mkdir(
        parents=True, exist_ok=True
    )
    (tmp_path / "receipts" / "gbm-slice-vocab-census.json").write_text(
        json.dumps(
            {
                "core": core,
                "core_sha256": _sha256(
                    json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
                ),
            }
        )
    )

    # split manifest
    slot_ids = [
        ("gbm-cf-s06", "S06", 137),
        ("gbm-cf-s07", "S07", 139),
        ("gbm-cf-s08", "S08", 145),
        ("gbm-cf-s09", "S09", 152),
        ("gbm-cf-s10", "S10", 144),
        ("gbm-cf-s11", "S11", 153),
        ("gbm-cf-s12", "S12", 128),
    ]
    slots = [
        {
            "slot_id": sid,
            "family": "gbm",
            "slice_id": slc,
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": vsize,
        }
        for sid, slc, vsize in slot_ids
    ]
    (tmp_path / "split-manifest.json").write_text(
        json.dumps({"rotation_freeze": {"checkpoint_slots": slots}}, indent=1)
    )
    return monkeypatch


def test_happy_path_all_slots_match(tmp_path, monkeypatch):
    """All 7 GBM slots match census; should pass."""
    monkeypatch.setattr(vc, "GATE", tmp_path)
    core = {"slices": _ALL_SLICES, "gbm_slots_censused": 7}

    census_dir = tmp_path / "receipts"
    census_dir.mkdir(parents=True, exist_ok=True)
    (census_dir / "gbm-slice-vocab-census.json").write_text(
        json.dumps(
            {
                "core": core,
                "core_sha256": _sha256(
                    json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
                ),
            }
        )
    )

    slots = [
        {
            "slot_id": f"gbm-cf-s{s}",
            "family": "gbm",
            "slice_id": f"S{s}",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": vs,
        }
        for s, vs in [
            ("06", 137),
            ("07", 139),
            ("08", 145),
            ("09", 152),
            ("10", 144),
            ("11", 153),
            ("12", 128),
        ]
    ]
    (tmp_path / "split-manifest.json").write_text(
        json.dumps({"rotation_freeze": {"checkpoint_slots": slots}}, indent=1)
    )

    monkeypatch.setattr(vc, "load_census_receipt", _mock_load_core(core))
    assert vc.main() == 0


def test_mismatched_vocab_fails(tmp_path, monkeypatch):
    """Slot expected_vocab_size differs from census → fail."""
    monkeypatch.setattr(vc, "GATE", tmp_path)
    core = {"slices": _ALL_SLICES, "gbm_slots_censused": 7}

    census_dir = tmp_path / "receipts"
    census_dir.mkdir(parents=True, exist_ok=True)
    (census_dir / "gbm-slice-vocab-census.json").write_text(
        json.dumps(
            {
                "core": core,
                "core_sha256": _sha256(
                    json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
                ),
            }
        )
    )

    # S06 has vocab 137 in census, but slot says 999
    slots = [
        {
            "slot_id": "gbm-cf-s06",
            "family": "gbm",
            "slice_id": "S06",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 999,
        },
        {
            "slot_id": "gbm-cf-s07",
            "family": "gbm",
            "slice_id": "S07",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 139,
        },
        {
            "slot_id": "gbm-cf-s08",
            "family": "gbm",
            "slice_id": "S08",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 145,
        },
        {
            "slot_id": "gbm-cf-s09",
            "family": "gbm",
            "slice_id": "S09",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 152,
        },
        {
            "slot_id": "gbm-cf-s10",
            "family": "gbm",
            "slice_id": "S10",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 144,
        },
        {
            "slot_id": "gbm-cf-s11",
            "family": "gbm",
            "slice_id": "S11",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 153,
        },
        {
            "slot_id": "gbm-cf-s12",
            "family": "gbm",
            "slice_id": "S12",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 128,
        },
    ]
    (tmp_path / "split-manifest.json").write_text(
        json.dumps({"rotation_freeze": {"checkpoint_slots": slots}}, indent=1)
    )

    monkeypatch.setattr(vc, "load_census_receipt", _mock_load_core(core))
    assert vc.main() != 0


def test_missing_expected_vocab_field_fails(tmp_path, monkeypatch):
    """Slot missing expected_vocab_size entirely → fail."""
    monkeypatch.setattr(vc, "GATE", tmp_path)
    core = {"slices": _ALL_SLICES, "gbm_slots_censused": 7}

    census_dir = tmp_path / "receipts"
    census_dir.mkdir(parents=True, exist_ok=True)
    (census_dir / "gbm-slice-vocab-census.json").write_text(
        json.dumps(
            {
                "core": core,
                "core_sha256": _sha256(
                    json.dumps(core, sort_keys=True, separators=(",", ":")).encode()
                ),
            }
        )
    )

    slots = [
        {
            "slot_id": "gbm-cf-s06",
            "family": "gbm",
            "slice_id": "S06",
            "slot_status": "PENDING",
            "artifact_sha256": None,
        },
        # NB: no expected_vocab_size
        {
            "slot_id": "gbm-cf-s07",
            "family": "gbm",
            "slice_id": "S07",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 139,
        },
        {
            "slot_id": "gbm-cf-s08",
            "family": "gbm",
            "slice_id": "S08",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 145,
        },
        {
            "slot_id": "gbm-cf-s09",
            "family": "gbm",
            "slice_id": "S09",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 152,
        },
        {
            "slot_id": "gbm-cf-s10",
            "family": "gbm",
            "slice_id": "S10",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 144,
        },
        {
            "slot_id": "gbm-cf-s11",
            "family": "gbm",
            "slice_id": "S11",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 153,
        },
        {
            "slot_id": "gbm-cf-s12",
            "family": "gbm",
            "slice_id": "S12",
            "slot_status": "PENDING",
            "artifact_sha256": None,
            "expected_vocab_size": 128,
        },
    ]
    (tmp_path / "split-manifest.json").write_text(
        json.dumps({"rotation_freeze": {"checkpoint_slots": slots}}, indent=1)
    )

    monkeypatch.setattr(vc, "load_census_receipt", _mock_load_core(core))
    assert vc.main() != 0
