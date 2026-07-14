**Why the −2.0 pp on-policy guardrail exists:** **the expansion added ZERO on-policy data.** `ARCHETYPE_CORE = {6, 678, 1102, 1141, 1142, 1152}` (`scripts/policy_imitation.py:74`). The only >=1100 team hitting 6/6 core is **Benjamin Zhao3927** — **553 records in the OLD dataset, 553 in the NEW dataset. Literally zero growth.** Its supervision *share* collapsed 5.3% → 0.7%. Meanwhile kazuki0123 + WinDecks — **46% of the new supervision (31,488 records)** — appear in **no harvest file at all**; we do not know what deck they pilot. And on that one on-policy slice, retraining **measurably hurts**: C-v2 vs C-v1 = **−4.7 pp overall / −7.3 pp MAIN** (n=506, MAIN n=328, ~2–2.5σ — suggestive, not conclusive, but pointing exactly the way the contrarian case predicts). A −2.0 pp tolerance admits noise and blocks the observed magnitude. **We will not trade a real loss on the deck we field for an aggregate gain across 32 decks we do not.**

### THE STRONGEST COUNTERARGUMENT, AND WHY IT LOSES

> *"Agreement is a proven-decoupled proxy in this exact lane. The B battery recorded per-decision agreement rising 28.2% → 41.8% while win rate collapsed to 0.0675. Every number in this pre-screen is an agreement number. You are about to select the artifact with the metric that already burned you."*

It is the right objection and I accept its core. Three reasons it does not overturn C:

1. **The pre-screen is a SELECTOR, never a PROMOTER.** No agreement number may close a gate, and none will. The B-battery failure was agreement being used as *evidence of quality*. Here it is used only to choose **which of two members of the same model family** — differing solely in a weight vector fit on the same objective by the same code — spends the game budget. That is a strictly weaker, strictly safer use.
2. **The B-battery poison was structurally different.** The RCA names it: *"the dominant poison is the UNFLAGGED flat MAIN_SCORES reorder itself"* — a change in the **search head**, unflagged. C-v1f vs C-v2f is not a search-head reorder; it is the same ranker with more supervision. The documented decoupling does not transfer, and pretending it does would mean **refusing all static signal — i.e. gating blind, which Eddie's standing directive forbids.**
3. **The alternative is worse.** **D (gate both arms) doubles exposure to a metric with six recorded n40 mirages**, forces alpha-splitting on the only bar that counts (n160 vs live-s14 >= 0.55), and — with **ONE Kaggle probe slot** — *still requires a tiebreak at the end*. Tiebreaking for free before the gate beats tiebreaking for 2× the games after it. **D is also actively unsafe today:** a C-vs-C arm is the configuration most exposed to `PTCG_IMITATION_WEIGHTS` (`policy_imitation.py:349`), which is read from the **shared process env by both bundles** — a stray value silently makes both sides play identical weights while the two strategy SHAs honestly certify different bytes — and in C-vs-C **both sides have `search_begin == 0`, so the result JSON carries literally zero liveness signal.** That is invariant I3 of #3206 and it is not implemented. **Do not run C-vs-C before #3206 lands.**

**A is rejected** (no speed advantage; gates a model the screen says loses to A1 out of domain). **B is rejected** (C minus the decision rule — same cost, no pre-registration). **D is rejected** (2× arms, alpha dilution, one probe slot, and unsafe until #3206).

### DOES THE PRE-SCREEN EXIST? PARTIALLY. Building the rest is small.

`cmd_train --baseline` (`scripts/policy_imitation.py:528-575`) already does the episode-disjoint split, grades with `agreement()`, emits `train_eval` / `val_eval_full` / `val_eval_archetype6`, and grades A1 under identical argmax semantics with an identical denominator. **But `train` is the only subcommand and it ALWAYS refits — there is no way to score the EXISTING committed weights against the NEW split.** Without that, you cannot distinguish *"more data helped"* from *"the val split got easier."* **The whole decision rests on that distinction.**

The missing piece is **a ~10-line `eval` subcommand** wiring `agreement(records, perceptron_scorer(load_weights(path)))` — both building blocks already exist (`:429-440`, `:462-489`). Plus a **one-line fix to `archetype_teams()`** (`:503`), which hard-codes two date-stamped harvest files and — unlike the dataset builder — **does not read `manifest.json`**, so the archetype-6 slice silently collapses to Benjamin Zhao3927 alone and `agreement()` returns `None` on an empty slice rather than raising. **Rule (ii) is noise until that is fixed.**

**Is it worth it? Yes.** ~30 minutes of engineering, inside a ≥1-hour block, to avoid spending 2,800 games on the wrong artifact and a one-shot Kaggle slot on a model that cannot beat the heuristic. That is not a research project. It is a spec.

---

## 5. WORK SPECS TO DISPATCH

### SPEC 1 — mroute — "C-v2 build env, bucket fallback, static pre-screen"

**GOAL:** Produce two comparable C artifacts (C-v1f, C-v2f) and a reproducible held-out pre-screen report that mechanically applies the pre-registered rule in §4.

**CONSTRAINTS**
- Work in a **NEW worktree** `/home/admin/gh/wt/ptcg-cv2` at `origin/feat/ptcg-agent` (`7e6fee5`). **Do NOT rebase, reset, or checkout in `/home/admin/gh/ready-player-one-ptcg`** — it is divergent (6 ahead / 39 behind) and it holds the only copy of the corpus.
- Symlink the corpus in (see §3). `runs/imitation/` must be a **real dir** (the trainer writes into it); only `imitation_pairs.jsonl` is symlinked. Source corpus is **READ-ONLY**.
- **FORMATTER-HOOK HAZARD:** do **not** use the Edit tool on tracked files. **Bash heredoc write → `uv run ruff format <file>` → `git diff --stat` to verify the write survived.** An Edit "success" in this repo means nothing.
- No torch. No new deps. Pure stdlib + existing engine ctypes.

**TASKS**
1. **`archetype_teams()` fix** (`scripts/policy_imitation.py:503`): read `runs/replay_mining/manifest.json` in addition to the two dated `inline_harvest_*.json` files, matching `build_imitation_dataset.load_team_scores` (`:62,:70`). Make `agreement()` raise (not return `None`) when handed an empty slice.
2. **Bucket fallback:** in `choose()` (`scripts/policy_imitation.py:302-335`), route `seltype == 8` (COUNT) and `seltype == 9` (YES_NO) to `ready_player_one.ptcg.policy.choose`. Gate behind `PTCG_IMITATION_BUCKET_FALLBACK`, **default ON**, via the existing `_flag(name, default=True)` pattern. Unit test: fallback ON vs OFF changes only seltypes 8/9.
3. **New `eval` subcommand:** `python scripts/policy_imitation.py eval --pairs <jsonl> --rm-dir runs/replay_mining --weights <path> [--baseline]` → scores **existing** weights on the same episode-disjoint split, emits `val_eval_full` + `val_eval_archetype6` + `train_eval` + A1 baseline, writes `--out/imitation_eval_<label>.json`. ~10 lines around `agreement(records, perceptron_scorer(load_weights(path)))`.
4. **Retrain:** `python scripts/policy_imitation.py train --pairs runs/imitation/imitation_pairs.jsonl --rm-dir runs/replay_mining --out runs/imitation --baseline`.
5. **TRAP #1 — MANDATORY, SILENT-FAILURE:** training writes `runs/imitation/imitation_weights.json`, but the bundle builder bakes **`scripts/imitation_weights.json`** (`build_submission_search.py:54,:413`), and `validate_imitation` only asserts the weights are **non-empty, not fresh**. You **must** `cp runs/imitation/imitation_weights.json scripts/imitation_weights.json` **and assert the key count != 111** before any bundle build. Skipping this ships the OLD 9,269-pair weights while every log says "imitation bundle."
6. **Stash hygiene:** `git stash show -p stash@{0} > .fleet-goal/evidence/M2/stash-de4d705-superseded.patch`, then `git stash drop`. (Refs are shared across worktrees — one stash, one ref.)

**ALLOWED PATHS:** `/home/admin/gh/wt/ptcg-cv2/scripts/policy_imitation.py`, `/home/admin/gh/wt/ptcg-cv2/scripts/imitation_weights.json`, `/home/admin/gh/wt/ptcg-cv2/tests/`, `/home/admin/gh/wt/ptcg-cv2/runs/imitation/` (write), `.fleet-goal/evidence/M2/`. **Read-only:** `/home/admin/gh/ready-player-one-ptcg/runs/**`.

**ACCEPTANCE EVIDENCE**
- `imitation_eval_c_v1f.json` and `imitation_report.json` (C-v2f), both with `val_eval_full.main_top1_agreement` and `val_eval_archetype6.main_top1_agreement`, plus the A1 baseline, on the **same** episode-disjoint split.
- Archetype-6 slice: report `main_n`. **If `main_n < 200`, declare rule (ii) unmeasurable and say so** — do not silently fall back to rule (i).
- Sanity anchor: A1 full-set MAIN must reproduce ≈**0.2866** (the independently-measured 28.2% plateau). If it does not, the harness is lying — stop.
  - **[CORRECTED 2026-07-13 (sctst-aide, per Eddie): anchor := full-set MAIN ≈0.3385 on the 679-corpus, NOT 0.2866.** Reproduced from the bytes with the frozen `heuristic_scorer()`+`agreement()` (332a390): 679-corpus full-set MAIN = **0.3385**, val-split (`val_eval_full`) MAIN = **0.3318**; 106-corpus = 0.4177 / 0.3941. The `heuristic_scorer` reproduces NEITHER corpus at 0.2866. The 0.2866 is the M1 divergence-analysis plateau (separate code path / pre-bugfix policy), not an R0 the ablation harness emits — treating it as the pass condition would falsely trip the "harness is lying → stop" clause on a CORRECT run. Evidence: `2026-07-13-r0-anchor-correction.md`.]
- SHA-256 of both `imitation_weights.json` files, and the key count of each (v1 = 111; v2 ≠ 111).
- Full test suite green; `ruff` clean; `git diff --stat` confirming every intended write landed.
- **Do not build a bundle or run a game rung under this spec.** Report the rule's outcome; the coordinator selects.

---

### SPEC 2 — mroute — "#3206 liveness + evaluator hygiene" (BLOCKS the battery)

**GOAL:** Make a C gate rung capable of failing loudly. Until this lands, **no C rung counts — a positive result is as unpromotable as a negative one.**

**TASKS (I1–I7 per the #3206 spec, plus three confirmed defects):**
1. **`validate_imitation` counts ATTEMPTS, not SUCCESSES.** `build_submission_search.py:466-468` increments the counter **before** delegating, so `assert counter['choose'] > 0` (`:497`) passes and prints "VALIDATION OK — imitation ranker wired" **even if `choose()` raises on 100% of decisions.** This is the s14 `search_begin_calls` bug reincarnated. Count successful returns.
2. **`IMITATION_REQUIRED_STRATEGY_MEMBERS`** (`eval_search_head2head.py:28-32`) **omits `deck.csv`**, which the search required-set demands. Not exploitable today (`build_imitation` always writes it) but it is an asymmetric weakening of the manifest check. Add it.
3. **`PTCG_IMITATION_WEIGHTS`** (`policy_imitation.py:349`) takes precedence over bundled weights and is read from the **shared process env by both bundles**. Guard it (invariant I3): assert unset, or assert each side's loaded-weights SHA matches its own bundled file.
4. **`check_invariants([])` passes vacuously** (`build_imitation_dataset.py:157-190`). Add `assert records`. Also: either give **inv4** a real assert with a corpus-*relative* bound, or delete it from the "invariants" list and call it a metric. **Its docstring constant (6,071) is currently violated at 41,692 with nothing failing.**
5. **A/A recertification (A1–A5)**: bytes / SHA / structure / dynamic n60 / play-identity. **PR #27's verification was a 4-game smoke run, not an A/A.** This is still owed from #3201.
6. **Echo `git rev-parse HEAD` at the top of `run_c_gates.sh`.** The last battery launched from a worktree pinned one commit before the fix and burned 13 rungs on `ValueError`.

**ACCEPTANCE:** A/A n60 at ~0.50 with liveness counters non-zero on both sides; six negative controls (blind weights, empty weights, raising `choose`, wrong-file weights, env-override, missing member) each **fail loudly**; positive control n40 passes. Total ~124 games, ~2 min. Self-estimate ~1 hour engineering. **This forces a C bundle rebuild** — any pre-existing C tar is stale.

---

### SPEC 3 — sctst-aide — "on-policy supervision, not more ladder"

**GOAL:** Answer the highest-value missing fact and fix the corpus's actual defect. **Do NOT harvest more random ladder replays** — per-replay yield already fell 21%, and the last 573 episodes added **zero** on-policy data.

1. **Mine the decklists for `kazuki0123` and `WinDecks`.** They are **46% of the >=1100 supervision (31,488 records)** and appear in **no harvest file**. Until we know their decks we cannot say whether the single largest chunk of our supervision is on- or off-policy. Cheap; highest value.
2. **Targeted expansion on core>=6 teams only** (`ARCHETYPE_CORE = {6, 678, 1102, 1141, 1142, 1152}`): Benjamin Zhao3927, kuma_jp, and any newly-identified 6/6 team. Target: raise Benjamin Zhao3927 from **553 records** to **>= 2,500**, enough to make rule (ii) decisive rather than 2σ.
3. Same frozen-miner discipline as before (hash-pinned `mine_replays.py`, scratchpad wrapper, `--rate 0.5`). **Report per-replay yield, not just episode count.**

**ACCEPTANCE:** decklists for the top-2 supervision sources, with core-card overlap vs `ARCHETYPE_CORE`; `dataset_stats.json` showing Benjamin Zhao3927 record count; **and the honest cross-basis growth statement** (fixed-manifest, per-replay yield), not a headline multiple.

---

## 6. WHAT TO TELL RPO

**Obligation 1 — THE GATED ARTIFACT WILL DIFFER FROM `C @332a390c`. EITHER WAY.** This is not conditional on the retrain. The **bucket fallback changes `policy_imitation.py` bytes**, so even C-v1f is no longer `@332a390c`. Guardrail (1) of the #3202 pre-registration names that commit explicitly. **Notify rpo before any rung runs.** Silence-equals-proceed does **not** carry across an artifact change.

**Obligation 2 — Re-open a fresh, time-boxed objection window** on the amended artifact, same duration as #3202, and **do not launch rung 1 until it closes.** The probe memo must pin, per the pre-registration: **bundle SHA-256 + deck CSV SHA-256 + imitation-weights SHA-256** — and, because #27 now folds `agpkg/imitation_weights.json` into the strategy SHA, also the **candidate strategy SHA-256** emitted by the evaluator.

**Obligation 3 — Correct three things in the shared record.** (a) **"4 fail-loud invariants" is THREE**; inv4 is an unenforced metric whose documented expected value is now silently violated. (b) **"67,802 pairs" is a filtered sub-metric** of 76,405 written records (the 9,269 baseline uses the same key, so the ratio is sound — the *label* is not). (c) **"7.3x pairs off 6.4x replays" is cross-basis and reads backwards**: on a fixed manifest the corpus contributed **5.26x**, and **per-replay yield fell 21%**. Anyone deciding "harvest more replays" off the 7.3x figure would be deciding off a flattered number.

**Obligation 4 — Correct the standing brief's stale premises.** `/home/admin/gh/wt/ptcg-evalfix` **does not exist**; mroute's evaluator fix **already merged as PR #27 (`7e6fee5`)**. **The blocker is #3206 (C-gate liveness), which is DISPATCHED but NOT STARTED** — no branch, no worktree, and the A/A recertification owed from #3201 was never done. **Name an owner for #3206 today.** The C battery cannot legitimately run without it, and a *passing* result without it is as unusable as a failing one.

**Obligation 5 — Pre-register the decision rule itself** (§4, verbatim) **before** the pre-screen runs, not after. That is the whole point. And restate the constraint that makes it binding: **the pre-screen is a SELECTOR, never a PROMOTER. No agreement number closes a gate.** Promotion requires n400 + independent reconfirm on **games**, vs frozen s14, exactly as the lane learned the hard way six times.

**Obligation 6 — Flag the corpus's real limitation honestly.** The expansion is genuine and it is a good piece of work. It is also **50.7% WinDecks by episode, 33 teams after the >=1100 filter, and it added ZERO records for the only team running our archetype deck.** We are currently distilling how to pilot decks we do not field. That is a strategic question for the next milestone, not a reason to withhold DONE — but rpo should hear it from us, not discover it.

---

### ONE-LINE SUMMARY
**ACCEPT the corpus DONE with three corrections to the record; DROP the stash (zero surviving hunks, non-compiling); build C-v2 in a fresh worktree at `7e6fee5` with the corpus symlinked in; apply the free COUNT/YES_NO fallback to BOTH candidates; run the static pre-screen inside the ≥1h #3206 block at zero calendar cost; gate exactly ONE artifact per the pre-registered rule (+5.0 pp full-MAIN AND no worse than −2.0 pp on-policy); and notify rpo now, because the gated artifact is no longer `C @332a390c` under any branch of the decision.**