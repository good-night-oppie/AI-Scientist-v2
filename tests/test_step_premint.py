"""AC2 -- the pre-minted child_node_id is per-future, non-None, and distinct.

Drives the REAL ``ParallelAgent.step`` (never a re-implementation) with a recorder
executor and a fake ``self``, and asserts that each ``executor.submit`` receives a
distinct, non-None ``child_node_id`` as its LAST positional arg — after ``seed_eval``.

``parallel_agent`` pulls in heavy optional deps (pandas, genson, ...) that are absent
on this GPU-less/torch-less host, so we stub exactly the missing third-party modules
in ``sys.modules`` before importing it. Real modules (numpy, dataclasses_json, ...)
are never stubbed — the retry loop only stubs a name that actually raises
``ModuleNotFoundError``.
"""

from __future__ import annotations

import importlib
import sys
import types
from unittest import mock

import pytest


def _load_parallel_agent():
    heavy = set()
    for _ in range(80):
        for name in list(heavy):
            sys.modules.setdefault(name, mock.MagicMock())
        try:
            return importlib.import_module("ai_scientist.treesearch.parallel_agent")
        except ModuleNotFoundError as exc:  # noqa: PERF203
            if not exc.name or exc.name in heavy:
                raise
            heavy.add(exc.name)
    raise RuntimeError("could not stub-import parallel_agent")


class _RecorderExecutor:
    """Records submit() args and returns a future whose result() times out.

    ``step()`` catches ``TimeoutError`` and continues, so no node body ever runs —
    we only observe what was submitted."""

    def __init__(self):
        self.calls = []

    def submit(self, fn, *args):
        self.calls.append(args)
        fut = mock.Mock()
        fut.result.side_effect = TimeoutError("stubbed: not executed")
        return fut


def _fake_agent(parallel_agent, executor, n_nodes):
    ParallelAgent = parallel_agent.ParallelAgent
    return types.SimpleNamespace(
        _select_parallel_nodes=lambda: [None] * n_nodes,  # None => fresh draft
        cfg=types.SimpleNamespace(agent={}),  # cfg.agent.get("summary", None) -> None
        journal=types.SimpleNamespace(generate_summary=lambda **k: ""),
        gpu_manager=None,
        stage_name=None,  # short-circuits the stage-2/4 branches (no node_data[...] deref)
        best_stage1_node=None,
        best_stage2_node=None,
        best_stage3_node=None,
        executor=executor,
        timeout=1,
        task_desc="t",
        evaluation_metrics=None,
        _process_node_wrapper=ParallelAgent._process_node_wrapper,
        _update_hyperparam_tuning_state=lambda node: None,
        _update_ablation_state=lambda node: None,
    )


@pytest.mark.parametrize("n_nodes", [1, 3, 7])
def test_step_premints_distinct_non_none_child_ids(n_nodes):
    pa = _load_parallel_agent()
    rec = _RecorderExecutor()
    fake = _fake_agent(pa, rec, n_nodes)

    pa.ParallelAgent.step(fake, exec_callback=None)

    assert len(rec.calls) == n_nodes
    ids = [args[-1] for args in rec.calls]  # child_node_id is the LAST positional arg
    assert all(i is not None for i in ids), ids
    assert len(set(ids)) == len(ids) == n_nodes  # mutually distinct
    # seed_eval must be the arg immediately before child_node_id (append-at-end proof).
    assert all(args[-2] is False for args in rec.calls)
