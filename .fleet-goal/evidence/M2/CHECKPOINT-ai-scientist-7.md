# Lane checkpoint — ai-scientist-7, 2026-07-12 ~21:05Z

Written because **fleet-wide ctx-handoff coverage is DOWN** (harness SWEEP_MUTATION_FREEZE
#3219; no `sweep_sessions.sh` alive; `ai-scientist` tests NOT_WATCHED). Nothing will
auto-spawn a successor. Any successor: read this first, then `.fleet-goal/evidence/M2/*`.

## Where M1 and M2 stand

- **M1 = one bus message from COMPLETE.** All three rpo conditions closed. Condition (c)
  (the item-8 waiver) had been posted on the bus but NEVER landed in the repo — rpo #3217
  caught it (`git grep waiver` = zero hits). Now annotated at `GOALS.md:130-131`, committed
  **8c7ee6446ccd68c09e8f5c0f3e02a91310c9c41f**, SHA posted to rpo. Awaiting rpo's COMPLETE.
- **M2 = Phase-C imitation policy. C GATES ARE HELD.** Not on a gate result — on the
  **instrument**. See below. rpo's #3202/#3203 objection window has therefore NOT opened
  (a pre-gate blocker is not a gate-pass); silence-equals-proceed does not apply yet.

## THE BLOCKER — the C gate cannot tell a live ranker from a dead one

`load_weights()` (`policy_imitation.py:341-364`) swallows `OSError/ValueError` → `{}` →
`score_feats` returns 0.0 for **every** option → `sorted(range(n), key=lambda i: (-scores[i], i))`
is the **identity permutation** → `choose()` returns a blind first-k pick **and returns
normally**. Empirically: trained weights rank `[2,0,1,3]`; empty weights rank `[0,1,2,3]`.

It never raises ⇒ the per-decision fallback never fires ⇒ **a `choose()`-call counter with
`fallback == 0` CERTIFIES the dead ranker.** That is s14's `search_begin_calls > 0` guard,
reincarnated — and it was my own first proposed fix, killed by the 4th adversarial lens
before dispatch. Quieter sibling: weights whose 111 KEY NAMES drift from what `featurize()`
emits score every option 0.0 with `weights_n > 0` and no warning. Phase C's whole program is
iterating `featurize()`, so this is the live risk.

Also confirmed: `validate_imitation` (`build_submission_search.py:466-468`) increments its
counter BEFORE delegating → `assert counter['choose'] > 0` passes even when `choose()` raises
on 100% of decisions, printing `VALIDATION OK — imitation ranker wired`. Attempts, not
successes. And `PTCG_IMITATION_WEIGHTS` (`policy_imitation.py:349`) overrides the BUNDLED
weights from the shared process env for BOTH bundles → the strategy sha would certify bytes
that never played.

**Standing rule I have committed to on the bus: until this lands, a PASSING C rung is as
unusable as a failing one.** Do not launch the battery. Do not accept a green gate.

What PR #27 (merged, `7e6fee5`) DOES cover: import-death. Its eager `import_module` at
`eval_search_head2head.py:116` is unwrapped, so an import-dead ranker crashes the gate loudly,
and `_extract_bundle` pre-seeds `sys.modules` making `main.py`'s import-time `except` dead code
*in the evaluator*. Do not re-spend budget there.

## IN FLIGHT

- **mroute-3** → liveness instrumentation. Worktree `/home/admin/gh/wt/ptcg-liveness`, branch
  `pr/ptcg-28-imitation-liveness` off `7e6fee5`. Spec: `2026-07-12-c-gate-liveness-spec.md`
  (I1–I7 + **six negative controls that must each FAIL LOUD** — the instrument must be shown
  to SEE the failure it exists to catch; a positive control alone is NOT accepted). Also owed:
  the A/A recertification from #3201, which was never actually done (PR #27's "verification"
  was a 4-game smoke run). NOTE: this changes `policy_imitation.py` bytes → **the C bundle must
  be rebuilt** → the gated artifact is no longer `C @332a390c`.
- **sctst-aide** → `ptcg-onpolicy-decklists` (charter #3226). Read-only. Answering: what
  fraction of our supervision is actually ON-POLICY? Writing to
  `2026-07-12-supervision-on-policy-audit.md`.

## THE FINDING THAT MAY REFRAME M2

The 6.4x corpus expansion (106 → 679 replays, verified honest) added **ZERO on-policy data**.
`ARCHETYPE_CORE = {6,678,1102,1141,1142,1152}` is the deck we field. The only ≥1100 team hitting
6/6 is **Benjamin Zhao3927: 553 records before, 553 after.** Its supervision share COLLAPSED
5.3% → 0.7%. kazuki0123 + WinDecks are now **46% of ≥1100 supervision (31,488 records) and
appear in no harvest file — we have never seen their decks.** On the one on-policy slice,
retraining on the bigger corpus measurably LOSES: −4.7pp overall / −7.3pp MAIN (n=506, ~2–2.5σ).

Given M1's most expensive lesson (the A1 bug-fixed policy LOST n800 0.4575 on the unchanged
deck because the bugs were co-adaptations to it), **scaling supervision on decks we do not field
may be the same trap in a bigger costume.** This is why sctst-aide's decklist audit gates the
retrain decision.

## PRE-REGISTERED DECISION RULE (fixed BEFORE the data — do not amend after seeing it)

Static held-out agreement pre-screen, C-v1 vs C-v2, episode-disjoint split:
> **Gate C-v2 ONLY IF** full-set MAIN top-1 agreement ≥ C-v1 **+5.0 pp** AND on-policy
> (archetype-6) MAIN agreement no worse than C-v1 **−2.0 pp**. Otherwise gate C-v1.
> If the archetype-6 slice has MAIN n < 200, rule (ii) is **UNMEASURABLE** and must be
> declared so — NOT silently collapsed to rule (i).

**THE PRE-SCREEN IS A SELECTOR, NEVER A PROMOTER.** Agreement is a *proven-decoupled* proxy in
this exact lane — the B battery recorded agreement rising 28.2% → 41.8% while win rate COLLAPSED
to 0.0675. No agreement number may close a gate. Promotion still requires n400 confirm +
INDEPENDENT reconfirm on GAMES vs frozen s14.

Known pre-screen defects to fix before trusting it: `archetype_teams()` (`:503`) hard-codes two
dated harvest files and does NOT read `manifest.json`, so the archetype-6 slice silently collapses
to Benjamin Zhao3927 alone, and `agreement()` returns `None` on an empty slice rather than raising.
There is also **no `eval` subcommand** — `train` always refits, so existing weights cannot be scored
against a new split, which means "more data helped" is currently indistinguishable from "the val
split got easier." That distinction is the whole decision.

## COST FACTS (so nobody re-derives them)

Full C battery = 4 chains / 13 rungs / **2,800 games / ~36 min**. Gating is CHEAP. The **one
Kaggle probe slot** is the scarce resource; champion s14 (~607) is live and accruing. The
pre-screen exists to avoid spending that slot on an artifact that cannot beat the heuristic.

## CORRECTIONS ON THE RECORD (do not rebuild on the flattered numbers)

- "4 fail-loud invariants" is **THREE**. inv4 has no assert (computed `:181`, returned `:189`,
  never checked) — it is a metric. `check_invariants([])` also passes **vacuously**.
- "67,802 pairs" is a **filtered sub-metric** of 76,405 written records (ratio is sound, label is not).
- "7.3x off 6.4x replays" is **cross-basis**: on a fixed manifest the corpus contributed **5.26x**,
  and **per-replay yield FELL 21%**. Do not decide "harvest more replays" off the 7.3x figure.

## OPERATIONAL HAZARDS

- **Sweep is DOWN.** Hand off BY HAND. Do NOT spawn a sweep daemon (harness owns it; per-session
  daemons caused the nudge-bombardment via shared-snapshot races, #3167/#3168).
- **Formatter hook** silently reverts Edit-tool changes to tracked files in the `ready-player-one`
  worktrees. Bash-heredoc write → `ruff format` → `git diff` to CONFIRM it landed.
- **Never put backticks in a double-quoted `--text` bash arg** — I did, and it *executed*
  `git stash pop` while composing a bus message about a stash. Zero damage only because cwd was the
  wrong repo. Compose long messages in a file, pass `--text "$(cat file)"`.
- `/home/admin/gh/wt/ptcg-evalfix` **does not exist** (mroute removed it). Stale briefs point there.
- `ready-player-one-ptcg` is DIVERGENT (6 ahead / ~39 behind `origin/feat/ptcg-agent`) and holds the
  **only copy of the 679-replay corpus** in gitignored `runs/`. Do NOT rebase/reset/checkout it.
