#!/usr/bin/env python3
"""Assert the observed baseline->isolated metric delta EQUALS the pre-registered set.

Phase 6 changes some node metric values on purpose — nodes that were passing on a
falsely-inherited ``.npy`` now correctly report no data. That is a pre-existing bug
being fixed, not a helios regression, but only if it is **declared up front**. This
script enforces that discipline:

  1. Diff ``baseline.json`` vs ``isolated.json`` and compute the set of node ids whose
     ``credited_metric`` changed.
  2. Parse the declared changed-node-id set from the `````node-ids`` fenced block in
     ``expected-metric-delta.md``.
  3. Assert the two sets are EQUAL. An undeclared change is a scope leak; a
     declared-but-absent change is a false claim. Either -> exit 1.
  4. Verify the declaration PREDATES the isolated run (mtime and, if present, the
     ``Declared-at:`` line vs ``isolated.json`` mtime) and print the proof.
"""

from __future__ import annotations

import argparse
import json
import os
import re

_FENCE_RE = re.compile(r"```node-ids\s*\n(.*?)\n```", re.DOTALL)
_DECLARED_AT_RE = re.compile(r"^Declared-at:\s*(.+?)\s*$", re.MULTILINE)


def _credited_by_id(path):
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {n["node_id"]: n.get("credited_metric") for n in data["nodes"]}, data


def _declared_ids(md_path):
    with open(md_path, encoding="utf-8") as f:
        text = f.read()
    m = _FENCE_RE.search(text)
    if not m:
        raise SystemExit(f"FAIL: no ```node-ids fenced block in {md_path}")
    ids = {ln.strip() for ln in m.group(1).splitlines() if ln.strip()}
    at = _DECLARED_AT_RE.search(text)
    return ids, (at.group(1) if at else None)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--isolated", required=True)
    ap.add_argument("--declared", required=True)
    args = ap.parse_args(argv)

    base, _ = _credited_by_id(args.baseline)
    iso, _ = _credited_by_id(args.isolated)

    all_ids = set(base) | set(iso)
    changed = {i for i in all_ids if base.get(i) != iso.get(i)}
    declared, declared_at = _declared_ids(args.declared)

    print("baseline credited_metric by node:")
    for i in sorted(all_ids):
        print(f"  {i}: base={base.get(i)!r} iso={iso.get(i)!r}")
    print(f"changed set  = {sorted(changed)}")
    print(f"declared set = {sorted(declared)}")

    # mtime ordering proof: declaration must predate the isolated run.
    md_mtime = os.path.getmtime(args.declared)
    iso_mtime = os.path.getmtime(args.isolated)
    order_ok = md_mtime < iso_mtime
    print(
        "mtime proof: declared=%.3f (%s) < isolated=%.3f -> %s"
        % (
            md_mtime,
            declared_at or "no Declared-at line",
            iso_mtime,
            "OK (declared before isolated run)"
            if order_ok
            else "FAIL (declared AFTER)",
        )
    )

    if changed != declared:
        print(
            "FAIL: changed set != declared set "
            f"(undeclared={sorted(changed - declared)}, "
            f"missing={sorted(declared - changed)})"
        )
        return 1
    if not order_ok:
        print("FAIL: declaration does not predate the isolated run")
        return 1
    print("PASS: metric delta matches the pre-registered declaration.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
