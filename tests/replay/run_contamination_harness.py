#!/usr/bin/env python3
"""Deterministic replay harness that OBSERVES the stale-`.npy` metric contamination.

The whole point of Phase 6 is to stop *inferring* the contamination bug from code
reading and instead make it FIRE on a reproducible harness, then show per-node
isolation eliminates it. To keep the observation honest, this harness imports the
**shipped** dir-keying and stale-detection helpers from
``ai_scientist.treesearch.workspace_isolation`` — the exact functions the production
worker (``parallel_agent._process_node_wrapper``) uses. Nothing about the predicate
is re-implemented here, so a green result is a statement about shipped code.

Structural replay (mirrors parallel_agent.py exactly)
-----------------------------------------------------
One pool worker (``SpawnPoolWorker-1``) processes two nodes back-to-back:

* **Node A (buggy)** writes ``experiment_data.npy`` holding a distinctive sentinel
  metric ``{"test_accuracy": 0.99}`` and is marked ``is_buggy=True``. Because the
  real archival move is gated on ``not is_buggy`` (parallel_agent.py), a buggy node
  archives NOTHING — so its ``.npy`` is **left behind** in the working dir. The
  harness reproduces that by skipping archival.
* **Node B (honest, produced no data)** writes nothing, then runs the shipped
  ``detect_saved_npy`` on its working dir. Under baseline keying both nodes share
  ``process_SpawnPoolWorker-1/working``, so B finds A's un-moved ``.npy``, loads it,
  and is credited with A's sentinel metric it never produced — contamination.

A node is ``contaminated`` iff it is credited a metric equal to A's sentinel while
having produced none itself (``true_metric is None``).

Modes
-----
``--mode baseline``  (isolated=False): A and B share one dir -> B is contaminated.
``--mode isolated``  (isolated=True):  B gets its own fresh empty ``node_<id>/`` dir
                                        -> ``detect_saved_npy`` returns ``[]`` -> clean.

Node ids are FIXED (not random) so ``baseline.json`` and ``isolated.json`` refer to
the same nodes and ``assert_delta.py`` can diff them node-for-node.
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import sys
import tempfile

import numpy as np

# Make the repo importable when run as a plain script (python tests/replay/...).
_REPO_ROOT = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

# THE SHIPPED helpers — never a local copy (AC7).
from ai_scientist.treesearch.workspace_isolation import (  # noqa: E402
    detect_saved_npy,
    resolve_node_workdir,
)

# Fixed, deterministic node ids (uuid4().hex shape: 32 lowercase hex chars).
NODE_A_ID = "0a" * 16  # buggy producer, leaves experiment_data.npy behind
NODE_B_ID = "0b" * 16  # honest, produced no data of its own
PROCESS_NAME = "SpawnPoolWorker-1"  # single worker -> A and B collide under baseline
SENTINEL = {"test_accuracy": 0.99}  # the metric A produces and B must never inherit


def _load_npy_metric(path):
    return np.load(path, allow_pickle=True).item()


def _classify(credited_metric, true_metric):
    return (
        credited_metric is not None
        and credited_metric == SENTINEL
        and true_metric is None
    )


def run(mode):
    isolated = mode == "isolated"
    root = tempfile.mkdtemp(prefix=f"contam_{mode}_")
    nodes = []
    try:
        # ---- Node A (buggy): writes the sentinel .npy, SKIPS archival ----
        ws_a, wd_a = resolve_node_workdir(root, NODE_A_ID, PROCESS_NAME, isolated)
        np.save(os.path.join(wd_a, "experiment_data.npy"), SENTINEL)
        # (Archival is gated on `not is_buggy` in parallel_agent.py; a buggy node
        #  moves nothing, so the .npy stays put. We deliberately do NOT move it.)
        detected_a = detect_saved_npy(wd_a)
        credited_a = (
            _load_npy_metric(os.path.join(wd_a, detected_a[0])) if detected_a else None
        )
        true_a = SENTINEL  # A genuinely produced this
        nodes.append(
            {
                "node_id": NODE_A_ID,
                "node_type": "buggy_producer",
                "is_buggy": True,
                "worker_dir": os.path.relpath(wd_a, root),
                "wrote_npy": True,
                "detected_npy": detected_a,
                "credited_metric": credited_a,
                "true_metric": true_a,
                "contaminated": _classify(credited_a, true_a),
            }
        )

        # ---- Node B (honest, no data): writes NOTHING, then detects ----
        ws_b, wd_b = resolve_node_workdir(root, NODE_B_ID, PROCESS_NAME, isolated)
        detected_b = detect_saved_npy(wd_b)  # baseline: sees A's leftover .npy
        credited_b = (
            _load_npy_metric(os.path.join(wd_b, detected_b[0])) if detected_b else None
        )
        true_b = None  # B produced no data of its own
        nodes.append(
            {
                "node_id": NODE_B_ID,
                "node_type": "honest_no_data",
                "is_buggy": False,
                "worker_dir": os.path.relpath(wd_b, root),
                "wrote_npy": False,
                "detected_npy": detected_b,
                "credited_metric": credited_b,
                "true_metric": true_b,
                "contaminated": _classify(credited_b, true_b),
            }
        )
    finally:
        shutil.rmtree(root, ignore_errors=True)

    return {
        "mode": mode,
        "process_name": PROCESS_NAME,
        "sentinel": SENTINEL,
        "node_a_id": NODE_A_ID,
        "node_b_id": NODE_B_ID,
        "nodes": nodes,
        "contaminated_count": sum(1 for n in nodes if n["contaminated"]),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mode", required=True, choices=["baseline", "isolated"])
    ap.add_argument("--out", required=True, help="path to write the JSON result")
    args = ap.parse_args(argv)

    result = run(args.mode)

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, sort_keys=True)
        f.write("\n")

    # Human-readable transcript (teed by the caller into harness-transcript.txt).
    print(f"=== contamination harness: mode={args.mode} ===")
    for n in result["nodes"]:
        print(
            f"  node {n['node_id'][:8]}.. type={n['node_type']:15s} "
            f"dir={n['worker_dir']:45s} detected={n['detected_npy']} "
            f"credited={n['credited_metric']} true={n['true_metric']} "
            f"contaminated={n['contaminated']}"
        )
    print(f"  contaminated_count = {result['contaminated_count']}")
    print(f"  wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
