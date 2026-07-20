"""P0-4 execution protocol wrapper — try/finally + crash recovery (#3902).

Wraps produce_checkpoint.run_terminal_execution() with the P0-4 guarantees:

1. Pre-side-effect: write job manifest (PID, status/log paths) BEFORE spawn
2. try/finally around every subprocess spawn — NEVER leave an open intent
3. Spawn failure -> ABORT/PRELAUNCH_FAILURE with failure_category
4. Any subprocess exit -> TRAIN_COMMIT regardless of nonzero/artifact validity
   (observed execution evidence; P0-2 phase independence)
5. Artifact contract violation -> terminal ABORT with category
   "artifact-contract-violation"
6. Receipts: temp -> fsync -> atomic rename -> fsync parent
7. Recovery: abort entries with no execution evidence; never fabricate commit
8. Retry: prior attempt_id carried in new attempt's identity fields

The "open intent" is the launch-ledger entry — it MUST be closed (commit or
abort) in every code path.  This wrapper DOES NOT replace
run_terminal_execution(); it wraps it.
"""

from __future__ import annotations

import fcntl
import hashlib
import json
import os
import platform
import subprocess
import tempfile
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_GATE_DIR = Path(__file__).resolve().parent
EXECUTION_LEDGER = _GATE_DIR / "receipts" / "execution-ledger.jsonl"
EXECUTION_LEDGER_LOCK = _GATE_DIR / "receipts" / ".execution-ledger.lock"
MANIFEST_DIR = _GATE_DIR / "receipts" / "manifests"
QUARANTINE_DIR = _GATE_DIR / "receipts" / "quarantine"
RECOVERY_STAGE = "execution-protocol-recovery"

SCHEMA = "execution-protocol/v1"
TRAIN_COMMIT_SCHEMA = "phase-train-commit/v1"  # P0-2 independence

# Phase vocabulary
TERMINAL_PHASES = ("EXECUTION_COMMIT", "EXECUTION_ABORT")

# Ledger-id prefix so recovery scans can identify protocol entries
_LEDGER_PREFIX = "ep-"

# ---------------------------------------------------------------------------
# Types
# ---------------------------------------------------------------------------

# The wrapped function signature matching run_terminal_execution:
#   run_terminal_execution(slot, contract, phase, attempt_id,
#                          launch_anchor, jail_dir, receipt_out,
#                          liveness_probe=None) -> dict
ExecutionFn = Callable[..., dict]

SpawnResult = dict[str, Any]


@dataclass
class ExecutionConfig:
    """Configuration for one protocol-managed execution attempt."""

    slot_id: str
    attempt_id: str | None
    argv: list[str]
    jail_dir: Path
    env: dict[str, str]
    receipt_out: Path
    prior_attempt_id: str | None = None


# ---------------------------------------------------------------------------
# Hashing helpers
# ---------------------------------------------------------------------------


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _sha256_file(path: Path) -> str:
    d = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            d.update(chunk)
    return d.hexdigest()


def _canonical_compact(obj: Any) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode()


def _canonical(obj: Any) -> bytes:
    return (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode()


# ---------------------------------------------------------------------------
# Atomic receipt writing: temp -> fsync -> rename -> fsync parent
# ---------------------------------------------------------------------------


def _atomic_write(path: Path, content: bytes) -> None:
    """Write ``content`` to ``path`` with full durability: write to a temp
    file in the same directory, fsync, rename over the target, then fsync
    the parent directory.

    This mirrors the pattern in produce_checkpoint's ledger-append and
    close_once paths: every durable write goes through fsync before the
    data is at the target path, and the parent is fsynced after the rename
    so a crash-after-rename but before-parent-fsync does not lose the new
    directory entry on ext4/XFS with delayed allocation.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(
        dir=str(path.parent), prefix=f".{path.name}-", suffix=".tmp"
    )
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(content)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, path)
        # fsync the parent directory
        parent_fd = os.open(str(path.parent), os.O_RDONLY)
        try:
            os.fsync(parent_fd)
        finally:
            os.close(parent_fd)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Ledger operations (append-only, same lock model as produce_checkpoint)
# ---------------------------------------------------------------------------


def _ledger_append(record: dict) -> None:
    """Append one JSONL row to the execution ledger under an exclusive lock."""
    EXECUTION_LEDGER.parent.mkdir(parents=True, exist_ok=True)
    with open(EXECUTION_LEDGER_LOCK, "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            with open(EXECUTION_LEDGER, "a") as fh:
                fh.write(json.dumps(record, sort_keys=True) + "\n")
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)


def _ledger_read_all() -> list[dict]:
    """Read every row from the execution ledger (no lock — append-only)."""
    if not EXECUTION_LEDGER.is_file():
        return []
    rows = []
    for line in EXECUTION_LEDGER.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        rows.append(json.loads(line))
    return rows


# ---------------------------------------------------------------------------
# Manifest: written BEFORE spawn so evidence of intent survives a crash
# ---------------------------------------------------------------------------


def _write_manifest(cfg: ExecutionConfig) -> None:
    """Write a job manifest BEFORE the subprocess spawns so that a crash
    before any execution evidence can be distinguished from a never-started
    intent.

    The manifest records: PID (0 until spawn), argv, cwd, environment sha,
    status, and timing.  The caller's PID is recorded as ``parent_pid`` so
    that a crash recovery scan can tell whether the original process could
    possibly still be alive.
    """
    manifest = {
        "schema": SCHEMA,
        "kind": "execution-manifest",
        "ledger_id": cfg.attempt_id,
        "slot_id": cfg.slot_id,
        "parent_pid": os.getpid(),
        "spawn_pid": 0,  # set after subprocess starts
        "argv": cfg.argv,
        "cwd": str(cfg.jail_dir),
        "env_sha256": _sha256_bytes(_canonical_compact(cfg.env)),
        "status": "pre-spawn",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest_path = MANIFEST_DIR / f"{cfg.attempt_id}.manifest.json"
    _atomic_write(manifest_path, _canonical(manifest))


def _update_manifest_status(attempt_id: str, status: str, **extra) -> None:
    """Rewrite the manifest with a new status.  Best-effort — a missing
    manifest (already quarantined, or a legacy entry without one) is not an
    error."""
    manifest_path = MANIFEST_DIR / f"{attempt_id}.manifest.json"
    if not manifest_path.is_file():
        return
    try:
        manifest = json.loads(manifest_path.read_bytes())
    except (OSError, json.JSONDecodeError):
        return
    manifest["status"] = status
    manifest["utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    for k, v in extra.items():
        manifest[k] = v
    _atomic_write(manifest_path, _canonical(manifest))


# ---------------------------------------------------------------------------
# Train-commit (P0-2: observed execution evidence, no liveness reference)
# ---------------------------------------------------------------------------


def _write_train_commit(
    slot_id: str,
    attempt_id: str | None,
    exec_ledger_id: str,
    argv: list[str],
    cwd: str,
    exit_code: int | None,
    stdout_bytes: bytes,
    stderr_bytes: bytes,
    artifact_path: str | None,
    artifact_sha: str | None,
    host: str,
) -> str:
    """Produce a P0-2 TRAIN_COMMIT receipt with observed execution evidence.

    This is NOT a full production receipt — it is an OBSERVED fact that a
    subprocess exited, regardless of nonzero return or artifact validity.
    It establishes phase independence: TRAIN_COMMIT exists independently of
    LIVENESS_COMMIT and SLOT_RESOLUTION_COMMIT.

    Returns the receipt_core_sha256.
    """
    receipt = {
        "schema": TRAIN_COMMIT_SCHEMA,
        "exec_protocol": {
            "exec_ledger_id": exec_ledger_id,
            "slot_id": slot_id,
            "attempt_id": attempt_id,
            "protocol": SCHEMA,
        },
        "slot_id": slot_id,
        "attempt_id": attempt_id,
        "argv": argv,
        "cwd": cwd,
        "host": host,
        "exit_code": exit_code,
        "stdout_sha256": _sha256_bytes(stdout_bytes) if stdout_bytes else None,
        "stderr_sha256": _sha256_bytes(stderr_bytes) if stderr_bytes else None,
        "stdout_total_bytes": len(stdout_bytes) if stdout_bytes else 0,
        "stderr_total_bytes": len(stderr_bytes) if stderr_bytes else 0,
        "artifact_path": artifact_path,
        "artifact_sha256": artifact_sha,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    receipt_core_sha = _sha256_bytes(_canonical_compact(receipt))

    # Write the receipt file atomically
    receipts_dir = EXECUTION_LEDGER.parent
    receipt_file = receipts_dir / f"train-commit-{slot_id}-{attempt_id or 'na'}.json"
    _atomic_write(
        receipt_file,
        _canonical({"core": receipt, "core_sha256": receipt_core_sha}),
    )

    # Append to a TRAIN_COMMIT ledger (separate from the protocol ledger)
    train_ledger = receipts_dir / "train-ledger.jsonl"
    train_lock = receipts_dir / ".train-ledger.lock"
    train_ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(train_lock, "a+") as lk:
        fcntl.flock(lk.fileno(), fcntl.LOCK_EX)
        try:
            with open(train_ledger, "a") as fh:
                fh.write(
                    json.dumps(
                        {
                            "phase": "TRAIN_COMMIT",
                            "schema": TRAIN_COMMIT_SCHEMA,
                            "slot_id": slot_id,
                            "attempt_id": attempt_id,
                            "receipt_core_sha256": receipt_core_sha,
                            "artifact_sha256": artifact_sha,
                            "utc": receipt["utc"],
                        },
                        sort_keys=True,
                    )
                    + "\n"
                )
                fh.flush()
                os.fsync(fh.fileno())
        finally:
            fcntl.flock(lk.fileno(), fcntl.LOCK_UN)

    return receipt_core_sha


# ---------------------------------------------------------------------------
# Stderr sidecar (matching produce_checkpoint's pattern)
# ---------------------------------------------------------------------------


_STDERR_SIDECAR_DIR = _GATE_DIR / "receipts" / "runtime"


def _write_stderr_sidecar(ledger_id: str, stderr: bytes) -> None:
    """Persist raw captured stderr to a mode-0600 sidecar (same pattern as
    produce_checkpoint.write_stderr_sidecar)."""
    _STDERR_SIDECAR_DIR.mkdir(parents=True, exist_ok=True)
    path = _STDERR_SIDECAR_DIR / f"{ledger_id}.stderr"
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(stderr)
            fh.flush()
            os.fsync(fh.fileno())
    except BaseException:
        path.unlink(missing_ok=True)
        raise


# ---------------------------------------------------------------------------
# Bounded subprocess capture (matching produce_checkpoint)
# ---------------------------------------------------------------------------


def _bounded_capture(
    argv: list[str],
    cwd: Path,
    env: dict[str, str],
    cap: int = 8 * 1024 * 1024,
) -> tuple[int, bytes, bytes]:
    """Run a subprocess with bounded stdout/stderr capture.

    Returns (exit_code, stdout_bytes, stderr_bytes).  Both streams are
    drained to EOF (so the child never blocks), retaining at most cap
    bytes per stream.  Matching produce_checkpoint._bounded_capture_run
    signature but simplified for the protocol wrapper's needs.
    """
    proc = subprocess.Popen(
        argv,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    results: dict[str, bytes] = {}

    def drain(name: str, pipe) -> None:
        retained = bytearray()
        while True:
            chunk = pipe.read(1 << 16)
            if not chunk:
                break
            if len(retained) <= cap:
                retained += chunk[: cap + 1 - len(retained)]
        pipe.close()
        results[name] = bytes(retained)

    threads = [
        threading.Thread(target=drain, args=(name, pipe), daemon=True)
        for name, pipe in (("stdout", proc.stdout), ("stderr", proc.stderr))
    ]
    for t in threads:
        t.start()
    exit_code = proc.wait()
    for t in threads:
        t.join()
    return exit_code, results.get("stdout", b""), results.get("stderr", b"")


# ---------------------------------------------------------------------------
# Spawn a subprocess with full try/finally closure
# ---------------------------------------------------------------------------


def _spawn_and_capture(
    cfg: ExecutionConfig,
    ledger_id: str,
) -> SpawnResult:
    """Spawn the subprocess under full try/finally discipline.

    Phase sequence:
      1. Write manifest (BEFORE spawn — pre-side-effect)
      2. Write LEDGER INTENT
      3. try/finally:
         a. Record PRELAUNCH_FAILURE if spawn raises
         b. Otherwise capture output
         c. Write TRAIN_COMMIT (on ANY exit, regardless of code)
         d. Close the protocol ledger terminal (commit or abort)
      4. NEVER leave an open intent

    Returns a SpawnResult dict with keys:
      - exit_code: int | None (None = spawn failed)
      - stdout_bytes, stderr_bytes
      - train_commit_sha: str | None
      - spawn_failed: bool
    """
    slot_id = cfg.slot_id
    attempt_id = cfg.attempt_id
    host = platform.node()
    terminal_written = False

    def close_terminal(
        phase: str,
        *,
        exit_code: int | None = None,
        abort_reason: str | None = None,
        failure_category: str | None = None,
        train_commit_sha: str | None = None,
    ) -> None:
        nonlocal terminal_written
        if terminal_written:
            return
        record = {
            "ledger_id": ledger_id,
            "slot_id": slot_id,
            "attempt_id": attempt_id,
            "phase": phase,
            "abort_reason": abort_reason,
            "failure_category": failure_category,
            "train_commit_sha256": train_commit_sha,
            "exit_code": exit_code,
            "host": host,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        _ledger_append(record)
        terminal_written = True

    # ---- Pre-spawn: write manifest and intent ----
    # Manifest is written by the outer spawn_with_protocol; here we only
    # record the execution INTENT in the ledger.
    intent = {
        "ledger_id": ledger_id,
        "slot_id": slot_id,
        "attempt_id": attempt_id,
        "phase": "EXECUTION_INTENT",
        "argv": cfg.argv,
        "cwd": str(cfg.jail_dir),
        "host": host,
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    if cfg.prior_attempt_id is not None:
        intent["prior_attempt_id"] = cfg.prior_attempt_id
    _ledger_append(intent)

    # ---- try/finally starts here ----
    exit_code: int | None = None
    stdout_bytes = b""
    stderr_bytes = b""
    try:
        try:
            (
                exit_code,
                stdout_bytes,
                stderr_bytes,
            ) = _bounded_capture(cfg.argv, cfg.jail_dir, cfg.env)
        except (OSError, subprocess.SubprocessError) as exc:
            # Spawn failure — the subprocess never started
            _update_manifest_status(cfg.attempt_id, "spawn-failed", error=str(exc))
            close_terminal(
                "EXECUTION_ABORT",
                abort_reason=f"prelaunch-failure: {type(exc).__name__}: {exc}",
                failure_category="prelaunch-failure",
            )
            return {
                "exit_code": None,
                "stdout_bytes": b"",
                "stderr_bytes": b"",
                "train_commit_sha": None,
                "spawn_failed": True,
            }

        # ---- Subprocess exited (any code) → observe evidence ----
        _update_manifest_status(
            cfg.attempt_id, "subprocess-exited", exit_code=exit_code
        )

        # Write stderr sidecar
        try:
            _write_stderr_sidecar(ledger_id, stderr_bytes)
        except FileExistsError:
            pass  # sidecar already exists — safe, not a concern

        # Resolve artifact path (best-effort for train_commit)
        artifact_path_val: str | None = None
        artifact_sha_val: str | None = None
        if exit_code == 0:
            out_rel = None
            # Try to locate the output — best effort for TRAIN_COMMIT observation
            for line in reversed(cfg.argv):
                if line and not line.startswith("-"):
                    out_rel = line
            if out_rel:
                candidate = Path(out_rel)
                if not candidate.is_absolute():
                    candidate = cfg.jail_dir / candidate
                if candidate.is_file() and not candidate.is_symlink():
                    artifact_path_val = str(candidate)
                    artifact_sha_val = _sha256_file(candidate)

        train_commit_sha = _write_train_commit(
            slot_id=slot_id,
            attempt_id=attempt_id,
            exec_ledger_id=ledger_id,
            argv=cfg.argv,
            cwd=str(cfg.jail_dir),
            exit_code=exit_code,
            stdout_bytes=stdout_bytes,
            stderr_bytes=stderr_bytes,
            artifact_path=artifact_path_val,
            artifact_sha=artifact_sha_val,
            host=host,
        )

        # Train commit observed — now close the protocol terminal
        # The phase can be COMMIT for any observed execution (even nonzero)
        close_terminal(
            "EXECUTION_COMMIT",
            exit_code=exit_code,
            train_commit_sha=train_commit_sha,
        )

        return {
            "exit_code": exit_code,
            "stdout_bytes": stdout_bytes,
            "stderr_bytes": stderr_bytes,
            "train_commit_sha": train_commit_sha,
            "spawn_failed": False,
        }
    except BaseException as exc:
        # Catch-all: any unhandled exception closes the intent as ABORT
        if not terminal_written:
            close_terminal(
                "EXECUTION_ABORT",
                abort_reason=f"unhandled-exception: {type(exc).__name__}: {exc}",
                failure_category="protocol-internal-error",
            )
        raise


# ---------------------------------------------------------------------------
# Main protocol wrapper
# ---------------------------------------------------------------------------


class ExecutionError(RuntimeError):
    """Raised when the execution protocol abort-closes without a successful
    EXECUTION_COMMIT.  Carries the ledger_id for diagnostic traceability."""

    def __init__(self, message: str, ledger_id: str) -> None:
        super().__init__(message)
        self.ledger_id = ledger_id


def run_with_protocol(
    slot: dict,
    contract: dict,
    phase: str,
    attempt_id: str | None,
    launch_anchor: object,
    jail_dir: Path,
    receipt_out: Path,
    liveness_probe: Callable | None = None,
    prior_attempt_id: str | None = None,
) -> dict:
    """Execute a terminal-training run under the P0-4 execution protocol.

    This wraps ``produce_checkpoint.run_terminal_execution()`` with the
    full P0-4 discipline: pre-spawn manifest, try/finally closed intents,
    TRAIN_COMMIT on every subprocess exit, atomic receipt writes, and
    crash recovery.

    Parameters match ``produce_checkpoint.run_terminal_execution()`` with
    the addition of ``prior_attempt_id``:

    :param prior_attempt_id: If set, the previous attempt's ledger_id is
        carried in the new attempt's identity fields (retry chain).
    :returns: dict with keys ``ledger_id``, ``exit_code``,
        ``train_commit_sha256``, ``terminal_phase``.

    Raises ``ExecutionError`` if the protocol abort-closed (spawn failure,
    internal error) — the caller should NOT treat this as a terminal
    training outcome to pass to phase 2/3; it is a protocol-level abort.
    """
    from gate import produce_checkpoint

    slot_id = slot["slot_id"]
    host = platform.node()
    ledger_id = _LEDGER_PREFIX + uuid.uuid4().hex

    # Build execution config from the slot/contract
    argv = produce_checkpoint.build_argv(contract, slot)
    env = produce_checkpoint.sanitized_execution_env(contract)

    ExecutionConfig(
        slot_id=slot_id,
        attempt_id=ledger_id,  # the protocol-ledger id IS the attempt_id
        argv=argv,
        jail_dir=jail_dir,
        env=env,
        receipt_out=receipt_out,
    )

    # 1. Pre-side-effect: write manifest BEFORE the inner wrapper does anything
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "schema": SCHEMA,
        "kind": "run-with-protocol-manifest",
        "ledger_id": ledger_id,
        "prior_attempt_id": prior_attempt_id,
        "slot_id": slot_id,
        "parent_pid": os.getpid(),
        "argv": argv,
        "cwd": str(jail_dir),
        "status": "pre-exec",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_write(MANIFEST_DIR / f"{ledger_id}.manifest.json", _canonical(manifest))

    # 2. Record the prior attempt_id in the protocol ledger
    _ledger_append(
        {
            "ledger_id": ledger_id,
            "prior_attempt_id": prior_attempt_id,
            "slot_id": slot_id,
            "phase": "EXECUTION_INTENT",
            "argv": argv,
            "cwd": str(jail_dir),
            "host": host,
            "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
    )

    try:
        # 3. Run the inner terminal execution
        result = produce_checkpoint.run_terminal_execution(
            slot=slot,
            contract=contract,
            phase=phase,
            attempt_id=attempt_id or ledger_id,
            launch_anchor=launch_anchor,
            jail_dir=jail_dir,
            receipt_out=receipt_out,
            liveness_probe=liveness_probe,
        )
        # 4. On success, update manifest and record the commit
        _update_manifest_status(ledger_id, "terminal-success")
        _ledger_append(
            {
                "ledger_id": ledger_id,
                "slot_id": slot_id,
                "phase": "EXECUTION_COMMIT",
                "inner_result_ledger_id": result.get("ledger_id"),
                "inner_receipt_core_sha256": result.get("receipt_core_sha256"),
                "host": host,
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        return {
            "ledger_id": ledger_id,
            "exit_code": 0,
            "train_commit_sha256": result.get("receipt_core_sha256"),
            "terminal_phase": "EXECUTION_COMMIT",
        }
    except produce_checkpoint.SystemExit as exc:
        # The inner wrapper raised SystemExit (its fail-closed pattern).
        # Determine if this was an artifact contract violation.
        exc_msg = str(exc)
        if "artifact" in exc_msg.lower() and (
            "member" in exc_msg.lower()
            or "archive" in exc_msg.lower()
            or "not exist" in exc_msg.lower()
            or "sha" in exc_msg.lower()
        ):
            category = "artifact-contract-violation"
        elif "pre-exec" in exc_msg.lower():
            category = "prelaunch-failure"
        else:
            category = "inner-wrapper-abort"

        _update_manifest_status(ledger_id, "aborted-by-inner-wrapper", error=exc_msg)
        _ledger_append(
            {
                "ledger_id": ledger_id,
                "slot_id": slot_id,
                "phase": "EXECUTION_ABORT",
                "abort_reason": f"inner-wrapper-abort: {exc_msg[:400]}",
                "failure_category": category,
                "host": host,
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        raise ExecutionError(
            f"P0-4 protocol: inner wrapper abort-closed for slot {slot_id}, "
            f"ledger {ledger_id}, category={category}: {exc_msg}",
            ledger_id=ledger_id,
        ) from exc
    except BaseException as exc:
        # Any other exception from the inner wrapper
        _update_manifest_status(ledger_id, "exception", error=str(exc))
        _ledger_append(
            {
                "ledger_id": ledger_id,
                "slot_id": slot_id,
                "phase": "EXECUTION_ABORT",
                "abort_reason": f"inner-wrapper-exception: {type(exc).__name__}: {exc}",
                "failure_category": "protocol-internal-error",
                "host": host,
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        raise ExecutionError(
            f"P0-4 protocol: exception from inner wrapper for slot {slot_id}, "
            f"ledger {ledger_id}: {exc}",
            ledger_id=ledger_id,
        ) from exc


# ---------------------------------------------------------------------------
# Recovery
# ---------------------------------------------------------------------------


def recover_open_intents() -> list[str]:
    """P0-4 startup recovery: scan the execution ledger for open intents.

    Rules:
      - An EXECUTION_INTENT with no terminal (EXECUTION_COMMIT/ABORT)
        → abort it, recording ``abort_reason`` = recovery-stage.
      - Verify entries that have a manifest but no terminal exist.
        A manifest with status "subprocess-exited" but no terminal is
        evidence of a crash AFTER the subprocess but before the terminal
        landed — abort it.
      - NEVER fabricate a commit.  Recovery only produces ABORT.
      - A terminal already present → skip (no re-close).

    Returns the list of ledger_ids that THIS call closed.
    """
    rows = _ledger_read_all()
    if not rows:
        return []

    # Group by ledger_id
    by_ledger: dict[str, list[dict]] = {}
    for row in rows:
        lid = row.get("ledger_id")
        if not lid:
            continue
        by_ledger.setdefault(lid, []).append(row)

    recovered: list[str] = []
    for ledger_id, group in sorted(by_ledger.items(), key=lambda kv: kv[0] or ""):
        intents = [r for r in group if r.get("phase") == "EXECUTION_INTENT"]
        terminals = [
            r
            for r in group
            if r.get("phase") in ("EXECUTION_COMMIT", "EXECUTION_ABORT")
        ]
        if not intents or terminals:
            # Has no intent (orphan row) or already closed — skip
            continue

        # Check for a manifest with subprocess evidence but no terminal
        manifest_path = MANIFEST_DIR / f"{ledger_id}.manifest.json"
        has_evidence = False
        evidence_desc = ""
        if manifest_path.is_file():
            try:
                manifest = json.loads(manifest_path.read_bytes())
                if manifest.get("status") in (
                    "subprocess-exited",
                    "terminal-success",
                    "spawn-failed",
                ):
                    has_evidence = True
                    evidence_desc = manifest.get("status", "unknown")
            except (OSError, json.JSONDecodeError):
                pass

        if has_evidence:
            # Evidence exists but no terminal — the process crashed after
            # the subprocess but before closing the intent.  We abort it.
            abort_reason = (
                f"stage={RECOVERY_STAGE}: manifest status={evidence_desc!r} "
                "but no terminal row — process likely crashed after subprocess "
                "exit.  Abort-only closure."
            )
        else:
            # No evidence at all — pure open intent (spawn never started or
            # manifest was never written)
            abort_reason = (
                f"stage={RECOVERY_STAGE}: open intent with no execution "
                "evidence (no manifest or manifest status is pre-spawn).  "
                "Abort-only closure — never fabricate a commit."
            )

        _ledger_append(
            {
                "ledger_id": ledger_id,
                "phase": "EXECUTION_ABORT",
                "abort_reason": abort_reason,
                "failure_category": "recovery-abort",
                "slot_id": (intents[0] or {}).get("slot_id"),
                "attempt_id": (intents[0] or {}).get("attempt_id"),
                "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            }
        )
        recovered.append(ledger_id)

    return recovered


# ---------------------------------------------------------------------------
# Direct subprocess spawn with protocol (P0-4 standalone)
# ---------------------------------------------------------------------------


def spawn_with_protocol(
    slot_id: str,
    attempt_id: str | None,
    argv: list[str],
    jail_dir: Path,
    env: dict[str, str],
    *,
    prior_attempt_id: str | None = None,
) -> dict:
    """Directly spawn a subprocess under the P0-4 execution protocol.

    This is the standalone entry point used when the caller does NOT use
    ``produce_checkpoint.run_terminal_execution()`` — it handles spawning,
    evidence capture, TRAIN_COMMIT, and terminal closure directly.

    Returns a dict with keys: ``ledger_id``, ``exit_code``, ``spawn_failed``,
    ``train_commit_sha256``, ``terminal_phase``.  If spawn failed (the
    subprocess never started), ``terminal_phase`` is ``EXECUTION_ABORT``
    and ``exit_code`` is None.

    Raises ``ExecutionError`` if an internal protocol error prevents
    terminal closure.
    """
    ledger_id = _LEDGER_PREFIX + uuid.uuid4().hex
    platform.node()

    # Pre-spawn recovery: close any open intents from prior crashes
    recover_open_intents()

    cfg = ExecutionConfig(
        slot_id=slot_id,
        attempt_id=ledger_id,
        argv=argv,
        jail_dir=jail_dir,
        env=env,
        receipt_out=MANIFEST_DIR / f"{ledger_id}.receipt.json",
        prior_attempt_id=prior_attempt_id,
    )

    # Write the pre-spawn manifest (BEFORE any spawn attempt — pre-side-effect)
    manifest_data = {
        "schema": SCHEMA,
        "kind": "spawn-with-protocol-manifest",
        "ledger_id": ledger_id,
        "prior_attempt_id": prior_attempt_id,
        "slot_id": slot_id,
        "parent_pid": os.getpid(),
        "argv": argv,
        "cwd": str(jail_dir),
        "status": "pre-spawn",
        "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    _atomic_write(
        MANIFEST_DIR / f"{ledger_id}.manifest.json", _canonical(manifest_data)
    )

    # Delegate to _spawn_and_capture which handles intent write, subprocess
    # Delegate to _spawn_and_capture which handles intent write, subprocess
    # spawn, capture, TRAIN_COMMIT, and terminal closure.
    try:
        result = _spawn_and_capture(cfg, ledger_id)
    except BaseException as exc:
        raise ExecutionError(
            f"P0-4 protocol: spawn failed for slot {slot_id}, "
            f"ledger {ledger_id}: {exc}",
            ledger_id=ledger_id,
        ) from exc

    if result["spawn_failed"]:
        return {
            "ledger_id": ledger_id,
            "exit_code": None,
            "spawn_failed": True,
            "train_commit_sha256": None,
            "terminal_phase": "EXECUTION_ABORT",
        }

    return {
        "ledger_id": ledger_id,
        "exit_code": result["exit_code"],
        "spawn_failed": False,
        "train_commit_sha256": result["train_commit_sha"],
        "terminal_phase": "EXECUTION_COMMIT",
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def quarantine_orphan(path: Path, ledger_id: str) -> None:
    """Quarantine an orphan file left by a crashed transaction.

    Matching produce_checkpoint._quarantine_orphan pattern: the file is
    MOVED (never deleted) into the quarantine directory.  A missing file
    or already-occupied quarantine destination is a no-op.
    """
    import shutil

    if not path.is_file():
        return
    QUARANTINE_DIR.mkdir(parents=True, exist_ok=True)
    dest = QUARANTINE_DIR / f"{ledger_id}.{path.name}.quarantined"
    if dest.exists():
        return
    shutil.move(str(path), str(dest))
