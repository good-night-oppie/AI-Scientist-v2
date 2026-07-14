# R0 sanity-anchor correction — 0.2866 is wrong for the ablation harness

**Author:** sctst-aide · **Date:** 2026-07-13 · **Requested by:** Eddie ("fix the R0 anchor and tell mroute")
**Corrects:** `2026-07-12-deck-agnostic-ablation-spec.md` (R0 line + ACCEPTANCE) and
`2026-07-12-gate-target-decision-memo.md` (sanity-anchor bullet).

## TL;DR

The ablation spec's R0 sanity anchor — *"A1 full-set MAIN must reproduce ≈0.2866, else the harness
is lying, STOP"* — **would misfire.** The frozen ablation harness does **not** produce 0.2866 on
either corpus. Reproduced from the bytes:

| corpus | full-set MAIN | val-split (`val_eval_full`) MAIN |
|---|---:|---:|
| 106-replay (baseline, 9,269 pairs) | 0.4177 | 0.3941 |
| **679-replay (canonical, 76,405 pairs)** | **0.3385** | **0.3318** |

**Neither corpus yields 0.2866 through `policy_imitation.py`.** So 0.2866 is not an R0 the harness
emits — it is *"the independently-measured 28.2% plateau"* (the decision memo's own words) from **M1's
separate divergence analysis**, a different code path and/or the pre-bugfix policy. If mroute
implements R0 as `heuristic_scorer` full-set MAIN and gates on `≈0.2866`, it will read **0.3385**,
see a +5.2 pp mismatch, and conclude *"the harness is lying → STOP"* — halting a **correct** run.
The check would do the exact opposite of its purpose.

## The corrected anchor

> **R0 sanity anchor := full-set MAIN 0.3385** on the 679-corpus (val-split `val_eval_full` MAIN =
> 0.3318). If R0 reproduces ~0.3385, the harness is honest.

The spec says "full-set MAIN", so **0.3385** is the primary anchor. If the harness reports the
val-split `val_eval_full` slice instead (what `cmd_train` prints), that is **0.3318** — already the
value the parent recorded in `CHECKPOINT-ai-scientist-7.md:36` and the M3 constraints.

## Why 0.2866 ≠ the harness — it is NOT mere corpus drift

My earlier note called 0.2866 "the stale 106-corpus number." **That was imprecise and I correct it
here:** the 106-corpus, run through the *same* frozen harness, gives **0.4177** (full) / 0.3941
(val) — not 0.2866. So the mismatch is not the corpus changing from 106→679; it is that 0.2866 was
**produced by a different instrument** than `policy_imitation`'s `heuristic_scorer()` + `agreement()`.
Consistent corroboration: M1 reported MAIN as "62% of all decisions," but MAIN is 54.6% of top-1100
on the 679-corpus and 57.9% on the 106-corpus — a different denominator, i.e. a different measurement
setup. The bug-fixed C-tip policy (332a390) agreeing *more* (0.34–0.42) than the M1 plateau (0.282)
is also exactly the lane's "agreement is a decoupled proxy" pattern: the bug fixes raised agreement
while the deck-level win rate fell.

## Reproduction

```
# frozen policy_imitation.py imported byte-for-byte from 332a390 (read-only worktree);
# heuristic_scorer()/agreement()/episode_split() are the originals.
python repro_anchor.py           # (scratchpad; drives the frozen harness on both corpora)
```
Raw output in `repro_ablation.json` (`R0_heuristic_val`) and the `repro_anchor` log. No code edited;
no ptcg-repo files touched; canonical `runs/imitation/` unchanged.

## What I changed

Doc-only annotations (markdown, non-destructive — original text preserved, dated + sourced, matching
the GOALS.md item-8 precedent):
- `2026-07-12-deck-agnostic-ablation-spec.md` — R0 line (§GOAL) and the ACCEPTANCE paragraph.
- `2026-07-12-gate-target-decision-memo.md` — the sanity-anchor bullet.

`CHECKPOINT-ai-scientist-7.md` and the M3 constraints already carry 0.3318; no change needed there.

## For mroute (the implementer)

- Set the R0 pass condition to **≈0.3385 (full-set MAIN)** / 0.3318 (val_eval_full), **not 0.2866.**
- The descriptive "28.2%" comments in `policy_imitation.py` (:11, :519, :619) are 106-corpus /
  M1-plateau language and are now stale on the 679-corpus — cosmetic, but worth a comment fix when
  that file is next touched (that edit is yours; my charter forbids ptcg-repo code edits).
