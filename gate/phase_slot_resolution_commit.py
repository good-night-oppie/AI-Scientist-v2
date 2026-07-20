"""Phase 3: SLOT_RESOLUTION_COMMIT — requires both train commit + liveness commit.

#3902 P0-2: break the training/liveness causal cycle.

Validates BOTH train and liveness commits exist in their respective ledgers.
Resolution requires both — refuses if either is missing. If resolution is FILLED
but the train commit has no artifact_sha256, refuses.

Calls slot_resolution_txn.resolve_slot() for the final atomic manifest mutation.

Usage:
  phase_slot_resolution_commit.py --slot-id gbm-cf-s01 \
      --train-ledger-id <id> --liveness-ledger-id <id> \
      --resolution FILLED --freeze-manifest f.json --split-manifest s.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
from pathlib import Path

from gate import slot_resolution_txn

SCHEMA = "phase-slot-resolution-commit/v1"
_DEFAULT_GATE = Path(__file__).resolve().parent
_GATE_DIR = _DEFAULT_GATE


def _gate() -> Path:
    return _GATE_DIR


def _slot_resolution_ledger() -> Path:
    return _gate() / "receipts" / "slot-resolution-ledger.jsonl"


def _slot_resolution_ledger_lock() -> Path:
    return _gate() / "receipts" / ".slot-resolution-ledger.lock"


def die(msg: str) -> None:
    raise SystemExit(f"FAIL-CLOSED: {msg}")


def sha256_file(p: Path) -> str:
    d = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def load_split(split_manifest: Path) -> dict:
    try:
        data = json.loads(split_manifest.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        die(f"split-manifest {split_manifest}: {exc}")
    section = data.get("rotation_freeze")
    if not isinstance(section, dict):
        die("split-manifest has no rotation_freeze section")
    return section


def load_freeze(freeze_manifest: Path) -> dict:
    try:
        data = json.loads(freeze_manifest.read_bytes())
    except (OSError, json.JSONDecodeError) as exc:
        die(f"freeze-manifest {freeze_manifest}: {exc}")
    return data


def slot_row(section: dict, slot_id: str) -> dict:
    for s in section.get("checkpoint_slots", []):
        if s.get("slot_id") == slot_id:
            return s
    die(f"unknown slot {slot_id!r}")


def ledger_read_all(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Phase 3 SLOT_RESOLUTION_COMMIT — requires BOTH train "
        "and liveness commits before slot resolution"
    )
    ap.add_argument("--slot-id", required=True)
    ap.add_argument("--train-ledger-id", required=True)
    ap.add_argument("--liveness-ledger-id", required=True)
    ap.add_argument("--resolution", required=True, choices=["FILLED", "FAILED"])
    ap.add_argument("--freeze-manifest", required=True, type=Path)
    ap.add_argument("--split-manifest", required=True, type=Path)
    args = ap.parse_args()

    this_file = Path(__file__).resolve()
    wrapper_sha = sha256_file(this_file)
    section = load_split(args.split_manifest)
    freeze = load_freeze(args.freeze_manifest)
    slot = slot_row(section, args.slot_id)

    # Validate wrapper sha256 against freeze pin
    census_key = "fac:gate/phase_slot_resolution_commit.py"
    frozen_pin = ((freeze.get("files") or {}).get(census_key) or {}).get("sha256")
    if frozen_pin and wrapper_sha != frozen_pin:
        die(
            f"phase_slot_resolution_commit.py sha256 {wrapper_sha[:16]} != "
            f"freeze pin {frozen_pin[:16]} — the wrapper bytes are not the "
            "frozen ones"
        )

    receipts_dir = _gate() / "receipts"

    # Phase 1 check: validate train commit exists in train ledger
    train_ledger = receipts_dir / "train-ledger.jsonl"
    train_rows = ledger_read_all(train_ledger)
    train_commit = None
    for row in train_rows:
        if row.get("phase") == "TRAIN_COMMIT" and row.get("slot_id") == args.slot_id:
            train_commit = row
            break
    if train_commit is None:
        die(
            f"SLOT_RESOLUTION refused: no TRAIN_COMMIT found for slot "
            f"{args.slot_id}. A train commit must exist before slot resolution."
        )

    # Phase 2 check: validate liveness commit exists in liveness ledger
    liveness_ledger = receipts_dir / "liveness-ledger.jsonl"
    liveness_rows = ledger_read_all(liveness_ledger)
    liveness_found = False
    for row in liveness_rows:
        if row.get("phase") == "LIVENESS_COMMIT" and row.get("slot_id") == args.slot_id:
            liveness_found = True
            break
    if not liveness_found:
        die(
            f"SLOT_RESOLUTION refused: no LIVENESS_COMMIT found for slot "
            f"{args.slot_id}. A liveness commit must exist before slot "
            "resolution."
        )

    # If FILLED, train commit must have an artifact_sha256
    if args.resolution == "FILLED":
        train_artifact_sha = train_commit.get("artifact_sha256")
        if not train_artifact_sha:
            die(
                "SLOT_RESOLUTION refused: resolution=FILLED but train commit "
                "has no artifact_sha256. A FILLED resolution requires the "
                "train commit to provide artifact evidence."
            )

    # Build the resolution facts — references to both commits
    resolution_facts = {
        "train_ledger_id": args.train_ledger_id,
        "liveness_ledger_id": args.liveness_ledger_id,
        "train_commit_artifact_sha256": train_commit.get("artifact_sha256"),
    }

    family = slot.get("family")
    if not family:
        die("slot row has no family field")
    contract = (freeze.get("checkpoint_command_contract") or {}).get(family)
    if not isinstance(contract, dict):
        die(f"freeze has no checkpoint_command_contract for family {family!r}")

    # Resolve artifact sha from evidence for the engine
    artifact_sha = None
    if args.resolution == "FILLED":
        artifact_sha = resolution_facts["train_commit_artifact_sha256"]

    # Produce the verified_evidence object for the neutral resolution engine
    transport_evidence = json.loads(json.dumps(resolution_facts))
    evidence = slot_resolution_txn.verified_evidence(
        transport="local",
        evidence_schema=SCHEMA,
        evidence_core_sha256=sha256_bytes(
            json.dumps(
                transport_evidence, sort_keys=True, separators=(",", ":")
            ).encode()
        ),
        parser_tool_sha256=wrapper_sha,
        verifier_tool_sha256=wrapper_sha,
        slot_id=args.slot_id,
        slot_row_projection_sha256=slot_resolution_txn.slot_row_immutable_projection(
            slot
        ),
        resolution_facts=resolution_facts,
    )

    paths = slot_resolution_txn.TransactionPaths(
        split=args.split_manifest.resolve(),
        freeze_manifest=args.freeze_manifest.resolve(),
        fill_lock=receipts_dir / ".fill.lock",
        fill_journal=receipts_dir / "fill-journal.jsonl",
        resolution_log=receipts_dir / "resolution-log.jsonl",
    )

    def parse_evidence(_slot, _section, _freeze, parent_sha):
        updates = {
            "artifact_sha256": artifact_sha,
            "slot_status": args.resolution,
        }
        return evidence, updates

    current_sha = sha256_file(args.split_manifest)
    result = slot_resolution_txn.resolve_slot(
        paths=paths,
        expect_parent_sha=current_sha,
        slot_id=args.slot_id,
        resolution=args.resolution,
        parse_evidence=parse_evidence,
        engine_tool_sha256=sha256_file(Path(slot_resolution_txn.__file__).resolve()),
    )

    utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    receipt = {
        "schema": SCHEMA,
        "slot_id": args.slot_id,
        "resolution": args.resolution,
        "train_ledger_id": args.train_ledger_id,
        "liveness_ledger_id": args.liveness_ledger_id,
        "wrapper_tool_sha256": wrapper_sha,
        "new_manifest_sha256": result.new_manifest_sha256,
        "parent_manifest_sha256": result.parent_manifest_sha256,
        "resolution_record_txn": result.resolution_record.get("txn"),
        "resolution_facts": resolution_facts,
        "utc": utc,
    }

    receipt_core_sha = sha256_bytes(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    )

    _slot_resolution_ledger().parent.mkdir(parents=True, exist_ok=True)
    ledger_entry = {
        "phase": "SLOT_RESOLUTION_COMMIT",
        "schema": SCHEMA,
        "slot_id": args.slot_id,
        "resolution": args.resolution,
        "train_ledger_id": args.train_ledger_id,
        "liveness_ledger_id": args.liveness_ledger_id,
        "receipt_core_sha256": receipt_core_sha,
        "resolution_txn": result.resolution_record.get("txn"),
        "utc": utc,
    }
    import fcntl

    with open(_slot_resolution_ledger_lock(), "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            with open(_slot_resolution_ledger(), "a") as fh:
                fh.write(json.dumps(ledger_entry, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)

    print(
        f"SLOT_RESOLUTION_COMMIT: slot={args.slot_id} resolution={args.resolution} "
        f"txn={result.resolution_record.get('txn')}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
