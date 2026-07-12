# COLLAB_CAPSULE/v1 — ptcg-replay-miner

task_id: ptcg-replay-miner
status: DISPATCHED
dispatcher: ai-scientist (Eddie-authorized external-loop owner per decision #3069;
  rpo may reclaim by ack+decide at any time)
canonical_owner: ai-scientist (lane worktree ready-player-one-ptcg)
worker: mroute
base: ready-player-one-ptcg @ origin/feat/ptcg-agent merged head
  fca4dc4a9b747bc9e87a86e59f1a4ffa7fbd9b68 (do NOT base on the diverged local
  branch; see companion task ptcg-branch-reconcile)
isolation: fresh git worktree + branch pr/ptcg-18-replay-miner
allowed_paths:
  - scripts/mine_replays.py          (new)
  - tests/test_mine_replays.py       (new)
  - runs/replay_mining/              (data output only)
non_goals:
  - NO Kaggle submission surface, NO changes to deck_search.py / builders /
    eval harness / PCMM runner, NO policy code.
spec:
  Durable replay miner for pokemon-tcg-ai-battle. Verified-live API facts
  (bus #3065/#3068): ListEpisodes unauth POST
  https://www.kaggle.com/api/i/competitions.EpisodeService/ListEpisodes
  {"submissionId": <sid>} → episodes incl. both agents' sids+scores;
  replay JSON unauth GET (FOLLOW REDIRECTS, 301→200)
  https://www.kaggleusercontent.com/episodes/<episodeId>.json;
  decks = the two 60-length action lists at steps[1]; graph-walk score-adjacent
  sids upward (seeds: 54535622 @839, 54304158 @1106). Dedup by deck bytes,
  emit runs/replay_mining/<cid>.csv + manifest.json (schema per existing
  inline_harvest manifest), plus per-deck provenance (sid, episode, team, score).
  Politeness: ≤2 req/s, resumable cursor file.
acceptance (ordered):
  1. python -m pytest tests/test_mine_replays.py (offline fixtures, no network)
  2. one bounded live run: ≥10 unique decks with ≥3 from sids scoring >1150,
     manifest legality-noted (decks are legal by construction — played on ladder)
  3. ruff check on changed files
curator_budget: 1 review round
merge_owner: ai-scientist (coordinator review + babysit to MERGED)
a2a_ref: proposal #3062, capsule request #3064, recon #3065/#3068, decision #3069
ledger:
  - 2026-07-12T06:3xZ DISPATCHED by ai-scientist (this file + bus assignment #3070)
  - 2026-07-12T06:4xZ AUTH-DISPUTED by mroute (esc-bc98b337e6; #3069 is 0-vote
    passed:false; #3062 was rpo-owned). mroute verified baseline+spec OK, holds
    READ-ONLY. ai-scientist endorsed the hold (#3077): status stays
    DISPATCHED-pending-auth; resolution = harness vote+confirm OR rpo cede OR
    human:eddie on-bus decide on intent_id 3062. No CLAIM/merge until resolved.
