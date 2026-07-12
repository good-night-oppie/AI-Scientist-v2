# PROGRESS — ai-scientist child fleet-agent

_Updated: 2026-07-11T21:38Z. Full recovery doc: /home/admin/gh/ready-player-one-ptcg/LANE_STATE.md_

## Goal (assigned by Eddie mid-session)
Conquer Kaggle `pokemon-tcg-ai-battle` (PTCG simulation comp, cabt engine) BY DRIVING
IT THROUGH the AI-Scientist-v2 BFTS pipeline — evolve the agent autonomously, then
package + submit. Research seeds: ~/gh/ready-player-one/src/ready_player_one/seeds.

## What's done (evidence in ./evidence/ + commits)
1. Competition + engine recon: agent contract, option/select enums, card DB
   (AllCard/AllAttack ctypes), submission format (.tar.gz main.py+deck.csv).
2. Seed agent built in ~/gh/ready-player-one-ptcg (branch feat/ptcg-agent, commits
   1a75620, 8570f2a): heuristic option-scoring policy, winrate 0.90 vs 'random' /
   0.54 vs 'first' baselines; eval + trace harnesses; submission builder validated
   by local self-play (DONE/DONE).
3. AI-Scientist-v2 wired for the custom task (branch ptcg-run, commits 68fa1cd, +1):
   idea json + seed .py (node contract: working/experiment_data.npy + plots, metric
   = mean winrate over seat-alternated games vs both baselines, standalone-verified
   mean_winrate 0.719); LLM backend = LOCAL cli-proxy-gemini (zero paid API) via
   OPENAI_BASE_URL; patches: GEMINI_BASE_URL override, gemini VLM route, tool-schema
   'strict' strip (gemini 400 fix), rmtree guard, psutil broad-kill sweep gated off
   (fleet-host safety — never set AI_SCIENTIST_BROAD_KILL=1 here).
4. BFTS smoke run #2 (b7xffdw0i, killed at session restart) VALIDATED the loop:
   stage 1 → 3/3 non-buggy nodes, parsed metrics (best mean_winrate 0.694),
   plots+VLM+archives OK. But post-step it hit an INFINITE LLM BACKOFF LOOP
   (91 retries/45min) — exception swallowed by unconfigured logger.
5. Backoff root cause CONFIRMED empirically (run #3 instrumented print):
   `InternalServerError: 502 unknown provider for model gpt-4o` — journal.py's
   summary/select_node fall back to "gpt-4o" when unset in config; proxy 502s
   unknown models; 502 is in the retry list → infinite loop. FIXED: summary +
   select_node pinned to gemini-3-flash in bfts_config; --model_agg_plots
   gemini-3-flash added at launch (same trap, o1 default). Committed.
6. Smoke run #4 (bg bak0yvzte, monitor bh2v0ujpm) CROSSED INTO STAGE 2
   baseline_tuning — infinite-backoff class confirmed dead; plumbing validated
   through the fatal transition. On clean completion → scale to full run.
7. KAGGLE CREDS DELIVERED (Eddie, ~/.kaggle-pokemon-token 1P export → installed
   ~/.kaggle/access_token mode 600, value never printed). esc-ced2411dbe ACKED.
8. SUBMISSION VALIDATED: v1.1 ref 54539166 COMPLETE, publicScore 600.0 (mu0), in matchmaking pool. (v1 54539022 ERRORED: __file__ absent in runner exec; fixed e629707.)
   Accrues rating (μ0=600) + real-opponent replays; evolved agent replaces it
   later (latest-2 rule).
9. Side-seed crawl (Eddie): agent-evolution.com deep-crawl via bounded ad-hoc
   workflow w7dy2to3e → seeds/agent-evolution-distilled.md (BFTS loop upgrades).

## Status update 2026-07-11T00:2xZ (ai-scientist-2 successor)
- **s14 determinized-search champion SUBMITTED + VALIDATED on Kaggle** (ref
  54554870, publicScore 600.0, COMPLETE) per Eddie "submit s14 as ladder probe,
  dont wait for rpo". Bundled the VENDORED cg/libcg.so (good SearchBegin ABI) +
  agpkg package; runner-faithful make(cabt) validation: 76 games, 0 forfeits,
  search was initially reported active, 60 legal cards. **Later disproven:**
  `search_begin == games` is the dead-search/fallback signature. Builder: ready-player-one-ptcg
  scripts/build_submission_search.py (committed ce07f42). Latest-2 scored now
  {seed v1.1 560.5, s14 600.0}.
- **BFTS full run (b9faasveg) DIED** mid-stage-4: sweep auto-retired the
  predecessor session ~00:19Z → SIGHUP'd its session-bound children (BFTS + weco
  derives). Harvest verdict: stage 1/2/3 best_solutions are ALL torch-NN policies
  (global_model), NOT Kaggle-deployable, weights unsaved → unverifiable/unpromotable.
  BFTS drifts into neural-policy territory with this idea/seed. Champion stands = s14.

## Status update 2026-07-11T19:4xZ (ai-scientist-3 rate-limit failover session)
- **🔴 CRITICAL DISCOVERY: s14's search NEVER fired a move.** 19-agent adversarial
  review (run to vet the new deck-search harness) confirmed statically+empirically:
  `search_step(root_id,[i,j])` is an ABI misuse rejected on the FIRST search attempt
  of every game → silent heuristic fallback for the entire game. `calls==games` in
  every historical eval is the crash signature (the h2h guard only checked >0).
  s15/s16 h2h = A/A tests; s14 ≈ heuristic; live Kaggle agent effectively heuristic.
  Fix identified (step from branched child id) — s17 workstream opened.
- **Deck search LAUNCHED (the #2717 diversified lever):** policy frozen, evolve the
  60-card deck vs frozen live-s14 baseline via the trusted h2h harness verbatim.
  4-rung ladder (40/160/400/400-reconfirm, ~0.03 expected false promotables per 3k
  null screens), A/A control, legality-by-construction. DETACHED (setsid, PID
  1829394, own session — long-compute-durability applied), 3 workers, 10h cap.
  State: ready-player-one-ptcg runs/deck_search/ledger.jsonl; commits 48f0f9f+b374098
  pushed. Deck-under-heuristic measurement is deployment-faithful given the discovery.
- Evidence: .fleet-goal/evidence/2026-07-11-deck-search-ledger.md

## Status update 2026-07-11T20:2xZ (ai-scientist-5 successor)
- **DECK SEARCH → 1st fully-vetted PROMOTABLE `2c1368bc03`** (frozen live-s14 policy,
  evolved deck). 4-rung ladder: n40 0.625 → n160 0.556 → n400 confirm 0.570 → n400
  independent reconfirm 0.5725 [0.524,0.62]. Combined 457/800 = 0.571 vs live-s14.
  Review-ready bundle built+validated: `submission_search_deck_2c1368bc03.tar.gz`
  (self-play 20-0, search 20/20, 0 forfeits, 60 legal). Awaiting rpo review →
  ladder-probe decision (no auto-submit). Evidence: evidence/2026-07-11-deck-search-promotable.md
- **s18 SEARCH-TUNING LEVER EXHAUSTED:** powered N=300 h2h landed = 130-170, wr 0.4333
  [0.378,0.49] vs s14 (cand search fires 43333/300 games; baseline 300=games dead
  signature). Wilson-upper 0.49<0.50 → mechanically-correct search LOSES to the
  heuristic-effective champion. DECK is the productive lever, not search internals.
- **Champion s14 live (fresh poll):** Kaggle 54554870 publicScore 580.7 COMPLETE,
  leads seed v1.1 (526.0) by +54.7. No privateScore. KEEP live.
- Deck search still running (PID 1829394, 10h cap ~05:31Z); re-harvest best PROMOTABLE
  at run end. Fleet hygiene: retired ai-scientist-4 + stale ai-scientist-3; harness-41
  remains sole sweep orchestrator (no duplicate daemon).

## Status update 2026-07-11T20:58Z (Codex takeover of ai-scientist-5)
- **What's done:** recovered Claude session `6adb5ba8-e934-46e3-8270-9f17b96885ba`;
  completed fleet enrollment (`#2794`, `#2795`); ran fleet-doctor heal and verified
  a healthy fleet; deterministically re-audited candidate `2c1368bc03` and its
  review bundle; registered A/A `0.495` and candidate `0.57125` in Weco Observe run
  `7393d6ae-46a4-4b22-9cb5-a48abbab3d41`; sent refreshed parent evidence as A2A
  `#2800`. Full evidence: `evidence/M1/2026-07-11-ai-scientist-5-takeover.md`.
- **What's next:** keep the detached search + harvester running; at completion audit
  the final best fully reconfirmed candidate, log it to the Weco run, rebuild/check
  its review bundle, and return the promotion decision to parent `rpo`.
- **Any blockers:** infrastructure is healthy. Kaggle ladder-probe promotion and
  final child-goal completion require parent `rpo` approval.

## Status update 2026-07-11T21:01Z (inherited goal activated)
- **What's done:** created active goal-service thread
  `019f52f2-7d79-7ad0-a1c6-d02bdcd3199e` from the predecessor's exact PTCG
  objective; expanded `GOALS.md` from a generic child-evidence placeholder into
  the explicit deck-search, validation, packaging, Weco, Kaggle, and `rpo`
  approval contract. Parent/child cross-links remain intact.
- **What's next:** continue M1 only: let detached search PID 1829394 and the then-live
  harvester PID 2136762 finish (historical; replaced by corrected PID 2260719), audit the final selected candidate, persist the missing raw
  runner-validation transcript, update Weco, and send completion evidence to rpo.
- **Any blockers:** none operational. Final harvest is time-dependent; promotion
  and goal completion remain parent-gated.

## Status update 2026-07-11T21:05Z (runner-validation false-positive fixed)
- **What's done:** independently reran the `2c1368bc03` bundle through the Kaggle
  file-path runner (20 games: 19-1, invalid=0, zero forfeits) and persisted the raw
  validator result plus hashes in
  `evidence/M1/2026-07-11-runner-validation-2c1368bc03.md`. Corrected
  `build_submission_search.py`: `search_begin == games` now reports the known
  live-s14 inactive/fallback signature instead of falsely claiming active search;
  optional strict mode fails unless calls exceed games. Updated LANE_STATE and
  promotion evidence to describe this as a deck-only improvement under the
  deployment-faithful heuristic-effective policy.
- **What's next:** let the detached deck search/harvester finish, apply the same
  honest runner validation to the final selected deck, update Weco, then request
  rpo review.
- **Any blockers:** none operational. Final selection is still running and parent
  approval remains mandatory.

## Status update 2026-07-11T21:09Z (final harvester evidence path hardened)
- **What's done:** fixed `deck_search_harvest.py` so an already-built winning
  bundle no longer bypasses validation. Every final selection is now validated,
  its full output is written to `runs/deck_search/validation_<cid>.log`, and the
  harvest succeeds only on validator rc=0 plus `VALIDATION OK`. Replaced the old
  waiting harvester PID 2136762 with corrected detached PID 2260719; search PID
  1829394 was untouched and remains live.
- **What's next:** wait for the bounded search to end, audit HARVEST_RESULT and the
  final validation log, update Weco if the winner changes, then send the complete
  evidence bundle to rpo.
- **Any blockers:** none operational; final search and parent gate remain open.

## Status update 2026-07-11T21:21Z (strong confirm rejected by reconfirm)
- **What's done:** candidate `d40d9dd567` passed N=400 confirm at 233-167,
  winrate 0.5825, Wilson lower 0.534, but the mandatory independent N=400
  reconfirm regressed to 205-195, winrate 0.5125, Wilson lower 0.464. It is
  correctly `reconfirm_out`, not promotable. Logged the completed negative result
  as Weco Observe step 2 (parent step 1) and persisted
  `evidence/M1/2026-07-11-d40d9dd567-reconfirm-out.md`.
- **What's next:** continue the bounded search; `2c1368bc03` remains the only
  fully reconfirmed candidate. Final harvester and rpo approval are still required.
- **Any blockers:** rpo currently has unread evidence because its runtime is
  quota-stranded; harness owns the active same-lineage recovery escalation.

## Status update 2026-07-11T21:29Z (deterministic validation tests landed)
- **What's done:** harness restored rpo and its inbox is drained; rpo is actively
  performing the independent parent review, but has not yet approved. Added
  dependency-free deterministic tests for the corrected packaging/harvest gates:
  `calls == games` is inactive, `calls > games` is active, an already-built bundle
  is still validated with a persisted transcript, validator failure rejects the
  bundle, and final selection prefers Wilson lower bound over point estimate.
  `python -m unittest -v tests.test_deck_search_validation` passes 4/4. PTCG
  commit: `838bb91`.
- **What's next:** keep the bounded producer and corrected harvester running;
  continue recording any candidate that reaches independent reconfirm, then audit
  the final harvest before asking rpo for the final approve/rework decision.
- **Any blockers:** none operational. Parent approval is pending, not assumed.

## Status update 2026-07-11T21:32Z (parent-approved Kaggle probe submitted)
- **What's done:** rpo recovered, independently reviewed all evidence, and granted
  explicit one-probe approval in A2A `#2852`. Rebuilt `2c1368bc03` through the
  committed honest validator (18-2 vs random, invalid=0, zero forfeits,
  `search_active=False`), verified exact deck bytes/legal composition and frozen
  policy/engine hashes, then used the single authorized slot. Kaggle submission
  `54585744` is `PENDING`; required description includes deck-only scope, full deck
  SHA-256, search-fallback caveat, and s14-champion statement. Evidence:
  `evidence/M1/2026-07-11-kaggle-probe-54585744.md`.
- **What's next:** poll submission `54585744` to terminal status while the bounded
  search/harvester continue. No further submission without fresh rpo review.
- **Any blockers:** Kaggle validation/scoring and final search harvest are pending.

## Status update 2026-07-11T21:34Z (Kaggle probe validated)
- **What's done:** Kaggle ref `54585744` reached `COMPLETE` with initial public
  score `600.0`. Same poll: s14 `580.7`, seed `521.0`; s14 remains the other scored
  submission. Updated Weco step 1 with terminal probe evidence. The `+19.3` initial
  gap is ladder support, not settled superiority, because known rating volatility
  is much larger and no private score exists.
- **What's next:** continue the bounded search and final harvester; monitor the
  probe without reacting to rating noise. No additional submission without fresh
  rpo review.
- **Any blockers:** only final search harvest and child-completion review remain.

## Status update 2026-07-11T21:38Z (probe fell below s14; hold activated)
- **What's done:** Kaggle ref `54585744` moved from its initial `600.0` to early
  publicScore `464.5`; same poll s14 `580.7`, seed `521.0`. This contradicts the
  initial favorable read but remains noisy early ladder evidence, not a settled
  causal verdict. Updated Weco step 1 and notified rpo/harness in A2A `#2870`.
- **What's next:** no further external submission. Continue only the bounded
  search/final harvest and audit; any future probe requires new reconfirmed evidence
  plus fresh rpo review.
- **Any blockers:** parent condition 3 is an intentional promotion hold, not an
  infrastructure failure. Final search harvest remains pending.

## Status update 2026-07-11T22:51Z (mixed-field evidence substrate committed)
- **What's done:** inherited goal thread remains active; fleet enrollment and
  doctor heal re-verified healthy. PokeChamp paper-release and MetaMon flagship
  mechanisms were pinned and distilled clean-room. In isolated worktree
  `feat/ptcg-pcmm-r1`, commit `0ed92d6` adds a three-arm canonical
  source+deck-bound portfolio gate, per-run module isolation, raw Wilson/seat
  gates, artifact mutation checks, and 21 deterministic/no-game tests. AI-Scientist
  research/run evidence is committed at `eaddb5a`. Detached search PID 1829394 and
  harvester PID 2260719 remain alive; a second local PROMOTABLE `58c77982cd`
  reached confirm 0.56 [0.511,0.608] and reconfirm 0.5525 [0.504,0.6]. Status was
  delivered to rpo/harness as A2A `#2921`; no build or submission followed.
- **What's next:** finish and independently audit the pure MetaMon-style guarded
  router and PokeChamp-style macro-turn max-min seams, then run only the recorded
  bounded mixed-field screen if candidate packaging/preflight remains green.
  Continue read-only monitoring until the harvester writes `HARVEST_RESULT.md`.
- **Any blockers:** no infrastructure blocker. Parent hold `#2872` prohibits any
  further Kaggle submission; final child completion still requires explicit rpo
  approval.

## Status update 2026-07-12T00:29Z (PCMM implementation published; screen safely deferred)
- **What's done:** completed and independently audited both clean-room strategy
  families: PokeChamp-style complete-turn macro-minimax (`7b6dbb2`, 23 tests) and
  MetaMon-style guarded proposer/judge (`e9a9484`, 49 tests). Built/imported both
  immutable bundles and bound their archive plus canonical source/deck hashes into
  the three-arm portfolio alongside exact live ladder availability. Refreshed Weco
  Observe with `58c77982cd` (0.55625), `89f76904cf` (0.56875), and negative
  `f007dbfd89` (0.53375, reconfirm_out); no Optimize credits were used. Published
  the full ready-player-one chain as green, review-thread-free merged PRs #3-#16,
  including CI repairs and the durable s18 N=300 rejection artifact. Parent rpo
  independently returned `SOUND` for the macro candidate in A2A `#2940`.
- **What's next:** continue read-only monitoring of detached search PID 1829394 and
  harvester PID 2260719. Only after their evaluator children exit, terminal harvest
  evidence exists, and CPU load settles: re-verify all hashes and run the frozen
  N=40-per-arm seat-balanced PCMM screen, then send the per-arm table to rpo.
- **Any blockers:** no implementation or infrastructure blocker. The running search
  intentionally blocks uncontaminated game measurement; at 00:27Z the ledger was
  still advancing (1,874 rows), three workers occupied about three cores, and no
  HARVEST_RESULT existed. The no-submit hold remains binding and completion still
  requires explicit rpo approval.

## Status update 2026-07-12T01:18Z (immutable Stage-B runner merged)
- **What's done:** published the exact PCMM screen/confirm/reconfirm producer as
  ready-player-one PR #17 and babysat it through green CI, a clean merge surface,
  zero comments/reviews/threads, and MERGED commit `fca4dc4`. The runner freezes
  config, artifact hashes, phase, and unique arm run IDs; persists an exact ordered
  prefix of receipt-bound raw arm evidence; makes interrupted bootstrap/arm writes
  safely retryable; hard-stops invalid/search-inactive/latency failures; and
  requires a passing, fresh, disjoint, independently recomputed confirm dataset
  before reconfirm. Final no-game verification passed 45 tests and 18 subtests
  plus Ruff, format, byte-compile, and diff checks. An adversarial re-audit of the
  exact final hashes returned `COMMIT`.
- **What's next:** keep detached search PID 1829394 and harvester PID 2260719
  read-only until terminal harvest evidence exists and load settles, then recheck
  all bundle hashes and invoke PR #17's immutable N=40-per-arm screen.
- **Any blockers:** the measurement hold remains intentional. At 01:08Z, three
  evaluator children were active, the ledger had reached 2,111 rows and was still
  advancing, no `HARVEST_RESULT` existed, and 8-core load was 7.80/6.94/6.45. No
  games, Weco credits, or submissions were consumed. A durable A2A refresh found
  rpo's one-deck probe grant for `2804af5498`; it remains unconsumed until the
  terminal harvester strict-builds and validates that exact artifact. Every other
  deck remains held, and explicit rpo completion approval is still required.

## Status update 2026-07-12T05:5xZ (ai-scientist-5 Claude coordinator — goal re-armed)
- **What's done:** Eddie unset the /goal thread; goal re-anchored on .fleet-goal/ +
  session task list + A2A (GOALS.md updated: operating_mode COORDINATOR per Eddie —
  no direct coding, implementation → mroute). Fleet-enroll SELF-CHECK/SETUP green
  (ON_BUS, WATCHED, retro #3059); fleet-doctor DIAGNOSE: healthy (exit 0).
  **DECK SEARCH TERMINAL 05:37Z:** 3,399 evals, 46 PROMOTABLE; harvester fired
  cleanly (honest validator rc=0): best `58f62b5135` reconfirm 261/400 wr 0.6525
  Wilson [0.605,0.698] — CLEARS the preregistered in-basin bar (≥235/400, lo>0.5367);
  bundle submission_search_deck_58f62b5135.tar.gz + validation log persisted;
  harvester A2A #3058. **Kaggle fresh poll:** probe 54585744 recovered 464.5→548.1;
  champion s14 54554870 at 602.4 (leads +54.3). Hold #2872 still binding.
- **What's next:** (1) launch the frozen PCMM Stage-B N=40/arm screen — launch
  condition NOW satisfied (producer+harvester exited, HARVEST_RESULT exists, load
  settling) — from a read-only worktree at origin merged head fca4dc4 after
  re-verifying all five archive/canonical hashes; (2) dispatch mroute (capsule) to
  reconcile diverged feat/ptcg-agent (local 6 ahead — content-dupes of merged PRs —
  / 31 behind); (3) ask rpo: grant currently on a41403b867 (lo .579) vs terminal
  best 58f62b5135 (lo .605) — transfer decision + reviews #18-#20.
- **Any blockers:** rpo review latency (rpo-27 quota-blocked per #3052, since
  healed per fleet-doctor); hold #2872 prohibits all submissions pending rpo.

## Status update 2026-07-12T06:0xZ (PCMM Stage-B screens LAUNCHED)
- **What's done:** all launch conditions verified — producer/harvester exited,
  HARVEST_RESULT.md terminal, load settled, **all five archive hashes PASS** vs
  frozen configs/pcmm_r1_portfolio.json, runner digest byte-identical to audited
  `7736b873…`. Both candidate screens launched DETACHED + SEQUENTIAL from
  read-only worktree `ready-player-one-ptcg-screen` @ merged head fca4dc4:
  metamon_router_r1 then pokechamp_macro_minimax_r1, phase=screen (N=40/arm,
  seat-balanced, ≤3.0 s/game). Run dirs:
  `ready-player-one-ptcg-pcmm-r1/runs/pcmm_r1/screen_{metamon,pokechamp}_r1/`;
  done-marker `stageB_screen.done`. No code edits (coordinator ops only);
  diverged feat/ptcg-agent left untouched — mroute reconcile capsule requested
  from harness in A2A #3060.
- **What's next:** on done-marker → read per-arm raw JSON + portfolio summaries,
  deliver per-arm table to rpo alongside the grant-transfer question
  (a41403b867 lo .579 vs terminal best 58f62b5135 lo .605). Any screen pass earns
  parent review for at most one probe; it does not displace champion s14.
- **Any blockers:** hold #2872 binding; rpo decision latency.

## Status update 2026-07-12T06:1xZ (PCMM Stage-B screens COMPLETE — both FAIL)
- **What's done:** both screens finished clean (~5 min total, zero invalids, spg
  within budget). **metamon_router_r1 gates_pass=False** (macro .5583 OK but
  worst-arm .375 < .40 — collapses vs the evolved-deck arm while beating both
  reference arms .625/.675). **pokechamp_macro_minimax_r1 gates_pass=False**
  (macro .4667 < .55 with search genuinely active, 976/742/1130 calls). PCMM
  candidate stream CLOSED at screen — honest negative; the mixed-field gate
  prevented a 4th overfit promotion. Results → rpo/harness A2A #3061; evidence
  evidence/M1/2026-07-12-pcmm-stageB-screen-results.md; immutable artifacts in
  ready-player-one-ptcg-pcmm-r1/runs/pcmm_r1/screen_{metamon,pokechamp}_r1/.
- **What's next:** deck stream is the sole promotion path. Awaiting rpo:
  grant transfer a41403b867 → 58f62b5135 + reviews #18-#20. mroute reconcile
  capsule pending from harness (#3060). Ladder monitoring continues (probe
  548.1 vs s14 602.4).
- **Any blockers:** hold #2872 binding; all next moves are rpo-gated.

## Status update 2026-07-12T06:0xZ (EDDIE DIRECTIVE: external loop — break the 600 stall)
- **Ground truth:** leaderboard top 1232.3, a dozen teams >1100; we are 607.6
  (s14) + 548.1 (probe). ~620pt CLASS gap — the inner ±5pt loop cannot close it.
- **What's done:** PROPOSAL #3062 on the bus (rpo-owned external loop: L0 mroute
  replay miner → L1 bene mh_search seeded from MINED top-meta decks → L2 frozen
  PCMM portfolio runner with top-meta arms as surrogate gate → L3 ~3/day ladder
  probes as true fitness; reframe: mid-season rating is information, final
  ranking = latest-2 at deadline, so slot conservation now optimizes the wrong
  objective). ENFORCED escalation esc-8f57f8aa02 → rpo (ack by 06:30Z).
  Capsule request #3064 → harness (mroute miner build). **L0 FEASIBILITY
  CONFIRMED live** (#3065): EpisodeService/ListEpisodes works by submissionId;
  opponent submissionIds + scores visible in our own episodes → graph-walk to
  >1100 teams → GetEpisodeReplay → decks+actions readable. No auth needed.
- **What's next:** rpo decide #3062 (+ hold conversion to budgeted probes);
  harness capsule → mroute builds miner; then swap PCMM arms to top-meta
  reconstructions and rpo starts mh_search. ai-scientist coordinates evidence +
  probe bookkeeping only.
- **Any blockers:** rpo ack pending (enforcer backs up after 06:30Z).
- **EDDIE AUTHORIZATION 2026-07-12 ~06:1xZ (recorded verbatim intent):** if rpo
  does not ack esc-8f57f8aa02 by 06:30Z, ai-scientist DRIVES the external loop
  itself: assumes loop ownership (decide #3062 citing this authorization),
  becomes dispatcher for the mroute miner capsule, starts bene-mh surrogate-gated
  search, and operates the L3 probe budget per #3062. Coding stays delegated to
  mroute; ai-scientist drives via orchestration/MCP/frozen evaluators. This
  authorization supersedes the rpo hold posture in the no-ack branch.

## Status update 2026-07-12T06:3xZ (TAKEOVER EXECUTED — external loop live)
- **esc-8f57f8aa02 expired unacked 06:30:19Z; rpo silent since 04:19Z.** Posted
  decision #3069 on proposal #3062 (verified type=decision by read-back):
  ai-scientist ASSUMES external-loop ownership per Eddie order; rpo reclaimable.
- **L0 LIVE + producing:** replays confirmed AUTH-FREE (redirect-follow;
  correction #3068). Inline harvest: 8 unique top-meta decks (≤1106-rated) at
  runs/replay_mining/ + manifest. META FINDING: top decks play ZERO card-3
  energy (ours carry 33) — our whole deck search explored the wrong basin;
  dominant archetype core {6,678,1102,1141,1142,1152} across ≥6 top players.
- **First surrogate screens (frozen h2h, n40):** meta0_1106 deck under OUR
  frozen policy 25-15 (0.625) vs live-s14; meta2_1031 24-16 (0.600); meta1_1106
  8-32, meta4_983 11-29 → mined decks TRANSFER selectively; policy-deck
  coevolution confirmed necessary.
- **Running detached:** (a) full ladder chain meta0+meta2 (n160→n400→n400
  reconfirm, runs/replay_mining/ladder.log); (b) hop-2 harvest seeded at
  1106-tier targeting >1200 (hop2.log).
- **Dispatched:** COLLAB_CAPSULE ptcg-replay-miner → mroute (#3070; capsule doc
  in .fleet-goal/capsules/), base = origin merged head fca4dc4.
- **Probe policy under my ownership:** NO Kaggle slot until a candidate passes
  full confirm+reconfirm surrogate gates; Eddie/rpo notified before any consume.

## Status update 2026-07-12T06:5xZ (LOOP PIVOT: deck-transfer dead, policy is the gap)
- **Ladder verdicts (frozen h2h):** meta0_1106 deck n40 0.625 → n160 0.450 →
  n400 0.5075 [0.459,0.556] = confirm_out; meta2_1031 trending 0.459 @ n400.
  Deck-transfer under our policy ≈ parity — dead end, twice confirmed. Sharpest
  proof: ZETADIVISION deck 0.20 under our policy vs 1180+ under theirs → the
  620pt gap is POLICY. (Winner's-curse discipline caught the n40 mirage again.)
- **Hop-2 harvest:** reached 1220 tier (sid 54349578); 16 more decks
  (inline_harvest_hop2_20260712.json); all top decks zero card-3 energy.
- **CAPSULE 2 dispatched → mroute:** ptcg-imitation-policy (dataset from
  1100+ replays ≥5k (obs,action) pairs + stdlib-only distilled policy targeting
  dominant archetype {6,678,1102,1141,1142,1152}; frozen-gate acceptance).
  bene-mh benchmark adapter = follow-on capsule (mh needs a registered
  benchmark; candidates are def run(problem) harnesses — adapter is code →
  mroute, not coordinator).
- **Next:** miner CLAIM by mroute (note: mroute mid-escalation esc-0de9ce977c
  on its curator — may delay claims; harness owns that); meta2 chain finish;
  imitation dataset → policy → gates → probe decision w/ Eddie/rpo notice.

## Status update 2026-07-12T15:3xZ (🔴 IN-FLIGHT: paired meta0 gate trending A1-NEGATIVE — context-clear checkpoint)
- **Coordinator context may be cleared (Eddie notice). Ground truth for successor:**
  this file + capsules/ + evidence/M1/ + bus (a2a-coord.db, last relevant ~#3130)
  + two Monitors in session ai-scientist-6 (lane bus watch; paired-gate log watch).
- **Paired meta0 gate RUNNING** (detached pid on host, log:
  session scratchpad a1-gate/paired_meta0_ladder.log). Design: chain1 =
  A1-policy×meta0_1106 vs old-policy×meta0_1106 (policy delta where bugs bind);
  chain2 = A1×meta0 vs frozen s14 (historical ref old×meta0 = 0.5075 n400).
- **Chain1 so far: n40 0.45 → n160 0.5125 → n400 #1 = 0.395 [0.348, 0.444]**
  (Wilson-upper ≪ 0.50). If the second n400 + chain2 confirm: A1 is WORSE on the
  engine deck too — bug fixes alone are harmful everywhere tested.
- **Leading hypothesis (mechanism):** A1 gave deck-search SIGHT but ranks picks
  with `_card_keep_value`, whose extremes are INVERTED vs top play (they protect
  energy, shed spare Pokémon — verified finding #5, scheduled for Phase B).
  Blind index-0 was accidentally aligned (cf. EVOLVE index-0 = 94% top-play
  match); sighted-with-inverted-values is confidently wrong. ⇒ A1 (sight) and
  B (correct value model) are COUPLED — never ship/gate A1 alone again.
  Attribution test when B lands: ENABLE_DECK_SIGHT=off should recover most gap.
- **Worker:** mroute-1→mroute-2 baton (bus #3130), Phase B in prep (ablation
  flags ENABLE_RETREAT_FIX/ENABLE_TARGET_TIEBREAKS/ENABLE_DECK_SIGHT + reorder).
- **Next actions:** (1) await chain1 reconfirm + chain2 → commit evidence memo;
  (2) relay to mroute: B priority rises, A1+B gate as ONE candidate;
  (3) then attribution 3×n160 with B's flags. NO Kaggle slots; s14 live.

## Status update 2026-07-12T11:3xZ (⚠️ A1 GATE: MIRROR REGRESSION — co-adaptation cuts both ways)
- **PR #21 MERGED (ca937183)** after one review round (area-aware bug4 + format;
  merge race with mroute's restore force-push resolved — trees verified identical).
- **A1 gate result (bug-fixed policy × UNCHANGED s14 deck vs frozen live-s14):**
  n40 0.575 (mirage #6) → n160 0.500 → n400 0.4625 → n400b 0.4525;
  **combined n800 = 0.4575 [0.423, 0.492] — Wilson-upper < 0.50, a real mirror
  REGRESSION.** Evidence: evidence/M1/2026-07-12-a1-gate-results.md.
- **Reading:** deck↔policy co-adaptation confirmed in REVERSE — top-player-correct
  mechanics hurt the degenerate 33-energy deck; the old bugs were accidental
  co-adaptations. Does NOT test the M2 joint intervention (fixed × mined deck),
  which is now the only informative experiment. A1 stays merged as lineage base;
  NO A1-only bundle promotion; champion s14 untouched.
- **Consequences wired:** B/C gates must pair with mined decks (fixed×mined vs
  old×mined AND vs s14 bundle); mroute asked to expose per-pathway ablation
  flags in B for cheap attribution (3×n160). Mirror-only gates are now known to
  mis-rank policy work in both directions.
- **mroute:** A2 dataset builder in progress (alignment #3098 + 4 invariants).

## Status update 2026-07-12T11:2xZ (🔬 PLATEAU ROOT-CAUSE VERIFIED — READ FIRST)
- **Analysis complete (Eddie's ask):** evidence/M1/2026-07-12-plateau-root-cause-analysis.md
  (31-agent workflow wf_fc1549e0-ff8, 0 errors — the verify phase that died on spend
  limit in wpgxy045l now COMPLETE: 24 adversarial verdicts on 12 claims × 2 lenses).
- **Verdicts:** bugs 1/3/4 + orderings 1,2,3,5,6 CONFIRMED×2. TWO CORRECTIONS:
  (a) bug2 select-level fix DOWNGRADED — ~3 divergent decisions/106 games
  (ATTACH_TO never carries inPlay* 0/103; EVOLVE index-0 = top play 94%);
  (b) BENCH_TARGET 3→5 REFUTED (non-binding for bench count; wrong direction
  intra-turn). Also: bug1 PRIZE half is a no-op (hidden info); bug4 negligible
  until a Night-Stretcher-class meta deck is adopted; bug4 fix must be
  area-aware, NOT removal from SELF_LOSS_CONTEXTS.
- **NEW ROOT CAUSE (unowned):** deck_search.py is_legal floors (Kyogre>=2,
  {W}energy>=15) exclude ALL 14 mined meta decks — the whole 2,857-deck archive
  lives in a caged region (max Jaccard 0.11 to any meta deck; we run 1 of the
  5-6 near-universal staples). Needs a follow-on capsule before any future deck
  search matters.
- **Rating mechanics:** all submissions enter at 600; volatility band ~182pts;
  607.6 ≈ parity-with-pool equilibrium; per-poll effects <~100pts unmeasurable.
  Bottom line: ship policy-fixes × mined-deck as ONE joint intervention, gate
  n400 vs s14 AND vs >=2 mined meta decks, then ONE probe slot; treat <+100pt
  poll delta as unresolved (not failed).
- **mroute pipeline:** capsule 1 MERGED+audited (PR #20 → 30ef89fb); capsule 2
  Phase A CLAIMED — A1 bugs cleared by mroute's own 6-verifier pass (#3097),
  alignment algorithm delivered (t+1 convention, invariants, ref code committed);
  Phase B verdicts relayed → UNBLOCKED with corrected scope. Capsule 3
  (mh-surrogate-adapter) revised per Eddie's Meta+Continuous directive
  (static pre-screen, evidence cards, k>1 n600/alpha-spending, racing arms).

## Status update 2026-07-12T10:0xZ (✅ AUTH CLEARED; mroute BUILDING — READ FIRST)
- **Session baton:** ai-scientist-6 took over from ai-scientist-5 at 09:57Z (G1 serial
  handoff; predecessor retired, sweep daemon transitioned).
- **AUTH DEADLOCK RESOLVED (supersedes "get auth unblocked" below):** human:eddie
  voted +1 on proposal #3062 (bus #3083, 09:07Z), issued explicit AUTHORIZATION #3084
  (ai-scientist = OWNER + DISPATCHER + MERGE_OWNER of the PTCG external loop;
  supersedes 0-vote decision #3069), and ACKed esc-bc98b337e6 (#3085).
- **Capsule 1 (ptcg-replay-miner) CLAIMED by mroute** (#3086, 09:11Z); build in
  progress in worktree /home/admin/gh/wt/ptcg-18-replay-miner (pane verified 10:02Z —
  live replay-endpoint probes). Coordinator babysits to MERGED per merge_owner.
- **Capsule 2 (ptcg-imitation-policy) auth-cleared, queued.** NO data dependency on
  the miner: existing corpus (106 raw replays, 9,267 multi-option pairs) already
  clears the >=5k acceptance bar; bugs 1-4 need zero new data. mroute starts it the
  moment capsule 1 lands.
- **Detached chains COMPLETE:** META_LADDER_DONE 06:49:56Z (meta2 n400b final 0.460
  [0.412,0.509] — deck-transfer closure stands, no revision); hop-2 harvest artifacts
  landed (inline_harvest_hop2_20260712.json).
- **Probe policy unchanged:** champion s14 live at 607.6; NO Kaggle slot without full
  confirm+reconfirm surrogate gates + Eddie/rpo notice.

## Status update 2026-07-12T09:1xZ (🔴 BREAKTHROUGH: divergence measured — READ FIRST)
- **What's done:** corpus expanded to 106 replays; workflow wpgxy045l replayed OUR
  policy against **9,267 real multi-option decisions by >=1100-rated players**.
  **AGREEMENT = 40.6%.** MAIN bucket (62% of decisions) = 28.2%; mean rank of THEIR
  pick under our scorer = 4.57. The imitation thesis is CONFIRMED — and the gap is
  **mostly BUGS**: blind deck/prize search (19.8% of decisions are coin-flips),
  blind evolve/attach target (100% blind), retreat NEVER fires (0/6071),
  CTX_TO_DECK misclassified. Biggest behavioral miss: OPT_ABILITY(25) < OPT_ATTACK(30)
  ⇒ we fire abilities 1.7% vs their 44.1% — the draw/search engine is disabled.
  Full spec + MAIN_SCORES rewrite: evidence/M1/2026-07-12-policy-divergence-imitation-spec.md
  (committed 098eeae; bus #3087). Capsule ptcg-imitation-policy points at it.
- **What's next (SUCCESSOR — this is the top of the queue):** get auth unblocked, then
  mroute fixes bugs 1-4 (verifiable by READING policy.py — no stats needed) + reorders
  MAIN_SCORES → n40/n160/n400/n400-reconfirm h2h ladder → mixed-field vs 1180-tier decks.
  Pair the fixed policy with a mined top deck (policy+deck must move TOGETHER — that is
  why deck-transfer alone failed).
- **Any blockers:** AUTH (below). Also: workflow verify phase died on a monthly spend
  limit (25/30 verifiers errored) → findings are count-grounded but NOT independently
  refuted. Bugs 1-4 need no stats; verify them by reading the source.

## Status update 2026-07-12T07:0xZ (deck-transfer CLOSED; auth dispute pending)
- meta2 final rungs: n400 0.4675 [0.419,0.516], n400b 0.460 — BOTH mined decks
  sub-parity at high N. Deck-transfer negative result FINAL (bus #3079-ish).
- AUTH DISPUTE (mroute, procedurally correct): decision #3069 is 0-vote; both
  capsules DISPATCHED-pending-auth (ledgers updated). Resolution = harness
  adjudication (esc-bc98b337e6) OR rpo cede OR human:eddie decide on 3062.
  Eddie given the exact one-line command in-session. NO claim/merge meanwhile.
- IMITATION DATASET SIZED (16 raw replays archived): ~159 pairs/replay, 96%
  single-option selects → option-scorer re-weighting, stdlib-distillable;
  5k bar ≈ 31 replays. Capsule 2 de-risked; mroute starts warm post-auth.

## What's next (decision points for rpo/Eddie)
- CHAMPION s14 is live on the ladder accruing rating — no action needed there.
- BFTS relaunch: NOT recommended as-is (reproduces undeployable torch artifacts);
  if pursued, constrain idea to deployable heuristic/search policies + launch
  DETACHED (session-bound compute died once — see memory long-compute-durability).
- weco-search round-2 (productive lineage, died too): resumable via
  `weco run derive d0895b64 --from-step 14` if continuing to hunt > s14.

## Historical blockers snapshot (superseded by current status updates)
- NONE. Creds delivered + installed 2026-07-10 ~20:49Z (esc-ced2411dbe acked);
  first submission live (ref 54539022).

## [M1-HISTORICAL — RETIRED 2026-07-12 per rpo condition (a), bus #3203]
The completion bar below predates the negative closure and contradicts it (it
assumed a positive result: "evolved agent beats seed >=+5pts AND submission
validates"). M1 closed as an honest NEGATIVE result (GOALS.md M1 section);
M2's bar supersedes. Preserved verbatim for the record:

## Completion evidence offered for rpo approval [RETIRED]
- E1: local winrate table (seed vs evolved) from experiment_data.npy — reproducible
  via scripts/ptcg_eval.py.
- E2: BFTS run artifacts (journal.json, best_solution_*.py, tree_plot.html) under
  ~/gh/AI-Scientist-v2/experiments/<ts>_ptcg_agent_evolution_attempt_0/.
- E3: validated submission.tar.gz + (post-creds) Kaggle submission id + validation
  episode result + leaderboard rating.
Proposed completion bar: evolved agent beats seed baseline locally by a clear margin
(≥+5pts mean winrate) AND a submission validates on Kaggle. Rating targets need
ladder data, not promises.
