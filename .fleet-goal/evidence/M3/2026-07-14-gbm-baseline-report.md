# Phase-2 GBM imitation baseline — agreement SANITY gate

adx-server (arena-1) · 2026-07-14 · corpus `runs/imitation/imitation_pairs.jsonl` (76,405 top1100 rows)
Trainer: `scripts/gbm_imitation.py` · machine JSON: `artifacts/adx/gbm-baseline-report.json`

## Headline — MAIN top-1 agreement (episode-disjoint val, SAME split, SAME `agreement()`)

| model | MAIN top-1 agreement | vs linear | vs heuristic |
|-------|----------------------|-----------|--------------|
| A1 heuristic (frozen anchor) | **0.3318** | — | — |
| Linear perceptron (C-FULL anchor) | **0.4749** | — | +14.31 pp |
| **LightGBM lambdarank (this)** | **0.5181** | **+4.32 pp** | +18.63 pp |

- val MAIN denominator `main_n = 8481`; overall (all buckets) val top-1 = 0.5762.
- **Both anchors were re-derived on THIS split and reproduce to the digit** (linear 0.4749,
  heuristic 0.3318) — a stale anchor has bitten this lane twice; these are fresh.
- Train MAIN = 0.5240 vs val MAIN = 0.5181 → **train–val gap 0.6 pp, not overfit.**

### ⚠️ This is a SANITY/agreement gate ONLY — not a promotion signal
Agreement is **proven-decoupled** from win rate in this lane: the linear model was **+14.3 pp
agreement over the heuristic and LOST games**. So +4.3 pp of GBM agreement over the linear model
earns **at most the right to a GAMES gate** (beat s14: screen n40 → confirm n400 → reconfirm),
which the coordinator runs. It is **not** evidence the GBM closes the ~500 MMR policy gap. Do not
over-claim.

## Split (reproducible)
`load_pairs → top1100 filter → episode_split(val_every=5)`, `archetype_core_min=0` — identical to
`policy_imitation.cmd_train`.
- records 76,405 · train 60,973 (538 episodes) · val 15,432 (135 episodes)
- train decisions used (multi-option, has-chosen, all seltypes — mirrors perceptron `prepared`):
  55,879 → 418,781 option rows · **vocab = 177 feature keys** (same `featurize()` keys as the linear model)

## Plumbing proof (why 0.5181 is comparable, not a wiring artifact)
Before trusting any GBM number, the perceptron's own weights were scored **through the GBM's
vectorizer + argmax + the imported `agreement()`**: result **0.4749 MAIN, abs-delta 0.0** vs the
native `perceptron_scorer`. The vectorizer/argmax/grading wiring is therefore proven; the +4.32 pp
is a real model-class effect, not a bug.

## Does the GBM find signal the linear model missed? (feature importances)
The GBM uses **110 / 177** features. The divergence is the story:

| GBM top by gain | gain | splits | | Linear top by \|weight\| |
|---|---|---|---|---|
| `tgt_best_atk` | 65,092 | 1226 | | `dmg_target_low_hp` 9.30 |
| `bias_type=10` | 42,119 | 33 | | `loss_keep_value` −7.08 |
| `bias_type=8` | 40,951 | 136 | | `heal_missing_hp` 6.39 |
| `bias_type=14` | 26,713 | 84 | | `play_card=169` 5.97 |
| `dmg_target_low_hp` | 15,712 | 185 | | `is_mine` −5.54 |
| `abil_card=112` | 15,405 | 52 | | `play_card=756` −4.92 |
| `tgt_hp_frac` | 12,230 | 721 | | `play_card=183` 4.63 |
| `card_pokemon_value` | 11,272 | 290 | | `play_card=162` 4.46 |
| `atk_dmg` | 10,376 | 178 | | `play_card=506` 4.40 |
| `poke_hp` | 10,066 | 284 | | `play_card=1259` 3.95 |

**Read:** the linear model's strength is a bag of per-card one-hots (`play_card=…`) it can only
weight linearly. The GBM instead extracts most of its signal from **continuous** features via
nonlinear thresholds/interactions — the *quality of the attach/evolve target* (`tgt_best_atk`
1226 splits, `tgt_hp_frac` 721 splits, `card_pokemon_value`), board HP state (`poke_hp`), and
**type-conditional** value (`bias_type=8/9/10/12/14` carry huge gain — the GBM learns per-option-type
value with interactions where the linear model has only a flat per-type bias). That is exactly the
class of signal a 111-weight linear perceptron cannot represent and the tree can.

## Learning curve (rpo #3320 protocol — episode-subsampled TRAIN, val fixed)
| train frac | episodes | records | val MAIN agreement |
|---|---|---|---|
| 0.25 | 134 | 15,175 | 0.5104 |
| 0.50 | 269 | 30,296 | 0.5181 |
| 1.00 | 538 | 60,973 | 0.5181 |

**RISES 25→50 % (+0.77 pp) then FLAT 50→100 %.** On the current corpus + current feature set the
GBM has **saturated by ~half the data** — the signal is a real model-class effect, and at this
size the ranker looks **feature-limited, not data-starved**. Actionable read for the coordinator:
the next harvest batch is unlikely to move MAIN much *unless the feature set is enriched* (e.g.
richer target/board interaction features); re-run this exact curve when the batch lands to confirm
(per the binding protocol) rather than assuming more rows alone will lift it.

## Deployability — path is clean (bundle NOT built, per task)
- Model: **300 trees, max depth 6** (mean depth 6.0), **702 KB** `.txt`, trained in **16.8 s**
  (single-thread, deterministic).
- **stdlib-only path confirmed:** `booster.dump_model()` → either pure-python if/else trees or a
  numpy traversal. **numpy IS on the Kaggle runner (verified)** — no `lightgbm` in the submission.
- Per-decision cost: `n_options × n_trees × depth` ≈ a few thousand float compares ≈ **microseconds**,
  negligible against the 0.38 s/move search budget. The learning curve saturates by 50 % of data, so
  the deployed model could very likely be shrunk (fewer trees) with no agreement loss — a tuning step
  for the eventual bundle.
- **Known next step (not solved here):** float-threshold reproducibility between lightgbm's `predict`
  and the transpiled trees — the one real risk for a byte-faithful bundle. Flagged, not addressed
  (task said don't build the bundle).

## Determinism
`objective=lambdarank`, `num_boost_round=300`, `learning_rate=0.05`, `num_leaves=31`, `max_depth=6`,
`min_data_in_leaf=50`, `lambda_l2=1.0`, bagging OFF, `seed=0`, `deterministic=True`, `num_threads=1`,
`force_col_wise=True`. Hyperparameters fixed **a-priori** — no early stopping, no tuning against val
(the curve's 100 % point 0.5181 equals the full-model val, consistent). Re-run reproduces bit-for-bit.
