# COLLAB_CAPSULE/v1 — ptcg-replay-miner

task_id: ptcg-replay-miner
status: MERGED + AUDITED (PR #20 → feat/ptcg-agent @ 30ef89fb)
dispatcher: ai-scientist (Eddie-authorized external-loop owner per bus #3084, which
  supersedes 0-vote decision #3069; rpo may reclaim by ack+decide at any time)
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
  - 2026-07-12T09:07-09:11Z AUTH RESOLVED: human:eddie voted +1 on #3062 (bus
    #3083) and issued explicit AUTHORIZATION #3084 (ai-scientist = OWNER +
    DISPATCHER + MERGE_OWNER of the PTCG external loop; supersedes 0-vote
    #3069); esc-bc98b337e6 ACKed by eddie (#3085). mroute CLAIMED (#3086) and
    began the build in worktree /home/admin/gh/wt/ptcg-18-replay-miner.
  - 2026-07-12T10:0xZ ledger synced by ai-scientist-6 (successor session);
    mroute pane verified actively building (live replay-endpoint probes).
    Next coordinator action: review + babysit to MERGED per merge_owner.
  - 2026-07-12T10:14-10:17Z DELIVERED (bus #3089, commit 559786f) and MERGED as
    PR #20 → 30ef89fb by EdwardTang (Eddie live-driving; CI test job SUCCESS).
    Merge preceded coordinator review — post-merge audit substituted.
  - 2026-07-12T10:3xZ POST-MERGE AUDIT PASSED (ai-scientist-6, scratch worktree
    at 30ef89fb): pytest 17/17 offline; ruff clean; fresh bounded live run =
    12 unique decks, 7 >1150 (two 1200-tier: Dng 1203.4, kazuki0123 1199.6) in
    41 requests — exceeds acceptance bar (>=10 unique, >=3 >1150). Audit
    artifacts: scratchpad/audit-pr20/runs/replay_mining/. CAPSULE CLOSED.
