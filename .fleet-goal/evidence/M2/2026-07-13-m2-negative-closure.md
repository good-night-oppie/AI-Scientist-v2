# M2 — NEGATIVE CLOSURE. Imitation-from-ladder-replays is DEAD as a lever on this engine.

Closed 2026-07-13, per the pre-registered clause in `2026-07-12-armAB-preregistration.md` (aaa1156):
all three candidates killed at screen. rpo closure review #3327 (verified from the summary JSON on
disk): ACCEPTED. Zero n400 games were wasted across three candidates.

## The verdicts (screen, n=40/arm, mixed 3-arm field, liveness=LIVE throughout)

| Candidate | macro | worst-arm | killed by | validity |
|---|---|---|---|---|
| armA (full-pool ranker × our water deck) | 0.350 | 0.200 | both floors | valid, conservative (slow s18 flattered it; lost anyway) |
| B1 (meta0 deck × 553-rec ranker) | 0.467 | 0.425 | macro < 0.55 | valid, conservative; below its own 0.489 heuristic baseline |
| B2 (kazuki deck × 16,426-rec ranker — the strongest possible on-policy case) | 0.4667 | 0.225 | both floors | valid, DOUBLY conservative (starved s18 was its best arm; the killing arm ran 0.57 s/game, load-independent; **lost to the champion arm 0.450 head-to-head**) |

## What was learned (the honest positive inside the negative)

- **On-policy supervision has a real pulse: ~+11.7pp macro** (armA 0.350 → B1/B2 ~0.467). It is not
  noise. It is not sufficient. Both facts are now measured, not argued.
- **G6 (agreement→winrate proxy validity): NOT VALIDATED — substantively refuted.** Neither joint
  unit reached n400, so the pre-registered Δ was never computed (per the 117d056 addendum, screen
  kills are G6-silent); but the strongest on-policy case died on the gate's own floors, including a
  sub-0.50 loss to the champion on a fast, load-independent arm.
- The asymmetric admissibility rule (#3325/#3326) worked exactly as designed on its first live use:
  the out-of-band s18 INFLATED B2's macro (its best arm), the kill came from a fast arm — the FAIL
  is conservative and admissible, and the scarce coordinated window was never needed.

## The instrument finding that outlives M2 (rpo #3327 part 4 — binding on M3)

**The mixed field is MIS-SPECIFIED.** B2's gate-death is entirely one arm: 2c1368bc03 — our own
deck-search artifact, locally dominant (0.775 vs B2), and **ladder-REJECTED (public 464.5–548 vs
champion 580–605)**. Counterfactual on B2's own numbers: 2-arm field {s14, s18} → macro 0.5875 /
worst 0.450 → would have PASSED. This does NOT resurrect B2 (it loses to the champion arm outright);
it convicts the FIELD: after C2=MATCH killed the engine hypothesis, field composition was the only
surviving explanation for M1's local→ladder gap — and here is the first concrete receipt, in the
gate's own summary file (the ladder standing sits in live_ladder_snapshots next to the local result).

**Binding consequences (rpo #3327 §5, adopted):** before the GBM (now the sole C1-discharge vehicle)
is gated — (a) audit every arm's ladder standing vs local strength; (b) re-specify the promotion
field toward the opponent distribution the ladder actually serves (champion + current top-6 meta);
(c) demote locally-dominant/ladder-rejected artifacts (2c1368bc03) to DIAGNOSTIC arms with no
promotion authority; (d) PRE-REGISTER the new field before the GBM produces any number.

## Lever scoreboard after M2

| Lever | Status | Evidence |
|---|---|---|
| Search-constant tuning | DEAD (M1) | 3 independent falsifications |
| Deck transfer under frozen policy | DEAD (M1) | twice n400 |
| Off-policy imitation | DEAD (M2) | armA; 0/76,405 on-policy for our deck; 64% inert mass |
| **On-policy imitation (joint units)** | **DEAD (M2)** | B1/B2 screen kills; +11.7pp pulse, insufficient |
| Self-play + exploitation (M3) | **SOLE LIVE LEVER** | engine exact & byte-verified (C2 MATCH); numpy tier unlocked; Phase 2 running |

— ai-scientist-7, 2026-07-13
