# Lane checkpoint — ai-scientist-7, updated 2026-07-13 ~00:10Z

**Sweep is MONITOR-ONLY (CTX_THRESHOLD=101 = unreachable; harness #3230/#3265). NO auto-handoff.
Successor: hand off BY HAND. Read this + `.fleet-goal/evidence/M2/*` + `/M3/*` first.**

## Milestones

- **M1 = COMPLETE** (rpo #3264, recorded). All conditions closed; 229-171 exonerated; retro-contamination
  audit CLEAN (3 sweeps + adversarial verify + rpo independent confirmation, #3282: chronology + code-path
  + zero-C-games, any one sufficient).
- **M2 = Arm A/B battery STAGED, blocked on an environmental latency window.** All 3 candidates built,
  validated LIVE, hashes pinned (branch `pr/ptcg-29-armAB-battery`, commits 25b1932/142c040):
  - armA = shipped C bundle (111-key full-pool, strategy_sha 57f7c479..c72) × our water deck
  - B1 = meta0/BZ deck (`runs/replay_mining/meta0_1106_BenjaminZhao.csv`, sha c2f58250f2c0..aa5e, 6/6 core)
    × archetype-slice ranker (553 recs, deployment-max protocol)
  - B2 = kazuki0123 deck × kazuki ranker (16,426 recs; covers 15/19 of its own deck's cards — the
    mechanical restoration of the card channel)
  - **Blocker ruling (#3286): fire when loadavg(1m)<3.0 sustained 5min AND s18 pre-flight probe <3.0 s/game;
    6h deadline → then request harness quiet window. Floor 3.0 stays VERBATIM. Reason beyond prereg
    integrity: s18's search is wall-time-coupled ⇒ under load it is a WEAKER OPPONENT than the one the
    floors were calibrated on — running would change the gate's meaning, not just trip a floor.**
  - mroute's partial n40 numbers from aborted load-contaminated screens are QUARANTINED (not evidence).
- **M3 = declared** (Eddie): mass PAT harvest + own model + self-play (AlphaZero-shaped core RATIFIED by
  Eddie; "rules-first design, first-principles training"). Founding docs committed:
  `M3/2026-07-12-m3-constraints-and-directives.md`, `M3/2026-07-12-wild-ideas-first-principles.md` (10-idea
  slate + the founding fact: LADDER = STATIC-POPULATION ECOSYSTEM ⇒ exploitation beats Nash; challenge-back:
  GBM/tabular + no-NN exploitation stack BEFORE any transformer — LLM is the escalation tier).
  Full program synthesis (7-agent workflow, all measured): `scratchpad/m3-plan.md` — **NOT yet committed as
  the program doc; merge with fable-5 seat outputs when they land.**

## Decisions locked (do not relitigate)

- **SERVE C-FULL.** Triple-derived ablation (+12.02pp MAIN; 132/44 split; 5/11→1/11 coverage). LOTO:
  C-FULL transfers better 15/15 (+7.60pp record-weighted); my C-AG hypothesis REFUTED; sctst-aide's hybrid
  arms (H1 splice / H2 residual) CLOSED — in-domain +1.64pp evaporates out-of-domain (−0.04pp = 0.16 SE).
- **R0 agreement anchor on the 679-corpus split = MAIN 0.3318** (0.2866 is stale 106-corpus; flatters
  every arm, worst for C-AG whose true margin is +2.3pp).
- **Slot governance: Eddie's alone** (his ruling supersedes silence-equals-proceed; rpo #3272 retired its
  objection window; guardrails demoted to evidence standard (1')–(7'): mixed-field worst-arm gate replaces
  h2h-vs-s14; artifact sha pinning; notice-first; one slot; honest labeling; liveness proof (satisfied by
  0c017a4); expected-effect-size vs ±100 ladder noise — probe request only if winner clears macro≥0.60 AND
  worst-arm Wilson-lo≥0.55 on confirm AND reconfirm).
- **rpo G6 stands**: agreement may be an ANTI-proxy on an off-meta deck; Arm B is the proxy-validity test
  for link 1 of agreement→h2h→ladder (link 2 already falsified).

## In flight

- **fable-5 dual seats via TeamClaude (127.0.0.1:3456, Anthropic-native, model claude-fable-5)** — Eddie's
  directive after prisma bridge (fetch failed; container itself healthy, its own upstream 8318 works) and
  pal (401: its CUSTOM_API_KEY was the ROTATED 20-char key; fixed in ~/.claude.json to the 67-char proxy key,
  backup `.bak-palkey`; needs MCP reconnect to take effect) both failed. seatA = architecture deep-plan,
  seatB = adversarial attack. Prompts+outputs in scratchpad/seat{A,B}.{json,out.json}; retry loop running
  (rate-limit contention on 3456; honor 90s backoff).
- **mroute-3** (53% ctx): battery staged, auto-fire armed on quiet window.
- **sctst-aide**: standing by, all arms closed, scorecard exemplary (refuted parent once, itself 4×).
- **Ladder (live poll ~22:45Z)**: s14 592.2 (drifting down from 609.8); probe deck 569.3 (recovered from
  464.5); top-1 ~1306 (Yushin Ito per pseudo-leaderboard from 3 ListEpisodes calls).

## M3 measured facts (from the 7-agent design workflow — trust these, they were verified)

- Harvest: ListEpisodes accepts ONLY submissionId or ids[] (teamId filter DOES NOT EXIST — 400); cap 1000
  episodes/response, no pagination; teams[] in every response carries publicLeaderboardSubmissionId (the
  enumeration key); GetEpisodeReplay is 404 — kaggleusercontent GET is the sole replay path; replays mean
  3.6MB raw, compress 34-48× (~75-105KB stored); top-50 backfill ≈ 80-85k unique episodes ≈ 12-24h politely,
  6-9GB stored; Meta Kaggle dataset (via PAT) = completeness backstop; agent logs = deployability forensics
  only (own team only), not training data.
- Auth: `~/.kaggle/access_token` (37B) is a COMPLETE credential for `uvx --from kaggle kaggle` (Bearer);
  Eddie's dotfile `/home/admin/.kaggle-pokemon-token` (2.4KB) also present. NEVER print either.
- Engine: 0.30-0.34 s/game measured (median 0.336 over 3,444 eval JSONs); cabt spec actTimeout=0,
  runTimeout=2000s; self-play floor 50-70k NN-games/day on 8 cores (adversarially verified), ceiling
  180-530k/day with pinned BLAS threads.
- Compute ladder: local CPU → Kaggle free GPU (PAT, corpus as private dataset) → AWS via
  `/home/admin/aws-openmythos` (g5 configured; H100 = config change). aws-cli installed, creds inactive.

## Hazards (standing)

- Formatter hook silently reverts Edit-tool writes in rpo worktrees → Bash-heredoc + ruff + `git diff` confirm.
- `ready-player-one-ptcg` worktree: DIVERGENT, sole corpus copy, READ-ONLY, never rebase.
- Backticks in double-quoted `--text` EXECUTE → compose in file, `--text "$(cat file)"`.
- Output-token blowouts kill workers silently (mroute-3 died 26min at 15% ctx); write incrementally.
- TSA dispatch: text + Enter separately; verify with capture-pane; missed-Enter stalls look like idle.
- n40 = mirage (six recorded, both directions). Load-contaminated runs = quarantined.
