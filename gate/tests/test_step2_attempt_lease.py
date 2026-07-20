"""Tests for gate/step2_attempt_lease.py — durable attempt lease/record manager
#3902 P0-5. All tests use in-memory/temporary paths; no persistent state."""

from __future__ import annotations

from pathlib import Path

import pytest

from gate import step2_attempt_lease as al

# ---------------------------------------------------------------------------
# Fixtures: each test gets an isolated temp lease ledger
# ---------------------------------------------------------------------------


@pytest.fixture
def tmp_lease_env(tmp_path: Path):
    """Redirect LEASE_LEDGER and LEASE_LOCK to a temp directory."""
    old_ledger = al.LEASE_LEDGER
    old_lock = al.LEASE_LOCK
    try:
        al.LEASE_LEDGER = tmp_path / "attempt-leases.jsonl"
        al.LEASE_LOCK = tmp_path / ".attempt-lease.lock"
        yield tmp_path
    finally:
        al.LEASE_LEDGER = old_ledger
        al.LEASE_LOCK = old_lock


# ---------------------------------------------------------------------------
# Acquire lease — happy path
# ---------------------------------------------------------------------------


def test_acquire_lease_granted(tmp_lease_env):
    """Acquire lease for slot -> granted."""
    granted, reason = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted, f"expected granted, got: {reason}"
    assert "lease acquired" in reason

    # Verify the ledger entry
    rows = al._read_ledger()
    assert len(rows) == 1
    entry = rows[0]
    assert entry["schema"] == al.SCHEMA
    assert entry["slot_id"] == "gbm-cf-s01"
    assert entry["attempt_number"] == 1
    assert entry["state"] == "active"
    assert entry["outcome"] is None


# ---------------------------------------------------------------------------
# Single active lease invariant (#3902 req 3)
# ---------------------------------------------------------------------------


def test_acquire_same_slot_without_release_refused(tmp_lease_env):
    """Acquire lease for same slot without release -> refused (single active
    lease)."""
    granted1, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted1

    granted2, reason2 = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=2, launch_anchor_id="anchor-a2"
    )
    assert not granted2
    assert "single-active-lease" in reason2


def test_different_slots_allowed_concurrent(tmp_lease_env):
    """Different slots can have concurrent active leases."""
    granted1, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted1

    granted2, reason2 = al.acquire_lease(
        slot_id="gbm-cf-s02", attempt_number=1, launch_anchor_id="anchor-b1"
    )
    assert granted2, f"expected granted for different slot, got: {reason2}"


# ---------------------------------------------------------------------------
# Release -> next acquire succeeds
# ---------------------------------------------------------------------------


def test_release_then_acquire_succeeds(tmp_lease_env):
    """Release lease -> next acquire succeeds."""
    granted1, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted1

    released, rel_reason = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="failure",
        failure_category="resource-exhaustion",
        failure_signature="sig001",
    )
    assert released, f"expected release, got: {rel_reason}"

    granted2, reason2 = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=2, launch_anchor_id="anchor-a2"
    )
    assert granted2, f"expected granted after release, got: {reason2}"


def test_release_nonexistent_lease_refused(tmp_lease_env):
    """Releasing a nonexistent lease is refused."""
    released, reason = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="nonexistent",
        outcome="failure",
        failure_category="resource-exhaustion",
    )
    assert not released
    assert "no active lease" in reason


# ---------------------------------------------------------------------------
# Max attempts enforcement (#3902 req 2)
# ---------------------------------------------------------------------------


def test_enforce_max_attempts_below_limit(tmp_lease_env):
    """enforce_max_attempts returns True when history < max."""
    history = [
        al.AttemptRecord(
            slot_id="gbm-cf-s01",
            attempt_id="a1",
            attempt_number=1,
            lease_id="l1",
            outcome="failure",
            failure_category="resource-exhaustion",
        ),
        al.AttemptRecord(
            slot_id="gbm-cf-s01",
            attempt_id="a2",
            attempt_number=2,
            lease_id="l2",
            outcome="failure",
            failure_category="resource-exhaustion",
        ),
    ]
    assert al.enforce_max_attempts(history) is True


def test_enforce_max_attempts_at_limit(tmp_lease_env):
    """enforce_max_attempts returns False when history >= max."""
    history = [
        al.AttemptRecord(
            slot_id="gbm-cf-s01",
            attempt_id=f"a{i}",
            attempt_number=i,
            lease_id=f"l{i}",
            outcome="failure",
            failure_category="resource-exhaustion",
        )
        for i in range(1, 4)
    ]
    assert al.enforce_max_attempts(history) is False


def test_acquire_attempt_4_refused_by_ordinal(tmp_lease_env):
    """Acquiring attempt #4 is refused by ordinal (max attempts = 3)."""
    for n in range(1, 4):
        granted, _ = al.acquire_lease(
            slot_id="gbm-cf-s01",
            attempt_number=n,
            launch_anchor_id=f"anchor-a{n}",
        )
        assert granted, f"attempt {n} should be granted"
        released, _ = al.release_lease(
            slot_id="gbm-cf-s01",
            attempt_id=f"anchor-a{n}",
            outcome="failure",
            failure_category="resource-exhaustion",
        )
        assert released, f"release attempt {n} should succeed"

    # Attempt 4 should fail by ordinal invariant (expected 4 but first check
    # catches it)
    granted, reason = al.acquire_lease(
        slot_id="gbm-cf-s01",
        attempt_number=4,
        launch_anchor_id="anchor-a4",
    )
    assert not granted
    assert "maximum" in reason or "ordinal" in reason


# ---------------------------------------------------------------------------
# First success wins (#3902 req 4)
# ---------------------------------------------------------------------------


def test_enforce_first_success_wins_no_prior(tmp_lease_env):
    """enforce_first_success_wins returns True when no prior success."""
    history = [
        al.AttemptRecord(
            slot_id="gbm-cf-s01",
            attempt_id="a1",
            attempt_number=1,
            lease_id="l1",
            outcome="failure",
            failure_category="resource-exhaustion",
        ),
    ]
    assert al.enforce_first_success_wins(history) is True


def test_enforce_first_success_wins_prior_success(tmp_lease_env):
    """enforce_first_success_wins returns False when success exists."""
    history = [
        al.AttemptRecord(
            slot_id="gbm-cf-s01",
            attempt_id="a1",
            attempt_number=1,
            lease_id="l1",
            outcome="success",
        ),
    ]
    assert al.enforce_first_success_wins(history) is False


def test_acquire_after_success_refused(tmp_lease_env):
    """Acquiring a lease for a slot with a prior success is refused."""
    granted1, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted1
    released, _ = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="success",
    )
    assert released

    granted2, reason2 = al.acquire_lease(
        slot_id="gbm-cf-s01",
        attempt_number=2,
        launch_anchor_id="anchor-a2",
    )
    assert not granted2
    assert "first-success-wins" in reason2


# ---------------------------------------------------------------------------
# Ordinal enforcement (#3902 req 2)
# ---------------------------------------------------------------------------


def test_check_attempt_ordinal_empty_accepts_1(tmp_lease_env):
    """Empty history accepts ordinal 1."""
    assert al.check_attempt_ordinal([], 1) is True


def test_check_attempt_ordinal_empty_refuses_2(tmp_lease_env):
    """Empty history refuses ordinal 2."""
    assert al.check_attempt_ordinal([], 2) is False


@pytest.mark.parametrize(
    "history_numbers,next_num,expected",
    [
        ([1], 2, True),  # N -> N+1 accepted
        ([1], 1, False),  # N -> N refused (same number: duplicate)
        ([1], 3, False),  # N -> N+2 refused (skip)
        ([1, 2], 3, True),  # 2 -> 3 accepted
        ([1, 2], 2, False),  # 2 -> 2 refused
        ([1, 2], 4, False),  # 2 -> 4 refused (skip)
    ],
)
def test_check_attempt_ordinal_parametrized(
    tmp_lease_env, history_numbers, next_num, expected
):
    """Ordinal checker accepts only sequential N+1."""
    history = [
        al.AttemptRecord(
            slot_id="gbm-cf-s01",
            attempt_id=f"a{n}",
            attempt_number=n,
            lease_id=f"l{n}",
            outcome="failure",
            failure_category="resource-exhaustion",
        )
        for n in history_numbers
    ]
    assert al.check_attempt_ordinal(history, next_num) is expected


# ---------------------------------------------------------------------------
# Failure categories propagate to terminal record (#3902 req 1)
# ---------------------------------------------------------------------------


def test_failure_category_recorded_on_release(tmp_lease_env):
    """Failure categories propagate to terminal record."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    released, _ = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="failure",
        failure_category="engine-crash",
        failure_signature="crash_at_line_142",
    )
    assert released

    rows = al._read_ledger()
    released_rows = [r for r in rows if r.get("state") == "released"]
    assert len(released_rows) >= 1

    terminal = released_rows[-1]
    assert terminal["outcome"] == "failure"
    assert terminal["failure_category"] == "engine-crash"
    assert terminal["failure_signature"] == "crash_at_line_142"
    assert terminal["terminal_at"] is not None


def test_failure_category_required_on_failure(tmp_lease_env):
    """release_lease refuses to release a failure without failure_category."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    released, reason = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="failure",
    )
    assert not released
    assert "failure_category is None" in reason


def test_success_needs_no_failure_category(tmp_lease_env):
    """A success release requires no failure_category."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    released, _ = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="success",
    )
    assert released


# ---------------------------------------------------------------------------
# infra_exhausted vs deterministic distinction preserved (#3902 req 5)
# ---------------------------------------------------------------------------


def test_infra_exhausted_recorded(tmp_lease_env):
    """infra_exhausted failure_class is preserved in the terminal record."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    released, _ = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="failure",
        failure_category="resource-exhaustion",
        failure_class="infra_exhausted",
    )
    assert released

    history = al.load_history_for_slot("gbm-cf-s01")
    assert len(history) >= 1
    assert history[-1].failure_class == "infra_exhausted"


def test_deterministic_recorded(tmp_lease_env):
    """deterministic failure_class is preserved in the terminal record."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    released, _ = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="failure",
        failure_category="data-corruption",
        failure_class="deterministic",
    )
    assert released

    history = al.load_history_for_slot("gbm-cf-s01")
    assert len(history) >= 1
    assert history[-1].failure_class == "deterministic"


def test_success_has_no_failure_class(tmp_lease_env):
    """A success record carries failure_class=None."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    released, _ = al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="success",
    )
    assert released

    history = al.load_history_for_slot("gbm-cf-s01")
    assert len(history) >= 1
    assert history[-1].outcome == "success"
    assert history[-1].failure_class is None


# ---------------------------------------------------------------------------
# load_history_for_slot — integration
# ---------------------------------------------------------------------------


def test_load_history_only_released(tmp_lease_env):
    """load_history_for_slot only returns released/terminal leases."""
    al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    # Active — should not appear
    history = al.load_history_for_slot("gbm-cf-s01")
    assert len(history) == 0

    al.release_lease(
        slot_id="gbm-cf-s01",
        attempt_id="anchor-a1",
        outcome="failure",
        failure_category="resource-exhaustion",
    )

    history = al.load_history_for_slot("gbm-cf-s01")
    assert len(history) == 1
    assert history[0].attempt_id == "anchor-a1"


def test_load_history_multiple_attempts(tmp_lease_env):
    """load_history_for_slot returns attempts in order."""
    for n in range(1, 4):
        aid = f"anchor-a{n}"
        granted, _ = al.acquire_lease(
            slot_id="gbm-cf-s01", attempt_number=n, launch_anchor_id=aid
        )
        assert granted
        released, _ = al.release_lease(
            slot_id="gbm-cf-s01",
            attempt_id=aid,
            outcome="failure",
            failure_category="resource-exhaustion",
        )
        assert released

    history = al.load_history_for_slot("gbm-cf-s01")
    assert len(history) == 3
    numbers = [r.attempt_number for r in history]
    assert numbers == [1, 2, 3]


# ---------------------------------------------------------------------------
# Expire stale leases (crash recovery)
# ---------------------------------------------------------------------------


def test_expire_stale_leases(tmp_lease_env):
    """Stale active leases are expired."""
    granted, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted

    # With a very low max_age, this lease should be expired
    # (acquired_at is "now" when test runs, so we use -1 to force expire)
    expired = al.expire_stale_leases(max_age_seconds=-1)
    assert len(expired) >= 1
    assert "anchor-a1" in expired

    # The slot should now be free
    assert al.enforce_single_active_lease("gbm-cf-s01") is True


# ---------------------------------------------------------------------------
# Schema constant
# ---------------------------------------------------------------------------


def test_schema_constant():
    assert al.SCHEMA == "step2-attempt-lease/v1"


# ---------------------------------------------------------------------------
# Error cases: malformed ledger
# ---------------------------------------------------------------------------


def test_malformed_ledger_raises(tmp_lease_env):
    """Reading a malformed ledger raises ValueError."""
    al.LEASE_LEDGER.write_text("not-json\n")
    with pytest.raises(ValueError, match="malformed"):
        al._read_ledger()


# ---------------------------------------------------------------------------
# force=True bypasses checks (for recovery scenarios)
# ---------------------------------------------------------------------------


def test_acquire_force_bypasses_active_lease(tmp_lease_env):
    """force=True bypasses the single-active-lease check."""
    granted1, _ = al.acquire_lease(
        slot_id="gbm-cf-s01", attempt_number=1, launch_anchor_id="anchor-a1"
    )
    assert granted1

    # force=True should bypass the active lease check
    granted2, reason2 = al.acquire_lease(
        slot_id="gbm-cf-s01",
        attempt_number=2,
        launch_anchor_id="anchor-a2",
        force=True,
    )
    assert granted2, f"expected granted with force, got: {reason2}"
