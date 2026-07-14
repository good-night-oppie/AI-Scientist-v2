# P3.1 — League harness (schema-complete)

adx-server (arena-1) · 2026-07-14 · repo @ 0c017a4 · task `~/P31_LEAGUE_TASK.md` (coordinator ai-scientist-8)
**Harness BUILD + rehearsal only. P3.2 full-cadence training remains BLOCKED — no expert-iteration
rounds run.** Round-0 summary (the schema exemplar): `artifacts/adx/league_round0_summary.json`.

---

## Pre-task — shared tolerance tie-break → serve parity 1.000000
Per the P3.0 verdict (rpo #3422): the 0.9733 serve-fidelity gap was 100% **exactly-tied options**.
Added `src/ready_player_one/ptcg/nn_serve.py` — a single `serve_rank(scores, tol=1e-4)` (group scores
within `tol` of the group head, order that group by ascending index) used by the numpy serve path, the
stdlib fallback, and the train-time eval — one tie-break, so all three pick the same action.

- **ACTION parity = 1.000000 across all three paths** with the shared tie-break, 0 mismatches:
  torch-vs-numpy 1.000000 (2000 + 150 samples), numpy-vs-stdlib 1.000000 (150 samples). A full
  14,087-decision val sweep was not completed within the window (each numpy transformer forward is
  ~100 ms → ~24 min, and the box was intermittently contended); across every sample drawn the
  mismatch budget is **0** — consistent with the exact-tie diagnosis. `scripts/nn_parity.py`.
- `tol=1e-4` chosen deliberately (≫ the ~6e-6 float32↔float64 noise, ≪ typical score gaps); **not
  coarsened** — a wider tolerance would merge genuinely-distinct options. If a true option-gap lands in
  the ~[9e-5,1.1e-4] band the residual is reported as a small mismatch budget, not hidden.
- Fixed NN bundle rebuilt (`submission_nn.tar.gz`); liveness re-confirmed LIVE (I5 0.767, I6 1.0).
- Caveat: the P3.0 D4 agreement 0.618 used `pim.agreement`'s exact argmax; the pool bundle now plays
  `serve_rank`. They differ only on tied (equivalent) options — play is unaffected.

## D1 — league pool loader (`scripts/league_pool.py`)
18 arms, each **hash-recorded at load**: 5 frozen bundles (s14, s18, linear-imitation, GBM, NN — real
sha256), 6 heuristic bots on the **canonical top-6 decks** (deck sha256), 4 diversity-deck slots
(kashiwashira/S4nkurero/vibechu/taksai — corpus has no 60-card decklists for them → **pending
coordinator decklists**), an **off-meta stratum** slot (pending harvest index), a **checkpoints/** pool
(empty until P3.2), and a reserved **exploiter** slot. Coordinator-supplied data is `pending_coordinator_input`,
never fabricated. Manifest: `artifacts/adx/league_pool_manifest.json`.

## D2 — round scheduler + per-round summary schema (THE deliverable)
`scripts/league_round.py` emits the round summary with **every** required field (coverage
non-negotiable). Checklist ↓ (round-0 values in the JSON):

| field | source | round-0 status |
|---|---|---|
| live_ladder_snapshots | coordinator poll file | pending_coordinator_input (labeled) |
| frozen_field_macro_history + per-arm winrates/Wilson/n | rehearsal games | populated |
| seat_splits_per_arm | rehearsal games | populated |
| exploiter_probe {run,winrate,n,threshold=0.62,verdict,budget} | probe run | not_run (rehearsal), schema populated |
| inference_time_ms p50/p90/p99/max — **numpy AND stdlib** | micro-benchmark | populated |
| s18_seconds_per_game (reference arm) | rehearsal games | populated |
| terminal_code_distribution (all games) | env.state | populated |
| episode_invariant_violations {invalid_action,ply_cap,no_legit_terminal,discarded_count} | env.state | populated |
| harvest_index {age_days,sha256,stale_flag>7d} | deck-refresh hook | populated (sample index) |
| calibration_ledger {brier,reliability_bins} | value head | **null_until_p32** |
| g4_window (trailing-3-round macro deltas) | macro history | populated |
| pause_for_gate_evidence {proc_group_stopped,cpu_samples,overlap_checked} | live demo | populated |

Timing distributions come from a **micro-benchmark** of `score_options` (numpy + stdlib), decoupled
from game count — the 200 rehearsal games run the numpy serve path only.

## D3 — G4 detector wired to HALT (`scripts/league_gates.py`)
Two independent trip wires → HALT marker + stop scheduler: **(1) windowed** — frozen-field macro
degrades >2pp over any trailing 3-round window; **(2) strength-referenced** — current checkpoint loses
Wilson-lo<0.50 h2h to an incumbent ≥2 rounds ago. Delivered as tested logic with synthetic fixtures.
**19/19 unit tests pass** (both wires fire on degrade/regression; healthy history + too-recent incumbent
+ insufficient history do NOT trip).

## D4 — checkpoint-replacement rule (MF6) + gate trigger (`scripts/league_gates.py`)
Pure `should_replace(...)`: replace iff **macro≥0.55 AND non-overlapping Wilson vs incumbent (n≥400)
AND h2h Wilson-lo>0.55 (n≥400, seat-balanced)** — all required. Pure `gate_eligible(...)`: eligible for
a beat-s14 gate iff replaced-incumbent AND frozen-field macro≥0.60. Unit-tested (covered by the 19/19):
strong candidate replaces; low-macro / overlapping-Wilson / thin-h2h / seat-imbalanced all correctly refuse.

## D5 — deck-refresh hook (`scripts/league_deckrefresh.py`)
Consumes a harvest-index file → re-derives canonical top-N modal decklists + samples the off-meta
stratum (rating≥1000 band), logs index **age_days + sha256** into the summary, **stale_flag at >7 days**.
Tested: fresh (age 1d)→stale_flag false; age 10d→stale_flag true. A labeled **SAMPLE** index
(`configs/harvest_index.sample.json`) exercises the schema; the real index is coordinator-supplied.

## D6 — rehearsal round-0 (no training) ✅
Pool loaded (18 arms); **200 games** across the frozen field (NN vs each opponent, 50 each,
seat-balanced); full summary emitted with **every field populated** (nulls only where P3.2-dependent).
`artifacts/adx/league_round0_summary.json`.

**Frozen-field arms (NN = the learned sparring partner):**

| arm | winrate | Wilson95 | n | seat0 / seat1 | s/game |
|---|---|---|---|---|---|
| s14_reference | 0.32 | [0.208, 0.458] | 50 | 0.40 / 0.24 | 2.5 |
| s18_active_search | 0.58 | [0.442, 0.706] | 50 | 0.60 / 0.56 | 10.3† |
| gbm_imitation | 0.74 | [0.605, 0.841] | 50 | 0.80 / 0.68 | 5.5† |
| linear_imitation | 0.40 | [0.276, 0.538] | 50 | 0.48 / 0.32 | 4.4† |

**Frozen-field macro = 0.51** (worst arm 0.32). The NN beats the GBM and s18, is roughly even with
linear, and loses to the champion s14 — a coherent sparring-partner profile (rehearsal only; no
kill/crown authority). †game timing inflated by heavy box load during the run (loadavg 8–12).

- **terminal_code_distribution:** {DONE_win 102, DONE_loss 98} — all 200 games reached a legit terminal.
- **episode_invariant_violations:** {invalid_action 0, ply_cap 26, no_legit_terminal 0, discarded_count 0}
  — 0 illegal actions; the 26 ply_cap are long (turn≥60) games (mostly the s18 search arm), all DONE.
- **inference_time_ms (micro-benchmark, re-run on the quieter box, loadavg recorded):**
  numpy p50 35 / p90 87 / p99 159 / max 195 ms · stdlib p50 1345 / p90 1435 / p99 1470 / max 1471 ms.
- **s18_seconds_per_game:** mean 10.3, p50 10.5, p90 18.3, max 23.3 s (under load).
- **harvest_index:** age 1 day, stale_flag false, sha256 recorded (sample index).
- **g4_window:** no HALT (macro history rising 0.28→0.30→0.51); deltas [+0.02, +0.21].
- **calibration_ledger:** null_until_p32 (value-head calibration is a P3.2 artifact).
- **exploiter_probe:** schema populated, not run in rehearsal (threshold 0.62 on record).
- **pause_for_gate_evidence:** a dummy process group was **actually SIGSTOP'd** mid-window
  (`proc_group_stopped: true`), instantaneous CPU samples + overlap-jobs count recorded.
- **G4 + replacement-rule unit tests: 19/19 green.**

## Operational note
Box was heavily contended during the rehearsal (agy + clickhouse + this job; loadavg 8–12), which
inflated game and inference timing — re-benchmarked inference on the quieter box and recorded loadavg.
No background waiters were used (P3.0 lesson); the game run was detached with incremental writes and
polled via a bounded loop.

## Deliverables
`artifacts/adx/p31-league-report.{md,json}`, `artifacts/adx/league_round0_summary.json` (schema
exemplar), `artifacts/adx/league_pool_manifest.json`, `configs/harvest_index.sample.json`,
`src/ready_player_one/ptcg/nn_serve.py` + fixed `submission_nn.tar.gz`. Marker `artifacts/adx/P31_DONE`.
