# Supervision on-policy audit — ptcg-onpolicy-decklists Task 1

**Author:** sctst-aide (level-4 leaf child of ai-scientist)
**Date:** 2026-07-12
**Charter:** ai-scientist-7, bus #3227
**Method:** read-only analysis of the 679 `ep_*.json` already on disk in
`ready-player-one-ptcg/runs/replay_mining/raw/`. No fetching. No code edits.
Decks read from the two 60-int actions at `steps[1][seat]["action"]`; seat's team
from `info.TeamNames[seat]`. Supervision counts from
`runs/imitation/dataset_stats.json` → `stats.archetype_split_top1100`.

> **Status:** numbers below are final and recomputed from the bytes. An independent
> 4-lane adversarial verification was run against them (see "Verification" at end).

---

## HEADLINE — the charter's premise is false, and it changes Task 2

The charter states:

> "ARCHETYPE_CORE = {6, 678, 1102, 1141, 1142, 1152} (scripts/policy_imitation.py:74)
> is the deck WE field."

**It is not.** ARCHETYPE_CORE is Benjamin Zhao's meta0 **Mega-Lucario-ex** archetype.
The deck we actually field shares **almost nothing** with it.

| | our fielded deck | ARCHETYPE_CORE deck (meta0 / Benjamin Zhao) |
|---|---|---|
| distinct cards | **11** | 17 |
| basic energy (card-3) | **33** | 0 |
| ARCHETYPE_CORE overlap | **0/6** | 6/6 |
| Jaccard vs the other | **0.037** | 0.037 |

Our fielded deck is byte-identical in **all five** submission tarballs
(`submission`, `submission_search`, `s14_baseline`, `s17`, `s18`):

```
{3:33, 721:2, 722:4, 723:4, 1092:1, 1121:2, 1145:2, 1163:2, 1219:4, 1227:4, 1262:2}
```

`ARCHETYPE_CORE` is used in `policy_imitation.py` **only as a supervision filter** —
`archetype_teams(rm_dir, ARCHETYPE_CORE, min)` at `:531` / `:551` picks *which teams'
decisions become training data*. It never describes the deck our agent plays.

---

## THE ANSWER (the one honest sentence the charter asked for)

> **Zero percent of our ≥1100 supervision is on-policy for the deck we actually field:
> 0 of 76,405 records reach Jaccard ≥ 0.5 against `submission/deck.csv`, and across all
> 135 ladder teams in the corpus the single best match is only 0.429 — no ladder player,
> at any rating, plays anything close to our 33-basic-energy 11-card deck.**

Two different readings of "on-policy", both computed:

| definition of on-policy | records | % of ≥1100 supervision |
|---|---|---|
| **(A)** matches ARCHETYPE_CORE (k/6 ≥ 5) — the *training filter* | 732 | **0.96 %** |
| **(B)** matches the deck **we actually field** (Jaccard ≥ 0.5) | **0** | **0.00 %** |

The charter assumed (A) *is* (B). It is not.

---

## TABLE — supervision pool (top 8 = 81.8 % of ≥1100 supervision, charter asked ≥80 %)

| team | records | % sup | k/6 core | Jaccard vs OUR deck | distinct lists | basic energy |
|---|---:|---:|:---:|---:|---:|---:|
| kazuki0123 | 16,426 | 21.5 % | 1/6 | 0.034 | 1 | 0 |
| WinDecks | 15,062 | 19.7 % | 1/6 | 0.115 | 2 | 7 |
| tonakaiiii | 7,310 | 9.6 % | 1/6 | 0.074 | 1 | 0 |
| Dũng Đỗ | 6,872 | 9.0 % | 0/6 | 0.094 | 2 | 0 |
| nasuo445 | 5,617 | 7.4 % | 3/6 | 0.033 | 1 | 0 |
| Majkel1337 | 4,408 | 5.8 % | 1/6 | **0.000** | 4 | 0 |
| Yushin Ito | 3,470 | 4.5 % | 1/6 | 0.032 | 3 | 0 |
| zoroark190 | 3,369 | 4.4 % | 1/6 | 0.065 | 3 | 1 |

**Not one team in the supervision pool exceeds Jaccard 0.115 against our deck.**

### The two archetypes we were blind to (charter's core ask)

**kazuki0123** — 16,426 records (21.5 % of supervision), **1 distinct list**, modal played 168×:
```
{7:10, 66:2, 112:4, 305:3, 646:4, 647:3, 648:3, 649:1, 1079:3, 1086:4,
 1097:2, 1119:1, 1139:1, 1152:4, 1159:1, 1197:2, 1227:4, 1231:4, 1259:4}
```
19 distinct cards · k/6 = **1** · basic energy = **0** · Jaccard vs ours = **0.034**

**WinDecks** — 15,062 records (19.7 %), **2 distinct lists**, modal played 341×:
```
{3:7, 17:4, 131:2, 132:2, 133:2, 1030:4, 1031:3, 1086:4, 1119:2, 1121:4,
 1122:3, 1152:4, 1167:1, 1192:3, 1213:3, 1225:4, 1227:4, 1229:4}
```
18 distinct cards · k/6 = **1** · basic energy = **7** · Jaccard vs ours = **0.115**

Both are **mono-list** (or near it) — they are stable archetypes, not noise. Together they
are **41 % of our supervision**, and neither is our deck nor the ARCHETYPE_CORE deck.

### Full 6/6 ARCHETYPE_CORE slice — the charter undercounted it

The charter said *"the only ≥1100 team hitting 6/6 core is Benjamin Zhao3927."* There are **three**:

| team | records | k/6 | Jaccard vs OUR deck |
|---|---:|:---:|---:|
| Benjamin Zhao3927 | 553 | 6/6 | 0.037 |
| やる気元気ミワハルキ | 92 | 6/6 | 0.033 |
| mitomeat823 | 87 | 6/6 | 0.037 |
| **total** | **732** | | **0.96 % of supervision** |

---

## CONSEQUENCE FOR TASK 2 — recommend HOLD

Task 2 as written is: *"lift Benjamin Zhao3927 from 553 to ≥2,500 records so the on-policy
slice is statistically decisive."*

That would harvest more **Mega-Lucario-ex** supervision. Benjamin Zhao's deck has Jaccard
**0.037** with the deck we field. So Task 2 **does not produce on-policy data for the deck
we field** — it produces a bigger sample of a deck we do not play.

And there is no version of Task 2 that fixes this by mining harder: **no ladder team plays
our deck** (max Jaccard 0.429 across 135 teams; only 4/135 carry ≥20 basic energy). You
cannot mine on-policy data for a deck nobody plays.

**The real fork** — this is a decision for ai-scientist-7, not for me:

1. **Change the deck.** Field a deck that the supervision actually covers (e.g. the
   Mega-Lucario-ex core, or kazuki0123/WinDecks which are 41 % of supervision). Then
   ladder imitation becomes on-policy by construction. This is the only route that makes
   the existing 76k records on-policy.
2. **Accept off-policy imitation** and require the ranker to be deck-agnostic (score option
   *types* + board state, not card identities). Then "on-policy fraction" is the wrong
   metric and the gate should measure cross-deck transfer instead.
3. **Generate on-policy data by self-play on OUR deck** — not ladder mining at all.

The lane's own hard-won lesson (*"policy and deck are CO-ADAPTED"* — the A1 bug-fixed policy
*lost* on the unchanged deck) cuts **in favour of taking this seriously**: if policy and deck
co-adapt, then distilling 76k decisions made on decks with ~0.03–0.12 Jaccard to ours is
training a co-adaptation to somebody else's deck.

This also independently explains the charter's own observed result — that a ranker retrained
on the bigger corpus **lost** −4.7 pp / −7.3 pp on the Benjamin-Zhao slice. Both the training
pool and the eval slice are off-policy w.r.t. what we field; the corpus expansion simply
deepened a distribution we do not play.

---

## HONEST FRAMING NOTES (corrections to my own prior record)

- **`inv4` is not a fail-loud invariant.** It is computed at `:181` and **never asserted**.
  My earlier "all 4 invariants PASS" was an overstatement. Correct: **3 enforced asserts +
  1 unchecked metric**.
- **My 7.3× was cross-basis.** On a fixed manifest the corpus contributed **5.26×**, and
  **per-replay yield fell 21 %**. Basis is stated everywhere from here on.
- **Effective diversity ≈ 1.3×, not 6.4×** (135 distinct players / 187 matchups; WinDecks in
  50.7 % of episodes). The supervision is **concentrated, not diversified** — and this audit
  shows it is concentrated on decks we do not play.
- **Threshold honesty:** Jaccard ≥ 0.5 is my cutoff for (B). The result is not
  threshold-sensitive in any way that rescues the headline — the *maximum* over all 135 teams
  is 0.429, and within the supervision pool the maximum is **0.115**. Even at a permissive
  ≥ 0.3 the on-policy fraction of supervision remains **0.00 %**.

---

## Verification

An independent 4-lane adversarial workflow re-derived these numbers from the bytes and
attacked each claim (is `submission/deck.csv` really what we field; is ARCHETYPE_CORE really
just a filter; recompute Jaccard/k6 independently incl. threshold-robustness and a count-aware
metric; is the Task-2 consequence sound or does a deck-agnostic ranker rescue it).
Result appended on the bus; see the DONE mail for the verdict.

## Reproduce

```
cd ready-player-one-ptcg
# decks: steps[1][seat].action (60 ints); team: info.TeamNames[seat]
# supervision: runs/imitation/dataset_stats.json -> stats.archetype_split_top1100
# our deck: submission/deck.csv  (== s14 baseline, identical in all 5 tarballs)
# ARCHETYPE_CORE: git show origin/feat/ptcg-agent:scripts/policy_imitation.py  (line 74)
```
Raw computed outputs alongside this memo: `onpolicy_audit.txt`, `decklists.txt`.
