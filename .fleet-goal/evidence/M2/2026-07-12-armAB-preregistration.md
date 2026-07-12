# PRE-REGISTRATION — Arm A / Arm B gate battery (M2)

**Committed BEFORE any Arm-B data exists** (rpo #3272 G4 requirement). No number below may be
amended after Arm-B data is visible. If a floor proves wrong, the battery is re-run under a new
pre-registration — floors are never adjusted to fit data.

Status at commit time: Arm-B bundle NOT YET BUILT; no Arm-B game or agreement number exists
anywhere. Arm A has exactly one liveness-certified number (n40 h2h vs s14 = 16W/24L = 0.400,
Wilson [0.263, 0.554]) which per lane discipline decides nothing.

## The factorial this completes

| | our deck | meta0 (BZ) deck |
|---|---|---|
| **our heuristic policy** | s14 (champion, baseline) | ALREADY RAN: pooled n=1000 → **0.489** |
| **imitation ranker** | **ARM A** (ranker trained on all ≥1100 pool) | **ARM B** (ranker trained on the archetype slice — the JOINT unit, never run) |

Arm B is the only cell where imitation's precondition holds (the experts actually played the
instrument). It is also the story arm; hence this document.

## Candidates

- **A**  = post-liveness C bundle: full-pool ranker × our water deck.
- **B1** = meta0/BZ deck × ranker trained on the archetype-slice supervision (Eddie's named joint arm).
- **B2** (optional, capacity permitting) = kazuki0123 deck × ranker trained on kazuki0123 supervision
  (16,426 records — the supervision-maximal joint unit; mono-list archetype). Same floors. Listed now
  so it cannot be added post-hoc.

Every candidate bundle: built by `build_submission_search.py --imitation` at ≥0c017a4, SHA-256 +
deck CSV SHA-256 + weights SHA-256 + evaluator-emitted `candidate_strategy_sha256` pinned in the
result memo (guardrail 2).

## Instrument (rpo G2: mixed field, not single-arm)

`aggregate_h2h_portfolio.py` @ ≥0c017a4 (liveness-enforcing) with the PCMM-R1 3-arm field:
`live_s14_reference`, `s18_active_reference`, `live_s14_evolved_deck_2c1368bc03`.
h2h-vs-s14 alone is a sanity check only, never the promotion criterion (the single-arm gate is
0-for-1 against the ladder: 2c1368bc03 false positive).

## Floors (inherited verbatim from the proven pcmm_r1 config — not invented for this battery)

**Screen (n=40/arm):** macro ≥ 0.55; worst-arm ≥ 0.40; per-seat ≥ 0.20; seat gap ≤ 0.50.
Failing screen kills the candidate — no n400 spend.

**Confirm (n=400/arm):** macro ≥ 0.55; worst-arm ≥ 0.50 with Wilson-lo ≥ 0.50; per-seat ≥ 0.40;
seat gap ≤ 0.20.

**Reconfirm:** fresh run ids, must pass independently, NO pooling with confirm.

**Liveness (guardrail 6):** every imitation-side result must carry `liveness = "LIVE"` (I1–I7);
anything else, or a missing key, is INVALID per `aggregate_h2h_portfolio.py:187-204`.

**Multiple candidates:** 2–3 candidates through the same funnel is within the alpha budget already
audited by rpo (#2930: P(confirm+reconfirm both pass | H0) = 0.00032/candidate). No floor changes.

## KILL CONDITIONS (the numbers rpo asked for, fixed now)

- **Arm A is KILLED** if it fails the mixed-field screen, or fails confirm, or fails independent
  reconfirm. Verdict recorded: *imitation ranker does not transfer to the deck we field* —
  consistent with the 64%-inert-weight finding.
- **Arm B (B1, and B2 if run) is KILLED** by the same floors. **If ALL joint arms are killed,
  imitation-from-ladder-replays is DEAD as a lever on this engine** and M2 closes as an honest
  negative (the method-artifact precondition cannot be satisfied profitably even when restored).
  That closure memo cites this pre-registration.
- **No narrative rescue:** a candidate that fails worst-arm but shines on macro (metamon pattern,
  0.5583 macro / 0.375 worst-arm) is FAILED. A candidate that only beats s14 h2h but fails the
  field is FAILED.

## Slot posture (rpo G3 / guardrail 7')

Observed ladder poll noise on a fixed artifact: 83.6 pts (probe 464.5→548.1); s14 spread 26.9.
Working noise floor: **±100**. A local pass at the floors (macro ≈ 0.55) predicts a ladder effect
we CANNOT claim exceeds that noise. Therefore, pre-registered:

- The probe request goes to Eddie **only if** the winning candidate clears **macro ≥ 0.60 AND
  worst-arm Wilson-lo ≥ 0.55 on BOTH confirm and independent reconfirm** (strictly above the
  survival floors).
- If a candidate merely scrapes 0.55/0.50: it survives the gate but we do NOT ask for the slot —
  we ask for a better instrument (extended field / multi-poll protocol) instead.
- The slot is Eddie's call alone (his ruling supersedes silence-equals-proceed; rpo governance
  update #3272). s14 stays champion throughout.

## Provenance debts blocking Arm-B construction (rpo G5)

mroute must reproduce FROM SCRATCH before any number reaches this battery's record:
the −11.73pp card-feature ablation, the 132/44 weight split, the 5/11→1/11 coverage claim, and the
LOTO deltas (all currently second-hand from a verification subagent). The 0/76,405 on-policy count
and deck/Jaccard figures are first-hand (sctst-aide) and stand. The 64%-inert-mass measurement is
first-hand (ai-scientist-7, this session, from `origin/feat/ptcg-agent:scripts/imitation_weights.json`)
and reproducible in ~10 lines; mroute re-derives it anyway as part of the same pass.

— ai-scientist-7, 2026-07-12, pre-registered under rpo guardrails (1')–(7') [#3272]
