# C-GATE LIVENESS INSTRUMENTATION — work spec (BLOCKING the Phase-C n400 battery)

Status: DISPATCHED to mroute, 2026-07-12
Origin: ai-scientist-7 finding, adversarially verified 3/4 lenses (1 lens REFUTED the
coordinator's first fix design and forced the corrected one below).
Related: bus #3201 (manifest validation, merged as PR #27 @7e6fee5), #3206 (this hold).

## Verified corrections to the original finding (carry these — they change the fix)

1. IMPORT-DEATH IS ALREADY GUARDED. eval_search_head2head.py:116 eager-imports the ranker
   UNWRAPPED, so an import-dead ranker crashes the gate loudly (no JSON). _extract_bundle
   pre-seeds sys.modules, so IMITATION_MAIN_PY's import-time `except: _choose = None` is
   DEAD CODE inside the evaluator. PR #27 gets credit; do not spend budget here.
   (It remains live on Kaggle itself, where a raise forfeits — a deployment concern.)

2. THE DOMINANT DEATH MODE IS SILENT AND RAISES NOTHING. load_weights()
   (policy_imitation.py:341-364) swallows OSError/ValueError -> {} -> score_feats returns
   0.0 for EVERY option -> sorted(range(n), key=lambda i: (-scores[i], i)) is the IDENTITY
   permutation -> choose() returns a blind first-k pick and RETURNS NORMALLY.
   Empirical: trained weights rank [2,0,1,3]; empty weights rank [0,1,2,3].
   => A choose()-call counter with fallback==0 CERTIFIES THIS DEAD RANKER.
      That is s14's `search_begin_calls > 0` bug reincarnated. The naive fix is UNSOUND.

3. KEY-DRIFT IS EVEN QUIETER. A weights file with all 111 keys whose NAMES have drifted
   from what featurize() emits scores every option 0.0, weights_n > 0 passes, the one-shot
   empty-weights stderr warning never fires, and the strategy sha is clean. Phase C's whole
   program is iterating featurize() — this is the live risk, not a hypothetical.

4. THE BUILD-TIME GUARD IS BROKEN THE SAME WAY. validate_imitation's _counting
   (build_submission_search.py:463-470) increments BEFORE delegating, so `assert
   counter["choose"] > 0` (:497) passes even when choose() raises on 100% of decisions —
   it counts ATTEMPTS, not SUCCESSES, and prints "VALIDATION OK — imitation ranker wired".

5. PARTIAL DEATH IS INVISIBLE TODAY. Empirically reproduced: a ranker raising on 10% of
   decisions has those decisions silently absorbed by the heuristic; the result JSON is
   IDENTICAL to a healthy run. Zero forfeits, zero invalids — fallbacks play legal moves.

6. PROVENANCE CONTAMINATION. PTCG_IMITATION_WEIGHTS (policy_imitation.py:349) overrides the
   bundled weights file and is read from the shared process env by BOTH bundles. A stray
   value makes candidate_strategy_sha256 certify bytes that never played.

7. ORDERING TRAP (why we do NOT monkeypatch). main.py FROM-imports choose, binding the
   function object at exec_module time. A patch installed after exec_module leaves main.py
   holding the original -> the imitation counter reads 0 (false alarm) AND the heuristic
   counter reads 0 (fallback==0 = THE GREEN LIGHT = false PASS). Counters therefore live
   INSIDE the bundle, at module level.

---

The finding SURVIVES (3/4 lenses upheld). Spec follows.

---

# WORK SPEC — C-GATE IMITATION LIVENESS INSTRUMENTATION

**To:** mroute · **From:** coordinator · **Blocks:** the n400 Phase-C gate battery (do not start it)

## 0. PATH CORRECTION (read first)

`/home/admin/gh/wt/ptcg-evalfix` **does not exist**. Ignore any instruction pointing there — it will silently no-op or read a pre-#27 evaluator.

The real #27-merged state is `origin/feat/ptcg-agent @ 7e6fee5` ("fix(eval): accept imitation bundles in the h2h evaluator (#27)") on top of `49798a3` (#26) and `332a390` (#25), in `/home/admin/gh/ready-player-one-ptcg`. Cut a fresh worktree:

```bash
git -C /home/admin/gh/ready-player-one-ptcg fetch origin
git -C /home/admin/gh/ready-player-one-ptcg worktree add \
  /home/admin/gh/wt/ptcg-liveness -b pr/ptcg-28-imitation-liveness origin/feat/ptcg-agent
```
All line numbers below are from `7e6fee5`.

## GOAL

Make `scripts/eval_search_head2head.py` **fail loud** whenever an imitation bundle's ranker is not actually deciding the game — dead-on-import, raising per-decision, blind-on-empty-weights, or blind-on-key-drift — so that a Phase-C gate result is admissible evidence rather than an uninterpretable number.

## WHY

**s14 precedent:** the live Kaggle champion silently played the pure heuristic for weeks because its only liveness guard, `search_begin_calls > 0`, was satisfied by the one begin-per-game that immediately failed — a guard that counted *attempts*, not *successes*. Weeks of "search-constant evolution" tuned dead code.

Today the imitation gate has the same shape. Imitation/policy is the **last productive lever** (search-tuning exhausted at s18-vs-s14 n300 = 0.4333; deck-transfer twice n400-falsified). Every silent death mode biases the gate **downward** (heuristic hybrid → ~0.50 wash; blind ordering → worse than heuristic), so an uninstrumented n400 would retire the last lever on fabricated evidence. And the direction is not the only reason to halt: a *positive* result would be equally unpromotable, because you would be shipping a bundle whose runtime identity was never verified — literally the s14 mistake.

The fix is ~1 hour, pre-run, zero rerun cost.

## DESIGN

### D0. Two facts that constrain the design

1. **`_load_agent` (eval_search_head2head.py:106-137) is `try:/finally:` with NO `except`.** Line 116's `importlib.import_module(f"{pkg}.policy_imitation")` is unwrapped, so an import-dead ranker already crashes the gate loudly. `_extract_bundle` (:90-103) renames `agpkg`→`agpkg_{label}` and rewrites `main.py`'s text, so `main.py`'s `from agpkg_{label}.policy_imitation import choose` resolves **from `sys.modules`** to the same object. **The import-time fallback in `IMITATION_MAIN_PY` is dead code inside the evaluator.** Do not spend budget on it; keep it (it is correct on Kaggle, where a raise forfeits).
2. **`main.py` uses `from … import choose as _choose` (build_submission_search.py:136, :144) — from-imports bind at `exec_module` time.** A monkeypatch of the module attribute installed *after* `exec_module` leaves `main.py` holding the original function. The dangerous mis-order is asymmetric: a late patch on the *heuristic* counter reads `fallback == 0`, which **is the green light** — a mis-ordered patch manufactures the exact evidence that would certify an all-fallback run. **This is why we do not monkeypatch.**

### D1. Counters live INSIDE the bundle (module-level), not in the evaluator

Module-level counters incremented **inside function bodies** are immune to from-import binding order, `exec_module` ordering, and any future rewiring of `main.py`. They also mean we gate **the exact artifact we ship**, not an externally-modified play path. Kaggle-valid: pure stdlib, never raises, and **must not change PLAY at all** (same returns, same order, same determinism).

**(a) `scripts/policy_imitation.py`** — add a module-level `STATS` dict:

```python
STATS = {
    "choose_calls": 0,       # decisions entered (sel is not None)
    "choose_returns": 0,     # decisions RETURNED normally  <-- successes, not attempts
    "ko_rail": 0,            # returned via the lethal rail (no ranking)
    "rank_calls": 0,         # decisions that reached rank_options
    "rank_nontrivial": 0,    # decisions where max(scores)-min(scores) > 1e-9
    "feat_keys_seen": 0,     # probe window only
    "feat_keys_hit": 0,      # keys present in the weights dict
    "weights_n": -1,         # len(load_weights()); -1 == load_weights never ran
    "weights_path": None,
    "weights_env_override": False,
}
FEAT_PROBE_DECISIONS = 200   # bound the key-coverage probe; counters after that are cheap
```

- Rename the existing `choose` body to `_choose_impl` (byte-for-byte identical logic). Define:
  ```python
  def choose(obs, deck, weights=None):
      if obs.get("select") is None:
          return _choose_impl(obs, deck, weights)   # deck submission: not a decision
      STATS["choose_calls"] += 1
      out = _choose_impl(obs, deck, weights)        # NO try/except — a raise must propagate
      STATS["choose_returns"] += 1                  # increment AFTER the call: successes
      return out
  ```
  **`choose_returns` is incremented after `_choose_impl` returns.** This is the whole point. `validate_imitation`'s `_counting` (build_submission_search.py:466-468) increments *before* delegating, which is why its `assert counter["choose"] > 0` (:497) passes even when `choose()` raises on 100% of decisions — the s14 defect, re-implemented. Do not copy it.
- In `_choose_impl`, bump `STATS["ko_rail"]` on the lethal-rail return.
- In `rank_options`, hoist `featurize` out of the comprehension so keys are visible, then count. Scores and their order are unchanged:
  ```python
  def rank_options(weights, sel, cur):
      opts = sel.get("option") or []
      seltype, ctx = sel.get("type", 0), sel.get("context", 0)
      probe = STATS["rank_calls"] < FEAT_PROBE_DECISIONS
      scores = []
      for o in opts:
          feats = featurize(o, sel, cur, seltype, ctx)
          if probe:
              for k in feats:
                  STATS["feat_keys_seen"] += 1
                  STATS["feat_keys_hit"] += 1 if k in weights else 0
          scores.append(score_feats(weights, feats))
      STATS["rank_calls"] += 1
      if scores and (max(scores) - min(scores)) > 1e-9:
          STATS["rank_nontrivial"] += 1
      return scores
  ```
- In `load_weights` (:341-364), **do not change the `except (OSError, ValueError): w = {}` behaviour** (raising would forfeit on Kaggle). Only record: `STATS["weights_n"] = len(w)`, `STATS["weights_path"] = path`, `STATS["weights_env_override"] = bool(os.environ.get("PTCG_IMITATION_WEIGHTS"))`. Set these on the cache-hit path too. Enforcement belongs to the gate, not the bundle.

**Why `rank_nontrivial` is mandatory:** `load_weights()` swallows OSError/ValueError → `{}` → `score_feats` returns `weights.get(k, 0.0)` = 0.0 for every option → `sorted(range(n), key=lambda i: (-scores[i], i))` (:326) is the identity permutation → `choose()` returns `[0..k-1]` and **returns normally**. A dead ranker in this state has `choose_returns == choose_calls` and `fallback == 0`. A choose-counter alone **certifies it**. Same topology as `search_begin_calls > 0`. `rank_nontrivial` is exactly 0 in that state and large for a live ranker.

**Why `feat_keys_hit` is also mandatory:** a weights file with 111 keys whose names have drifted from what `featurize()` emits scores every option 0.0 too — `weights_n > 0` passes, the stderr empty-weights warning never fires, the strategy sha is clean. Phase C's entire program is iterating on `featurize()`, so this is the live risk, not a hypothetical.

**(b) `IMITATION_MAIN_PY` (build_submission_search.py:126-169)** — add a module-level `STATS` in the template. This is the *independent* second counter:

```python
STATS = {
    "import_ranker_ok": False, "import_deck_ok": False, "import_heuristic_ok": False,
    "decisions": 0, "ranker_ok": 0, "fallback_heuristic": 0, "fallback_structural": 0,
}
```
- Split the import try/except so `agpkg.policy_imitation` and `agpkg.deck` are separately observable, and set the three `import_*_ok` flags. (This changes behaviour *only* in states the gate now rejects.)
- In `kaggle_agent`: keep the `sel is None → return list(_DECK)` short-circuit **outside** the decision counter. Otherwise `STATS["decisions"] += 1` at the top, `STATS["ranker_ok"] += 1` on a successful `_choose` return, `STATS["fallback_heuristic"] += 1` in the ranker's `except`, `STATS["fallback_structural"] += 1` on the final structural return. Never raise. Returns must be identical to today's.

**(c) `scripts/eval_search_head2head.py`** — the evaluator **reads** the counters; it installs nothing. There is no ordering trap left.

- `_load_agent` returns `(agent, counter, probe)` where `probe = {"kind": "imitation"|"search", "main_mod": mod, "pi_mod": <imported policy_imitation module or None>}`. Keep the eager import at :116 (it is our import-death guard) and the search branch's `api.search_begin` patch **byte-identical**.
- At the top of `run()`, if either bundle is imitation: `if "PTCG_IMITATION_WEIGHTS" in os.environ: raise RuntimeError(...)`. That env var (policy_imitation.py:349) takes **precedence over the bundled file** and is read from the shared process env by **both** bundles — a stray value would make an imitation-vs-imitation h2h compare two policies with identical weights while `candidate_strategy_sha256` faithfully certifies bytes that never played.
- Read the STATS dicts **after the game loop, inside the `try`** — before `_purge_modules` and `shutil.rmtree` in the `finally` (:241).
- Emit into the result JSON, per side (`candidate_` / `baseline_`): `bundle_kind`, `imitation_decisions`, `imitation_ranker_ok`, `imitation_fallback_heuristic`, `imitation_fallback_structural`, `imitation_rank_calls`, `imitation_rank_nontrivial`, `imitation_nontrivial_frac`, `imitation_ko_rail`, `imitation_weights_n`, `imitation_feat_key_hit_frac`, `imitation_import_ok`, `liveness`. Run-level: `imitation_weights_env_override: false`. Search bundles: all `imitation_*` fields `null`; existing search fields **unchanged**.
- Add the live counts to the `PROGRESS` line so a dead run is visible at the first 10%, not at the end.
- Also **fix `validate_imitation`** (build_submission_search.py:463-470, :497): increment **after** `_orig(...)` returns, and assert `nontrivial_frac > 0` alongside the existing non-empty-weights assert. It is currently a guard that a fully-dead ranker passes.

## INVARIANTS (fail-loud; a rung is INVALID if any fires)

Raise `RuntimeError` naming the invariant, **before** the `print("JSON " + …)` line, and exit nonzero. A failed rung must produce **no parseable result**, not a flagged one.

For every side whose `bundle_kind == "imitation"`:

| # | Invariant | Kills |
|---|---|---|
| I1 | `import_ranker_ok and import_deck_ok and import_heuristic_ok` | silent import fallback |
| I2 | `weights_n > 0` | missing / empty / corrupt weights → `{}` |
| I3 | `PTCG_IMITATION_WEIGHTS` unset in the gate process (checked before any game) | provenance decoupling; cross-bundle contamination |
| I4 | `decisions >= games` **and** `ranker_ok == decisions` **and** `fallback_heuristic == 0` **and** `fallback_structural == 0` | per-decision raise, total & partial |
| I5 | `rank_nontrivial / rank_calls >= 0.30` (`--nontrivial-floor`, calibrate from the positive control) | **blind index ordering — the mode a choose-counter passes** |
| I6 | `feat_keys_hit / feat_keys_seen >= 0.50` (`--feat-hit-floor`) | featurize/weights key drift with a full-looking weights file |
| I7 | `main_mod.STATS["ranker_ok"] == pi_mod.STATS["choose_returns"]` | **the instrument itself is broken** — two independent counters must agree, or the measurement is worthless (this disagreement is precisely what let s14 live) |

`invalid` (non-DONE) is **not** a liveness signal — every fallback path plays legal moves, so it stays 0. Do not rely on it.

Downstream: `scripts/aggregate_h2h_portfolio.py` must **reject** any result JSON with `bundle_kind == "imitation"` and `liveness != "LIVE"`, and reject any imitation result JSON lacking the `liveness` key at all (i.e. produced by a pre-fix evaluator).

## A/A RECERTIFICATION (required by bus #3201)

The search path must remain byte-identical. `cabt` is unseeded, so "identical results" is not achievable dynamically; prove it statically + structurally + distributionally.

- **A1 (bytes).** `git diff --name-only origin/feat/ptcg-agent...HEAD` must show **zero** files under `src/ready_player_one/ptcg/**` (`policy.py`, `cards.py`, `enums.py`, `cg/**`) and **zero** changes to `MAIN_PY` (the *search* template, build_submission_search.py:62), `build_search`, `search_is_active` (:172-179), or `search_policy.py`. Those files are copied into **both** bundle types — touching `policy.py` would change the search bundle's strategy sha. **The heuristic-fallback counter therefore must NOT live in `policy.py`; it lives in `IMITATION_MAIN_PY`.**
- **A2 (sha).** Rebuild the s14 search bundle at the new HEAD; assert `_strategy_sha256(new_tar) == _strategy_sha256(<live s14 tar>)` and that `REQUIRED_STRATEGY_MEMBERS` selection is unchanged. Paste both hex digests.
- **A3 (structure).** Show the diff of `_load_agent`'s search branch: the `api.search_begin` patch must still be installed **before** `exec_module` (:121-127 today). The only permitted delta on that branch is populating `probe["kind"] = "search"`.
- **A4 (dynamic A/A).** s14-vs-s14, `n=60`, on the **patched** evaluator: `invalid == 0`; `candidate_search_begin_calls == baseline_search_begin_calls == 60` (the frozen-s14 one-begin-per-game signature — any deviation is itself a red flag); winrate's Wilson interval contains 0.50; **no `imitation_*` invariant is evaluated** (all imitation fields `null`). Paste the JSON. If the lane has a pre-change s14-vs-s14 A/A JSON, show CI overlap with it.
- **A5 (play-identity).** Unit test: for a fixed set of synthetic `obs` (including a KO-rail case, a self-loss case, a recovery `TO_DECK` case, and a `sel is None` deck submission), `choose()` returns **exactly** the same index list as the pre-change `policy_imitation.py` (extract the old module via `git show 7e6fee5:scripts/policy_imitation.py` into a temp file and import both). Counters must not change PLAY.

## ALLOWED PATHS

Touch only:
- `scripts/policy_imitation.py`
- `scripts/build_submission_search.py` — **only** `IMITATION_MAIN_PY` and `validate_imitation`
- `scripts/eval_search_head2head.py`
- `scripts/aggregate_h2h_portfolio.py` — reject non-LIVE imitation results
- `tests/test_imitation_bundle.py`, `tests/test_eval_imitation_members.py`, and a new `tests/test_imitation_liveness.py`

**Forbidden:** `src/ready_player_one/ptcg/**` (any file), `artifacts/**`, `MAIN_PY` / `build_search` / `search_is_active` in the builder, `scripts/deck_search*.py`. Negative-control bundles are built in a scratch dir and **never** committed.

**Note:** these edits change `agpkg/policy_imitation.py` and `main.py` bytes → the C bundle's `candidate_strategy_sha256` changes → **the C bundle must be rebuilt**. Any pre-existing C tar is stale. (No C gate evidence exists yet, so nothing is invalidated.)

## ACCEPTANCE EVIDENCE (paste all of it; no summaries)

1. `git diff --name-only` — allowed paths only. A2's two sha digests.
2. **POSITIVE CONTROL** — real weights, C-vs-s14, `n=40`. Paste the full result JSON. Must show: `candidate_bundle_kind=imitation`; `decisions > 0` and `decisions/games` (report the real per-game decision count); `ranker_ok == decisions`; `fallback_heuristic == fallback_structural == 0`; `weights_n > 0` (report it — the shipped file has ~111 keys); `nontrivial_frac` (report the **actual** value — this calibrates I5's floor; if it lands below 0.30, report and stop, do not lower the floor to fit); `feat_key_hit_frac`; `ranker_ok == choose_returns` (I7); `candidate_search_begin_calls == 0`, `baseline_search_begin_calls == 40`; `liveness == "LIVE"`.
3. **NEGATIVE CONTROLS — this is the point of the whole spec.** Each must **FAIL LOUD**: nonzero exit, a `RuntimeError` naming the invariant, and **no `JSON ` line on stdout**. `n=4` games is enough. Paste the stderr and name the invariant that fired for each:
   - **N1 import-dead** — inject `raise ImportError` at the top of the bundled `agpkg/policy_imitation.py`. (Confirms the existing eager import still kills the run; this is a regression check, not a new capability.)
   - **N2 raise-on-every-decision** — patch bundled `choose` to raise. Today this is **invisible**: `main.py` swallows it, the heuristic plays, `search_begin` stays 0, the JSON is byte-indistinguishable from a healthy run. Must now fail with `fallback_heuristic == decisions`, `ranker_ok == 0` (**I4**).
   - **N3 partial raise (every 10th decision)** — must **FAIL**, not warn (**I4**).
   - **N4 blind weights** — replace `agpkg/imitation_weights.json` with `{}`. `choose()` never raises; `ranker_ok == decisions`; `fallback == 0`. **A naive choose-counter passes this.** Must fail on **I2 and I5 independently** — show both fire.
   - **N5 key drift** — keep all 111 keys but prefix every key with `x_`. `weights_n == 111 > 0`, no exception, no stderr warning, clean strategy sha. Must fail on **I6** (and I5). This is the mode `weights_n` alone cannot see.
   - **N6 env override** — run with `PTCG_IMITATION_WEIGHTS=/tmp/other.json`. Gate must refuse to start (**I3**), before any game.
4. **A/A recert:** A4's JSON, plus A5's play-identity test passing.
5. **Builder guard fixed:** show `validate_imitation` now increments after the call, and that an N2-style bundle (raises on every decision) now **fails** build validation. Today it prints `VALIDATION OK — imitation ranker wired`.
6. `ruff check` + `ruff format --check` + `python -m pytest -q` all green.

A rung that only proves the positive control is **not accepted**. The instrument must be shown to *see* the failure it exists to catch.

## HAZARD

**Edit-tool changes to tracked files in the `ready-player-one` worktrees are silently reverted by a formatter hook.** Write with `Bash` heredoc (`cat > path <<'EOF'`), then run `ruff format` manually, then **`git diff` to confirm the change actually landed** before running anything. A silently-reverted instrumentation patch that then "passes" the positive control is the same failure class this spec exists to prevent.