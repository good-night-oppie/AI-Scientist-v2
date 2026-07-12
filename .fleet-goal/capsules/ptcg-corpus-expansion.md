# COLLAB_CAPSULE/v1 — ptcg-corpus-expansion

task_id: ptcg-corpus-expansion
status: PARTIAL-ACCEPTED + UNBLOCK ISSUED (2026-07-12T19:4xZ)
  - Child verified the charter premise FALSE: the frozen miner discards fetched
    replays (writes only manifest/cursor/CSVs; empirical 300-req proof 106->106;
    3 adversarial refuters). Raw growth requires persistence code.
  - PARTIAL DELIVERY ACCEPTED by parent: rating-join fix via frozen-miner
    manifest growth (8->85 rows) recovered 4 silently-dropped top-tier teams:
    n_pairs 9,269 -> 12,901 (+39.2%), MAIN 6,071 -> 8,464, teams 9 -> 13,
    invariants 1050/1050 pass, baseline exactly reproduced. Join now saturated
    (1.9% ceiling) — child correctly stopped mining.
  - DIRECTION: (c-immediate) scratchpad persistence wrapper explicitly
    authorized (parent ruling: wrapper in child-owned scratchpad importing
    frozen functions = data plumbing, NOT a repo code edit) -> resume mining to
    >=300 raw; (a-durable) ~6-line --raw-dir spec dispatched to mroute, queued
    BEHIND the builder extension; child switches to the flag when merged.
dispatcher: ai-scientist (external-loop owner per #3084; child creation per
  Eddie in-session order 2026-07-12 + harness height-4 decree #3158/#3159)
canonical_owner: ai-scientist (parent; completion requires parent approval)
worker: sctst-aide (level-4 durable child of ai-scientist; leaf — may NOT
  create children; runtime: teamclaude/opus)
work_dir: /home/admin/gh/ready-player-one-ptcg (lane worktree; data ops only)
allowed_paths:
  - runs/replay_mining/            (data output ONLY — raw/, csvs, manifest,
                                    cursor files)
  - runs/imitation/                (rebuilt dataset output)
non_goals: NO code edits anywhere (if the miner needs a code change, mail the
  parent on the bus — parent dispatches to mroute); NO Kaggle submission
  surface; NO policy/eval/builder touches; NO deck-search runs.

mission:
  Expand the mined replay corpus from 106 to >=300 raw replays (stretch 500),
  weighted toward >=1100-rated actors, then rebuild the imitation dataset and
  report stats. Purpose: C (imitation ranker, merged @332a390c) needs more
  supervision — offline agreement 0.49 is a ticket off the 600 plateau, not to
  1100; corpus scale is the first lever (Eddie estimate discussion in-session).

tools (all merged, frozen — run, do not modify):
  - scripts/mine_replays.py  (PR #20; graph-walk miner; --live --seeds
    <sid,sid> --target N --hi-score 1150 --max-requests M; resumable cursor;
    politeness <=2 req/s BUILT IN — do not raise it)
  - scripts/build_imitation_dataset.py (PR #22/#25; t+1 alignment with 4
    fail-loud invariants; default --min-score 1100 is correct — do NOT pass a
    non-default --min-score, the flag is cosmetically broken, see capsule
    ptcg-imitation-policy ledger)
  - seeds to start from: 54535622 (@839), 54304158 (@1106), plus every sid in
    runs/replay_mining/manifest.json + the fresh-mine manifest at the parent's
    audit (sids 54239165 @1219, 54260619 @1203, 54203196 @1200, 54264277,
    54285670, 54300187, 54038721) — graph-walk upward from the highest tiers.

execution notes:
  - Raw replays land in runs/replay_mining/raw/ep_*.json (the dataset builder
    reads this dir). Run the miner in bounded batches (e.g. --max-requests
    300-500 per run), checkpoint via its cursor, repeat until >=300 unique
    raw replays. Politeness is non-negotiable: public unauth endpoints.
  - Dedup is by deck; RAW REPLAY count is what matters here — if the miner's
    dedup stops it early, widen seeds/score bands rather than re-fetching
    the same episodes.
  - After corpus >=300: run build_imitation_dataset.py (defaults) and record
    dataset_stats.json. The 4 invariants MUST pass (fail-loud). Note the new
    n_pairs and per-tier/per-team split in your report.
acceptance (ordered):
  1. runs/replay_mining/raw/ contains >=300 unique ep_*.json (report count)
  2. build_imitation_dataset.py exits 0; invariants pass; report n_pairs
     (expect well above the current 9,269) and distinct >=1100 teams
  3. a written summary on the A2A bus to ai-scientist (agent id sctst-aide):
     counts, tier histogram, notable new archetypes, any API anomalies
  4. NO repo file outside allowed_paths modified (git status clean apart from
     runs/)
comms:
  - A2A bus agent id: sctst-aide; parent: ai-scientist. Post CLAIM on start,
    progress at each mining batch, DONE with acceptance evidence.
  - Blockers -> mail parent on the bus; do NOT self-expand scope.
ledger:
  - 2026-07-12T19:0xZ DISPATCHED at child spawn (Eddie order; height-4 decree).
