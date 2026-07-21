"""STEP-2 durable attempt lease/record manager — #3902 P0-5.

PURE LEDGER LAYER over the pure evaluator (step2_attempt_policy.py). This module
adds DURABLE lease acquisition/release, durable attempt records with failure
category propagation, and machine-enforced invariants backed by an append-only
JSONL lease ledger.

Requirements from #3902 P0-5:
1. Every FAILED attempt must write failure_category in terminal evidence
2. Machine enforcement of: max attempts and attempt ordinal
3. Single active lease per slot (no concurrent attempts)
4. First-success-wins; later success is protocol violation
5. infra_exhausted distinct from deterministic

Schema: "step2-attempt-lease/v1"
Lease ledger: gate/receipts/attempt-leases.jsonl
Advisory lock: gate/receipts/.attempt-lease.lock

Standalone, stdlib-only.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import time
from dataclasses import dataclass
from pathlib import Path

SCHEMA = "step2-attempt-lease/v1"

MAX_ATTEMPTS = 3

# Paths relative to this module's directory
GATE = Path(__file__).resolve().parent
LEASE_LEDGER = GATE / "receipts" / "attempt-leases.jsonl"
LEASE_LOCK = GATE / "receipts" / ".attempt-lease.lock"


# ── Lease table record ────────────────────────────────────────────────────────


@dataclass(frozen=True)
class AttemptLease:
    """One row in the lease ledger: a claim on a slot for a specific attempt.

    A lease is acquired before execution begins and released (or expired)
    after the attempt completes.

    State machine:
      active  -> releasing -> released  (normal lifecycle)
      active  -> expired                 (crash recovery / timeout)
      active  -> releasing -> expired    (release failure)

    No other transitions are valid.
    """

    attempt_id: str
    slot_id: str
    attempt_number: int
    launch_anchor_id: str
    state: str  # "active" | "releasing" | "released" | "expired"
    acquired_at: str  # ISO-8601 UTC
    released_at: str | None = None  # ISO-8601 UTC, set on releasing/expired
    # Durable record, populated on release
    train_commit_id: str | None = None
    liveness_commit_id: str | None = None
    outcome: str | None = None  # "success" | "failure"
    failure_category: str | None = None
    failure_signature: str | None = None
    terminal_at: str | None = None  # ISO-8601 UTC, when terminal evidence landed

    @property
    def is_terminal(self) -> bool:
        return self.state in ("released", "expired")

    @property
    def is_active(self) -> bool:
        return self.state == "active"


# ── Attempt record (durable, written after execution) ─────────────────────────


@dataclass(frozen=True)
class AttemptRecord:
    """Durable per-attempt record, persisted after execution completes.

    Mirrors step2_attempt_policy.Attempt but adds ledger-level fields:
    lease_id links to the lease that governed this attempt.
    """

    # identity — all required fields first
    slot_id: str
    attempt_id: str
    attempt_number: int
    lease_id: str
    outcome: str  # "success" | "failure"

    # optional fields
    schema: str = SCHEMA
    train_commit_id: str | None = None
    liveness_commit_id: str | None = None
    failure_category: str | None = None  # REQUIRED on failure (#3902 req 1)
    failure_signature: str | None = None
    failure_class: str | None = (
        None  # "infra_exhausted" | "deterministic" | None (#3902 req 5)
    )
    acquired_at: str | None = None
    terminal_at: str | None = None


# ── Internal helpers ──────────────────────────────────────────────────────────


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _utcnow() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _read_ledger(path: Path | None = None) -> list[dict]:
    path = path or LEASE_LEDGER
    if not path.is_file():
        return []
    rows = []
    for n, line in enumerate(path.read_text().splitlines(), 1):
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            raise ValueError(f"lease ledger {path}: malformed JSON on line {n}")
    return rows


def _append_ledger(record: dict, path: Path | None = None) -> None:
    path = path or LEASE_LEDGER
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as fh:
        fh.write(json.dumps(record, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def _last_lease_for_slot(rows: list[dict], slot_id: str) -> dict | None:
    """Return the most recent lease entry for a given slot_id."""
    candidates = [r for r in rows if r.get("slot_id") == slot_id]
    return candidates[-1] if candidates else None


# ── Lease acquisition ─────────────────────────────────────────────────────────


def acquire_lease(
    slot_id: str,
    attempt_number: int,
    launch_anchor_id: str,
    *,
    force: bool = False,
) -> tuple[bool, str]:
    """Atomically claim an attempt lease for ``slot_id``.

    Returns ``(granted: bool, reason: str)``.

    A lease is refused when:
    - There is an active lease for this slot (single-active-lease invariant).
    - ``attempt_number`` is not the next sequential number (ordinal invariant).
    - ``attempt_number`` exceeds MAX_ATTEMPTS.
    - There is a prior success for this slot (first-success-wins).

    Pass ``force=True`` to bypass ordinal/active-lease checks (for recovery).
    """
    LEASE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LEASE_LOCK, "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            rows = _read_ledger()

            if not force:
                # ── single active lease invariant (#3902 req 3) ──
                # The ledger is append-only; an attempt may have multiple rows
                # (active, releasing, released).  We check the LATEST per-
                # attempt_id — a released/expired attempt whose earlier
                # ``active`` row is still present does NOT block.
                slot_attempts: dict[str, dict] = {}
                for r in rows:
                    if r.get("slot_id") == slot_id and r.get("attempt_id"):
                        slot_attempts[r["attempt_id"]] = r  # last wins
                live = [
                    e
                    for e in slot_attempts.values()
                    if e.get("state") not in ("released", "expired")
                ]
                if live:
                    return (
                        False,
                        f"slot {slot_id} already has active lease "
                        f"({live[-1].get('attempt_id')}) — single-active-lease "
                        "invariant refuses concurrent attempt",
                    )

                # ── first-success-wins (#3902 req 4) ──
                for r in rows:
                    if r.get("slot_id") == slot_id and r.get("outcome") == "success":
                        return (
                            False,
                            f"slot {slot_id} was already resolved by attempt "
                            f"{r.get('attempt_id')} — first-success-wins: "
                            "no further attempts are legal",
                        )

                # ── ordinal invariant (#3902 req 2) ──
                slot_leases = [r for r in rows if r.get("slot_id") == slot_id]
                last_number = 0
                for r in slot_leases:
                    an = r.get("attempt_number")
                    if isinstance(an, int) and an > last_number:
                        last_number = an
                expected = last_number + 1
                if attempt_number != expected:
                    return (
                        False,
                        f"slot {slot_id} attempt ordinal violation: "
                        f"requested #{attempt_number} but next expected is "
                        f"#{expected} — attempts must be strictly sequential",
                    )

                # ── max attempts (#3902 req 2) ──
                if attempt_number > MAX_ATTEMPTS:
                    return (
                        False,
                        f"slot {slot_id} attempt #{attempt_number} exceeds "
                        f"maximum of {MAX_ATTEMPTS} — no further attempts allowed",
                    )

            now = _utcnow()
            entry = {
                "schema": SCHEMA,
                "attempt_id": launch_anchor_id,
                "slot_id": slot_id,
                "attempt_number": attempt_number,
                "launch_anchor_id": launch_anchor_id,
                "state": "active",
                "acquired_at": now,
                "released_at": None,
                "train_commit_id": None,
                "liveness_commit_id": None,
                "outcome": None,
                "failure_category": None,
                "failure_signature": None,
                "terminal_at": None,
            }
            _append_ledger(entry)
            return (True, f"lease acquired for {slot_id} attempt #{attempt_number}")
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)


# ── Lease release ─────────────────────────────────────────────────────────────


def release_lease(
    slot_id: str,
    attempt_id: str,
    *,
    outcome: str,
    failure_category: str | None = None,
    failure_signature: str | None = None,
    failure_class: str | None = None,
    train_commit_id: str | None = None,
    liveness_commit_id: str | None = None,
) -> tuple[bool, str]:
    """Release a previously-acquired lease, writing terminal outcome.

    Requirement #3902 req 1: EVERY FAILED attempt MUST carry failure_category
    in the terminal evidence. The caller is responsible for calling the
    policy's failure classifier first; this function enforces the durable
    recording of whatever category the classifier returned.

    Requirement #3902 req 5: failure_class distinguishes ``infra_exhausted``
    from ``deterministic`` — the caller determines which via
    step2_attempt_policy.evaluate_attempt_history; this function records it.

    Returns ``(released: bool, reason: str)``.
    """
    if outcome == "failure" and failure_category is None:
        return (
            False,
            f"attempt {attempt_id} on {slot_id}: outcome=failure but "
            "failure_category is None — every FAILED attempt must carry "
            "a failure category in terminal evidence (#3902 P0-5 req 1)",
        )

    LEASE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LEASE_LOCK, "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            rows = _read_ledger()

            # Find the active lease
            match = None
            for r in rows:
                if (
                    r.get("slot_id") == slot_id
                    and r.get("attempt_id") == attempt_id
                    and r.get("state") == "active"
                ):
                    match = r
                    break

            if match is None:
                return (
                    False,
                    f"no active lease found for {slot_id} attempt {attempt_id} "
                    "- cannot release a nonexistent or already-released lease",
                )

            now = _utcnow()
            terminal = {
                "schema": SCHEMA,
                "attempt_id": attempt_id,
                "slot_id": slot_id,
                "attempt_number": match["attempt_number"],
                "launch_anchor_id": match["launch_anchor_id"],
                "state": "releasing",
                "acquired_at": match["acquired_at"],
                "released_at": now,
                "train_commit_id": train_commit_id,
                "liveness_commit_id": liveness_commit_id,
                "outcome": outcome,
                "failure_category": failure_category,
                "failure_signature": failure_signature,
                "failure_class": failure_class,
                "terminal_at": now,
            }
            _append_ledger(terminal)

            # Mark released (second append: releasing -> released)
            released_entry = {**terminal, "state": "released"}
            _append_ledger(released_entry)

            return (
                True,
                f"lease released for {slot_id} attempt {attempt_id} outcome={outcome}",
            )
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)


# ── Invariant enforcement helpers ─────────────────────────────────────────────


def load_history_for_slot(slot_id: str) -> list[AttemptRecord]:
    """Load the complete durable attempt history for a slot.

    Returns a list of AttemptRecord in attempt_number order. Only leases
    that reached a terminal state (released/expired) with a recorded outcome
    are included — active or mid-transition leases are filtered out, as they
    represent in-flight attempts whose outcome is not yet known.
    """
    rows = _read_ledger()
    slot_rows = [
        r
        for r in rows
        if r.get("slot_id") == slot_id
        and r.get("state") == "released"
        and r.get("outcome") is not None
    ]
    # Deduplicate by attempt_id: take the last released entry per attempt
    seen: dict[str, dict] = {}
    for r in slot_rows:
        aid = r.get("attempt_id")
        if aid:
            seen[aid] = r
    records = []
    for r in sorted(seen.values(), key=lambda x: x.get("attempt_number", 0)):
        records.append(
            AttemptRecord(
                schema=SCHEMA,
                slot_id=r.get("slot_id", slot_id),
                attempt_id=r.get("attempt_id", ""),
                attempt_number=r.get("attempt_number", 0),
                lease_id=r.get("attempt_id", ""),
                train_commit_id=r.get("train_commit_id"),
                liveness_commit_id=r.get("liveness_commit_id"),
                outcome=r.get("outcome", "failure"),
                failure_category=r.get("failure_category"),
                failure_signature=r.get("failure_signature"),
                failure_class=r.get("failure_class"),
                acquired_at=r.get("acquired_at"),
                terminal_at=r.get("terminal_at"),
            )
        )
    return records


def enforce_max_attempts(
    history: list[AttemptRecord], max_n: int = MAX_ATTEMPTS
) -> bool:
    """Return True if len(history) < max_n (more attempts allowed)."""
    return len(history) < max_n


def enforce_single_active_lease(slot_id: str) -> bool:
    """Return True if there is NO active lease for this slot.

    The ledger is append-only; an attempt may have multiple rows (active,
    releasing, released).  This function groups by attempt_id and checks
    only the LATEST state per attempt — a released/expired attempt whose
    earlier ``active`` row is still in the ledger does NOT count as live.
    """
    rows = _read_ledger()
    # Per-attempt_id, track the latest row by position in the ledger
    latest: dict[str, dict] = {}
    for r in rows:
        if r.get("slot_id") == slot_id and r.get("attempt_id"):
            aid = r["attempt_id"]
            latest[aid] = r  # last wins
    for state in (e.get("state") for e in latest.values()):
        if state not in ("released", "expired"):
            return False
    return True


def enforce_first_success_wins(history: list[AttemptRecord]) -> bool:
    """Return True if there is NO prior success in the history."""
    return not any(r.outcome == "success" for r in history)


def check_attempt_ordinal(
    history: list[AttemptRecord], next_attempt_number: int
) -> bool:
    """Return True only if ``next_attempt_number`` is the next sequential
    ordinal after the last attempt in ``history``.

    An empty history accepts 1. A history ending at N accepts N+1. Anything
    else (same N, N+2, N-1, etc.) is refused.
    """
    if not history:
        return next_attempt_number == 1
    last = max(r.attempt_number for r in history)
    return next_attempt_number == last + 1


# ── Convenience: lease cleanup / expiry ───────────────────────────────────────


def expire_stale_leases(
    max_age_seconds: int = 86400,
) -> list[str]:
    """Expire any active lease older than ``max_age_seconds``.

    This is a crash-recovery mechanism: if the producer crashed after
    acquiring a lease but before releasing it, the lease is stuck in
    "active". A recovery sweep should call this to clean up abandoned
    leases so the slot is not permanently blocked.

    Returns the list of attempt_ids that were expired.
    """
    LEASE_LOCK.parent.mkdir(parents=True, exist_ok=True)
    with open(LEASE_LOCK, "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            rows = _read_ledger()
            now_ts = time.time()
            expired: list[str] = []

            for r in rows:
                if r.get("state") != "active":
                    continue
                acquired = r.get("acquired_at")
                if not acquired:
                    continue
                try:
                    acquired_ts = time.strptime(acquired, "%Y-%m-%dT%H:%M:%SZ")
                except (ValueError, TypeError):
                    continue
                age = now_ts - time.mktime(acquired_ts)
                if age > max_age_seconds:
                    record = {
                        **r,
                        "state": "expired",
                        "released_at": _utcnow(),
                        "terminal_at": _utcnow(),
                        "outcome": "failure",
                        "failure_category": "infra-exhaustion",
                        "failure_signature": _sha256_bytes(
                            f"stale-lease-expired-after-{max_age_seconds}s".encode()
                        ),
                    }
                    _append_ledger(record)
                    expired.append(r.get("attempt_id", ""))
            return expired
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)
