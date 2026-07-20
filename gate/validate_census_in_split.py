"""Per-slice vocabulary census binding — R3 machine enforcement (bus #3878/#3885).

Reads the signed census receipt and asserts that every GBM slot in the split
manifest carries an ``expected_vocab_size`` matching the census value for its
slice. Also asserts the census receipt SHA matches the frozen pin.

This is the "per-slice vocabulary table in the split" requirement from #3902:
the split's GBM slot rows must carry frozen per-slice vocab sizes so that the
artifact contract and the launch anchor both bind the same vocabulary, and no
census drift can go undetected.

Usage:
  python3 gate/validate_census_in_split.py
    (reads split-manifest.json + receipts/gbm-slice-vocab-census.json)

Exit 0 = all GBM slots match their census vocab size.
Exit 1 = any mismatch / missing field / missing file.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parent

SCHEMA = "validate-census-in-split/v1"

EXPECTED_CENSUS_RECEIPT_SHA256 = (
    "6dd093041c8253e2972a81791b58fe733941ccae83772726593374829ca96e5a"
)

_SLICE_VOCAB_MAP: dict[str, int] = {
    "S06": 137,
    "S07": 139,
    "S08": 145,
    "S09": 152,
    "S10": 144,
    "S11": 153,
    "S12": 128,
}


def die(msg: str) -> None:
    raise SystemExit(f"FAIL-CLOSED (validate-census-in-split): {msg}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_census_receipt(path: Path) -> dict:
    """Load and verify the census receipt against its pinned SHA."""
    if not path.is_file():
        die(f"census receipt {path} missing")
    observed = sha256_file(path)
    if observed != EXPECTED_CENSUS_RECEIPT_SHA256:
        die(
            f"census receipt sha256 {observed[:16]} != pinned "
            f"{EXPECTED_CENSUS_RECEIPT_SHA256[:16]} — re-run gbm_slice_vocab_census.py"
        )
    rec = json.loads(path.read_bytes())
    core = rec.get("core") if isinstance(rec, dict) else None
    if not isinstance(core, dict):
        die("census receipt has no core object")
    return core


def load_split_slots(path: Path) -> list[dict]:
    """Return the checkpoint_slots list from the split manifest."""
    if not path.is_file():
        die(f"split manifest {path} missing")
    m = json.loads(path.read_bytes())
    section = m.get("rotation_freeze") if isinstance(m, dict) else None
    if not isinstance(section, dict):
        die("split manifest has no rotation_freeze section")
    slots = section.get("checkpoint_slots")
    if not isinstance(slots, list) or not slots:
        die("split manifest has no checkpoint_slots")
    return slots


def main() -> int:
    census_path = GATE / "receipts" / "gbm-slice-vocab-census.json"
    split_path = GATE / "split-manifest.json"

    census_core = load_census_receipt(census_path)

    # Build lookup: slice_id -> census vocab_size
    census_by_slice: dict[str, int] = {}
    for row in census_core.get("slices", []):
        sid = row.get("slice_id")
        vsize = row.get("vocab_size")
        if sid and isinstance(vsize, int) and vsize > 0:
            census_by_slice[sid] = vsize

    if len(census_by_slice) < 7:
        die(
            f"census receipt has {len(census_by_slice)} valid slice entries "
            "(expected >= 7)"
        )

    slots = load_split_slots(split_path)
    gbm_slots = [s for s in slots if s.get("family") == "gbm"]

    if not gbm_slots:
        die("no GBM slots found in split manifest")

    errors: list[str] = []
    seen_slices: set[str] = set()

    for slot in gbm_slots:
        sid = slot.get("slot_id")
        slc = slot.get("slice_id")
        if not sid or not slc:
            errors.append(f"GBM slot {sid!r} missing slot_id or slice_id")
            continue
        seen_slices.add(slc)

        expected = _SLICE_VOCAB_MAP.get(slc)
        if expected is None:
            errors.append(
                f"GBM slot {sid!r} slice {slc!r} is not in the frozen vocab map"
            )
            continue

        slot_expected = slot.get("expected_vocab_size")
        if slot_expected is None:
            errors.append(
                f"GBM slot {sid!r} (slice {slc!r}) has no expected_vocab_size "
                "in the split manifest — add it"
            )
            continue

        if slot_expected != expected:
            errors.append(
                f"GBM slot {sid!r} (slice {slc!r}) expected_vocab_size "
                f"{slot_expected} != census value {expected}"
            )
            continue

        census_val = census_by_slice.get(slc)
        if census_val is None:
            errors.append(
                f"GBM slot {sid!r} slice {slc!r} missing from census receipt slices"
            )
            continue

        if slot_expected != census_val:
            errors.append(
                f"GBM slot {sid!r} (slice {slc!r}) expected_vocab_size "
                f"{slot_expected} != census receipt vocab_size {census_val}"
            )

    # Check every frozen slice is present
    for slc in sorted(_SLICE_VOCAB_MAP):
        if slc not in seen_slices:
            errors.append(
                f"frozen slice {slc!r} (vocab={_SLICE_VOCAB_MAP[slc]}) "
                "has no GBM slot in the split manifest"
            )

    if errors:
        for e in errors:
            print(e, file=sys.stderr)
        return 1

    print(
        f"DONE validate-census-in-split: {len(gbm_slots)} GBM slots match "
        f"frozen census, receipt SHA matches pin, all slices accounted for."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
