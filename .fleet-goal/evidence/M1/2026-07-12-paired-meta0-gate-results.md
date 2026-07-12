# Evidence — Paired meta0 gate: A1 policy on the ENGINE deck (both chains)

_ai-scientist-6, 2026-07-12T15:37Z. Frozen harness `eval_search_head2head.py`.
Deck = `meta0_1106_BenjaminZhao` (only mined deck with 6/6 archetype-core
overlap; the phase-C imitation target; historical deck-transfer reference).
A1 bundle from merged ca937183 (sha256 bda18f95…, strategy 6cae26d8…);
old-policy bundle from 30ef89fb; both runner-faithful, zero forfeits.
Raw log: session scratchpad `a1-gate/paired_meta0_ladder.log`._

## Chain 1 — A1×meta0 (cand) vs OLD×meta0 (base): policy delta where bugs bind

| rung | W-L | wr | Wilson 95% |
|---|---|---|---|
| n40 | 18-22 | 0.450 | [0.307, 0.602] |
| n160 | 82-78 | 0.5125 | [0.436, 0.589] |
| n400 | 158-242 | 0.395 | [0.348, 0.444] |
| n400 (independent) | 170-229 | 0.425 | [0.377, 0.474] |
| **pooled n800** | **328-471** | **0.410** | **[0.376, 0.445]** |

## Chain 2 — A1×meta0 (cand) vs frozen live-s14 (deployment-relevant)

| rung | W-L | wr | Wilson 95% |
|---|---|---|---|
| n40 | 18-22 | 0.450 | [0.307, 0.602] |
| n160 | 59-101 | 0.3688 | [0.298, 0.446] |
| n400 | 161-239 | 0.4025 | [0.356, 0.451] |

Historical reference (deck-transfer closure): OLD×meta0 vs s14 n400 = 0.5075
[0.459, 0.556]. **The A1 policy costs the meta0 deck ~10 winrate points
against the champion.**

## Verdict

A1 alone is worse than the buggy policy EVERYWHERE tested: s14-deck mirror
(0.4575 [0.423, 0.492] n800), engine-deck head-to-head (0.410 [0.376, 0.445]
n800), and engine-deck vs champion (0.4025 vs ref 0.5075). Three independent
environments, all Wilson-uppers < 0.50 at n400+.

**Mechanism hypothesis (leading, falsifiable):** A1's deck-search SIGHT ranks
picks via `_card_keep_value`, whose extremes are INVERTED vs verified top play
(finding #5: they protect energy / shed spare Pokémon; the inversion fix sits
in Phase B). Blind index-0 was accidentally aligned with engine option
ordering (CTX_EVOLVE index-0 = 94% top-play match), so sight×wrong-values <
blindness — and the engine deck fires ~17 deck-searches/game, which is why the
damage is LARGER on meta0 (0.41) than in the mirror (0.4575).
Falsifiable prediction: with B's flags, `ENABLE_DECK_SIGHT=off` recovers most
of chain 1's gap; full A1+B (sight × corrected values) beats OLD×meta0.

## Binding consequences (Eddie directive, in-session 2026-07-12)

1. **A1+B are ONE candidate — gated together; A1 is never shipped/gated alone.**
2. B's `ENABLE_*` flags are for attribution runs only, never shipping variants.
3. The keep-value inversion fix is the LOAD-BEARING element of B, not tuning.
4. Gate plan when B lands: (A1+B)×meta0 and ×btk15049_1180 vs OLD×same-deck
   AND vs frozen s14; n40→n160→n400→n400 unchanged.

Cost: ~2,700 games total today, zero Kaggle slots; champion s14 live at 607.6.
