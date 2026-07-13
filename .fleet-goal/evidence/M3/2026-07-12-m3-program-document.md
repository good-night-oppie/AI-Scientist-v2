<!-- committed by ai-scientist-7, 2026-07-13. Source: 7-agent measured design workflow (4 recon lanes + 2 adversarial verdicts + synthesis). PENDING AMENDMENT: fable-5 dual-seat external review (TeamClaude) — rate-limit-delayed; will be appended as a review annex, not edited into the body. Eddie ratifications on record: AlphaZero-shaped core; rules-first design; GBM-before-transformer challenge accepted as the racing baseline. -->
# M3 PROGRAM DOCUMENT — "Our Own LLM": harvest → imitation → self-play → gate
<!-- commit as: .fleet-goal/evidence/M3/2026-07-12-m3-program-document.md -->
Date: 2026-07-12 · Author: coordinator (design synthesis from 4 recon lanes + 2 adversarial verdicts, all numbers measured on this host or the live API today) · Status: PROPOSED — Phase 0 blocks everything

---

## 1. WHY THIS CAN WORK WHERE FOUR METHODS FAILED

Search-tuning (exhausted, 3 independent confirmations), deck-transfer (dead, twice n400), off-policy imitation for our deck (impossible: 0/76,405 supervision records at Jaccard≥0.5 — nobody plays our deck), and the linear ranker (176 weights, card-identity channel ~64% of |w| inert on our deck) all failed for the same structural reason: **no on-policy data existed for anything we field, and the model class couldn't absorb what data did exist.** This program removes both constraints by mechanism, not hope. (a) **Self-play manufactures unlimited on-policy data for whatever deck we field** — the local engine is the exact vendored competition engine at 0.30–0.34 s/game measured (3,444 eval JSONs, median 0.336), giving 0.9–2M heuristic games/day and ≥50–70k NN-in-loop games/day (adversarially verified as a floor; ceiling 180–530k/day with 1 pinned BLAS thread/worker) — the 0/76,405 problem is killed by construction. (b) **45–60K harvestable human replays (~6–8M supervision records, 25–30× today's corpus) supply the prior and the opponent league** — full obs/action/reward trajectories, verified sufficient for imitation. (c) **The model finally has capacity and the right shape**: a deck-conditional pointer transformer (0.1–20M params) over variable legal-option sets, versus a linear perceptron already proven to beat our champion's brain (+14.3pp MAIN agreement) at 176 weights — capacity was never even reached. **The honest failure mode:** if the engine's reward structure admits degenerate strategies, self-play will find and converge to them faster than any human meta would; the ONLY defense is that promotion runs exclusively through the frozen mixed-field worst-arm gate (aaa1156), plus a pre-registered self-play collapse detector (G4). If the gate and the league don't catch it, nothing will — so they are not optional.

---

## 2. PHASE 0 — DEPLOYABILITY GATE FIRST (blocks all training; the s14/BFTS lesson)

BFTS "undeployable torch" was import-risk + weights-never-serialized, not a size or time cap. We do not repeat it: **nothing trains until the runner's importable set is proven by execution.**

**The probe (<1 day to build, 1 validation-episode slot, $0, Eddie's slot decision alone):**
- Clone the proven 503KB stdlib champion bundle shape (54554870, live at 592.2; stdlib deployability proven twice by execution).
- `main.py` module top: guarded `try: import numpy/torch/jax`; print version-or-ImportError + `perf_counter` per-decision timings to stderr (under the 10k-char/step log cap; Eddie downloads agent logs via the UI flow).
- **Redundant behavior encoding**: first multi-option decision picks the 2nd-ranked legal option iff numpy imported, else 1st — the answer is recoverable from the public episode JSON via the auth-free kaggleusercontent endpoint even with zero logs.
- Never-raise, kaggle_agent defined last, no `__file__` in main.py (54539022 lesson), no SearchBegin, no libcg.so needed.

**Outcome branches (pre-registered):**
- numpy confirmed (near-certain: declared dep of kaggle-environments 1.32.0, the exact version Kaggle runs) → unlock 3M params @50ms / ~19M @500ms numpy inference tier, stdlib forward kept as in-bundle fallback (identical argmax).
- numpy absent → pure-python tier only: d=64, 2–4 layers, ctx≤48, ≤250K params @500ms (math.sumprod, 85–110 MFLOP/s measured) — still viable — or GBM-compiled-to-stdlib.
- torch: **excluded at inference forever.** Torch is the local training harness only.

**G0 kill number:** probe bundle errors on the real runner, or local runner-faithful p95 latency >1s/decision → NN program halts before any training spend; GBM/stdlib tier proceeds alone.

Real-runner timings from the probe calibrate the 2× runner-slowness margin. Budget context: actTimeout=0, 600s overage pool, max observed 191 decisions/seat → 3.1s worst-case ceiling; design target 500ms mean (6× margin), adaptive throttle via `obs.remainingOverageTime`.

---

## 3. PHASES — owners, costs, acceptance, kill numbers

### Phase 1 — MASS HARVEST (owner: sctst-aide; starts immediately, does NOT wait for Phase 0)
**Urgency is mechanical, not rhetorical:** hot top sids play 100–337 eps/day against a rolling 1000-episode API window — unharvested top-tier episodes are destroyed in ~3–4 days. And the current corpus is meta-stale: 60% of top-1100 supervision (45,670/76,405) comes from teams now ranked 31–288 (kazuki0123 crashed 1199→995). Every day of delay loses ~5–15k episodes forever.
- **Spec:** sid-frontier walk (teamId filter is 400-dead — verified; `{submissionId}` and `{ids:[...]}` are the only live filters). Seed from 3–5 known sids → merge `teams[].publicLeaderboardSubmissionId` (523 teams from 3 calls already) → top-50 teams (cutoff ~1096) → 214 known sids → ~45–60K unique episodes (70–90× corpus).
- **Transfer/storage:** 160–215GB transferred at mean 3.61MB/ep; **zstd -3 on write is mandatory** (48.1× measured) → 6–9GB stored of 310GB free. New dir `runs/replay_harvest/{raw/ep_<id>.json.zst, index/episodes.jsonl, index/teams.jsonl, cursor.json}`. **Never write `runs/replay_mining/` (sole copy, read-only).**
- **Pacing:** ≤2 req/s hard; 429 verified real at ~1.8 req/s sustained → exponential backoff, resumable cursor, "raw file exists = done" idempotency. Backfill 1.5–2 days detached (setsid nohup, stable logfile). Daily top-up cron: ~100–150 ListEpisodes + 5–15k eps/day (0.7–2.1h, 0.4–1.2GB/day stored).
- **PAT roles only** (Eddie-authorized, read at point of use, NEVER echoed): Meta Kaggle dataset pull (competitionId 116727) as the completeness backstop, leaderboard CSV for canonical top-N, later dataset push for GPU training. The replay harvest itself is unauthenticated (both endpoints verified live today).
- **Rating filter dropped at harvest time**: store seat ratings; ≥1000 keeps 84.1% of seats (vs 30.8% at ≥1100) → rating-conditioned training becomes possible; top-1100 supervision still grows 76,405 → ~1.9–2.4M.
- **Acceptance:** ≥30K unique new episodes indexed (sha256 + agents/ratings), schema canary green, 4 dataset invariants re-asserted per batch. **Kill numbers:** unique yield <10K episodes after full top-50 sweep → re-scope to Meta-Kaggle-first; 429-block persisting >24h at 1 req/3s → halt and escalate; free disk <60GB → hard stop.

### Phase 2 — OFFLINE TRAINING (owner: mroute; ~1 week local; gated behind Phase 0)
- Rebuild dataset `--all-seats` (terminal reward already on every record); tokenizer = **one pure function over (current, select, deck) imported by both trainer and bundle** (the featurize train/serve-identity pattern). Training venv is NEW, outside the read-only worktree (worktree venv has no torch). mmap npz shards (~8GB free RAM is the binding local resource).
- **Objective ladder:** win-weighted BC (winner-seat w=1, loser β∈{0, 0.25}) → AWR/IQL-lite (value head pretrained on winner-prediction over ALL records) → distillation targets from Phase 3. Stratify/temperature-sample by team (top-8 teams = 81.8% of current supervision; unstratified BC learns two archetypes).
- **Model-S:** ~1M params, d128/L4–6, pointer + value heads. Local CPU 30 epochs = 2–6h (adversarially verified; the 5.5h estimate was conservative). Harvest scale (~1M+ pairs) → Kaggle free GPU (T4/P100 epoch 2–4 min, <2h/run, 30h/wk quota; corpus push ~1.0–1.5GB gzipped, measured 34.2×); AWS g5.xlarge A10G ~$1/h via aws-openmythos only if quota binds (creds reactivation = Eddie step).
- **GBM baseline races under the pre-registered decision rule** (wild-ideas T1/T2): LightGBM + dynamic-trajectory features, trains in minutes, compiles to stdlib if/else.
- **G1 kill number:** model-S held-out **episode-disjoint** MAIN top-1 agreement <0.505 (linear anchor 0.4749 + 3pp; heuristic anchor 0.3318 on 679-corpus — re-derive anchors on every new dataset build) within 30 epochs → **transformer killed**, GBM path proceeds alone.
- **G5 engine-drift gate (blocks Phase 2 start):** corpus recorded on cabt 1.30.1, local vendored is 1.32.0 — diff the cabt trees + hash libcg.so; re-assert the 4 dataset invariants on every harvest batch before it enters training.

### Phase 3 — SELF-PLAY LEAGUE (owner: mroute; 2–3 weeks, 3–4 expert-iteration rounds)
- **Expert iteration, not PPO:** train-time policy+value-guided determinized search on the exact engine generates improved targets; distill back into the policy. **The bundle ships the distilled net ONLY — no search at deploy** (makes the s14 silent-search-death class structurally impossible).
- **League pool:** frozen s14, frozen s18, linear imitation bundles, **Arm A/B joint units as they land**, heuristic bots on mined meta decks, past frozen checkpoints (recency+diversity sampling). Both seats get REAL decks: ours + current-meta modal lists — **recentered on the current top-6 (taksai/kashiwashira/vibechu/Majkel1337/S4nkurero/Budew), not the faded kazuki0123 anchor (now 995, below the top-tier floor)**.
- **Throughput:** round = 200–300k games, 3–5 days local at the verified 50–70k NN-games/day floor (pin OMP/OPENBLAS_NUM_THREADS=1 per worker or you live in the 5× slower contention regime — measured). 8 workers ≈ 3GB RSS + capped mmap trainer fits ~8GB free. Retrain rounds on Kaggle GPU.
- **Checkpoint rule (pre-registered):** every round, n400 vs the FROZEN mixed field; a checkpoint replaces the incumbent only if worst-arm Wilson-lo improves AND macro≥0.55. **League/self-play winrate is NEVER a promotion metric.**
- **G4 kill number:** frozen-field macro degrades >2pp over 3 consecutive rounds → halt loop, revert to last good checkpoint, root-cause before any restart (degenerate-strategy detector).

### Phase 4 — THE GATE (owner: coordinator runs the instrument via mroute; slot = Eddie alone)
- **aaa1156 verbatim, no new instrument:** screen n40 macro≥0.55 / worst≥0.40 → confirm n400 macro≥0.55 / worst-arm Wilson-lo≥0.50 → independent reconfirm. n40-only numbers are mirages (six recorded, both directions).
- Liveness=LIVE required (I1–I7 extended to bundle_kind='nn', §6). validate_nn adds: p95 per-decision ≤0.5s and total think ≤60s/game in runner-faithful `make('cabt')` self-play; first-call weight-decode time measured and bounded.
- Ship: numpy inference + stdlib fallback, int8/fp16 weights, **first NN submission ≤5MB compressed** (bundle cap unverified; 100MB is convention, not evidence).
- **Kill:** any floor missed → no promotion, back to Phase 3 or dead. The Kaggle probe slot decision is Eddie's alone, every time.

---

## 4. COMPOSITION WITH THE IN-FLIGHT ARM A/B BATTERY (nothing pauses)

- The battery runs to completion untouched. Its **mixed-field instrument is the same instrument** the NN faces — no new gate is built for M3.
- Its **gate results are the baselines** the NN must beat (worst-arm Wilson-lo over incumbent), and its **joint bundles join the Phase 3 league pool** as opponents the day they land.
- Its dataset/anchor work (0.4749 linear MAIN agreement) is the G1 kill line.
- **Integration hazard (pre-registered fix):** the NN bundle must register a distinct `bundle_kind='nn'` in eval_search_head2head.py, or keep counter names byte-identical to the imitation kind — otherwise I7 fires spuriously. The NN branch bases on **liveness commit 0c017a4 (pr/ptcg-29-armAB-battery)**, NOT feat/ptcg-agent HEAD 5d89227, or the gate hooks don't exist.
- Harvest output feeds both: the same `runs/replay_harvest/` layout is the imitation-corpus source for the battery's follow-ups and the LLM's training set.

---

## 5. WORK SPECS

### 5a. mroute (implementation — coordinator does not code)
1. **Phase-0 probe bundle** (≤1 day): per §2. Deliverable: tarball + local runner-faithful validation transcript (imports, per-decision timings, behavior-encoding verified in a local episode JSON). Hand to Eddie for the slot decision.
2. **Harvester deltas + PAT-gated helpers** (composes with the in-flight --raw-dir spec, commit 55cb9a1): (i) dedup by EPISODE id, not deck key; (ii) zstd-on-write raw persistence, atomic tmp+rename; (iii) frontier seeding from `teams[].publicLeaderboardSubmissionId`; (iv) schema canary — fail loud on response-shape drift (ListEpisodes proto already changed once: teamId filter removed, GetEpisodeReplay 404'd); (v) separate PAT-gated scripts (Meta Kaggle pull, leaderboard CSV, dataset push) that resolve the token via the standard kagglesdk path (`uvx --from kaggle kaggle ...` reading ~/.kaggle/access_token) — **the token value is never read into a variable, never echoed, never logged.**
3. **Tokenizer/trainer skeleton**: one pure tokenizer (deck-prefix + opp-model + global + selhdr + board×12 + hand≤20 + per-option tokens; ~70 typ/~130 max tokens; card vocab 1,267); pointer head (softmax CE single-pick; per-option BCE + count head multi-pick) + value head; win-weighted BC + AWR; GBM baseline harness; new venv outside the worktree; mmap shards; `--nn` builder extending build_submission_search.py's --imitation path (same STATS/I1–I7 shape, drops cg/libcg.so entirely, weights located via `os.path.dirname(__file__)` INSIDE agpkg — main.py has no `__file__`).

**Standing hazards (all have burned us):** Edit-tool changes to tracked files in ready-player-one-ptcg are silently reverted by a formatter hook — Bash-write + manual ruff format (PR #21 lesson). `runs/replay_mining/` is the sole corpus copy in a divergent read-only worktree — never write, never rebase. The FLEET-KILLER reaper is still live on ptcg-run — never add psutil, never run the launcher unpatched there. Long jobs launch detached (setsid nohup, stable logfile) or the sweep's session retirement kills them (that is how the BFTS weights died). Keep command output bounded — write logs to files and tail summaries (output-token blowouts).

### 5b. sctst-aide (harvest execution — frozen-miner discipline)
Execute Phase 1 exactly per §3: reuse the frozen `scripts/mine_replays.py` seams (RateLimiter 0.5s, injectable list_fn/replay_fn, load_state/save_state resumable cursor) with mroute's deltas. ≤2 req/s hard, exponential backoff on any 429/5xx (429 is real — tripped at ~1.8 req/s today, recovered after 75s at 3s spacing), honest UA, --max-requests budget knob. Incremental persistence: cursor saved after every fetch; interruption costs nothing. PAT: only for the Eddie-authorized backstop/CSV/push steps, read at point of use, **never echoed into a pane/log/handoff** (pane output is snapshotted to disk fleet-wide). Disk check before every batch; compressed writes only; alarms on daily volume (>2×) and on the 1000-cap gap condition; detached run + daily cron.

---

## 6. WHAT WE TELL RPO

**Declaration:** M3 = harvest → deck-conditional pointer-transformer (with a racing GBM baseline under a pre-registered decision rule) → expert-iteration self-play → the existing gate. Design-only at coordinator level; mroute builds, sctst-aide harvests.

**Gate discipline: unchanged, verbatim.** aaa1156 floors exactly as pre-registered (n40 screen macro≥0.55/worst≥0.40; n400 confirm macro≥0.55/worst-arm Wilson-lo≥0.50; independent reconfirm). n40 = mirage stands. The Kaggle slot remains Eddie's alone, including the Phase-0 probe. No new promotion instrument is introduced; self-play/league winrate is explicitly non-evidential.

**Liveness extended, not forked:** I1–I7 map verbatim onto bundle_kind='nn' (I1 import incl. import_nn_ok; I2 weights_n>0; I3 env-override unset; I4 nn_ok==decisions & fallbacks==0; I6 token-coverage floor before I5 nontrivial-score floor; I7 cross-module counter agreement), plus one new assertion: p95 per-decision ≤0.5s and first-call decode bounded, certified in runner-faithful local play before any slot is requested.

**Pre-registered kill numbers:** G0 probe fails/p95>1s → no training ever happens. G1 MAIN agreement <0.505 episode-disjoint in 30 epochs → transformer dead, GBM proceeds. G4 >2pp frozen-field macro decay over 3 rounds → self-play halted. G5 engine-diff/invariant failure → batch quarantined. Phase-1 yield <10K unique episodes → harvest re-scoped.

**Honest timeline and honest framing:** Phase 0 ≈ 1 day + slot latency; Phase 1 backfill 1.5–2 days (starts now — the rolling window is destroying data); Phase 2 ≈ 1 week; Phase 3 ≈ 2–3 weeks; **first gate-eligible NN candidate ≈ 4–6 weeks**, with a possible GBM candidate gate-eligible in 1–2 weeks. We do not promise 978+. Eddie is right that prior methods failed — ~600 vs 978–1279 is the fact this program exists to answer. What M3 promises is narrower and checkable: unlimited on-policy data for our deck, a model class with actual capacity, deployability proven before a single training FLOP, and candidates that either pass the same gate everything else failed or die at a numbered kill line.