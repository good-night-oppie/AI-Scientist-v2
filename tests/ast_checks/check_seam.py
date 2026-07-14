#!/usr/bin/env python3
"""Structural (AST) proof that the Phase-5 helios snapshot hook sits at the right seam.

Runs WITHOUT importing ``parallel_agent`` (un-importable on this host: needs
``humanize``). It ``ast.parse``s the file named in ``argv[1]``, builds a parent map
(each node -> its parent), and asserts nine invariants about the single
``snapshot_node_working_dir`` call inside ``_process_node_wrapper``:

  AC1  the ``_process_node_wrapper`` FunctionDef exists.
  AC2  ``exec_result = process_interpreter.run(child_node.code, ...)`` is located.
  AC3  ``worker_agent.parse_exec_result(...)`` is located.
  AC4  the ``if not child_node.is_buggy:`` archival gate is located.
  AC5  EXACTLY ONE call to ``snapshot_node_working_dir`` exists in the function.
  AC6  that call is the RHS of an assign to ``child_node.snapshot_id`` (plain str,
       no ``Path().relative_to()`` wrapper -- constraint 6).
  AC7  its lineno is AFTER the exec/cleanup and BEFORE the metric parse (recon Section 2).
  AC8  its lineno is BEFORE the ``if not is_buggy`` gate AND the gate is NOT an
       ancestor of the call -- the buggy-node black-hole escape (the single most
       important structural invariant of the phase).
  AC9  one arg is ``working_dir`` and none is ``workspace`` / ``idea_dir`` / a repo-root
       string literal (constraint 8: commit only the node's ``working/`` dir).

Each check writes ``AC<n>: PASS <detail>`` to stdout; any failure raises
``SystemExit("AC<n> FAIL: ...")`` (exit 1). Output uses ``sys.stdout.write`` (never
``print``) to keep the Phase-5 cleanliness grep green.
"""

from __future__ import annotations

import ast
import sys


def _emit(n: int, msg: str) -> None:
    sys.stdout.write("AC%d: PASS %s\n" % (n, msg))


def _fail(n: int, msg: str) -> None:
    raise SystemExit("AC%d FAIL: %s" % (n, msg))


def _is_name(node, name: str) -> bool:
    return isinstance(node, ast.Name) and node.id == name


def _is_attr(node, attr: str, val_name=None) -> bool:
    return (
        isinstance(node, ast.Attribute)
        and node.attr == attr
        and (val_name is None or _is_name(node.value, val_name))
    )


def main(argv) -> int:
    if len(argv) < 2:
        _fail(0, "usage: check_seam.py <path-to-parallel_agent.py>")
    path = argv[1]
    with open(path) as fh:
        tree = ast.parse(fh.read(), filename=path)

    # Parent map: id(child) -> parent node, for the ancestor test in AC8.
    parents = {}
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            parents[id(child)] = node

    def is_ancestor(anc, node) -> bool:
        cur = node
        while id(cur) in parents:
            cur = parents[id(cur)]
            if cur is anc:
                return True
        return False

    # --- AC1: the single funnel FunctionDef ---------------------------------------
    func = None
    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) and node.name == "_process_node_wrapper":
            func = node
            break
    if func is None:
        _fail(1, "FunctionDef '_process_node_wrapper' not found")
    _emit(1, "FunctionDef '_process_node_wrapper' at line %d" % func.lineno)
    body_nodes = list(ast.walk(func))

    # --- AC2: exec_result = process_interpreter.run(child_node.code, ...) ----------
    exec_lineno = None
    for n in body_nodes:
        if isinstance(n, ast.Assign) and any(
            _is_name(t, "exec_result") for t in n.targets
        ):
            v = n.value
            if (
                isinstance(v, ast.Call)
                and _is_attr(v.func, "run", "process_interpreter")
                and v.args
                and _is_attr(v.args[0], "code", "child_node")
            ):
                exec_lineno = n.lineno
                break
    if exec_lineno is None:
        _fail(
            2, "exec_result = process_interpreter.run(child_node.code, ...) not found"
        )
    _emit(2, "exec_result run(child_node.code) at line %d" % exec_lineno)

    # --- AC3: worker_agent.parse_exec_result(...) ---------------------------------
    parse_lineno = None
    for n in body_nodes:
        if isinstance(n, ast.Call) and _is_attr(
            n.func, "parse_exec_result", "worker_agent"
        ):
            parse_lineno = n.lineno
            break
    if parse_lineno is None:
        _fail(3, "worker_agent.parse_exec_result(...) not found")
    _emit(3, "worker_agent.parse_exec_result(...) at line %d" % parse_lineno)

    # --- AC4: the `if not child_node.is_buggy:` archival gate ----------------------
    gate_node = None
    gate_lineno = None
    for n in body_nodes:
        if isinstance(n, ast.If):
            t = n.test
            if (
                isinstance(t, ast.UnaryOp)
                and isinstance(t.op, ast.Not)
                and _is_attr(t.operand, "is_buggy", "child_node")
            ):
                gate_node = n
                gate_lineno = n.lineno
                break
    if gate_node is None:
        _fail(4, "`if not child_node.is_buggy:` archival gate not found")
    _emit(4, "`if not child_node.is_buggy:` gate at line %d" % gate_lineno)

    # --- AC5: EXACTLY ONE snapshot_node_working_dir call ---------------------------
    snap_calls = []
    for n in body_nodes:
        if isinstance(n, ast.Call):
            f = n.func
            if (isinstance(f, ast.Name) and f.id == "snapshot_node_working_dir") or (
                isinstance(f, ast.Attribute) and f.attr == "snapshot_node_working_dir"
            ):
                snap_calls.append(n)
    if len(snap_calls) != 1:
        _fail(
            5,
            "expected exactly 1 snapshot_node_working_dir call, found %d"
            % len(snap_calls),
        )
    snap_call = snap_calls[0]
    _emit(5, "exactly one snapshot_node_working_dir call at line %d" % snap_call.lineno)

    # --- AC6: RHS of assign to child_node.snapshot_id (plain str) ------------------
    parent = parents.get(id(snap_call))
    assign_ok = False
    if isinstance(parent, ast.Assign) and parent.value is snap_call:
        assign_ok = len(parent.targets) == 1 and _is_attr(
            parent.targets[0], "snapshot_id", "child_node"
        )
    elif isinstance(parent, ast.AnnAssign) and parent.value is snap_call:
        assign_ok = _is_attr(parent.target, "snapshot_id", "child_node")
    if not assign_ok:
        _fail(
            6,
            "snapshot call is not the RHS of an assign to child_node.snapshot_id "
            "(parent=%s)" % type(parent).__name__,
        )
    _emit(6, "call is RHS of assign to child_node.snapshot_id (no relative_to wrapper)")

    # --- AC7: after exec/cleanup, before the metric parse --------------------------
    if not (exec_lineno < snap_call.lineno < parse_lineno):
        _fail(
            7,
            "placement wrong: need exec(%d) < snap(%d) < parse(%d)"
            % (exec_lineno, snap_call.lineno, parse_lineno),
        )
    _emit(
        7,
        "exec(%d) < snap(%d) < parse(%d)"
        % (exec_lineno, snap_call.lineno, parse_lineno),
    )

    # --- AC8: outside the `if not is_buggy:` archival gate -------------------------
    if snap_call.lineno >= gate_lineno:
        _fail(8, "snap(%d) is not before gate(%d)" % (snap_call.lineno, gate_lineno))
    if is_ancestor(gate_node, snap_call):
        _fail(8, "snap call is nested INSIDE the `if not is_buggy:` gate (black hole)")
    _emit(
        8,
        "snap(%d) < gate(%d) and gate is NOT an ancestor -> buggy nodes snapshotted"
        % (snap_call.lineno, gate_lineno),
    )

    # --- AC9: commits working_dir only, never workspace/idea_dir/repo-root ---------
    arg_names = []
    literal_args = []
    all_arg_values = list(snap_call.args) + [kw.value for kw in snap_call.keywords]
    for a in all_arg_values:
        if isinstance(a, ast.Name):
            arg_names.append(a.id)
        elif isinstance(a, ast.Constant) and isinstance(a.value, str):
            literal_args.append(a.value)
    if "working_dir" not in arg_names:
        _fail(9, "no `working_dir` argument in the snapshot call; args=%r" % arg_names)
    forbidden = {"workspace", "idea_dir", "workspace_dir"} & set(arg_names)
    if forbidden:
        _fail(9, "forbidden root argument(s) passed to commit: %r" % sorted(forbidden))
    if literal_args:
        _fail(9, "string-literal path arg(s) (possible repo root): %r" % literal_args)
    _emit(9, "arg is working_dir; no workspace/idea_dir/repo-root arg (constraint 8)")

    sys.stdout.write("SEAM_AST_OK %s\n" % path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
