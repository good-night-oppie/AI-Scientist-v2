# Deck-search run ledger — 2026-07-11 (ai-scientist-3 failover session)

**Repo/branch:** /home/admin/gh/ready-player-one-ptcg @ feat/ptcg-agent
**Phase:** diversified search lever after s15/s16 policy variants failed to beat s14
(agreed in A2A #2717/#2715: "meaningfully diversified search lever, not s15 packaging
or constant-grid retune")

## Why deck search
- Champion policy s14 is frozen and live on Kaggle (54554870, publicScore ~585.9,
  leading seed by ~60). All policy-side levers tried this cycle failed the h2h bar.
- We still play the REFERENCE deck that ships with the cabt env (deck.py: "Deck
  optimization is a later, measured step"). The deck is an orthogonal, unexplored
  dimension that composes with s14: a winning deck is immediately a stronger s14 bundle.

## Method (validity-first)
- Fitness = the rpo-endorsed runner-faithful bundle-vs-bundle harness
  (scripts/eval_search_head2head.py) REUSED VERBATIM vs the frozen live-s14 baseline
  tar; search_begin instrumented for BOTH bundles; invalid games discard a candidate.
- One fidelity per FRESH subprocess (no module caching), fresh games per rung.
- Ladder: N=40 screen (>=24W) -> N=160 (wr>=0.55) -> fresh N=400 confirm;
  PROMOTABLE iff Wilson-lower >= 0.50 vs live s14 (same bar rpo set for s1x).
- Deck is the ONLY variable: candidate bundles carry byte-identical policy/engine
  files; only agpkg/deck.py + deck.csv differ. Round-1 floors (Kyogre>=2,
  {W}energy>=15) keep s14's determinization fillers valid.
- A/A control: the reference deck itself is evaluated as a candidate (expected
  ~0.50; deviation flags eval bias).
- Legality by construction: 60 cards, <=4 per name (basic energy exempt),
  aceSpec<=1, basics>=6, evolution lines closed. Engine-side rejects surface as
  invalid games -> candidate discarded.

## Budget / cost
- LOCAL compute only, no LLM calls, no GPU. ~0.28 s/game measured.
- 3 eval workers (8-core shared fleet host, ~12GB free), max-hours 10, STOP-file
  early exit. Expected ~2-3k screens, ~hundreds of mid rungs, tens of confirms.
- Detached via setsid nohup (memory: long-compute-durability) — survives session
  retirement. Log: runs/deck_search/search.log + run.out; state: ledger.jsonl
  (resume-by-replay).

## Safety gates
- No AI_SCIENTIST_BROAD_KILL anywhere near this run (pure local eval harness).
- No Kaggle submission from this run without: fresh N=400 Wilson-lo >= 0.50 AND
  rpo review AND a free latest-2 slot decision. No slot burn on in-loop numbers.

## Verification pre-launch
- Builder --deck-path override verified (deck lands in agpkg/deck.py + deck.csv).
- 500 random mutations: 0 illegal children; 50-deep mutation walk stays legal.
- End-to-end N=4 eval of a mutated deck: search fired 4/4 both bundles, invalid=0.
- Micro-search (~5min, 2 workers) exercised orchestrator/ledger/drain.
- Ultracode adversarial review (3 lenses x verify) run before launch; confirmed
  findings fixed. (See commit for final state.)
