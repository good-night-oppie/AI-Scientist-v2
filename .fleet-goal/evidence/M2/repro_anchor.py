#!/usr/bin/env python3
"""Pin down the R0 sanity anchor on BOTH corpora, all configs, from the bytes.

The spec said: "R0 A1 heuristic baseline -- full-set MAIN must reproduce ~0.2866".
That 0.2866 was measured on the 106-replay corpus. We now serve the 679-replay
corpus. This confirms the 106 number (proving the harness is honest) and produces
the correct 679-corpus replacement, in the SAME config the anchor uses.

RESULT (see 2026-07-13-r0-anchor-correction.md):
    679-corpus  full-set MAIN = 0.3385   val-split (val_eval_full) MAIN = 0.3318
    106-corpus  full-set MAIN = 0.4177   val-split                 MAIN = 0.3941
  => the heuristic_scorer reproduces NEITHER corpus at 0.2866. The corrected
     R0 anchor is 0.3385 (full-set MAIN, 679-corpus).

FROZEN-ARTIFACT PIN (load-bearing -- do not "helpfully" point this at repo tip):
    heuristic_scorer() / agreement() / episode_split() must come from
    policy_imitation.py + ready_player_one.ptcg.policy AT COMMIT 332a390
    (PR #25, "Phase-C distilled imitation policy"). Repo tip (0c017a4) carries
    +56 lines of C-gate liveness instrumentation (PR #28) and a rewritten
    policy.py (PRs #23/#24). Measuring against the tip measures a DIFFERENT
    artifact than the one the anchor is defined on.

Every path below is env-overridable; the defaults are the exact values this was
originally run with. The frozen tree resolves in two ways, in order:
  1. the as-run scratchpad worktree, if it still exists (bit-exact reproduction);
  2. otherwise `git archive <PIN>` out of the ready-player-one repo -- durable,
     read-only, and works on any machine with the repo.

Usage:
    python3 repro_anchor.py
    ANCHOR_REPO=/path/to/ready-player-one-ptcg python3 repro_anchor.py
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile

# --- config: defaults are the as-run values ---------------------------------- #
REPO = os.environ.get("ANCHOR_REPO", "/home/admin/gh/ready-player-one-ptcg")
PIN = os.environ.get("ANCHOR_POLICY_COMMIT", "332a390")  # frozen Phase-C (PR #25)
# The original scratchpad. EPHEMERAL (/tmp) -- kept only as the bit-exact path.
SP = os.environ.get(
    "ANCHOR_SCRATCHPAD",
    "/tmp/claude-1000/-home-admin-gh-ready-player-one-ptcg/"
    "ee00de82-038b-4069-83a0-9ff667a82781/scratchpad",
)
CORPUS_679 = os.environ.get(
    "ANCHOR_CORPUS_679",
    os.path.join(REPO, "runs", "imitation", "imitation_pairs.jsonl"),
)
# The 106-corpus exists ONLY in the scratchpad -- there is no repo copy. If the
# scratchpad is gone this arm is skipped; the 679 arm (which defines the anchor)
# still runs.
CORPUS_106 = os.environ.get(
    "ANCHOR_CORPUS_106", os.path.join(SP, "baseline_out", "imitation_pairs.jsonl")
)


def log(*a):
    print(*a, flush=True)


def resolve_frozen_tree() -> tuple[str, str]:
    """Return (tree_dir, provenance) for a tree containing src/ + scripts/ at PIN."""
    wt = os.path.join(SP, "wt-c")
    if os.path.isdir(os.path.join(wt, "src")):
        return wt, f"as-run scratchpad worktree {wt}"

    log(f"[info] scratchpad gone; rebuilding the frozen tree from git at {PIN}")
    # NB: do NOT test `isdir(REPO/.git)` -- in a git WORKTREE, .git is a FILE.
    probe = subprocess.run(
        ["git", "-C", REPO, "rev-parse", "--git-dir"], capture_output=True, text=True
    )
    if probe.returncode != 0:
        log(f"FATAL: ANCHOR_REPO is not a git repo/worktree: {REPO}")
        log(f"       {probe.stderr.strip()}")
        sys.exit(1)
    tmp = tempfile.mkdtemp(prefix="anchor-frozen-")
    subprocess.run(
        ["sh", "-c", f"git -C {REPO!r} archive {PIN!r} | tar -x -C {tmp!r}"], check=True
    )
    return tmp, f"git archive {PIN} from {REPO}"


TREE, PROVENANCE = resolve_frozen_tree()
sys.path.insert(0, os.path.join(TREE, "src"))
sys.path.insert(0, os.path.join(TREE, "scripts"))
import policy_imitation as M  # noqa: E402  (frozen; path set above)

# Integrity guard: the FROZEN artifact must NOT carry the PR-#28 liveness counters.
# If STATS is present we are importing repo tip, i.e. the wrong artifact.
if hasattr(M, "STATS"):
    log(
        "FATAL: imported policy_imitation carries STATS (PR #28 liveness "
        "instrumentation) -- this is repo tip, NOT the frozen 332a390 artifact "
        "the anchor is defined on. Refusing to report a number off the wrong bytes."
    )
    sys.exit(1)

log(f"[frozen] policy_imitation from: {PROVENANCE}")
log(f"[frozen] STATS absent -> confirmed pre-#28 artifact (pin {PIN})")

# --------------------------------------------------------------------------- #
# PREFLIGHT: the card DB must be LIVE, or this script fabricates a number.
#
# agreement() is documented to count "a scorer that raises on a record" as a
# MISS -- a deliberate choice so competing rankers share one denominator. The
# side effect: if ready_player_one.ptcg.cards cannot import `kaggle_environments`,
# every card-dependent decision raises and is silently scored as a miss, while
# the ~40% of decisions carrying no card-identity features (OPT_ATTACH energy
# plays) still score normally. The run does NOT crash. It prints
# full-set MAIN = 0.0067 -- a plausible-looking, entirely FABRICATED number.
#
# That is the dead-ranker failure mode this whole evidence line exists to police,
# so we refuse to emit any number unless the DB answers.
# --------------------------------------------------------------------------- #
try:
    from ready_player_one.ptcg import cards as _cards  # noqa: E402

    _n_cards = len(_cards.all_cards())
    if _n_cards == 0:
        raise RuntimeError("card DB loaded but is EMPTY")
except Exception as _e:  # noqa: BLE001
    log("")
    log(f"FATAL: the card DB is not live -> {_e!r}")
    log("")
    log("  agreement() scores a raising scorer as a MISS, so this run would NOT")
    log("  crash -- it would print a FABRICATED ~0.0067 as if it were the anchor.")
    log("  Refusing to report a number off a dead scorer.")
    log("")
    log("  Fix: use the venv that has kaggle_environments, e.g.")
    log(f"    {REPO}/.venv/bin/python {os.path.basename(__file__)}")
    sys.exit(1)

log(f"[preflight] card DB live: {_n_cards:,} cards -> scorer is not dead")
log("")

CORPORA = {
    "106-corpus (baseline_out, 9,269 pairs)": CORPUS_106,
    "679-corpus (canonical, 76,405 pairs)": CORPUS_679,
}

h = M.heuristic_scorer()
if h is None:
    log("FATAL: heuristic_scorer unavailable")
    sys.exit(1)

log(f"{'corpus':44s} {'config':14s} {'MAIN n':>8s} {'MAIN agree':>11s} {'overall':>9s}")
log("-" * 92)
for name, path in CORPORA.items():
    if not os.path.exists(path):
        log(f"{name:44s}  (SKIPPED -- missing: {path})")
        continue
    recs = [r for r in M.load_pairs(path) if r.get("top1100")]
    # full set
    full = M.agreement(recs, h)
    log(
        f"{name:44s} {'FULL-SET':14s} {full['main_n']:>8,} "
        f"{full['main_top1_agreement']:>11.4f} {full['top1_agreement']:>9.4f}"
    )
    # val split (every 5th episode), matching cmd_train's val_eval
    _tr, val = M.episode_split(recs, 5)
    v = M.agreement(val, h)
    log(
        f"{'':44s} {'VAL-SPLIT':14s} {v['main_n']:>8,} "
        f"{v['main_top1_agreement']:>11.4f} {v['top1_agreement']:>9.4f}"
    )
