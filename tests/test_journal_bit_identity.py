"""Phase-4 acceptance test: flag-OFF serialization is ADDITIVE-ONLY vs baseline.

Adding ``snapshot_id`` to ``to_dict`` adds exactly one key -- ``"snapshot_id":
null`` -- to every node's serialized dict; every pre-existing key is unchanged.
That is the honest, falsifiable form of "bit-identical to baseline": not a literal
empty byte-diff, but a single additive key with value ``None`` on the OFF path.

Two halves:
  * ``test_journal_additive_only`` -- per node, ``from_dict(...).to_dict()`` gains
    exactly ``{"snapshot_id"}`` (value ``None``) and every non-relationship key is
    byte-equal. Relationship keys (``parent_id``/``children``) are excluded: they
    are reconstructed from journal context, orthogonal to this plumbing.
  * the transcript half -- rebuild a whole ``Journal`` from the fixture, reserialize,
    strip ``snapshot_id``, and diff against the baseline fixture. With the flag OFF
    the diff is EMPTY. The (empty) diff is written to the M4 evidence dir.
"""

from __future__ import annotations

import copy
import difflib
import json
import os

from ai_scientist.treesearch.journal import Journal, Node

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_FIXTURE = os.path.join(_REPO_ROOT, "tests", "fixtures", "baseline_journal.json")
_EVIDENCE_DIR = os.path.join(_REPO_ROOT, ".supergoal", "evidence", "M4")
_DIFF_OUT = os.path.join(_EVIDENCE_DIR, "journal_bit_identity.diff")

_RELATIONSHIP_KEYS = {"parent_id", "children"}


def _load_fixture():
    with open(_FIXTURE) as f:
        return json.load(f)


def test_journal_additive_only():
    fixture = _load_fixture()
    assert fixture["nodes"], "fixture has no nodes"
    for d in fixture["nodes"]:
        rd = Node.from_dict(copy.deepcopy(d)).to_dict()
        # Exactly one new key, and it is snapshot_id with value None.
        assert set(rd) - set(d) == {"snapshot_id"}
        assert rd["snapshot_id"] is None
        # Every pre-existing non-relationship key is byte-equal.
        for k in d:
            if k in _RELATIONSHIP_KEYS:
                continue
            assert rd[k] == d[k], f"key {k!r} changed: {d[k]!r} -> {rd[k]!r}"


def _normalize(nodes):
    """Strip snapshot_id and sort children so the compare is seed-independent."""
    out = []
    for n in nodes:
        n = dict(n)
        n.pop("snapshot_id", None)
        n["children"] = sorted(n["children"])
        out.append(n)
    return out


def test_journal_reserialize_additive_only_diff_empty():
    fixture = _load_fixture()
    # Rebuild the whole tree through a Journal so parent/child relationships are
    # reconstructed exactly (append in fixture order; from_dict links to parents).
    journal = Journal()
    for d in fixture["nodes"]:
        journal.append(Node.from_dict(copy.deepcopy(d), journal))
    reserialized = journal.to_dict()

    base_norm = _normalize(fixture["nodes"])
    reser_norm = _normalize(reserialized["nodes"])

    base_text = json.dumps(base_norm, indent=2, sort_keys=True).splitlines(
        keepends=True
    )
    reser_text = json.dumps(reser_norm, indent=2, sort_keys=True).splitlines(
        keepends=True
    )
    diff = "".join(
        difflib.unified_diff(
            base_text,
            reser_text,
            fromfile="baseline_journal.json (fixture)",
            tofile="flag-OFF reserialization (snapshot_id stripped)",
        )
    )
    os.makedirs(_EVIDENCE_DIR, exist_ok=True)
    with open(_DIFF_OUT, "w") as f:
        f.write(diff)
    assert diff == "", f"flag-OFF reserialization diverged from baseline:\n{diff}"
