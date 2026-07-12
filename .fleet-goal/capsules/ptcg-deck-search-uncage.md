# COLLAB_CAPSULE/v1 — ptcg-deck-search-uncage

task_id: ptcg-deck-search-uncage
status: DISPATCHED (queued LAST — after ptcg-imitation-policy phases and
  ptcg-mh-surrogate-adapter; same worker)
dispatcher: ai-scientist (external-loop owner per human:eddie authorization #3084;
  M2 execution approved by Eddie in-session 2026-07-12 "同意，开始干")
canonical_owner: ai-scientist
worker: mroute
base: ready-player-one-ptcg @ origin/feat/ptcg-agent head at claim time
isolation: fresh git worktree + branch pr/ptcg-21-deck-search-uncage
allowed_paths:
  - scripts/deck_search.py               (is_legal floors ONLY — see spec)
  - tests/test_deck_search_legality*.py  (new/updated)
non_goals: NO changes to eval harness/builders/policy; NO new search launches
  (uncaging the space is this capsule; running searches in it is a coordinator
  decision after the mh adapter lands).

motivation (verified root cause — plateau analysis R2):
  scripts/deck_search.py is_legal() enforces Kyogre>=2 and Basic {W} Energy>=15
  (~lines 192-196; mutation floor ~line 307). ALL 14 mined meta decks
  (977-1220 rated) violate these floors — the entire 2,857-deck search archive
  lives in a region containing ZERO meta decks (max Jaccard 0.11). Every future
  deck-mutation operator in the mh surrogate loop inherits this cage until fixed.

spec:
  1. Replace the hard archetype floors with PARAMETERIZED constraints
     (default = engine-legality only: 60 cards, copy limits, >=1 basic Pokémon
     per engine rules; archetype floors become an optional profile so old
     behavior stays reproducible for historical comparisons).
  2. Structural validation stays (known card ids from the pool universe).
  3. Regression: all 14 mined meta decks (runs/replay_mining/*.csv) must pass
     is_legal under the default profile; the historical s14 deck must also pass;
     the old caged profile must still reproduce its old verdicts on both sets.
acceptance (ordered):
  1. offline tests: 14/14 mined meta decks legal under default profile;
     s14 deck legal; caged profile reproduces historical accept/reject on a
     fixture set
  2. ruff clean
  3. NO behavior change to any other deck_search entry point (search loop
     untouched; only legality gating parameterized)
curator_budget: 1 round
merge_owner: ai-scientist
a2a_ref: authorization #3084; plateau analysis (evidence/M1/
  2026-07-12-plateau-root-cause-analysis.md R2 + section 3.4); Eddie M2 approval.
ledger:
  - 2026-07-12T11:4xZ DISPATCHED by ai-scientist-6 (queued last; prerequisite
    for any future deck-mutation operator, not for the M2 joint intervention
    itself — mined decks bypass the search).
