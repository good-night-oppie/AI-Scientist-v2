"""Audited single chokepoint for every helios snapshot-engine CLI call.

This wrapper exists so that the ~5 later call sites in the BFTS tree search never
have to re-handle the verified CLI landmines individually (any one omission
silently breaks a multi-hour run with no error). It is deliberately **pure
stdlib** and **import-safe**: importing this module pulls in nothing heavy
(no torch / numpy / anthropic / omegaconf) and never touches the filesystem or a
subprocess. The helios binary is only required at ``HeliosStore`` construction,
never at import, so an install without helios keeps working.

Landmines encoded here (all empirically verified against helios HEAD):

* The CLI prints ``{"snapshot_id": "blake3:<64hex>"}`` to **stdout** on success
  (``cli.go:84-87``). The README's own ``stdout.decode().strip()`` example would
  return the whole JSON object string and poison every node id -- so we parse the
  JSON key, never the raw line.
* On a nonzero exit the real cause is on **stderr** and stdout is **empty**
  (``main.go:148-151``); an unguarded ``json.loads`` would raise
  ``JSONDecodeError`` and mask it. ``_run`` raises ``HeliosCommandError`` *before*
  any parse. Exit 1 = operational, exit 2 = programming error (unknown verb / bad
  flag) -- both surface loudly.
* Store resolution is cwd-dependent and inconsistent between ``commit`` and
  ``materialize`` (``storeutil.go:24-30``); we pin ``HELIOS_STORE_DIR`` to an
  absolute path on **every** call so round-trips never depend on cwd.
* Pebble is a single-writer store (``objstore.go:62``); BFTS workers are separate
  **processes**, so a ``threading.Lock`` serializes nothing. We use
  ``fcntl.flock`` on a lockfile that is a **sibling** of the store dir.
* Reconstruction uses ``materialize --id X --out <fresh empty dir>`` exclusively;
  the merge-style read primitive that never deletes stale files is never invoked,
  and ``materialize`` refuses a non-empty out dir at the boundary.
"""

from __future__ import annotations

import fcntl
import json
import logging
import os
import re
import subprocess

logger = logging.getLogger(__name__)

# A helios snapshot id is a content hash: the literal prefix "blake3:" followed by
# 64 lowercase hex chars. Keep it a plain str -- never a Path, never .relative_to().
_SNAPSHOT_ID_RE = re.compile(r"^blake3:[0-9a-f]{64}$")


class HeliosError(Exception):
    """Base class for every failure raised by this wrapper."""


class HeliosUnavailableError(HeliosError):
    """The helios binary is missing, not executable, or otherwise unusable.

    Raised only at ``HeliosStore`` construction (or from ``available()``), never at
    import time -- helios is an optional dependency.
    """


class HeliosCommandError(HeliosError):
    """The CLI exited nonzero. Carries argv + returncode + captured streams.

    Exit-code map: 1 == operational failure (e.g. unknown snapshot), 2 ==
    programming error (unknown verb / bad flag). stdout is empty on failure, so
    callers must never ``json.loads`` it -- this exception is raised first.
    """

    def __init__(self, argv, returncode, stdout, stderr):
        self.argv = argv
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr
        kind = {1: "operational", 2: "programming-error"}.get(returncode, "unknown")
        super().__init__(
            f"helios {argv[1] if len(argv) > 1 else '?'} exited {returncode} "
            f"({kind}); stderr={stderr.strip()!r}"
        )


def _parse_snapshot_id(stdout: str) -> str:
    """Extract the snapshot id from a success-path stdout JSON object.

    Only ever reached when returncode == 0 (``_run`` raises first otherwise), so
    ``stdout`` is a real ``{"snapshot_id": ...}`` object here, never empty.
    """
    obj = json.loads(stdout)
    sid = obj["snapshot_id"]  # KeyError -> HeliosError below, never a bare .strip()
    if not isinstance(sid, str) or not _SNAPSHOT_ID_RE.match(sid):
        raise HeliosError(f"malformed snapshot_id: {sid!r}")
    return sid


class HeliosStore:
    """Thin, audited wrapper over the helios CLI. One instance == one store dir.

    Construct one per (binary, store_dir). Cheap to construct and picklable-free:
    it holds only strings and a float, so a fresh cold instance can be built inside
    each forked BFTS worker (which is exactly what the concurrency contract needs).
    """

    def __init__(self, helios_bin, store_dir, lock_path=None, timeout=120.0):
        if not os.path.isabs(helios_bin):
            raise HeliosUnavailableError(
                f"helios_bin must be an absolute path: {helios_bin!r}"
            )
        if not (os.path.isfile(helios_bin) and os.access(helios_bin, os.X_OK)):
            raise HeliosUnavailableError(
                f"helios binary missing or not executable: {helios_bin!r}"
            )
        if not os.path.isabs(store_dir):
            raise ValueError(f"store_dir must be an absolute path: {store_dir!r}")

        self.helios_bin = helios_bin
        # Normalize to an absolute, canonical path so HELIOS_STORE_DIR is pinned
        # identically on every call regardless of the caller's cwd.
        self.store_dir = os.path.abspath(store_dir)
        os.makedirs(self.store_dir, exist_ok=True)
        # The lockfile is a SIBLING of the store dir, never a child: a lockfile
        # inside store_dir would sit under Pebble's directory, and a lockfile
        # inside a --work dir would be ingested by commit.
        self.lock_path = (
            lock_path
            if lock_path is not None
            else self.store_dir.rstrip("/") + ".flock"
        )
        self.timeout = timeout

    # -- low-level runners -------------------------------------------------------

    def _run(self, args):
        """Run the CLI with HELIOS_STORE_DIR pinned; raise on nonzero exit.

        The nonzero branch raises *before* any JSON parse, so an exit-1 empty
        stdout can never reach ``json.loads``.
        """
        env = os.environ.copy()
        env["HELIOS_STORE_DIR"] = self.store_dir  # constraint 3/6, storeutil.go:24-30
        cp = subprocess.run(
            [self.helios_bin, *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=self.timeout,
        )
        if cp.returncode != 0:  # constraint 9: DO NOT json.loads on failure
            raise HeliosCommandError(
                [self.helios_bin, *args], cp.returncode, cp.stdout, cp.stderr
            )
        return cp

    def _locked_run(self, args):
        """Serialize a store-touching call behind a blocking exclusive flock.

        ``LOCK_EX`` (not ``LOCK_NB``) so concurrent cold worker processes queue
        instead of erroring -- this is what turns Pebble's single-writer exit-1
        into a wait. The ``finally`` guarantees release even when ``_run`` raises,
        so an error in one call cannot deadlock the next.
        """
        fd = os.open(self.lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)  # blocks; workers serialize, none fail
            return self._run(args)
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    # -- public API --------------------------------------------------------------

    def snapshot(self, work_dir) -> str:
        """Commit ``work_dir`` and return its plain-str snapshot id.

        Constraint 8: the caller points ``work_dir`` at the node's ``working/``
        dir; this wrapper forwards exactly that path and never walks upward
        (``commit`` reads every regular file whole into RAM, skipping only
        ``.git/`` and ``.helios/``).
        """
        if not os.path.isabs(work_dir):
            raise ValueError(f"work_dir must be an absolute path: {work_dir!r}")
        if not os.path.isdir(work_dir):
            raise ValueError(f"work_dir does not exist: {work_dir!r}")
        cp = self._locked_run(["commit", "--work", work_dir])
        return _parse_snapshot_id(cp.stdout)

    def materialize(self, snapshot_id, out_dir) -> None:
        """Reconstruct a snapshot into a FRESH EMPTY ``out_dir``.

        Refuses a non-empty ``out_dir`` at the boundary (before any subprocess) so
        we never merge into a dirty dir -- this closes the stale-file hole at the
        wrapper level even though the merge primitive is never called.
        """
        if not isinstance(snapshot_id, str) or not _SNAPSHOT_ID_RE.match(snapshot_id):
            raise ValueError(f"malformed snapshot_id: {snapshot_id!r}")  # constraint 2
        if os.path.isdir(out_dir) and os.listdir(out_dir):
            raise ValueError("materialize requires a fresh empty out dir")
        os.makedirs(out_dir, exist_ok=True)
        self._locked_run(["materialize", "--id", snapshot_id, "--out", out_dir])
        return None

    def available(self) -> bool:
        """Cheap probe: True iff ``version`` exits 0. Never raises.

        Used by the guarded-import path in later phases to decide whether helios
        checkpointing is active this run.
        """
        try:
            self._run(["version"])
            return True
        except (HeliosCommandError, OSError, subprocess.TimeoutExpired):
            return False

    # -- static helpers for the Phase 4/5 call sites -----------------------------

    @staticmethod
    def default_store_dir(log_dir: str) -> str:
        """The store's natural home: ``<abs log_dir>/helios_store``.

        ``log_dir`` (not ``workspace_dir``) is used because the workspace is
        rmtree'd on every exit -- a store under it would be destroyed each run.
        """
        return os.path.join(os.path.abspath(log_dir), "helios_store")

    @staticmethod
    def assert_store_outside_workspace(store_dir, workspace_dir):
        """Guard: the store must not live inside the workspace (constraint 3).

        The ``atexit`` rmtree of ``workspace_dir`` would otherwise destroy the
        store on every run. Raises ``ValueError`` when ``store_dir`` equals or is
        nested under ``workspace_dir``; returns ``None`` when it is safely outside.
        """
        s, w = os.path.abspath(store_dir), os.path.abspath(workspace_dir)
        if s == w or s.startswith(w.rstrip("/") + "/"):
            raise ValueError(
                f"HELIOS_STORE_DIR {s} is inside workspace_dir {w}; "
                "the atexit rmtree would destroy the store"
            )


def snapshot_node_working_dir(cfg, working_dir, *, node_id=None):
    """Write-only provenance hook for the BFTS snapshot seam (parallel_agent.py:1527).

    Commit ``working_dir`` (the node's post-exec ``working/`` dir) to the helios store
    and return its snapshot id string (``"blake3:<64hex>"``). Runs for EVERY node,
    buggy or not -- buggy nodes are the reproducibility black hole this hook exists to
    close (today they archive nothing and get ``exp_results_dir=None``).

    Duck-typed on purpose: it reads ``cfg.helios`` and ``working_dir`` by plain
    attribute/path access so the replay harness can drive the REAL function with a
    ``SimpleNamespace`` cfg, without importing config/journal (both un-importable on
    this host).

    Contract (all load-bearing):
      * NO-OP -> ``None`` if helios is disabled/absent: ``getattr(cfg, "helios", None)
        is None`` OR ``not helios.enabled``. No subprocess is spawned in that case.
      * NEVER RAISES into the caller. Any failure (missing/relative binary, exit 1 with
        empty stdout, JSONDecodeError, unresolvable store, malformed id) is caught,
        logged at WARNING, and turned into ``None``. A write-only hook that throws would
        kill the node result at :1785 and REGRESS the search -- the inverse of this
        phase's guarantee.
      * Commits ONLY ``working_dir`` (constraint 8: ``commit`` ignores .gitignore and
        reads every regular file whole into RAM -- never point it at
        workspace/idea_dir/repo root).
      * Delegates the CLI call to :class:`HeliosStore` -- the single audited chokepoint
        (stdout-JSON parse per constraint 9, ``flock`` per constraint 4, pinned
        ``HELIOS_STORE_DIR`` per constraint 6, materialize-only read discipline).
        Returns a PLAIN ``str``; the caller assigns it directly to
        ``child_node.snapshot_id`` (constraint 6 -- never through
        ``Path().resolve().relative_to(os.getcwd())``).
    """
    helios = getattr(cfg, "helios", None)
    if helios is None or not getattr(helios, "enabled", False):
        return None
    try:
        if not os.path.isdir(working_dir):
            return None
        # Forward whatever Phase 4's HeliosConfig defined; HeliosStore validates that
        # binary_path/store_dir are absolute+usable and raises loudly otherwise -- which
        # this except turns into a graceful None, never a propagated exception.
        lock_path = getattr(helios, "lock_file", None) or getattr(
            helios, "lock_path", None
        )
        store = HeliosStore(
            getattr(helios, "binary_path", None),
            getattr(helios, "store_dir", None),
            lock_path=lock_path,
        )
        return store.snapshot(working_dir)
    except (
        Exception
    ) as e:  # belt-and-suspenders: a write-only hook must never propagate
        logger.warning(
            "helios snapshot skipped (node=%s dir=%s): %s", node_id, working_dir, e
        )
        return None


def materialize(snapshot_id, out_dir, cfg):
    """Reconstruct a snapshot into a FRESH EMPTY ``out_dir`` (the reproduction path).

    The read-side counterpart to :func:`snapshot_node_working_dir`, exposed at module
    scope so the replay harness can import it alongside the write hook. Duck-typed on
    ``cfg.helios`` (``binary_path`` / ``store_dir`` / optional ``lock_file``) exactly
    like the write hook.

    Unlike the write hook this DOES surface errors -- the reproduction path is where a
    byte-for-byte proof must fail loudly rather than silently return a wrong dir.
    Constraint 5: this delegates to :meth:`HeliosStore.materialize`, which shells out to
    ``materialize --id X --out <fresh empty dir>`` and NEVER to the merge-style
    read verb (which never deletes stale files and would leak sibling-branch content).
    """
    helios = getattr(cfg, "helios", None)
    if helios is None:
        raise HeliosUnavailableError("cfg.helios is None; cannot materialize")
    lock_path = getattr(helios, "lock_file", None) or getattr(helios, "lock_path", None)
    store = HeliosStore(
        getattr(helios, "binary_path", None),
        getattr(helios, "store_dir", None),
        lock_path=lock_path,
    )
    return store.materialize(snapshot_id, out_dir)
