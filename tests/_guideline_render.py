"""Render the REAL ``_prompt_impl_guideline`` method body without importing parallel_agent.

``ai_scientist.treesearch.parallel_agent`` is un-importable on this host (pulls in
``pandas`` via ``utils.data_preview``), so — exactly like the Phase-5 ``check_seam.py``
AST proof — this helper reads the file, ``ast``-extracts the ``_prompt_impl_guideline``
FunctionDef *source*, execs THAT verbatim into a tiny namespace (only ``humanize`` in
scope, which the method actually uses), and calls it against a duck-typed ``self``.

This means the prompt-gate tests (AC3) and the flag-OFF byte-identity test (AC4) exercise
the SHIPPED method body from the SHIPPED file — never a re-implemented strawman. The same
renderer generates the golden fixture from baseline ref ``96bd516`` (one-shot script), so
"equal to the golden" is a real statement about drift in the shipped guideline text.
"""

from __future__ import annotations

import ast
import textwrap
from types import SimpleNamespace

import humanize  # the sole external symbol the method body references


def _make_cfg(helios):
    """A fixed, deterministic cfg for the guideline render.

    ``num_syn_datasets == 1`` and ``k_fold_validation == 1`` deliberately keep the two
    conditional guideline branches OFF so the rendered text is a stable golden; only the
    Phase-7 ``helios`` block varies between the OFF/ON/None cases under test.
    """
    return SimpleNamespace(
        experiment=SimpleNamespace(num_syn_datasets=1),
        agent=SimpleNamespace(k_fold_validation=1),
        exec=SimpleNamespace(timeout=3600),
        helios=helios,
    )


def render_guideline(parallel_agent_path, *, helios):
    """Return the joined (``"\\n"``) impl-guideline string for the given ``helios`` cfg.

    ``helios`` is passed straight onto ``cfg.helios`` — ``None`` (flag absent), or a
    ``SimpleNamespace(enabled=..., warm_start=...)`` to drive the Phase-7 gate.
    """
    with open(parallel_agent_path, "r", encoding="utf-8") as fh:
        source = fh.read()
    tree = ast.parse(source, filename=parallel_agent_path)

    func_src = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_prompt_impl_guideline":
            func_src = ast.get_source_segment(source, node)
            break
    if func_src is None:
        raise AssertionError("_prompt_impl_guideline FunctionDef not found")

    ns = {"humanize": humanize}
    exec(textwrap.dedent(func_src), ns)  # noqa: S102 -- extracting shipped code on purpose

    fake_self = SimpleNamespace(
        cfg=_make_cfg(helios),
        evaluation_metrics="EVALUATION_METRICS_PLACEHOLDER",
    )
    result = ns["_prompt_impl_guideline"](fake_self)
    lines = result["Implementation guideline"]
    return "\n".join(lines)
