# P3.0 — Phase-3 pipeline shakedown

adx-server (arena-1) · 2026-07-14 · repo @ 0c017a4 · task `~/P30_SHAKEDOWN_TASK.md` (coordinator ai-scientist-8)
**SHAKEDOWN ONLY — no number here kills or crowns. No submissions, no slots, no PAT.**
Machine JSON: `artifacts/adx/p30-shakedown-report.json`

---

## D1 — training venv (torch is TRAINING-ONLY) ✅
New venv **outside the repo**: `~/venvs/p3-train` (CPU torch; torch never enters a bundle — inference
tier is numpy + stdlib fallback, program-doc addendum 4).

| component | version |
|---|---|
| python | 3.12.13 |
| torch | 2.13.0+cpu (default 4 threads) |
| numpy | 2.4.4 |
| kaggle-environments (card DB) | 1.32.0 |

---

## D2 — tokenizer: ONE pure function, train/serve identity ✅
`src/ready_player_one/ptcg/nn_tokenizer.py` — a single pure `tokenize(current, select, deck)` in one
module, imported by BOTH the trainer and the (future) bundle (no copy-paste twin — the featurize/GBM
lesson). Depends only on `.enums`; no engine/card-DB call → trivially deterministic. Structure:
deck-prefix (unique cards) + opp-model (hidden zones as counts) + global + selhdr + board×12
(2 active + 2×5 bench) + hand≤20 as a **context token sequence**; **options are scored as structured
per-option features** (type / target-card / area / in-play-area) in EXACT `select['option']` order — so
nopt up to 64 never blows context length, and the pointer head scores position i → option i (the order
`agreement()` argmax depends on). Card vocab 1,268 (ids 0–1267); unified token vocab 1,383.

**Unit test** (`scripts/nn_unit_test.py`):
- **Train/serve identity:** tokenizing 300 real decisions in two fresh processes → identical sha256
  (`ee65cf86…`). PASS.
- **Full 76,405-record scan:** max context length **61** (cap 100); max nopt **61** (cap 64,
  **0 option truncation**); **max total tokens 112 ≤ 130** (typical ~70); **option order preserved**
  (0 mismatches). PASS.

---

## D3 — Model-S skeleton + trainer ✅ (built, smoke-validated; full train = D4)
- **Model-S** (`scripts/nn_model.py`): pre-norm transformer, **d128 · L4 · 4 heads · ffn256**, hand-written
  layer ops (not `nn.TransformerEncoderLayer`) so the numpy/stdlib serve forward reimplements them
  exactly. Pointer head (MLP over `[opt_repr, ctx, opt_repr·ctx]`, masked softmax CE single-pick /
  per-option BCE multi-pick) + value head (tanh winner) + count head. **788,803 params** (~0.8M).
  GELU uses the tanh approximation so numpy/stdlib reproduce it without scipy.
- **Shards** (`scripts/nn_build_shards.py` → `runs/imitation/nn_shards.npz`, 53 MB, mmap): tokenized
  fixed-width arrays for **69,966** decisions. Episode-disjoint split **identical to
  `policy_imitation.cmd_train`** (val_every=5 over the full top1100 ep set): **train 55,879 / val
  14,087**, main_val **8,481**, 33 teams — the exact split the GBM/linear anchors use. 95% single-pick.
- **Trainer** (`scripts/nn_train.py`): win-weighted BC (winner-seat w=1.0, loser 0.25, draw/unknown 0.5),
  **team-stratified** sampling (weight ∝ 1/√team-freq — top-8 teams are 81.8% of supervision),
  AdamW, grad-clip, checkpoint every epoch, OMP/OPENBLAS/MKL pinned to 4 threads.
- **Pipeline smoke (pre-launch, per review):** the whole chain — tokenize → shard → train step →
  eval agreement → checkpoint → **bundle build → numpy load/score → numpy-vs-stdlib fidelity → one
  liveness control** — all execute before the real run was launched.

---

## D4 — the shakedown numbers (sanity-only; G1 kill authority deferred, rpo #3320)
Trained to **plateau at epoch 9/30** (val MAIN oscillating 0.60–0.62; stopped at plateau per spec).
Threads pinned to 4 (OMP/OPENBLAS/MKL); **~183 s/epoch**, peak RSS **3.2 GB**, CPU **~387%** (≈3.9 cores).

**Val MAIN top-1 agreement — SAME `agreement()`, SAME episode-disjoint val split (val_every=5), SAME
anchors as the GBM/linear:**

| model | val MAIN top-1 agreement |
|---|---|
| A1 heuristic (anchor) | 0.3318 |
| Linear perceptron (anchor) | 0.4749 |
| GBM (prior gate) | 0.5181 |
| **Model-S BC-init — numpy serve path (what ships)** | **0.618** |
| Model-S — torch (training reference) | 0.620 |

The **numpy-serve 0.618** is the number that ships (the bundle plays numpy); torch 0.620 is the
training reference. Agreement is **sanity-only** (proven decoupled from win rate twice) — a strong
number here is an INIT diagnostic, not a candidate signal.

Loss curve (train→val): train loss 1.059→~0.80; **val loss bottoms at epoch 3 (0.8467) then RISES to
0.8793 @ep9** while val MAIN keeps climbing — see the D5 checkpoint hazard.

---

## D5 — NN bundle + fidelity + liveness + diagnostic n40

### Bundle (imitation-kind harness; `bundle_kind='nn'` wired into the evaluator)
`submission_nn.tar.gz` — ships as `agpkg/policy_imitation.py` (the NN ranker with **byte-identical
STATS**), numpy inference (`nn_infer.py`) + **pure-stdlib fallback** (`nn_infer_stdlib.py`), weights
baked as `agpkg/nn_weights.npz`. The evaluator now recognizes **`bundle_kind='nn'`** (detects
`nn_weights.npz`; `NN_REQUIRED_STRATEGY_MEMBERS` covers the npz so `strategy_sha256` certifies the
exact bytes that play) with **I1–I7 mapped verbatim**. GBM/imitation/search paths regression-checked
intact. torch is used only to export the checkpoint — it never enters the bundle.

### ⚠️ Checkpoint selection — OVERFIT HAZARD, NAMED (amended rule 3)
Frozen checkpoint `model_best.pt`, **sha256 `5027b5660e2bb44bb317baa4c7d2da21f0f749b6471848c9bf148d7411f0a8be`**,
**epoch 9, selected by MAX val-MAIN (0.62)**. **Val loss bottomed at epoch 3 (0.8467) and was RISING at
selection (0.8793 @ep9).** Selecting best-by-val-MAIN on a rising val loss is a **top-1-agreement-overfit
hazard**: the argmax keeps improving while calibrated loss degrades. For a real candidate the
conservative pick is ep3 (val-loss-optimal) or early-stop-on-val-loss; ep9 was used here to report the
strongest agreement number for the SHAKEDOWN, not as a candidate. **Named, not hidden.**

### Serve fidelity (amended rules 1–2, 4)
- **torch-vs-numpy argmax agreement = 0.9733** (not the GBM's 1.000000). **Diagnosis:** every divergence
  is an **exactly-tied option** — at each flip the torch top1–top2 logit gap is **0.0** (max |logit
  delta| 6e-6, float32↔float64). Identical option features → identical embeddings → genuine ties that
  float32(torch) and float64(numpy) break to different indices. **Not a policy divergence** (a
  transformer produces ties a tree's exact thresholds do not). Path to 1.000000: a shared
  tolerance-based lowest-index tie-break (train+serve) — **not applied here** (shakedown); noted as the
  pre-registered requirement before any ≥0.55 claim.
- **Deployment fidelity (numpy vs stdlib — both serve tiers, rpo-required):** argmax agreement
  **0.972** on a 250-decision sample, **max score |delta| 8.9e-15** (numerically identical; residual
  flips are the same exact ties). Stdlib ≈1.14 s/decision → full-val sweep ≈4.5 h (compute-bound; a
  large sample is reported, per the review's per-forward-cost projection).
- **The n40 ran the frozen numpy SERVE path** (bundle backend = numpy), with **candidate liveness LIVE
  in the run itself**.

### Liveness certification (GBM gold-standard bar) ✅
- **Positive control (NN vs s14, n4): LIVE**, `bundle_kind='nn'`, ranker_ok==decisions, fallbacks 0,
  **I5 nontrivial_frac 0.7411** (floor 0.30), **I6 feat_key_hit 1.0** (floor 0.50), weights_n 65.
- **All SIX negatives fail loud** (nonzero exit, no `JSON` line):

| control | defect | evaluator refusal |
|---|---|---|
| N1 import-dead | `raise ImportError` at scorer top | ImportError (eager-import crash) |
| N2 raise-every | choose raises every decision | I2_weights_n |
| N3 partial raise | raises every 10th decision | I4_per_decision_ranker |
| N4 zeroed-weights blind | all weight tensors → 0 | I5_nontrivial |
| N5 tokenizer-drift | card tokens shifted out of vocab | **I6_feat_key_hit** |
| N6 env override | `PTCG_IMITATION_WEIGHTS` set | I3 |

### Diagnostic n40 vs s14 — NUMBER ONLY (shakedown, no kill authority)
`loadavg 5.32→9.22` · `2.71 s/game` · 0 invalid · candidate liveness **LIVE**.

**winrate vs s14 = 0.35 (14 W / 26 L / 0 D), Wilson95 [0.221, 0.505]** — seats balanced (7/20 each).

Amended-rule reading: **Wilson-UPPER = 0.505 < 0.55**; the result sits below the 0.55 line, the
direction for which the 0.9733 serve fidelity is admissible (no pass/probe claim is made, and none
would be admissible until action parity = 1.000000). This task carries **no kill authority**
(P30 addendum 5) — I report the number; the verdict language is the coordinator's. Expectation on
record held: the imitation family loses to s14 (0.35 here vs GBM 0.125, linear ~0 — the strongest
learned opponent yet, still losing; the loop's starting point, not a candidate).

### Artifacts kept for P3.1
`runs/imitation/nn_ckpt/` (per-epoch + model_best.pt), `runs/imitation/nn_shards.npz`,
`submission_nn.tar.gz`, `runs/imitation/nn_team_map.json`.


