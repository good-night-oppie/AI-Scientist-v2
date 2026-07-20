"""Phase 1: TRAIN_COMMIT — observed execution only; no future liveness promise.

#3902 P0-2: break the training/liveness causal cycle.

Writes a train receipt with execution evidence (argv, artifacts, timestamps)
and does NOT reference liveness at all. The terminal record is an observed
fact of training having occurred, not a promise that anything survived.

Usage:
  phase_train_commit.py --slot-id gbm-cf-s01 --attempt-id a1 \
      --artifact-path /path/to/artifact --freeze-manifest f.json \
      --split-manifest s.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path

SCHEMA = "phase-train-commit/v1"
_DEFAULT_GATE = Path(__file__).resolve().parent
_GATE_DIR = _DEFAULT_GATE


def _gate() -> Path:
    return _GATE_DIR


def _train_ledger() -> Path:
    return _gate() / "receipts" / "train-ledger.jsonl"


def _train_ledger_lock() -> Path:
    return _gate() / "receipts" / ".train-ledger.lock"


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


def _canonical(obj) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()


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


def ledger_append(record: dict) -> None:
    import fcntl  # local: formatter hook strips module-level-unused imports

    tl = _train_ledger()
    tl.parent.mkdir(parents=True, exist_ok=True)
    with open(_train_ledger_lock(), "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            with open(tl, "a") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)


def main() -> int:
    ap = argparse.ArgumentParser(
        description="Phase 1 TRAIN_COMMIT — observed training evidence only"
    )
    ap.add_argument("--slot-id", required=True)
    ap.add_argument("--attempt-id", required=True)
    ap.add_argument("--artifact-path", required=True)
    ap.add_argument("--freeze-manifest", required=True, type=Path)
    ap.add_argument("--split-manifest", required=True, type=Path)
    args = ap.parse_args()

    this_file = Path(__file__).resolve()
    wrapper_sha = sha256_file(this_file)

    section = load_split(args.split_manifest)
    freeze = load_freeze(args.freeze_manifest)
    slot = slot_row(section, args.slot_id)

    # Validate wrapper sha256 against freeze pin
    census_key = "fac:gate/phase_train_commit.py"
    frozen_pin = ((freeze.get("files") or {}).get(census_key) or {}).get("sha256")
    if frozen_pin and wrapper_sha != frozen_pin:
        die(
            f"phase_train_commit.py sha256 {wrapper_sha[:16]} != freeze pin "
            f"{frozen_pin[:16]} — the wrapper bytes are not the frozen ones"
        )

    # Validate freeze manifest sha against split bind
    bound = (section.get("bound_manifests") or {}).get(
        "executable_freeze_manifest_sha256"
    )
    if not bound:
        die("split rotation_freeze binds no executable freeze manifest sha")
    freeze_actual = sha256_file(args.freeze_manifest)
    if freeze_actual != bound:
        die(f"freeze manifest sha256 {freeze_actual[:16]} != split-bound {bound[:16]}")

    # Validate produce_checkpoint contract from freeze
    family = slot.get("family")
    if not family:
        die("slot row has no family field")
    contract = (freeze.get("checkpoint_command_contract") or {}).get(family)
    if not isinstance(contract, dict):
        die(f"freeze has no checkpoint_command_contract for family {family!r}")

    # Verify produce_checkpoint wrapper pin
    producer_wrapper_pin = contract.get("producer_wrapper_sha256")
    if not producer_wrapper_pin:
        die(f"family {family!r} contract has no producer_wrapper_sha256")
    producer_path = this_file.parent / "produce_checkpoint.py"
    if not producer_path.is_file():
        die("produce_checkpoint.py not found alongside phase_train_commit.py")
    producer_actual = sha256_file(producer_path)
    if producer_actual != producer_wrapper_pin:
        die(
            f"produce_checkpoint.py sha256 {producer_actual[:16]} != frozen "
            f"contract pin {producer_wrapper_pin[:16]}"
        )

    # Resolve artifact and gather evidence
    artifact_path = Path(args.artifact_path)
    if not artifact_path.is_file():
        die(f"artifact path {artifact_path} does not exist")
    artifact_sha = sha256_file(artifact_path)

    utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    receipt = {
        "schema": SCHEMA,
        "slot_id": args.slot_id,
        "attempt_id": args.attempt_id,
        "family": family,
        "split_sha256": sha256_file(args.split_manifest),
        "freeze_sha256": sha256_file(args.freeze_manifest),
        "wrapper_tool_sha256": wrapper_sha,
        "producer_wrapper_sha256": producer_actual,
        "artifact_path": str(artifact_path.resolve()),
        "artifact_sha256": artifact_sha,
        "argv_sha256": contract.get("argv_contract", {}).get("trainer"),
        "host": platform.node(),
        "utc": utc,
    }

    receipt_core_sha = sha256_bytes(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    )

    # Verify no liveness reference in receipt
    if "liveness" in json.dumps(receipt).lower():
        die("TRAIN_COMMIT receipt must not reference liveness — P0-2 violation")

    ledger_entry = {
        "phase": "TRAIN_COMMIT",
        "schema": SCHEMA,
        "slot_id": args.slot_id,
        "attempt_id": args.attempt_id,
        "receipt_core_sha256": receipt_core_sha,
        "artifact_sha256": artifact_sha,
        "utc": utc,
    }

    ledger_append(ledger_entry)

    # Write receipt file
    receipts_dir = _train_ledger().parent
    receipt_path = receipts_dir / f"train-commit-{args.slot_id}-{args.attempt_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {"core": receipt, "core_sha256": receipt_core_sha}, indent=1, sort_keys=True
        )
        + "\n"
    )

    print(
        f"TRAIN_COMMIT: slot={args.slot_id} attempt={args.attempt_id} ledger-recorded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
