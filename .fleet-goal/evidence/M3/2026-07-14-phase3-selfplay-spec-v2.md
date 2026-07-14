# PHASE-3 SELF-PLAY SPEC v2 — league self-play with an exploitability spine, gated kill-only vs s14

Date: 2026-07-14 · Author: ai-scientist-8 (coordinator) · Status: PROPOSED v2 — rewritten against
rpo's NEEDS-REWORK verdict (recovered + committed: `2026-07-14-phase3-spec-review-rpo-verdict.md`),
for rpo re-review against exactly that list. SUPERSEDES v1 (same date; v1 stays on disk as record).
v1 items rpo endorsed (pause-for-gate, held-band, four #3347 rules mapped verbatim) are carried;
every blocker (B1–B4), must-fix (MF5–MF10), and should-fix from the verdict is pre-registered here.
Numbers marked ⟨coordinator-set⟩ are my proposals where the verdict asked for a number — rpo may
reset any of them at re-review; they bind once rpo accepts.

## 0. WHY SELF-PLAY — CORRECTED FRAMING (rpo's own #3333 correction, adopted)

Four levers are dead on the correct engine (search-tuning 3×, deck-transfer 2×n400,
policy-transfer, off-policy imitation 0-for-4 with the GBM killed at 0.125). The ~500 MMR gap is in
the POLICY and no mineable data can teach our deck. Self-play remains the only live lever — but the
correct precedent is **AlphaStar-league / PSRO, not AlphaZero**: PTCG is imperfect-information,
asymmetric, stochastic; AlphaZero's improvement guarantee does not transfer; determinized search is
a known-unsound policy operator there (strategy fusion, non-locality — Frank & Basin 1998, Long et
al. 2010), and naive self-play converges to self-consistent non-equilibria that a best-responder
exploits. Consequences wired into this spec: the improvement operator must be VERIFIED per round
(§3, B4), and exploitability is measured by a manufactured adversary, not assumed away (§2a, B1).

## 0.5 PROGRAM TERMINAL STATES (B3a) — M3 has a win state and a death line

- **SUCCESS:** a checkpoint CROWNS per §2b. Program reports success to Eddie; what ships next is
  Eddie's slot decision as always.
- **FALSIFIED:** after a pre-committed budget of **4 full rounds** ⟨coordinator-set, rpo's example
  adopted⟩, EITHER zero checkpoints have reached probe-eligibility (§2), OR every probe-eligible
  checkpoint that received a slot landed ≤ s14 + noise floor on the ladder → **self-play-on-this-
  engine is DEAD**, reported to Eddie with the same finality as the four prior levers.
- **PROGRAM CEILING (independent of results):** at **4 weeks wall-clock from P3.2 GO** or after
  **2 probe slots returning ≤ floor** ⟨coordinator-set⟩, whichever first, M3 returns to Eddie + rpo
  for an explicit continue-or-kill. The held-band re-gate (§2) counts inside this ceiling — held
  candidates cannot silently extend the program.

## 1. THE GATE (floors unchanged from #3347; admissibility hardened)

- **SCREEN n40 vs s14: kill if point winrate < 0.55.** n40 kills or is silent.
- **CONFIRM n400: kill unless Wilson-lo ≥ 0.50.**
- **INDEPENDENT RECONFIRM n400, fresh batch, same floor.**
- Retained: zero-invalid; both-seat balance. Liveness to the GBM gold-standard bar (I1–I7 + six
  negative controls) + NN deployment-fidelity (numpy vs stdlib argmax byte-agreement, full val
  sweep). bundle_kind='nn' mapped verbatim (program-doc §4 hazard).
- **INFERENCE-TIME TAIL GATE (MF8 — the (8') lesson, B2/s18 precedent):** log the full per-decision
  inference-time distribution (p50/p90/p99/max, BOTH numpy and stdlib paths) over a full val sweep,
  every bundle. Pre-registered: **stdlib p99 > 0.5s or max > 3.0s per decision ⇒ INADMISSIBLE
  regardless of winrate** ⟨coordinator-set; 0.5s = design target, 3.0s ≈ Kaggle worst-case ceiling
  3.1s with margin⟩. Correctness fidelity is not timing fidelity; both are required.
- **RUNNER-POLICY IDENTITY (MF5c — the new C2-class gap):** C2 proved engine BYTES match; it never
  proved the RUNNER's move-timeout / turn-cap / illegal-move-forfeit policy matches. Before any
  probe request: verify and record runner-policy identity alongside the C2 MATCH (from runner docs +
  the probe episode's observed limits). Bytes are necessary, not sufficient.
- **A gate pass earns exactly one thing: a probe REQUEST to Eddie.** Never a promotion.

## 2. PROBE-SLOT RATIONING (MF9 — reframed; "dominance" struck)

Local-vs-s14 is the PROVEN-BROKEN ladder predictor (2c1368bc03: 0.571 local, ladder-negative).
This section does NOT claim ladder prediction. It RATIONS Eddie's scarce slots: the threshold
selects our strongest LOCAL candidate as worth one slot to obtain a REAL ladder measurement — which
may still return ≤ s14. **Local Wilson-lo predicts NOTHING about ladder standing**; a <0.55
candidate may be a ladder winner and a ≥0.55 one a ladder loser. The number only rations slots, and
it is calibrated to n=1 (the single 2c1368bc03 point; it clears that false positive by ~3pp only).

- **Threshold: Wilson-lo ≥ 0.55 at CONFIRM AND at INDEPENDENT RECONFIRM, as two separate n400
  tests, AND'ed — POOLING IS FORBIDDEN** (a lucky confirm must not drag a mediocre reconfirm
  across; d40d9dd567 precedent). Any pooled-n800 wording in v1 is struck.
- **Kill-survivor band (Wilson-lo 0.50–0.55): HELD** — recorded, league-retained, re-gated after
  further rounds (inside the §0.5 ceiling), not probed, not dead.
- **Probe/slot discipline (should-fix, adopted):** at most ONE outstanding probe request at a time;
  the request is always for the strongest-so-far candidate (a request is withdrawn if a new
  candidate out-dominates it before Eddie acts); total M3 probe-slot ceiling to be agreed with
  Eddie at the 50k GO/NO-GO report ⟨proposed: 3⟩; a ≤floor probe result counts toward the §0.5
  falsification budget.
- **CALIBRATION LEDGER (should-fix, adopted):** every probe becomes a local→ladder calibration
  point (2c1368bc03 = point #1: 0.571 → ladder-negative). After each probe, refit this section's
  threshold against the real map; where a slot can be spared, prefer probes spanning the
  local-metric range (learn the map's shape, not its intercept). Ledger fields live in the round
  summary (§6).

## 2a. THE EXPLOITER PROBE (B1 — the keystone; first-class, pre-registered)

Decisive winrate vs one fixed ~605-MMR opponent is fully consistent with maximal exploitability at
the infoset level — and tighter dominance over s14 can mean MORE overfit, not less. The exploiter
probe is the constructible local upper bound on "the ladder eats it":

- **Protocol:** FREEZE the candidate. Train an approximate best-response against it with the same
  self-play machinery, candidate as sole frozen opponent (AlphaStar main-exploiter / PSRO
  approx-BR), from the current incumbent's weights ⟨coordinator-set: warm-start makes the probe
  stronger, which is conservative in the right direction⟩. **Budget: 50k games / ~1 day on
  arena-1** ⟨coordinator-set⟩.
- **Pre-registered DENY line: exploiter winrate vs candidate > 0.62** (n=400, Wilson point
  estimate; rpo's start value) **⇒ the probe REQUEST is DENIED regardless of vs-s14 numbers.**
  The candidate returns to the league; the exploiter joins the league pool (free diversity).
- **Periodic loop check (should-fix, adopted):** run the exploiter probe against the CURRENT
  incumbent every **2 rounds** ⟨coordinator-set⟩. **HALT the loop if exploitability rises while
  frozen-field macro rises** — the feedback-loop failure G4 cannot see.
- **Authority:** DENY authority over probe requests (this supersedes v1-Annex-A's diagnostic-only
  framing — rpo's verdict upgrades it). It cannot kill a candidate (kills belong to §1), cannot
  crown, cannot block a §1 kill. Threshold recalibrates via the §2 ledger as probes accrue.
- This does not reopen withdrawn-C1: the exploiter needs nobody's policy — it MANUFACTURES the
  adversary the way self-play manufactures data.

## 2b. CROWN CRITERION (B2 — the program's win state, three outcomes not two)

For any probed candidate, with the measured noise floor (|probe−s14| = 76.5 @ n≈50, floor
~75–100):

- **CROWN:** ladder standing ≥ s14 + **100 points** (floor point-estimate + measured floor SD) at
  **n ≥ 150 episodes** ⟨coordinator-set: materially above the n≈50 where the floor was measured⟩,
  matchmaking path recorded (`live_ladder_snapshots`).
- **NEGATIVE:** Δ ≤ −floor → counts toward §0.5 falsification.
- **INCONCLUSIVE:** |Δ| < floor → HELD; re-probe with more n only per §2 slot discipline.
- **FORBIDDEN, in text: reading any in-floor positive delta as success.** The standing incentive
  after weeks of sunk cost is to over-read; this line exists to make that a doctrine violation.

## 3. MODEL AND LOOP (B4 + MF10 wired in)

- **Model-S** unchanged from v1 (~1M-param deck-conditional pointer transformer + value head; ONE
  pure tokenizer imported by trainer AND bundle; torch = training-only, never in a bundle).
- **BC-init is a PERMANENT KL-ANCHOR (MF10):** win-weighted BC prior retained throughout training
  as a behavior regularizer (AlphaStar supervised-init + KL-to-human precedent) — the anti-proxy
  "level" problem does not void the equilibrium-ish STRUCTURE human data provides. FROM-SCRATCH is
  no longer a league-macro-triggered fallback: if considered at all, run both arms one round and
  adopt from-scratch **iff** BC fails to beat it by ≥2pp non-overlapping Wilson on the frozen field
  OR the exploiter probe shows BC-init strictly more exploitable ⟨per verdict⟩. League macro alone
  never decides this.
- **IMPROVEMENT GATE, per round, BEFORE distillation (B4):** the search-guided target policy must
  beat the current raw net head-to-head at **Wilson-lo ≥ 0.55, n ≥ 400, seat-balanced**, on the
  exact engine. FAIL ⇒ do NOT distill that round; root-cause (search config, value head, budget)
  before any further training spend. In imperfect-info the improvement operator is not free — this
  gate is the round-level proof it improved.
- **VALUE-HEAD CALIBRATION MONITOR (B4):** every round, log Brier score + reliability curve
  (predicted win-prob vs realized outcome) on a held-out self-play batch. Pre-registered halt:
  Brier degrades > **0.03** ⟨coordinator-set⟩ over 2 consecutive rounds ⇒ HALT symmetric to G4,
  root-cause before restart.
- **Search variant (should-fix, adopted):** prefer ISMCTS over single-world PIMC; measure
  strategy-fusion bias once at the 50k round (determinized-search value vs on-policy rollout value
  on held-out high-entropy infosets; report the gap); prefer on-policy MC rollout value targets
  where feasible. PTCG's high disambiguation factor may make determinized search adequate — that is
  a reason to MEASURE, not to assume.
- **Episode invariants (MF5a):** every training episode asserts: no invalid action sampled;
  ply-count under an explicit cap ⟨coordinator-set: 400 plies⟩; a legitimate terminal reached.
  Violators are discarded, counted, flagged; **halt if violations exceed 0.5% of a round**
  ⟨coordinator-set⟩.
- **Terminal-code distribution (MF5b):** logged per round; **a checkpoint whose wins concentrate
  on rare/anomalous terminal codes is blocked from any probe request** (pre-registered: any single
  non-standard terminal code accounting for >5% of its wins ⟨coordinator-set⟩ → blocked, escalate).

## 4. THE LEAGUE (structural immunity + MF6 + freshness)

- Pool as v1: frozen s14, s18, linear bundle, GBM bundle, heuristic bots on the canonical top-6
  decks (+ kashiwashira/S4nkurero/taksai/vibechu as unlabeled diversity), past checkpoints
  (recency+diversity), **plus every §2a exploiter** (free adversarial diversity), **plus an
  OFF-META STRATUM** drawn from the harvest tail (rating ≥1000 band, random decks — Metamon's
  verified C3-mitigation; v1-Annex-A item 1, kept).
- Checkpoints are LEAGUE SPARRING PARTNERS, never promotion arms; s14 sole promotion arm;
  league/self-play winrate never a promotion metric; `live_ladder_snapshots` mandatory everywhere.
- **CHECKPOINT-REPLACEMENT RULE, hardened (MF6):** a checkpoint replaces the incumbent only if
  (a) frozen-field macro ≥ 0.55 AND the frozen-field improvement is SIGNIFICANT (non-overlapping
  Wilson intervals vs incumbent's frozen-field run, n400), **AND (b) it beats the current incumbent
  head-to-head at Wilson-lo > 0.55 (n ≥ 400, seat-balanced)** — non-transitivity defense; no
  correlated drift-siblings faking §4 diversity.
- **LEAGUE→GATE TRIGGER (should-fix, adopted — the registered number that spends §1 compute):** a
  checkpoint may enter the §1 gate only after it has replaced the incumbent under the MF6 rule AND
  its frozen-field macro ≥ **0.60** ⟨coordinator-set⟩. Verdict language stays with the coordinator;
  the trigger is this number.
- **HARVEST-FRESHNESS INVARIANT (should-fix, adopted):** every round summary records the harvest
  index age + hash. Index older than **7 days** ⟨coordinator-set⟩ ⇒ that round's gate report
  carries a mandatory "C3 defense degraded: backbone stale" flag, and **no probe request may be
  made while the backbone is stale.**

## 5. COLLAPSE / OVERFIT DETECTION (G4 hardened + C3 relabeled)

- **G4 (windowed, per should-fix):** frozen-field macro degrades >2pp over ANY trailing 3-round
  window (not merely strictly-consecutive) ⇒ HALT, revert to last good checkpoint, root-cause.
- **G4 strength-referenced companion:** HALT if the current checkpoint loses at Wilson-lo < 0.50
  head-to-head to an incumbent from ≥2 rounds ago.
- **C3 RELABEL (MF10):** deck-diversity refresh defends the DECK axis ONLY. The dominant
  imperfect-info risk — strategic exploitability at the belief axis — is covered by the §2a
  exploiter probe, not by deck refresh. Both defenses named per axis in every gate report; the
  blind spot honestly labeled as before.

## 6. EXECUTION (owner adx-server; coordinator audits per milestone)

- **P3.0 — PROCEEDS** (already running: torch venv, tokenizer/trainer skeleton, train/serve
  identity, BC-init diagnostic; no kill authority, no promotion, no slot).
- **P3.1 — BUILD NOW, schema-complete:** league harness whose per-round summary JSON carries, from
  day one: exploiter-probe result + threshold, per-decision s18 spg AND inference-time
  distributions (p50/p90/p99/max, both paths), terminal-code distribution, episode-invariant
  violation counts, harvest index age+hash, calibration-ledger fields, `live_ladder_snapshots`,
  seat splits, frozen-field macro history, G4 window state. No schema rework later.
- **P3.2 — FULL CADENCE: BLOCKED** until (a) this v2 is accepted by rpo, and (b) the 50k GO/NO-GO
  fires GO.
- **50k GO/NO-GO (B3b — pre-registered NOW, reported to EDDIE before any full-cadence spend):**
  one reduced-scale round (50k games) through the complete loop (search targets → improvement gate
  → distill → frozen-field eval). **GO ⇔ frozen-field macro improves > 2pp one-sided over the
  BC-init baseline** ⟨coordinator-set: symmetric to G4's 2pp decay line⟩ **AND the B4 improvement
  gate passed AND episode invariants intact.** NO-GO ⇒ halt, report to Eddie, do not proceed to
  full cadence. This winrate is a MECHANISM signal only — never a promotion metric.
- **PAUSE-FOR-GATE, VERIFIED not asserted (MF7):** stop the training PROCESS GROUP/cgroup (not a
  lone PID — SIGSTOP is not inherited by pool workers); sample instantaneous per-core CPU N=5
  times across the gate window (loadavg lags by minutes); assert no cron/top-up/watchtower job
  overlapped the window; ONE-TIME POSITIVE CONTROL: same gate seed run workers-stopped vs under
  controlled background load → results must be consistent (record both). Every gate run records
  the verified-quiet evidence; fail-closed.
- **Resource envelope (should-fix):** round throughput math carries gate-pause downtime
  subtracted; checkpoint/resume durability (episode-boundary persistence, deterministic RNG-state
  resume; a round interrupted mid-gate is inadmissible); arena-1 is a named SPOF — outage runbook:
  tailscale re-auth via Eddie (already happened once), work resumes from last episode-boundary
  checkpoint, no round spans an outage.
- Standing hazards carry (detached jobs, no psutil, bounded pane output, no PAT, artifacts by
  ssh-cat, evidence commits by coordinator on this host).

## 7. TIMELINE, honestly (with pause downtime)

v2-acceptance → P3.1 ≈ 3–4 days (schema-complete harness). 50k GO/NO-GO ≈ +2 days. If GO: full
rounds ≈ 4–6 days each with gate-pause downtime, 4-round budget ≈ 3–4 weeks. First §1-gate-eligible
checkpoint plausibly ≈ 2 weeks after GO. §0.5 ceiling: 4 weeks from GO or 2 ≤floor probes. We do
not promise 978+; we promise a loop that verifies its own improvement, a gate that measures
exploitability, a defined crown, and a death line as honest as the four before it.

## ANNEX A (carried from v1, amended)

Item 1 (off-meta league stratum): ADOPTED into §4. Item 2 (exploiter probe): SUPERSEDED by §2a —
rpo's verdict upgraded it from diagnostic-only to pre-registered DENY authority. Item 3
(risk-penalized determinization Q(a)=E−λVar): unchanged — pre-registered ablation at the 50k round
only, no published antecedent, adopted only on frozen-field improvement.

— ai-scientist-8, v2 for rpo re-review per the recovered verdict