"""Phase 2: LIVENESS_COMMIT — references train ledger ID + artifact SHA;
liveness independently produced/validated.

#3902 P0-2: break the training/liveness causal cycle.

Validates artifact exists at the path the train commit claimed, then produces
an independent liveness receipt referencing the train commit's ledger_id.
Quality-blind validation (artifact existence/integrity, not quality).

Usage:
  phase_liveness_commit.py --slot-id gbm-cf-s01 --train-ledger-id <id> \
      --artifact-path /path/to/artifact --artifact-sha256 <sha> \
      --freeze-manifest f.json --split-manifest s.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
from pathlib import Path

SCHEMA = "phase-liveness-commit/v1"
_DEFAULT_GATE = Path(__file__).resolve().parent
_GATE_DIR = _DEFAULT_GATE


def _gate() -> Path:
    return _GATE_DIR


def _liveness_ledger() -> Path:
    return _gate() / "receipts" / "liveness-ledger.jsonl"


def _liveness_ledger_lock() -> Path:
    return _gate() / "receipts" / ".liveness-ledger.lock"


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


def ledger_append(record: dict) -> None:
    import fcntl

    ll = _liveness_ledger()
    ll.parent.mkdir(parents=True, exist_ok=True)
    with open(_liveness_ledger_lock(), "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            with open(ll, "a") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)


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
        description="Phase 2 LIVENESS_COMMIT — independent artifact liveness"
    )
    ap.add_argument("--slot-id", required=True)
    ap.add_argument("--train-ledger-id", required=True)
    ap.add_argument("--artifact-path", required=True, type=Path)
    ap.add_argument("--artifact-sha256", required=True)
    ap.add_argument("--freeze-manifest", required=True, type=Path)
    ap.add_argument("--split-manifest", required=True, type=Path)
    args = ap.parse_args()

    this_file = Path(__file__).resolve()
    wrapper_sha = sha256_file(this_file)

    section = load_split(args.split_manifest)
    freeze = load_freeze(args.freeze_manifest)
    slot_row(section, args.slot_id)

    # Validate wrapper sha256 against freeze pin
    census_key = "fac:gate/phase_liveness_commit.py"
    frozen_pin = ((freeze.get("files") or {}).get(census_key) or {}).get("sha256")
    if frozen_pin and wrapper_sha != frozen_pin:
        die(
            f"phase_liveness_commit.py sha256 {wrapper_sha[:16]} != freeze pin "
            f"{frozen_pin[:16]} — the wrapper bytes are not the frozen ones"
        )

    # Validate the train commit exists in the train ledger
    train_ledger = _liveness_ledger().parent / "train-ledger.jsonl"
    train_rows = ledger_read_all(train_ledger)
    train_commit = None
    for row in train_rows:
        if row.get("phase") == "TRAIN_COMMIT" and row.get("slot_id") == args.slot_id:
            train_commit = row
            break
    if train_commit is None:
        die(
            f"no TRAIN_COMMIT found for slot {args.slot_id} in the train ledger "
            "— liveness cannot proceed without a prior train commit"
        )
    train_artifact_sha = train_commit.get("artifact_sha256")
    if not train_artifact_sha:
        die(
            "train commit has no artifact_sha256 — cannot validate artifact "
            "integrity against an empty train claim"
        )

    # Validate the artifact exists at the claimed path
    if not args.artifact_path.is_file():
        die(
            f"artifact path {args.artifact_path} does not exist — a liveness "
            "commit can only validate an existing artifact"
        )

    # Validate artifact SHA matches the train commit's claim
    observed_artifact_sha = sha256_file(args.artifact_path)
    if observed_artifact_sha != args.artifact_sha256:
        die(
            f"artifact sha256 {observed_artifact_sha[:16]} != claimed "
            f"{args.artifact_sha256[:16]}"
        )
    if observed_artifact_sha != train_artifact_sha:
        die(
            f"artifact sha256 {observed_artifact_sha[:16]} != train commit's "
            f"artifact_sha256 {train_artifact_sha[:16]}"
        )

    utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

    receipt = {
        "schema": SCHEMA,
        "slot_id": args.slot_id,
        "train_ledger_id": args.train_ledger_id,
        "wrapper_tool_sha256": wrapper_sha,
        "artifact_path": str(args.artifact_path.resolve()),
        "artifact_sha256": observed_artifact_sha,
        "artifact_exists": True,
        "artifact_integrity": True,
        "host": platform.node(),
        "utc": utc,
    }

    receipt_core_sha = sha256_bytes(
        json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode()
    )

    ledger_entry = {
        "phase": "LIVENESS_COMMIT",
        "schema": SCHEMA,
        "slot_id": args.slot_id,
        "train_ledger_id": args.train_ledger_id,
        "receipt_core_sha256": receipt_core_sha,
        "artifact_sha256": observed_artifact_sha,
        "utc": utc,
    }

    ledger_append(ledger_entry)

    # Write receipt file
    receipts_dir = _liveness_ledger().parent
    receipt_path = receipts_dir / f"liveness-commit-{args.slot_id}.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(
        json.dumps(
            {"core": receipt, "core_sha256": receipt_core_sha},
            indent=1,
            sort_keys=True,
        )
        + "\n"
    )

    print(
        f"LIVENESS_COMMIT: slot={args.slot_id} train-ledger={args.train_ledger_id} "
        "ledger-recorded"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
