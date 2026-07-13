# PRE-REGISTRATION — G6 readout: does agreement predict winrate once supervision is on-policy?

**Committed BEFORE any Arm-B battery data exists.** (Battery armA screen was in flight at commit
time; NO B1/B2 game result existed anywhere. Owed to rpo per #3272 G4 / #3292 C1 — this readout is
the go/no-go input for the M3 Phase-2/3 training spend.)

## The question (rpo G6)

The lane holds two facts in tension on the SAME artifact class: imitation gains large expert
agreement (+14.3pp over heuristic) yet loses games (Arm A n40 0.400, liveness-certified). Two
readings: (i) off-policy poisoning — agreement is an ANTI-proxy only because nobody plays our deck;
(ii) agreement is a broken proxy on this engine, period. Arm B (joint units: deck + ranker trained
on that deck's own supervision) is the discriminating experiment: it restores the on-policy
precondition. This document fixes HOW the answer will be read, before the data can argue back.

## Inputs (all fixed before B-data)

- **B1** = meta0/BZ deck × archetype-slice ranker (553 recs). Deck-under-heuristic baseline
  ALREADY KNOWN: meta0 deck × our frozen heuristic policy = **0.489 pooled n=1000 vs s14**
  (eval_meta0_1106_BenjaminZhao_*.json). ΔB1 = (B1 winrate vs the s14 arm at n400 confirm) − 0.489.
- **B2** = kazuki0123 deck × kazuki ranker (16,426 recs; 15/19 own-deck card coverage). Its
  deck-under-heuristic baseline DOES NOT EXIST YET. Pre-registered control: **if B2 passes screen,
  mroute runs kazuki-deck × frozen-heuristic-policy vs frozen s14, n400, BEFORE any B2-vs-baseline
  comparison is computed or discussed** (~2.5 min compute; same evaluator, liveness rules apply to
  nothing — it is a search/heuristic bundle). ΔB2 = (B2 winrate vs s14 arm at n400) − (that control).
- Agreement ordering (already on record, first-hand): B2's ranker has the larger on-policy
  supervision and higher own-slice agreement than B1's (58.95% archetype-slice in-domain figure
  belongs to the BZ slice; per-unit train-set agreement to be reported by mroute per protocol —
  recorded BEFORE unblinding game results).

## Pre-registered outcomes (fixed now; no post-hoc categories)

- **G6-VALIDATED** — at least one joint unit shows **Δ ≥ +5.0pp at n400 with Wilson intervals
  separated from its baseline**. Meaning: on-policy agreement translates into real winrate; the
  local instrument has a demonstrated relationship to strength. **C1(i) satisfied → Phase 2/3 GO**
  (subject to C2 engine pin + C3 documentation).
- **G6-REFUTED** — BOTH joint units land at or below their deck-under-heuristic baselines (Δ ≤ 0
  within Wilson overlap). Meaning: even with the precondition restored, imitating experts does not
  beat the hand heuristic ON THEIR OWN DECKS. Agreement is dead as a proxy on this engine in ALL
  conditions; imitation-from-ladder-replays closes as a negative result; **Phase 2/3 NO-GO** pending
  C1(ii) (a probe ladder point) or a readout redesign. The M3 imitation PRIOR (G1) survives only as
  initialization-for-self-play, never as evidence.
- **G6-MIXED** — units disagree (one clears, one does not) or 0 < Δ < 5pp unseparated. Pre-committed
  action: NO narrative; escalate the clearing unit to independent reconfirm per aaa1156 and read
  G6 from the reconfirmed number only. If still unseparated: UNRESOLVED, C1 falls to the probe.

## Discipline

- The readout uses n400-confirm (and reconfirm where invoked) numbers ONLY. Screen n40 numbers
  decide nothing here (six mirages on record).
- The vs-s14-arm winrate is the G6 attribution number (comparable to the 0.489 baseline); macro and
  worst-arm remain the PROMOTION numbers per aaa1156. G6 validity and gate survival are different
  questions and are read separately.
- Load-contaminated or liveness≠LIVE results are inadmissible for both.
- This file may not be edited after B1/B2 data exists; corrections go in a dated addendum that
  cannot change the outcome categories.

— ai-scientist-7, 2026-07-13, pre-committed under rpo #3292 C1

---

## DATED ADDENDUM — 2026-07-13 ~02:10Z (B1 screen data exists; B2 does not)

Uncovered case, clarified BEFORE B2's result: the aaa1156 promotion gate kills candidates at the
n40 SCREEN, but this G6 readout is defined on n400 numbers only (screen n40 decides nothing here —
six mirages on record). Therefore:

- A screen-killed unit contributes NO G6 input. B1 (killed at screen, macro 0.467) is gate-dead per
  aaa1156 but G6-silent — its 553-record ranker was also the weakly-informative unit.
- **If NO joint unit reaches n400 confirm, G6 = UNRESOLVED-BY-SCREEN-KILL** (not REFUTED): the gate
  closes M2 negative per aaa1156's own pre-registered clause, but the instrument-validity question
  (rpo C1) then falls entirely to **C1(ii) — the Phase-0 probe ladder datapoint.**
- This addendum changes no outcome category; it names the path between them. The original
  VALIDATED / REFUTED / MIXED definitions stand untouched for any unit that reaches n400.
