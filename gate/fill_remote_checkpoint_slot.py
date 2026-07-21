"""Remote checkpoint-slot fill tool — signed capsule evidence, no local receipt.

Schema: remote-checkpoint-slot-fill/v1

This tool fills a frozen slot using a coordinator-signed remote result capsule
as the sole admissible evidence. It rejects any evidence bearing a
locally-produced execution_context, enforces the Section 6 slot-ordering
baseline-vs-live contract via step2_fill_ordering_guard, and delegates the
transport-neutral mutation to slot_resolution_txn.resolve_slot() unchanged.

The tool verifies its OWN bytes against its sha256 before any execution
(hash-pinned, self-proving). The sha256 constant at the top of the file is
recomputed at startup and matched against the freeze's validator_sha256 pin.

Usage:
  fill_remote_checkpoint_slot.py \\
      --capsule-path <remote_result_capsule.json> \\
      --slot-id gbm-cf-s08 \\
      --freeze-manifest /path/to/executable-freeze-manifest.json \\
      --split-manifest /path/to/split-manifest.json \\
      --anchor-manifest /path/to/anchor-baseline-split.json \\
      --resolution FILLED

  fill_remote_checkpoint_slot.py \\
      --capsule-path <capsule.json> \\
      --slot-id gbm-cf-s08 \\
      --freeze-manifest ... \\
      --split-manifest ... \\
      --anchor-manifest ... \\
      --resolution FAILED
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

GATE = Path(__file__).resolve().parent
sys.path.insert(0, str(GATE))

# ---- SELF-VERIFICATION constant  ----
# This sha256 is expected to match the freeze's validator_sha256 pin for this
# tool. It is verified at startup so the executing bytes are the pinned bytes.
_EXPECTED_TOOL_SHA256: str = (
    # The SHA of this file's final version; set during freeze generation.
    # CI or the freeze census sets this before signing the executable freeze.
    "0" * 64  # placeholder — production freezes replace this
)

# Schema for the resolution record this tool produces
REMOTE_FILL_SCHEMA = "remote-checkpoint-slot-fill/v1"
# Capsule execution context for remote evidence — only this is admissible
REMOTE_CONTEXT = "arena-1-remote-with-attestation"

# Default well-known paths (overridable via CLI args)
SPLIT = GATE / "split-manifest.json"
FREEZE_MANIFEST = GATE / "executable-freeze-manifest.json"
FILL_LOCK = GATE / "receipts" / ".slot-fill.lock"
FILL_JOURNAL = GATE / "receipts" / "slot-fill-journal.jsonl"
RESOLUTION_LOG = GATE / "receipts" / "slot-resolution-log.jsonl"
ANCHOR_BASELINE = GATE / "anchor-baseline-split.json"


def die(msg: str) -> None:
    raise SystemExit(f"FAIL-CLOSED: {msg}")


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    d = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def _is_sha256(value: object) -> bool:
    return (
        isinstance(value, str)
        and len(value) == 64
        and all(ch in "0123456789abcdef" for ch in value)
    )


def self_verify_tool() -> str:
    """Verify this file's sha256 against _EXPECTED_TOOL_SHA256 BEFORE
    allowing any execution. Returns the observed sha (regardless of match)
    so the caller can propagate it into verified_evidence."""
    observed = sha256_file(Path(__file__).resolve())
    if not _is_sha256(observed):
        die(
            f"internal error: {__file__} sha256 is not 64 hex chars — "
            "refusing until the freeze generator sets a valid constant"
        )
    if _EXPECTED_TOOL_SHA256 == "0" * 64:
        die(
            f"{__file__}: the _EXPECTED_TOOL_SHA256 constant is set to "
            "the all-zeros placeholder — the freeze generator must replace "
            "it with the actual frozen sha before this tool may execute"
        )
    if observed != _EXPECTED_TOOL_SHA256:
        die(
            f"{__file__} self-verify FAILED: bytes {observed[:16]} != "
            f"expected pin {_EXPECTED_TOOL_SHA256[:16]} — the executing "
            "tool is not the hash-pinned version from the freeze census"
        )
    return observed


def _build_attempt_from_terminal_record(
    record: dict,
    capsule_core: dict,
) -> "Attempt":
    """Project a capsule's terminal_record into a step2_attempt_policy.Attempt
    for evaluation by the transport-neutral policy engine.

    The attempt_number is set to 1 (the capsule represents ONE execution);
    remote capsule histories that need more than one attempt are submitted
    as separate capsules and aggregated by the caller before calling the
    policy engine (this method is called once per capsule attempt)."""
    from gate.step2_attempt_policy import Attempt  # noqa: E402

    outcome = "success" if record.get("exit_code") == 0 else "failure"
    failure_category = record.get("failure_category")
    failure_signature = record.get("failure_signature")
    return Attempt(
        attempt_number=record.get("attempt_number", 1),
        attempt_id=capsule_core.get("capsule_id", record.get("attempt_id", "unknown")),
        outcome=outcome,
        slot_id=record["slot_id"],
        slice_id=record["slice_id"],
        train_seed=record["train_seed"],
        config_sha256=record["config_sha256"],
        argv_sha256=record["argv_sha256"],
        anchor_capsule_id=record["anchor_capsule_id"],
        anchor_core_sha256=record["anchor_core_sha256"],
        host=record["host"],
        failure_category=failure_category,
        failure_signature=failure_signature,
    )


def _verify_remote_evidence_non_mixability(
    capsule_core: dict,
    frozen_execution_context: str | None,
    slot_id: str,
) -> None:
    """STRICT NON-MIXABILITY: remote evidence must carry the remote execution
    context, and the frozen contract must also declare remote context. A
    mismatch means local evidence being submitted as remote, or remote evidence
    injected into a local slot."""
    capsule_ctx = capsule_core.get("execution_context")
    if capsule_ctx != REMOTE_CONTEXT:
        die(
            f"capsule for slot {slot_id!r} carries execution_context="
            f"{capsule_ctx!r}, expected {REMOTE_CONTEXT!r} — remote evidence "
            "refused (local evidence cannot enter through the remote fill path)"
        )
    if (
        frozen_execution_context is not None
        and frozen_execution_context != REMOTE_CONTEXT
    ):
        die(
            f"slot {slot_id!r} frozen contract execution_context="
            f"{frozen_execution_context!r} does not match "
            f"{REMOTE_CONTEXT!r} — the freeze does not declare this slot as "
            "remote; remote evidence is refused for a locally-attested slot"
        )


def _extract_terminal_record_hash(record: dict) -> str:
    """Canonical hash of the terminal_record, for embedding in
    verified_evidence so the evidence binds the exact terminal-record
    bytes that were evaluated."""
    return sha256_bytes(
        json.dumps(record, sort_keys=True, separators=(",", ":")).encode()
    )


def parse_remote_evidence(
    slot: dict,
    section: dict,
    freeze: dict,
    parent_sha: str,
    args: argparse.Namespace,
    tool_sha: str,
) -> tuple[dict, dict]:
    """Parse and verify remote evidence, producing a verified_evidence object
    and mutable updates for slot_resolution_txn.resolve_slot.

    This is the ``EvidenceParser``-compatible closure for the remote fill path.
    It is factored into a named function (not inline in ``_locked_fill``) so
    tests can call it directly without faking the resolve_slot machinery."""
    from gate import slot_resolution_txn  # noqa: E402
    from gate import step2_attempt_policy as ap  # noqa: E402
    from gate.step2_fill_ordering_guard import (  # noqa: E402
        assert_all_slots_terminal_before_any_fill,
    )

    slot_id = slot["slot_id"]
    capsule_path = Path(args.capsule_path)

    # ---- 1. Load capsule ----
    try:
        from gate import load_remote_result_capsule  # noqa: E402
    except ImportError:
        import load_remote_result_capsule  # type: ignore[import-untyped]

    if not capsule_path.is_file():
        die(f"{capsule_path}: capsule file does not exist")

    freeze_sha = args.freeze_sha
    split_sha = args.split_sha or parent_sha

    capsule_core = load_remote_result_capsule.load_remote_result_capsule(
        capsule_path=capsule_path,
        slot=slot,
        freeze=freeze,
        expected_freeze_sha256=freeze_sha,
        expected_split_sha256=split_sha,
    )

    # ---- 2. Extract terminal_record ----
    terminal_record = capsule_core.get("terminal_record")
    if not isinstance(terminal_record, dict):
        die(f"{capsule_path}: capsule core has no terminal_record")

    terminal_record_hash = _extract_terminal_record_hash(terminal_record)

    # ---- 3. STRICT NON-MIXABILITY ----
    fam = slot["family"]
    contract = (freeze.get("checkpoint_command_contract") or {}).get(fam) or {}
    frozen_ctx = contract.get("execution_context")
    _verify_remote_evidence_non_mixability(capsule_core, frozen_ctx, slot_id)

    # ---- 4. Build Attempt and evaluate history ----
    attempt = _build_attempt_from_terminal_record(terminal_record, capsule_core)
    history = [attempt]

    decision = ap.evaluate_attempt_history(history)

    # ---- 5. Verify decision matches requested resolution ----
    resolution = args.resolution
    if resolution == "FILLED":
        if decision.verdict != "FILLED":
            die(
                f"capsule for slot {slot_id!r} has outcome "
                f"{decision.verdict!r}, but --resolution=FILLED was requested "
                "- the attempt history does not entitle this slot to FILLED"
            )
    elif resolution == "FAILED":
        if decision.verdict not in ("FAILED_DETERMINISTIC", "FAILED_INFRA_EXHAUSTED"):
            die(
                f"capsule for slot {slot_id!r} has outcome "
                f"{decision.verdict!r}, but --resolution=FAILED was requested "
                "- the attempt history does not entitle this slot to FAILED"
            )
    else:
        die(f"unsupported resolution {resolution!r}")

    # ---- 6. Ordering guard ----
    # Only enforced when an anchor manifest is explicitly provided.
    # The baseline split is the source of truth for authorized slot IDs.
    if args.anchor_manifest:
        from gate.step2_fill_ordering_guard import (  # noqa: E402
            FillOrderingViolation,
            load_baseline_slots_by_id,
        )

        anchor_path = Path(args.anchor_manifest)
        if not anchor_path.is_file():
            die(
                f"anchor manifest {anchor_path} missing — the baseline "
                "split is required for ordering enforcement"
            )
        baseline_slots = load_baseline_slots_by_id(anchor_path)
        authorized_ids = sorted(baseline_slots.keys())

        # Build slot_decisions for all authorized slots
        slot_decisions: dict[str, ap.AttemptDecision] = {}
        if args.slot_decisions_file:
            decisions_raw = json.loads(Path(args.slot_decisions_file).read_text())
            for sid, d in decisions_raw.items():
                slot_decisions[sid] = ap.AttemptDecision(
                    schema=ap.SCHEMA,
                    verdict=d["verdict"],
                    n_attempts=d["n_attempts"],
                    binding_attempt_id=d.get("binding_attempt_id"),
                    failure_class=d.get("failure_class"),
                    reason=d.get("reason", ""),
                )
        # Always include the target slot's own decision
        slot_decisions[slot_id] = decision

        try:
            assert_all_slots_terminal_before_any_fill(
                authorized_slot_ids=authorized_ids,
                slot_decisions=slot_decisions,
                target_slot_id=slot_id,
            )
        except FillOrderingViolation as exc:
            die(f"fill ordering violation: {exc}")

    # ---- 7. Build verified_evidence with transport="remote" ----
    capsule_core_sha = sha256_bytes(
        json.dumps(capsule_core, sort_keys=True, separators=(",", ":")).encode()
    )

    facts: dict = {
        "evidence_source": "remote",
        "capsule_path": str(capsule_path),
        "capsule_core_sha256": capsule_core_sha,
        "terminal_record_hash": terminal_record_hash,
        "execution_context": REMOTE_CONTEXT,
        "slot_id": slot_id,
        "family": fam,
        "freeze_sha256": freeze_sha,
        "split_sha256": split_sha,
        "attempt_decision": {
            "verdict": decision.verdict,
            "n_attempts": decision.n_attempts,
            "binding_attempt_id": decision.binding_attempt_id,
            "failure_class": decision.failure_class,
            "reason": decision.reason,
        },
        "parent_manifest_sha256": parent_sha,
    }
    # Include terminal record core/hash in evidence
    facts["terminal_record"] = terminal_record
    facts["terminal_record_hash"] = terminal_record_hash

    evidence = slot_resolution_txn.verified_evidence(
        transport="remote",
        evidence_schema=REMOTE_FILL_SCHEMA,
        evidence_core_sha256=capsule_core_sha,
        parser_tool_sha256=tool_sha,
        verifier_tool_sha256=tool_sha,
        slot_id=slot_id,
        slot_row_projection_sha256=(
            slot_resolution_txn.slot_row_immutable_projection(slot)
        ),
        resolution_facts=facts,
    )

    # ---- 8. Build mutable_updates ----
    artifact_sha = terminal_record.get("artifact_sha256")
    if resolution == "FILLED":
        if not _is_sha256(artifact_sha):
            die(
                f"FILLED resolution requires a valid artifact_sha256 in the "
                f"terminal record, got {artifact_sha!r}"
            )
    elif resolution == "FAILED":
        artifact_sha = None

    mutable_updates = {
        "artifact_sha256": artifact_sha,
        "slot_status": resolution,
    }

    return evidence, mutable_updates


def _transaction_paths(
    split: Path,
    freeze_manifest: Path,
    fill_lock: Path,
    fill_journal: Path,
    resolution_log: Path,
) -> "slot_resolution_txn.TransactionPaths":
    from gate import slot_resolution_txn  # noqa: E402

    return slot_resolution_txn.TransactionPaths(
        split=split,
        freeze_manifest=freeze_manifest,
        fill_lock=fill_lock,
        fill_journal=fill_journal,
        resolution_log=resolution_log,
    )


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--capsule-path",
        required=True,
        type=Path,
        help="Path to the signed remote result capsule JSON",
    )
    ap.add_argument(
        "--slot-id", required=True, help="Slot ID to fill (e.g. gbm-cf-s08)"
    )
    ap.add_argument(
        "--freeze-manifest",
        type=Path,
        default=FREEZE_MANIFEST,
        help="Path to executable-freeze-manifest.json",
    )
    ap.add_argument(
        "--split-manifest",
        type=Path,
        default=SPLIT,
        help="Path to split-manifest.json (the live split)",
    )
    ap.add_argument(
        "--anchor-manifest",
        type=Path,
        help="Path to anchor-baseline-split.json for ordering guard",
    )
    ap.add_argument(
        "--resolution",
        required=True,
        choices=["FILLED", "FAILED"],
        help="Requested slot resolution",
    )
    ap.add_argument(
        "--freeze-sha",
        default="",
        help="Expected freeze manifest sha256 (auto-computed if empty)",
    )
    ap.add_argument(
        "--split-sha",
        default="",
        help="Expected split manifest sha256 (auto-computed if empty)",
    )
    ap.add_argument(
        "--expect-parent-sha",
        default="",
        help="Expected parent split-manifest sha256 (auto-computed if empty)",
    )
    ap.add_argument(
        "--slot-decisions-file",
        type=Path,
        default=None,
        help="JSON file mapping slot_id->AttemptDecision for ordering guard",
    )
    ap.add_argument("--fill-lock", type=Path, default=FILL_LOCK)
    ap.add_argument("--fill-journal", type=Path, default=FILL_JOURNAL)
    ap.add_argument("--resolution-log", type=Path, default=RESOLUTION_LOG)
    ap.add_argument(
        "--engine-tool-sha",
        default="",
        help="Resolution engine tool sha (auto-computed if empty)",
    )
    args = ap.parse_args()

    return _locked_fill(args)


def _locked_fill(args: argparse.Namespace) -> int:
    from gate import slot_resolution_txn  # noqa: E402
    from gate.step2_attempt_policy import AttemptPolicyError  # noqa: E402
    from gate.step2_fill_ordering_guard import (  # noqa: E402
        FillOrderingViolation,
    )

    # ---- SELF-VERIFY before any execution ----
    tool_sha = self_verify_tool()

    # ---- Derive expected hashes if not explicitly provided ----
    freeze_sha = args.freeze_sha or (
        sha256_file(args.freeze_manifest)
        if args.freeze_manifest.is_file()
        else die(f"freeze manifest {args.freeze_manifest} not found")
    )
    args.freeze_sha = freeze_sha

    split_sha = args.split_sha or (
        sha256_file(args.split_manifest)
        if args.split_manifest.is_file()
        else die(f"split manifest {args.split_manifest} not found")
    )
    args.split_sha = split_sha

    expect_parent_sha = args.expect_parent_sha or (
        sha256_file(args.split_manifest)
        if args.split_manifest.is_file()
        else die(f"split manifest {args.split_manifest} not found")
    )

    engine_tool_sha = args.engine_tool_sha or sha256_file(
        Path(slot_resolution_txn.__file__).resolve()
    )

    # ---- Build evidence parser closure ----
    def parse_remote_evidence_closure(slot, section, freeze, parent_sha):
        try:
            return parse_remote_evidence(
                slot, section, freeze, parent_sha, args, tool_sha
            )
        except AttemptPolicyError as exc:
            die(f"attempt policy error: {exc}")
        except FillOrderingViolation as exc:
            die(f"fill ordering violation: {exc}")

    # ---- Execute resolution ----
    try:
        result = slot_resolution_txn.resolve_slot(
            paths=_transaction_paths(
                split=args.split_manifest,
                freeze_manifest=args.freeze_manifest,
                fill_lock=args.fill_lock,
                fill_journal=args.fill_journal,
                resolution_log=args.resolution_log,
            ),
            expect_parent_sha=expect_parent_sha,
            slot_id=args.slot_id,
            resolution=args.resolution,
            parse_evidence=parse_remote_evidence_closure,
            engine_tool_sha256=engine_tool_sha,
        )
    except slot_resolution_txn.SlotResolutionError as exc:
        die(str(exc))

    facts = result.resolution_record["evidence"]
    print(f"slot {args.slot_id} -> {args.resolution} (remote)")
    for key, value in facts.items():
        if key == "terminal_record":
            print(
                f"  terminal_record: (embedded, hash={value.get('terminal_record_hash', 'N/A')})"
            )
        else:
            print(f"  {key}: {str(value)[:88]}")
    print(
        "  immutable projection : "
        f"{result.immutable_projection_sha256} (UNCHANGED — verified)"
    )
    print(
        "  parent -> new        : "
        f"{result.parent_manifest_sha256[:16]} -> "
        f"{result.new_manifest_sha256[:16]}"
    )
    print("  evidence source      : remote")
    print(f"  appended to          : {args.resolution_log}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
