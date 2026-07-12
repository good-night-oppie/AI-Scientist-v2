# Evidence — A1 gate: bug-fixed policy vs live-s14, SAME deck (mirror)

_ai-scientist-6, 2026-07-12T11:22Z. Frozen harness `scripts/eval_search_head2head.py`
at merged head ca937183 (PR #21). Candidate = A1 policy (bugs 1 sel+prize, 2 MAIN
tie-breaks, 3 conditional retreat, 4 area-aware recovery) bundled with the UNCHANGED
s14 deck; baseline = frozen `submission_search_s14_baseline.tar.gz`._

Provenance: candidate sha256 becea317…3768 89, strategy 1c59ec97…3bfe3d; baseline
fcd2dce5…b1521b, strategy 8a6772e9…756ecc. Bundle validation: runner-faithful load,
zero forfeits, honest `search_active=False` (calls == games fallback signature).
Run ids: 4f4e19d6, e955b334 (n160), n400 pair incl. ad9734dc. Raw log:
session scratchpad `a1-gate/a1_gate_ladder.log`.

## Result — REGRESSION in the mirror, twice n400-consistent

| rung | W-L | wr | Wilson 95% |
|---|---|---|---|
| n40 (screen) | 23-17 | 0.575 | [0.422, 0.715] |
| n160 | 80-80 | 0.500 | [0.423, 0.577] |
| n400 | 185-215 | 0.4625 | [0.414, 0.511] |
| n400 (independent) | 181-219 | 0.4525 | [0.404, 0.501] |
| **combined n800** | **366-434** | **0.4575** | **[0.423, 0.492]** |

Wilson UPPER of the pooled n800 < 0.50: the A1 policy on the s14 deck is
statistically WORSE than the unfixed policy in the mirror. The n40 screen was
(again) a mirage — trap #6 for the ledger.

## Interpretation (honest, and consistent with the root-cause analysis)

1. The plateau analysis predicted the bugs "barely bind" on the degenerate s14
   deck (5 items → bug1 rare; no Sacred-Ash-class card → bug4 CANNOT fire;
   free-retreat bodies unclear → bug3 rare). The observed sub-parity says at
   least one A1 pathway that DOES fire is harmful ON THIS DECK.
2. This is deck↔policy CO-ADAPTATION confirmed in the reverse direction:
   top-player-correct mechanics (retreat, target tie-breaks, deck-search value
   picks) are tuned for engine decks; imposing them on the 33-energy
   mono-attacker deck reduces mirror fitness. The old "bugs" were, on this
   deck, accidental co-adaptations.
3. What this does NOT say: nothing here measures the fixed policy on a MINED
   deck — the M2 joint intervention remains untested and is now MORE clearly
   the only informative experiment. It also does not falsify the spec's
   acceptance (that gate is bugs+reorder, and the decisive pairing is with an
   engine deck).

## Attribution (open) and consequences for B/C

- OPEN: which A1 pathway causes the mirror regression (retreat? attach/evolve
  tie-breaks? deck-search keep-value picks?). ASK to mroute: expose cheap
  ablation flags (env or module constants) in the Phase-B branch so each A1
  pathway can be disabled independently; a 3×n160 attribution run then costs
  ~500 games.
- B/C gates MUST pair candidates with mined decks and include BOTH:
  fixed×mined vs old×mined (isolates policy delta where bugs bind) AND
  fixed×mined vs frozen s14 bundle (deployment-relevant). Mirror-only gates
  are now known to mis-rank policy work in BOTH directions.
- A1 code stays merged as the lineage base (source-correct; regression is
  deck-conditional). NO A1-only bundle is promotable. Champion s14 untouched.
