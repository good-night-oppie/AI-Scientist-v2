"""Phase-4 acceptance tests for ``Node.snapshot_id``.

``snapshot_id`` is the worker->main handle for a helios content id. It must be a
PLAIN ``Optional[str]`` (default ``None``), emitted verbatim by ``to_dict`` (the
only channel across ``parallel_agent.py:1785 -> :2160``), tolerant of legacy
dicts / pre-change unpickled nodes, and picklable into ``checkpoint.pkl``.

The load-bearing negative test is ``test_to_dict_off_cwd_verbatim``: it contrasts
``snapshot_id`` (verbatim passthrough, off-cwd safe) against the neighbouring
``exp_results_dir`` idiom (``Path(...).resolve().relative_to(os.getcwd())``) which
raises ``ValueError`` off-cwd -- the trap ``snapshot_id`` must never copy.
"""

from __future__ import annotations

import pickle

import pytest

from ai_scientist.treesearch.journal import Node

SID = "blake3:" + "a" * 64


def test_field_plain_str_default_none():
    assert Node().snapshot_id is None
    n = Node(snapshot_id=SID)
    assert n.snapshot_id == SID
    assert isinstance(n.snapshot_id, str)


def test_to_dict_off_cwd_verbatim(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    # Verbatim passthrough even when cwd is unrelated to the id.
    assert Node(snapshot_id=SID).to_dict()["snapshot_id"] == SID
    # Contrast: the exp_results_dir idiom raises off-cwd -- the very trap the
    # snapshot_id passthrough must not reproduce.
    with pytest.raises(ValueError):
        Node(exp_results_dir="/etc").to_dict()


def test_from_dict_roundtrips_snapshot_id():
    d = Node(snapshot_id=SID).to_dict()
    assert Node.from_dict(dict(d)).snapshot_id == SID


def test_from_dict_legacy_without_key():
    d = Node().to_dict()
    del d["snapshot_id"]
    # No KeyError / TypeError; dataclass default supplies None.
    assert Node.from_dict(d).snapshot_id is None


def test_node_pickles():
    n = Node(snapshot_id=SID)
    r = pickle.loads(pickle.dumps(n))
    assert r.snapshot_id == SID
    assert r.id == n.id


def test_checkpoint_dict_pickles():
    # Mirrors agent_manager.py:262-272: Node lives nested inside the checkpoint
    # dict that is pickle.dump'd. The plain-str snapshot_id must survive.
    n = Node(snapshot_id=SID)
    checkpoint = {"journals": {"1": [n]}, "cfg": None}
    r = pickle.loads(pickle.dumps(checkpoint))
    assert r["journals"]["1"][0].snapshot_id == SID


def test_to_dict_defensive_on_unpickled_old_node():
    # A Node unpickled from a PRE-change checkpoint has no snapshot_id in
    # __dict__; to_dict must read it with getattr(..., None), not self.x.
    n = Node()
    del n.__dict__["snapshot_id"]
    assert n.to_dict()["snapshot_id"] is None
