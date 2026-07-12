# COLLAB_CAPSULE/v1 — ptcg-mh-surrogate-adapter

task_id: ptcg-mh-surrogate-adapter
status: DISPATCHED (queued behind ptcg-imitation-policy PHASE A; same worker)
dispatcher: ai-scientist (external-loop owner per human:eddie authorization #3084;
  this capsule additionally answers Eddie's direct in-session ask 2026-07-12:
  "force proposer to do surrogate so we pivot at plateau")
canonical_owner: ai-scientist
worker: mroute
base: ready-player-one-ptcg @ origin/feat/ptcg-agent 30ef89fb (post-PR#20 head)
isolation: fresh git worktree + branch pr/ptcg-20-mh-surrogate-adapter
allowed_paths:
  - scripts/mh_surrogate_adapter.py     (new — benchmark registration + run())
  - tests/test_mh_surrogate_*.py        (new)
  - runs/mh_surrogate/                  (data output only)
non_goals: NO Kaggle submission surface; NO edits to frozen evaluators/builders/
  policy/deck_search (the adapter CALLS them read-only); NO mh core edits.

motivation (the ask, made precise):
  The external loop's proposer (bene-mh mh_search / mh_submit_candidate) currently
  has NO registered benchmark for the PTCG lane, so candidate generation cannot be
  surrogate-gated — every pivot decision needs manual eval dispatch. Eddie wants the
  proposer FORCED through the surrogate so that when the surrogate frontier
  plateaus, the loop pivots levers (policy params vs deck vs both) without burning
  Kaggle slots. Winner's-curse discipline (5 false n40 promotions) must be baked in.

spec:
  1. Register a bene-mh benchmark (e.g. "ptcg-h2h-surrogate") whose candidates are
     `def run(problem)` harnesses per the mh contract. A candidate = a policy
     parameterization (MAIN_SCORES dict / flags) and/or a 60-card deck CSV.
  2. run(problem) computes fitness via the FROZEN h2h harness vs the frozen
     live-s14 baseline tar — adaptive laddering: n40 screen; if Wilson-lo >= 0.50
     escalate n160; then n400. Fitness reported = Wilson LOWER bound at the highest
     rung reached (never the point estimate; kills n40 mirages by construction).
  3. Optional mixed-field mode: 3-arm PCMM portfolio gate (worst-arm) against
     mined 1180-tier decks (runs/replay_mining data from PR #20 miner).
  4. Plateau-pivot surface: adapter records per-generation frontier best into
     runs/mh_surrogate/frontier.jsonl so mh_next_iteration / the coordinator can
     detect K-generation stall and switch operator class (deck-mutation <->
     policy-param mutation <-> joint). Detection logic itself may live in the
     adapter as a pure function (stall(frontier, k) -> bool).
acceptance (ordered):
  1. offline tests pass (mocked eval fn; no games) incl. ladder-escalation logic
     and stall() detection
  2. A/A control: s14-identity candidate through the real surrogate scores
     n40 rung with Wilson interval containing 0.50 (sanity: gate not biased)
  3. one real candidate (any mined deck under frozen policy) produces a
     frontier.jsonl entry with rung provenance
  4. ruff clean
curator_budget: 1 round
merge_owner: ai-scientist
a2a_ref: authorization #3084; Eddie in-session ask (ai-scientist-6, 2026-07-12
  ~10:2xZ); PROGRESS.md "bene-mh benchmark adapter = follow-on capsule".
ledger:
  - 2026-07-12T10:4xZ DISPATCHED by ai-scientist-6 (queued behind
    ptcg-imitation-policy PHASE A — bugs 1-4 remain the highest-value item;
    this capsule is the loop plumbing that makes every FUTURE candidate
    surrogate-gated with automatic plateau-pivot).
