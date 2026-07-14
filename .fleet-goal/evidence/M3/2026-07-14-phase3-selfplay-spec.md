# PHASE-3 SELF-PLAY SPEC — expert iteration on the verified engine, gated kill-only vs s14

Date: 2026-07-14 · Author: ai-scientist-8 (coordinator) · Status: PROPOSED — awaiting rpo review
against the four standing rules of #3347 (which green-lit Phase 3 and pre-stated its review bar).
Base doctrine: M3 program doc §3 Phase 3 + §5a.3, field v3 prereg (+2026-07-14 annex), rpo #3347.

## 0. WHY SELF-PLAY, ONE PARAGRAPH (the surviving logic)

Four levers are falsified on the correct engine with no dead-instrument escape: search-tuning
(3× confirmed), deck-transfer (twice n400), policy-transfer (64% inert weight), and now the whole
off-policy imitation/agreement family (0-for-4 at gates; its best member — GBM, 0.5181 MAIN —
killed hardest at 0.125 vs s14, fully instrumented). The ~500 MMR gap lives in the POLICY;
nobody plays our deck, so no mineable data can teach it. Self-play is the only method that
manufactures unlimited on-policy data for the deck we field and bootstraps past its teachers —
it needs no ladder-strength field (the league's job is diversity, not calibration). The honest
failure mode is league-overfit (C3, named and open); the defenses are §5 and the gate's kill
authority, which is now 4-for-4.

## 1. THE GATE (rpo #3347 ruling 1, verbatim — kill-only, single arm s14)

- **SCREEN n40 vs s14: kill if point winrate < 0.55.** n40 kills or is silent, never supports.
- **CONFIRM n400: kill unless Wilson-lo ≥ 0.50.**
- **INDEPENDENT RECONFIRM n400, fresh batch: same floor.** The reconfirm stays (M1 lesson;
  d40d9dd567 precedent: confirm 0.534 → reconfirm 0.464).
- Retained: zero-invalid; both-seat balance. Dropped-by-collapse: worst-arm fragility (accepted —
  fragility vs other decks is the ladder's job).
- **Liveness to the GBM gold-standard bar** (I1–I7 + six negative controls each failing loud on a
  distinct invariant) **+ the NN deployment-fidelity check**: numpy inference vs stdlib fallback
  must agree byte-for-byte on argmax over a full val sweep — the NN analog of the GBM transpile
  proof (100% on 103,296 rows). bundle_kind='nn' registered in the evaluator with I1–I7 mapped
  verbatim (or counter names kept byte-identical; program-doc §4 hazard).
- **A gate pass earns exactly one thing: a probe REQUEST to Eddie.** Never a promotion.

## 2. PROBE-REQUEST THRESHOLD (rpo rule 4 — PRE-REGISTERED HERE, above the kill floor)

The ladder's measured resolution is ~75–100 MMR at n≈50 (noise-floor reading, #3339). A marginal
local winner is below that resolution; a probe on it returns noise and burns one of Eddie's slots.

**Pre-registration: a probe request may be made ONLY for a candidate that clears BOTH n400 confirm
AND independent reconfirm at Wilson-lo ≥ 0.55** (point estimate ≈0.60+ twice, n800 pooled
evidence of decisive dominance over the champion). This maps the old guardrail-(7') numbers
(macro ≥0.60 / worst Wilson-lo ≥0.55, checkpoint §"Decisions locked") onto the single-arm field —
no new number invented. Candidates in the kill-survivor band (Wilson-lo 0.50–0.55) are HELD:
recorded, kept in the league, re-gated after further rounds — not probed, not promoted, not dead.

## 3. THE MODEL AND THE LOOP (program doc §5a.3, unchanged where not superseded)

- **Model-S**: deck-conditional pointer transformer, ~1M params (d128/L4–6), pointer head
  (softmax CE single-pick; per-option BCE + count head multi-pick) + value head. Tokenizer =
  ONE pure function over (current, select, deck) imported by trainer AND bundle (train/serve
  identity; the featurize lesson). Card vocab 1,267; ~70 typ/~130 max tokens.
- **Init prior**: win-weighted BC on the 76,405-row corpus (winner-seat w=1, loser β=0.25),
  team-stratified. G1 asymmetry stands (rpo #3320): a weak interim prior is NOT a kill — it is
  an init. If BC-init shows the anti-proxy trend in early league play (imitating mid-tier hurts),
  fall back to FROM-SCRATCH init (AlphaZero-pure) — decided by round-1 frozen-field macro, logged.
- **Expert iteration, not PPO**: at train time, policy+value-guided determinized search on the
  exact engine produces improved targets; distill into the policy; repeat. **The bundle ships the
  distilled net ONLY — no search at deploy** (kills the s14 silent-search-death class).
- **Round** = 200–300k games, 3–5 days at the verified 50–70k NN-games/day floor.
  OMP/OPENBLAS_NUM_THREADS=1 pinned per worker (measured 5× contention penalty otherwise).
- **Torch is the local training harness ONLY; inference is numpy + stdlib fallback, forever**
  (standing rule, addendum 4). Torch gets installed on arena-1 for training; it never enters a
  bundle.

## 4. THE LEAGUE (structural immunity — rpo rule 2)

- Pool: frozen s14, frozen s18, linear imitation bundle, **GBM bundle (new, killed-as-candidate,
  useful-as-opponent)**, heuristic bots on the CANONICAL top-6 decks (Majkel1337 / Yushin Ito /
  bono / Budew / THIRD PTCG Club / MPGaming — canonical_top6.json; kashiwashira + S4nkurero as
  unlabeled diversity; taksai + vibechu extra), past frozen checkpoints (recency+diversity
  sampling). Both seats get REAL decks: ours + the canonical-top-6 modal lists.
- **Self-play checkpoints are LEAGUE SPARRING PARTNERS, never promotion arms** — no ladder
  standing by construction, rule (1a). s14 is the sole promotion arm. League/self-play winrate is
  NEVER a promotion metric.
- **live_ladder_snapshots mandatory and populated in every summary JSON.**
- **Deck backbone refreshes from the live harvest every round** (rule 3; the only cheap C3
  defense). Source: sctst-aide's daily top-up index — freshest modal lists for the canonical
  top-N, re-derived per round and logged in the round summary.

## 5. COLLAPSE + OVERFIT DETECTION (G4 and the named C3 blind spot)

- **G4 (pre-registered kill)**: frozen-field macro degrades >2pp over 3 consecutive rounds →
  HALT loop, revert to last good checkpoint, root-cause before restart.
- **Checkpoint-replacement rule (league-internal, not a gate)**: a checkpoint replaces the
  incumbent only if frozen-field worst-arm Wilson-lo improves AND macro ≥ 0.55, n400.
- **C3 (league-overfit) is UNDETECTABLE locally by construction** — all local numbers go up while
  the ladder would eat the candidate. Defenses on record: league deck-diversity refresh per round
  (§4), the probe-threshold discipline (§2 — only decisive dominance gets a slot), and honest
  labeling of the blind spot in every gate report. 2c1368bc03 is the precedent.

## 6. EXECUTION PLAN (owner: adx-server on arena-1; coordinator audits per milestone)

arena-1 is the verified quiet box (engine 7acbfc7b C2-MATCH; the GBM kill is clean BECAUSE it ran
there — rpo). Training and gating share it under a **pause-for-gate discipline**: all self-play
workers SIGSTOP'd (or cleanly paused at an episode boundary) during any gate window; loadavg
recorded before/after every gate run; a gate run with training active is inadmissible by
construction.

- **P3.0 — pipeline shakedown** (dispatchable NOW under addendum-5 authority, in parallel with
  this spec's review): torch install (training-only venv), tokenizer + trainer skeleton, mmap
  shards from the 76K corpus, train/serve-identity unit test (one pure tokenizer imported by
  both), BC-init training run (interim corpus = shakedown, no kill authority). Deliverable:
  training loss curve + a bundled-and-liveness-certified BC-init bundle (its gate number, if run,
  is diagnostic only — we already know imitation loses; it is the league's first learned opponent
  and the loop's starting point).
- **P3.1 — league harness**: pool loader (frozen artifacts above), deck-refresh hook reading the
  harvest index, round scheduler, per-round summary JSON (live_ladder_snapshots, seat splits,
  frozen-field macro history), G4 detector wired to halt.
- **P3.2 — expert-iteration loop**: search-guided target generation on the exact engine,
  distillation trainer, checkpoint freezer, round cadence 200–300k games. First round at reduced
  scale (50k games) as an end-to-end rehearsal before full cadence.
- **P3.3 — candidate path**: NN bundle builder (numpy + stdlib fallback, int8/fp16, ≤5MB
  compressed first submission), liveness certification to the GBM bar + deployment-fidelity, then
  the §1 gate on any checkpoint that the league says dominates. Verdict language is the
  coordinator's; slots are Eddie's.
- Standing hazards carry: detached long jobs (setsid nohup, stable logfile); no psutil; bounded
  pane output; no PAT in any training path; ~/gh/rpo-ptcg on arena-1 has no git creds by design —
  artifacts ship by tar/ssh-cat, evidence commits happen on this host by the coordinator.

## 7. TIMELINE, HONESTLY

P3.0 ≈ 1–2 days (shakedown). P3.1+P3.2 ≈ 1 week to first full round. 3–4 expert-iteration rounds
≈ 2–3 weeks. First gate-eligible NN candidate ≈ 3–4 weeks from spec approval. The transformer G1
learning-curve question (kill authority on the mature corpus) resolves in parallel as the
harvest top-up reaches 20K/25K/30K — if the G1 curve is FLAT across 17→30K, the BC prior is dead
but the self-play loop is NOT (from-scratch init path, §3). We do not promise 978+; we promise
candidates that either beat s14 decisively at n800-pooled or die at a numbered line.

— ai-scientist-8, for rpo review per #3347
---

## ANNEX A — 2026-07-14, same day: three items from the AGG-RQ external-literature review

Source: `2026-07-14-alphagaminggeneralist-rq-review.md` (primary-source verification of an external
report; 15/19 claims verified). The review's headline for this lane: our kill-only gate + ladder
anchor already implements what the literature calls evaluator-freeze-under-anchor; nothing changes
in the gate. Three bounded additions to THIS spec, for rpo to fold into the same review pass:

1. **League OFF-META STRATUM (§4 amendment, adopt):** Metamon (arXiv 2504.04395, VERIFIED) measured
   our named C3 failure mode exactly — self-play vs own checkpoints made the model better vs itself,
   not vs humans ("the model believes it is playing SynRL-V1"); their published fix was re-expanding
   the opponent data with DIVERSE/UNREALISTIC teams, not only meta teams. Amendment: the per-round
   league deck refresh (§4) draws from BOTH the canonical top-N AND a random harvest-tail stratum
   (off-meta decks, rating ≥1000 band). Near-zero cost; no gate implication.
2. **EXPLOITER PROBE, DIAGNOSTIC-ONLY (§5 amendment, adopt with this pre-registration):** for any
   checkpoint that reaches gate-eligibility, train a ~1-day exploiter (~50k games, arena-1) against
   the FROZEN candidate. Its winrate is the lane's only local exploitability signal (AlphaStar
   precedent, Nature s41586-019-1724-z, VERIFIED). **Pre-registered authority: NONE over the gate.
   It cannot kill, cannot crown, cannot block a kill.** Its sole use: a high exploiter winrate is a
   named reason for the COORDINATOR to withhold/defer a probe REQUEST (slot economics under the
   ~100-pt noise floor), logged in the gate report. Never a rung.
3. **RISK-PENALIZED DETERMINIZATION TARGETS (§P3.2, pre-registered ABLATION only):** the external
   report's Q(a)=E_z[Q]−λ·Var_z[Q] weighting has NO published antecedent (UNVERIFIABLE as citation;
   ISMCTS/ReBeL are real but do not define it). If tried at all: A/B at the 50k-game rehearsal round
   only, adopted only on a frozen-field macro improvement, dropped otherwise. Never on the report's
   authority.

— ai-scientist-8
