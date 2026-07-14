"""One-shot generator for tests/fixtures/baseline_journal.json.

Regeneration note (run on BASELINE journal.py, i.e. BEFORE the Phase-4
`snapshot_id` field is added, so the emitted key set is the pre-change one):

    .venv-test/bin/python tests/_gen_baseline_journal.py

Builds three genuinely path-free `Node`s and dumps `{"nodes":[n.to_dict()...]}`.
Path-free means `exp_results_dir=None`, `plot_paths=[]`, `plot_analyses=[]` so no
`Path(...).resolve().relative_to(os.getcwd())` transform ever runs on
re-serialization -- the additive-only comparison is then deterministic regardless
of cwd. The three nodes mirror a small real tree:

  * A -- draft, is_buggy=False, concrete metric, root (parent_id null)
  * B -- buggy child of A, is_buggy=True, all-None metric
  * C -- improve child of A, is_buggy=False, concrete metric

`children` on A is written SORTED so the committed fixture is independent of the
generating process's string-hash seed (Node.__hash__ hashes the id).
"""

from __future__ import annotations

import json
import os

from ai_scientist.treesearch.journal import Node
from ai_scientist.treesearch.utils.metric import MetricValue

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURE = os.path.join(_REPO_ROOT, "tests", "fixtures", "baseline_journal.json")


def build_nodes():
    a = Node(
        plan="draft plan A",
        overall_plan="overall plan",
        code="print('A')",
        step=0,
        is_buggy=False,
        is_buggy_plots=False,
        metric=MetricValue(value=0.9, maximize=True, name="acc", description="x"),
        analysis="analysis A",
    )
    b = Node(
        parent=a,
        plan="debug plan B",
        overall_plan="overall plan",
        code="print('B')",
        step=1,
        is_buggy=True,
        is_buggy_plots=False,
        metric=MetricValue(value=None, maximize=None, name=None, description=None),
        analysis="analysis B",
    )
    c = Node(
        parent=a,
        plan="improve plan C",
        overall_plan="overall plan",
        code="print('C')",
        step=2,
        is_buggy=False,
        is_buggy_plots=False,
        metric=MetricValue(value=0.95, maximize=True, name="acc", description="x"),
        analysis="analysis C",
    )
    return a, b, c


def main():
    a, b, c = build_nodes()
    da, db, dc = a.to_dict(), b.to_dict(), c.to_dict()
    # Deterministic child ordering (string-hash seed independent).
    da["children"] = sorted(da["children"])
    db["children"] = sorted(db["children"])
    dc["children"] = sorted(dc["children"])
    payload = {"nodes": [da, db, dc]}
    with open(_FIXTURE, "w") as f:
        json.dump(payload, f, indent=2, sort_keys=True)
        f.write("\n")
    print(f"wrote {_FIXTURE} with {len(payload['nodes'])} nodes")
    # Sanity: the baseline key set must NOT contain snapshot_id.
    assert "snapshot_id" not in da, "generator was run on POST-change journal.py"
    print("baseline key set confirmed (no snapshot_id)")


if __name__ == "__main__":
    main()
