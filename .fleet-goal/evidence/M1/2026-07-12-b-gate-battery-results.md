# Evidence — B gate battery: A1+B flat-reorder candidate FAILED all 4 chains + attribution

_ai-scientist-6, 2026-07-12T18:50Z. Frozen harness, candidate = merged 12d65c7e
(A1 bugs + B flat MAIN_SCORES reorder + keepvalue fix, all flags ON), decks =
meta0_1106 (archetype core 6/6) and btk15049_1180 (robustness). Raw log:
session scratchpad b-gate/b_gate_battery.log. ~2,700 games this battery._

## Chains (n40 → n160 → n400 [→ n400 reconfirm])

| chain | matchup | rungs | verdict |
|---|---|---|---|
| 1 | A1B×meta0 vs OLD×meta0 | 0.15 → 0.1812 → 0.215 → 0.205 (pooled n800 **0.210**) | FAIL |
| 2 | A1B×meta0 vs frozen s14 | 0.275 → 0.1875 → 0.2075 (refs: old×meta0 0.5075, A1-only 0.4025) | FAIL, worse than A1-only |
| 3 | A1B×btk1180 vs OLD×btk1180 | 0.30 → 0.3875 → 0.4075 | FAIL (milder on this deck) |
| 4 | A1B×btk1180 vs frozen s14 | 0.025 → 0.0875 → **0.0675** | CATASTROPHIC |

## Attribution (chain1 config, n160 each, one flag OFF; all-ON baseline 0.1812)

| flag OFF | wr | Wilson | delta vs all-ON |
|---|---|---|---|
| TARGET_TIEBREAKS | 0.3563 | [0.286, 0.433] | +17.5pp — largest single recovery |
| DECK_SIGHT | 0.2375 | [0.178, 0.309] | +5.6pp |
| KEEPVALUE_FIX | 0.2188 | [0.162, 0.289] | +3.8pp |
| RETREAT_FIX | 0.1688 | [0.119, 0.234] | −1.2pp (null) |

**No single flag recovers parity ⇒ the dominant poison is the UNFLAGGED flat
MAIN_SCORES reorder itself** (ability 85 flat / item 75), with
TARGET_TIEBREAKS as the largest interaction amplifier. Consistent with the
zero-game diagnostics: per-decision agreement ROSE 28.2%→41.8% while games
collapsed — ability fired on 89.3% of availability vs experts' 44.7%; expert
fire rates are per-card (Gabite 0.647 … Community Center 0.000), which a flat
constant cannot express.

## Verdicts

1. **A1+B (flat reorder) is DEAD** — never a probe candidate. Hand-tuned
   constants are now twice executed by dynamics (A1 inverted keep-value;
   B flat ability). Do not hand-tune a third time.
2. Attribution flags stay in the tree (useful instruments), but future
   candidates carry a 5th flag if any new global reorder is ever attempted.
3. **Path forward = Phase C** (merged @332a390c): learned per-card/state
   selectivity; full-corpus MAIN agreement independently reproduced at 0.4907
   (val 0.499). Blocked only on the bundle-builder extension (dispatched to
   mroute) → then C paired gates → probe flow per Eddie standing auth.

Session totals: ~6,100 gate games today; zero Kaggle slots; champion s14 live.
