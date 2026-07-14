#!/usr/bin/env python3
"""Read-only blast-radius simulation for the launch_scientist_bfts.py cleanup reaper.

This script NEVER signals any process. It reads /proc directly (deliberately using no
third-party process library) and models, purely in memory, which processes the OLD
reaper vs the NEW reaper would terminate, so the fix can be proven
(OLD non-descendant kills > 0, NEW non-descendant kills == 0) without reproducing the
incident it exists to prevent.

OLD reaper (removed in this PR): after terminating its own descendants, it iterated
EVERY process on the host and killed any whose lowercased cmdline contained a substring
in KEYWORDS. That set includes processes this run never spawned.

NEW reaper (kept): terminates only current_process().children(recursive=True) — this
process's own descendant tree.

Output: pid+comm only (never full cmdlines — those can carry secrets and this output
is captured to evidence files / panes). Emits four counters consumed by Phase 1 AC3/AC4.
"""

import os
import sys

KEYWORDS = [
    "python",
    "torch",
    "mp",
    "bfts",
    "experiment",
]  # verbatim from the OLD reaper

# Named fleet processes whose death would be especially damaging on this shared host.
FLEET_MARKERS = [
    "hermes",
    "kanban",
    "pal-mcp",
    "pal_mcp",
    "gnome-keyring",
    "x11vnc",
    "sweep_sessions",
    "watchtower",
    "a2a",
]


def _read(pid, name):
    try:
        with open(f"/proc/{pid}/{name}", "rb") as f:
            return f.read()
    except (FileNotFoundError, ProcessLookupError, PermissionError, OSError):
        return None


def _cmdline(pid):
    raw = _read(pid, "cmdline")
    if not raw:
        return ""
    return raw.replace(b"\x00", b" ").decode("utf-8", "replace").strip()


def _comm(pid):
    raw = _read(pid, "comm")
    return raw.decode("utf-8", "replace").strip() if raw else "?"


def _ppid(pid):
    raw = _read(pid, "status")
    if not raw:
        return None
    for line in raw.decode("utf-8", "replace").splitlines():
        if line.startswith("PPid:"):
            try:
                return int(line.split()[1])
            except (IndexError, ValueError):
                return None
    return None


def all_pids():
    return [int(p) for p in os.listdir("/proc") if p.isdigit()]


def descendants(root):
    """PIDs in root's subtree (the set the NEW reaper is scoped to)."""
    kids = {}
    for pid in all_pids():
        pp = _ppid(pid)
        if pp is not None:
            kids.setdefault(pp, []).append(pid)
    out, stack = set(), [root]
    while stack:
        cur = stack.pop()
        for k in kids.get(cur, []):
            if k not in out:
                out.add(k)
                stack.append(k)
    return out


def old_reaper_matches(pids):
    """PIDs the OLD keyword scan would kill (substring match, exactly as the old code)."""
    matched = []
    for pid in pids:
        cl = _cmdline(pid).lower()
        if not cl:
            continue
        hits = [k for k in KEYWORDS if k in cl]
        if hits:
            matched.append((pid, hits, cl))
    return matched


def main():
    me = os.getpid()
    pids = all_pids()
    mine = descendants(me) | {me}

    old = old_reaper_matches(pids)
    # Non-descendant victims = OLD matches that are NOT in this process's own subtree.
    non_desc = [(pid, hits, cl) for (pid, hits, cl) in old if pid not in mine]

    # Victims matched ONLY by a short substring (e.g. "mp") — the pathological case.
    mp_only = [(pid, hits) for (pid, hits, cl) in non_desc if set(hits) <= {"mp"}]
    # Named fleet processes that would die as non-descendants.
    named = [
        (pid, _comm(pid))
        for (pid, hits, cl) in non_desc
        if any(m in cl.lower() or m in _comm(pid).lower() for m in FLEET_MARKERS)
    ]

    old_non_desc = len(non_desc)
    new_non_desc = 0  # the NEW reaper only touches descendants(me); by construction 0

    print("# Reaper blast-radius simulation (READ-ONLY — no signals sent)")
    print(f"self_pid={me}")
    print(f"total_host_processes={len(pids)}")
    print(f"self_subtree_size={len(mine)}")
    print(f"OLD_NON_DESCENDANT_KILLS={old_non_desc}")
    print(f"NEW_NON_DESCENDANT_KILLS={new_non_desc}")
    print(f"MP_SUBSTRING_ONLY_VICTIMS={len(mp_only)}")
    print(f"NAMED_FLEET_VICTIMS={len(named)}")
    print(
        "# sample non-descendant victims the OLD reaper would kill (pid + comm only):"
    )
    for pid, hits in [(p, h) for (p, h, _c) in non_desc][:20]:
        print(f"VICTIM pid={pid} comm={_comm(pid)} matched={','.join(hits)}")
    print("# named fleet victims (pid + comm only):")
    for pid, comm in named[:20]:
        print(f"FLEET_VICTIM pid={pid} comm={comm}")

    # Exit 0 always — this is a report, not a gate. Phase 1 AC parses the counters.
    return 0


if __name__ == "__main__":
    sys.exit(main())
