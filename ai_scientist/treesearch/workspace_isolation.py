"""Per-node isolated working directories for the BFTS tree search.

Single source of truth for three things: how a node's exec dir is **keyed**, how
"did this node save data?" is **detected**, and how a node's dir is
**garbage-collected**. The deterministic contamination replay harness
(``tests/replay/run_contamination_harness.py``) imports the SAME functions the
production worker uses (``parallel_agent._process_node_wrapper``), so the observed
bug and its fix exercise shipped code, never a strawman copy.

Why this exists — the live bug it fixes
---------------------------------------
Baseline keys the exec dir on the POOL WORKER, not the node::

    os.path.join(cfg.workspace_dir, f"process_{worker_name}")

With a ~4-worker pool serving a ~250-node tree and NOTHING ever resetting those
dirs (no ``rmtree``/``unlink`` anywhere in ``parallel_agent.py``), a *buggy* node —
whose artifact archival move is gated on ``not is_buggy`` — leaves
``experiment_data.npy`` behind, and the NEXT node on the same worker sees it via
``os.listdir(working_dir)`` and is credited with the *previous* node's metric.
``resolve_node_workdir(..., isolated=True)`` gives every node a FRESH EMPTY dir
keyed on its own id, so a fresh node can never observe the stale ``.npy``.

Import-safety
-------------
Pure stdlib (``os``, ``shutil``, ``logging``, ``time``). No torch / numpy /
omegaconf / LLM, so the harness runs on a GPU-less, torch-less host and pytest
collection never errors (a heavy import here would surface as a collection skip).
"""

from __future__ import annotations

import logging
import os
import shutil
import time

logger = logging.getLogger(__name__)


def resolve_node_workdir(cfg_workspace_dir, child_node_id, process_name, isolated):
    """Return ``(workspace, working_dir)`` for a node's exec dir, creating it.

    ``isolated=False`` reproduces the pre-Phase-6 baseline BYTE-FOR-BYTE::

        os.path.join(cfg_workspace_dir, f"process_{process_name}")

    keyed on the pool worker name, so multiple nodes on one worker share a single
    dir — the metric-contamination vector.

    ``isolated=True`` keys on the node id instead::

        os.path.join(cfg_workspace_dir, f"node_{child_node_id}")

    one fresh dir per node, so a fresh node's ``working/`` is empty and cannot
    inherit a prior node's un-moved ``.npy``. ``working_dir`` (the child ``working/``
    subdir) is what the Phase-5 snapshot hook captures, so it still points at the
    node's own dir under isolation.
    """
    if isolated:
        workspace = os.path.join(cfg_workspace_dir, f"node_{child_node_id}")
    else:
        workspace = os.path.join(cfg_workspace_dir, f"process_{process_name}")
    working_dir = os.path.join(workspace, "working")
    os.makedirs(working_dir, exist_ok=True)
    return workspace, working_dir


def detect_saved_npy(working_dir):
    """The EXACT stale-detection predicate from ``parallel_agent.py``, extracted verbatim.

    Returns the list of ``*.npy`` files directly in ``working_dir``. On an isolated
    fresh dir this is naturally ``[]`` for a node that saved nothing; on a shared
    baseline dir it can return a PREVIOUS node's un-moved ``experiment_data.npy`` —
    the observation the replay harness is built to catch.
    """
    return [f for f in os.listdir(working_dir) if f.endswith(".npy")]


def gc_node_workdir(workspace, isolated, snapshot_id):
    """Delete a node's isolated workspace, DOUBLE-GATED on ``isolated`` AND a durable
    snapshot existing.

    Returns ``True`` iff a delete happened. NEVER deletes under baseline
    (``isolated=False``) and NEVER deletes a node that has no durable helios snapshot
    (``snapshot_id is None``) — so a node is never left without at least one
    recoverable copy, and the flag-OFF path stays byte-identical (no reset, no GC).
    The helios store lives OUTSIDE ``cfg.workspace_dir`` (constraint 6), so deleting
    ``node_<id>/`` after its snapshot is committed is fully recoverable.
    """
    if isolated and snapshot_id is not None and os.path.isdir(workspace):
        shutil.rmtree(workspace, ignore_errors=True)
        logger.info("gc_node_workdir removed %s (snapshot=%s)", workspace, snapshot_id)
        return True
    return False


def gc_bounded_node_workdirs(workspace_root, *, isolated, max_keep=64, max_age_s=None):
    """Bounded safety-net sweep over ``node_*`` dirs under ``workspace_root``.

    Per-node ``gc_node_workdir`` only fires when a durable snapshot exists; when
    helios capture is OFF but isolation is ON, the per-node dirs would otherwise grow
    UNBOUNDED (the old pool-worker keying accidentally capped them at ``num_workers``).
    This sweep re-imposes a bound: it removes the OLDEST ``node_*`` dirs beyond
    ``max_keep`` and/or older than ``max_age_s`` seconds, logging each removal and
    returning the list of removed dir names.

    Concurrency-safe by construction: with ``max_keep`` >> the pool size (default 64
    vs ~4 workers) the sweep only ever touches long-finished nodes, never the handful
    of dirs the live workers are currently executing in. Inert under baseline
    (``isolated=False``) and inert when ``workspace_root`` does not exist.
    """
    removed = []
    if not isolated or not os.path.isdir(workspace_root):
        return removed
    entries = []
    for name in os.listdir(workspace_root):
        if not name.startswith("node_"):
            continue
        path = os.path.join(workspace_root, name)
        if not os.path.isdir(path):
            continue
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            continue
        entries.append((mtime, name, path))
    entries.sort()  # oldest mtime first
    now = time.time()
    victims = []
    if max_age_s is not None:
        victims.extend(e for e in entries if now - e[0] > max_age_s)
    if max_keep is not None and len(entries) > max_keep:
        victims.extend(entries[: len(entries) - max_keep])
    seen = set()
    for _mtime, name, path in victims:
        if path in seen:
            continue
        seen.add(path)
        shutil.rmtree(path, ignore_errors=True)
        removed.append(name)
        logger.info("gc_bounded_node_workdirs removed %s", path)
    return removed
