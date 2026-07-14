# GBM GATE — bundle + liveness + kill-only n40 screen vs s14

adx-server (arena-1) · 2026-07-14 · repo @ 0c017a4 · candidate = GBM imitation ranker (val MAIN 0.5181)
Task: `~/GBM_GATE_TASK.md` (coordinator ai-scientist-8, #3341). **Gate KILLS, never crowns.**
Machine JSON: `artifacts/adx/gbm-gate-report.json`

---

## Stage A — TRANSPILE FIDELITY ✅ (the flagged risk, resolved)

Transpiled `artifacts/adx/gbm_imitation_model.txt` (300 trees, depth ≤ 6) → a **pure-stdlib
nested-node tree walker** (`tree_walk_stdlib` in `scripts/gbm_transpile.py`; the exact function
the bundle ships). Model serialized to `artifacts/adx/gbm_model_bundle.json`
(`{"vocab": {feat_key: col}, "trees": [...]}`, 517,695 bytes).

Fidelity vs `lightgbm.predict` on **all val option-rows** (same 15,432-record val split, option rows
rebuilt exactly as in training):

| metric | value |
|---|---|
| val option-rows scored | 103,296 |
| val decisions | 14,087 |
| **per-option score max-abs delta** | **0.0** (exact) |
| **per-decision argmax agreement** | **1.000000 (100%)** |
| argmax-mismatch decisions | 0 |
| argmax-mismatch rate | 0.0 (STOP threshold 0.1%) |

**No float-threshold divergence at all** — the walker uses lightgbm's numerical `<=` semantics
(`value <= threshold → left`, absent feature = 0.0 under `zero_as_missing=false`), and matches
bit-for-bit. The bundle will play the exact policy that scored 0.5181. Stage A STOP not triggered.

---

## Stage B — BUNDLE BUILD ✅

Builder: `scripts/build_gbm_bundle.py` → `submission_gbm.tar.gz` (95,846 bytes).
- **imitation-kind bundle** (evaluator detects `agpkg/policy_imitation.py`): the bundled ranker is
  the EXACT inference half of `scripts/policy_imitation.py` with only **two functions swapped** —
  `score_feats` (linear dot → stdlib tree walk) and `load_weights` (linear JSON →
  `{"vocab":…, "trees":…}` GBM model). `STATS` names + counter semantics, `rank_options`, `choose`,
  `_choose_impl`, KO rail, `featurize` are **byte-identical** → `bundle_kind` stays `imitation` and
  the evaluator's I1–I7 map verbatim. The `weights` object passed around is now the vocab map
  `{feat_key: col}`, so `k in weights` (the I6 feat-key-hit test) needs no change.
- Model ships **inside** the bundle as `agpkg/imitation_weights.json` (517 KB JSON → 96 KB gz);
  `load_weights()` locates it via `os.path.dirname(__file__)` inside `agpkg` (reads
  `PTCG_IMITATION_WEIGHTS` if set — same env seam the evaluator's I3 guards). `main.py` =
  `IMITATION_MAIN_PY` verbatim (never-raise, `kaggle_agent` defined last, stdlib only).
- Deck = **our default water deck** (`agpkg/deck.py` DECK, same as the linear/s14 bundles).
- **Bundled-module reproduces val MAIN 0.5181** through its own `featurize`+`score_feats` — the
  deployed artifact plays the accepted policy, not merely the standalone walker.
- `archive_sha256 = 06e729e1…`, `strategy_sha256 = 245b9ad7…`.

---

## Stage C — LIVENESS CERTIFICATION ✅ (positive LIVE + 6 negatives all fail loud)

### Positive control — GBM bundle vs s14, n=4 → **liveness = LIVE**
`artifacts/adx/liveness/positive_n4.log` (verbatim JSON in the machine report):

| field | value | invariant |
|---|---|---|
| liveness | **LIVE** | — |
| bundle_kind | imitation | — |
| decisions / ranker_ok | 196 / **196** (equal) | I4 |
| fallback_heuristic / fallback_structural | **0 / 0** | I4 |
| weights_n | 177 (>0) | I2 |
| rank_calls / rank_nontrivial | 195 / 156 | — |
| **rank_nontrivial / rank_calls (I5)** | **0.80** (floor 0.30) ✅ | I5 |
| **feat_key_hit_frac (I6)** | **0.9965** (floor 0.50) ✅ | I6 |
| ko_rail | 1 | — |

I5 nontrivial_frac = **0.80** is far above the 0.30 floor — **no STOP** (the GBM produces highly
non-trivial rankings; I did not touch any floor). I6 feat-key hit 0.9965.

### Six negative controls — GBM bundle mutated, n=4 each → **every one FAILS LOUD**
All six: **nonzero exit, zero `JSON ` lines on stdout**, RuntimeError naming the invariant. Bundles
built in scratch (`$CLAUDE_JOB_DIR/tmp/neg`), never in `artifacts/`.

| control | injected defect | evaluator refusal |
|---|---|---|
| **N1** import-dead | `raise ImportError` at top of bundled scorer module | `ImportError` at the evaluator's eager unwrapped import — loud crash, no JSON |
| **N2** raise-every-decision | `choose` raises on every decision | **I2_weights_n** (choose dies before `load_weights` runs → `weights_n=−1`) |
| **N3** partial raise (every 10th) | `choose` raises when `choose_calls % 10 == 0` | **I4_per_decision_ranker** (ranker_ok ≠ decisions; fallbacks > 0) |
| **N4** blind model | all leaf values zeroed → equal scores → identity order | **I5_nontrivial** ✅ (as specified; vocab intact → I2 passes, I5 catches) |
| **N5** key drift | every vocab key prefixed `x_` → featurize keys never match | **I6_feat_key_hit** ✅ (as specified; also collapses I5) |
| **N6** env override | `PTCG_IMITATION_WEIGHTS` set in the gate process | **I3** — evaluator refuses to start (override decouples play from `strategy_sha256`) |

The GBM path reads the **same** `PTCG_IMITATION_WEIGHTS` env seam as the linear imitation bundle,
so I3 (N6) fires verbatim — no new env knob was added. N2 catching on I2 rather than I4 is honest
and correct: a ranker that raises on *every* decision never reaches `load_weights`, so `weights_n`
stays at its −1 sentinel and I2 is the first tripwire; N3 (partial) does reach `load_weights` and is
caught by the per-decision invariant I4. **The instrument is shown to SEE all six failure modes** —
no admissible result can come from a dead/blind/drifted/overridden ranker.

---

## Stage D — THE SCREEN (kill-only, n40) — result reported, verdict is the coordinator's

Pre-flight: box quiet, load in-band. `loadavg_before 1.20 1.34 0.96` → `loadavg_after 1.26 1.52 1.12`
(8 cores). Run seconds/game = **0.64**; s14 did 40 `search_begin` calls total (1/game — the known
s14 search-fallback, confirmed). Same seed policy / invocation as prior adx n40 runs.

**GBM-bundle vs s14, n=40:**

| metric | value |
|---|---|
| **winrate vs s14** | **0.125** (5 W / 35 L / 0 D) |
| Wilson 95% | [0.055, 0.261] |
| invalid | 0 |
| by seat (cand seat0 / seat1) | 4/20 · 1/20 |
| candidate liveness *in this screen run* | **LIVE** (nontrivial_frac 0.7307) |
| pre-registered kill floor (single-arm field v3) | 0.55 |
| winrate < floor | **True** |

The screen number is **0.125**, far below the pre-registered **0.55** kill floor. Per the task, I
report the number only — the verdict language ("killed" vs "survives to n400") is applied by the
coordinator after rpo confirms the collapsed one-arm floor. **The result is admissible**: the
candidate's liveness was LIVE *within the screen run itself* (ranker decided every game, 0
fallbacks, nontrivial_frac 0.73), so 0.125 is the GBM genuinely losing to s14 — not a dead-ranker
artifact. This is consistent with the standing doctrine that agreement is decoupled from win rate
(the GBM's +4.3 pp MAIN agreement over the linear model did not translate into games vs s14, exactly
as the linear model itself did not). **n40 kills or is silent — this is not a "pass."** I did **not**
start n400; per the task that is a coordinated step (box time, seeds, rpo pre-review) and is not
warranted here regardless.

---

### Summary of numbers (no verdicts — those are the coordinator's)
- Stage A fidelity: per-decision argmax agreement **100%**, max-abs score delta **0.0**.
- Stage B: imitation-kind bundle, bundled module reproduces val MAIN **0.5181**.
- Stage C: positive **LIVE** (I5=0.80, I6=0.9965); all six negatives **fail loud**, invariants
  I1(ImportError)/I2/I4/I5/I6/I3 — instrument sees every failure mode.
- Stage D: GBM-vs-s14 n40 winrate **0.125**, Wilson [0.055, 0.261], floor 0.55, below-floor **True**,
  liveness LIVE (admissible), 0 invalid.



