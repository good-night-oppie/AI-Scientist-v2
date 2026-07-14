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

### Full 6/6 ARCHETYPE_CORE slice — and a correction *against me*

Against the **raw 679-episode corpus** there are **three** teams at 6/6:

| team | records | k/6 | Jaccard vs OUR deck |
|---|---:|:---:|---:|
| Benjamin Zhao3927 | 553 | 6/6 | 0.037 |
| やる気元気ミワハルキ | 92 | 6/6 | 0.033 |
| mitomeat823 | 87 | 6/6 | 0.037 |
| **total** | **732** | | **0.96 % of supervision** |

> **RETRACTION — I was unfair to the charter here.** I originally wrote that the charter
> "undercounted" this slice. It did not. `archetype_teams()` selects from the
> **`inline_harvest_*.json` files (16 decks / 9 teams)**, *not* from the 679-episode raw
> corpus. Under **the code's own selector**, k ≥ 6 picks **only Benjamin Zhao3927** → 553
> records = 0.72 %. The charter's single-team framing **matches what the code actually does**.
> My 732 / 3-teams figure is correct only against the raw corpus, which is a different
> population. The charter was right; I was measuring a different thing. Retracted.

> **Second self-correction — "the deck has never changed" is WRONG.** There are **eight**
> bundles, not five. Six share one deck (SHA256 `1156379a…`), but the **two deck-search
> bundles carry different decks**: `2c1368bc03` (10 distinct, 34× basic energy, Jaccard 0.750
> vs base) and `58f62b5135` (12 distinct, 34× basic energy, Jaccard 0.533). And the deck *did*
> change on the ladder — per `LANE_STATE.md`, the `2c1368bc03` deck was probed on Kaggle as ref
> **54585744**: scored 600.0, then **regressed to 464.5**, tripping rpo condition 3 and freezing
> further deck submissions.
>
> **The substance survives:** both evolved decks are still **k/6 = 0** and carry *more* basic
> energy (34 vs 33). Every deck we have ever fielded or probed is zero-core.

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

### ARCHETYPE_CORE is UNREACHABLE BY CONSTRUCTION (hardens everything above)

`deck_search.py:126-134` builds the basic-Pokémon pool as **`water_basics`**:

```python
"water_basics": [c["cardId"] for c in cards.values()
                 if c["cardType"] == 0 and c.get("basic")
                 and c.get("energyType") == 3          # WATER
                 and (c.get("hp") or 0) >= 100]
```

The Mega-Lucario-ex core cards `{6, 678, 1102, 1141, 1142, 1152}` **can never enter a searched
deck**. So *every* deck our pipeline can produce — current, probed, or future — is **k/6 = 0**.
On-archetype supervision is not merely 0 % today; it is **structurally unattainable** through
deck search.

### Root cause of the charter's error (worth a one-line fix)

`policy_imitation.py:549` comments the strict 6/6 **eval slice** as *"(the meta0 **gate deck**)"*,
and `:566` tags it `"val_eval_archetype6": _eval(val_arch),  # the deployment/gate deck`.

That comment calls an **eval slice** "the deployment/gate deck." That is almost certainly the
source of "ARCHETYPE_CORE is the deck WE field" — a **misleading comment**, not a reasoning
error by the charter author. Recommend mroute fix the wording; it is a latent trap that has
already cost one charter.

---

## THE FORK — revised after verification

> **RETRACTION (mine, material).** My first draft recommended *"change the deck to one the
> supervision covers."* **That experiment already ran, and it lost.** The meta0 /
> Benjamin-Zhao (ARCHETYPE_CORE) deck was built as a candidate bundle and gated head-to-head
> against the s14 baseline. From the bytes (`runs/replay_mining/eval_meta0_*.json`):
>
> | n | W–L | winrate |
> |---:|---:|---:|
> | 40 | 25–15 | 0.625 ← small-sample noise |
> | 160 | 72–88 | 0.450 |
> | 400 | 203–197 | 0.5075 |
> | 400b | 189–211 | 0.4725 |
> | **pooled 1000** | **489–511** | **0.489** |
>
> The ARCHETYPE_CORE deck **does not beat our water deck**. Option 1 as written is withdrawn.
>
> **Nuance — do not over-read the retraction.** That gate paired the meta0 *deck* with **our
> search policy** (via `--deck-path` override). Our policy is co-adapted to our deck — its
> determinization literally computes `Counter(DECK) - seen`. So what was tested is *"our policy
> + their deck"*: precisely the co-adaptation mismatch the lane's own lesson predicts will fail.
> The pairing that was **never tested** is *"meta0 deck + meta0-**trained** ranker."* That is the
> one live version of option 1, and it is the honest test of the co-adaptation hypothesis.

1. **~~Change the deck~~ — WITHDRAWN.** Already gated: winrate 0.489 @ n = 1000. Only live
   variant is *meta0 deck + meta0-trained ranker* (untested, expensive).
2. **Deck-agnostic ranker — now the primary recommendation.** Ablate `play_card=` / `abil_card=`,
   accept the −11.73 pp, and gate on **cross-deck transfer** rather than an "on-policy fraction"
   that is structurally 0 %. Half our deck (33/60 basic energy via `OPT_ATTACH`) and 40 % of all
   decisions already ride **zero** card-identity features.
3. **Self-play on OUR deck** — the only route to genuinely on-policy data, since nobody plays our
   deck and deck-search cannot reach theirs.

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

## Verification — 4-lane adversarial, **0 of 4 refuted**, all high confidence

Independent lenses re-derived everything from the bytes and attacked each claim. All four
failed to refute. Two produced evidence **stronger than mine**.

**Threshold robustness (the key attack — it fails).** On-policy fraction vs our deck:

| Jaccard ≥ | 0.05 | 0.10 | 0.12 | **0.15** | 0.20 | 0.30 | 0.50 |
|---|---:|---:|---:|---:|---:|---:|---:|
| % of supervision | 48.2 % | 20.8 % | 0.57 % | **0.00 %** | 0.00 % | 0.00 % | 0.00 % |

**0 % holds at every threshold from 0.15 up.** To get a nonzero fraction you must drop to
≈ 0.10 — decks sharing ~3 of ~30 card names. Not threshold-gamed. Count-aware metrics make it
**stronger**: weighted/multiset Jaccard = 0.00 % at ≥ 0.3; Bray-Curtis = 0.57 % at ≥ 0.3
(BluezLee alone, 433 records). And the four teams that *are* genuinely similar to us
(Bray-Curtis up to **0.817**, Tanaka Chiromo) have **zero supervision records** — one seat
each, none in the ≥ 1100 split — and both their seat-decks **lost** (reward −1).

### THE DECISIVE FACT — Task 2 is not merely useless, it is *actively harmful*

The steelman ("the ranker scores option *types*, not card identities, so it transfers") is
**false**. `featurize()` (`policy_imitation.py:165-240`) emits two **pure card-identity**
features — `play_card={cid}` and `abil_card={acid}` — and the comment at `:202-207` says this
is deliberate: *"Let the ranker learn a per-source-card weight — this per-card/state
selectivity is the whole point of distillation."*

Retrained from the 76,405 records (episode-disjoint split): **176 weights = 132 card-identity
+ 44 generic.** Ablating card identity costs **−11.73 pp MAIN** (47.13 % → 35.40 %) — the
per-card channel carries the **majority of the model's lift** over the 28.2 % heuristic.

**Per-card coverage of the 11 cards in the deck we actually field:**

| ranker trained on | cards of OUR deck covered |
|---|---|
| all top-1100 supervision | **5 / 11** → 1092 Secret Box, 1121 Ultra Ball, 1145 Mega Signal, 1219 Petrel, 1227 Lillie's |
| **archetype-core (= what Task 2 deepens)** | **1 / 11** → 1227 only |

Those 5 are exactly our **trainer engine** — the cards you hold several of at once, where
`play_card=` is the only available tiebreak. **Task 2 would strip 4 of the 5 per-card weights
our deck can actually use**, and spend the corpus on `play_card=678` (Mega Lucario ex), 1102,
1141, 1142, 1152 — cards we never draw, whose weights are **dead at serve time**.

Corroborating: leave-one-team-out transfer costs **−5.7 to −11.0 pp MAIN** even *between
ladder decks* (which resemble each other far more than any resembles ours). And Task 2's
direction taken to its limit (train on the 564-record archetype slice) scores 58.95 % MAIN on
its own decisions but only **35.18 % on every other deck** vs 47.19 % for the full-corpus model
— **−12.01 pp; it does not transfer.**

### The honest counterweight (in fairness to the charter — option 2 is live)

A genuine deck-agnostic backbone **does** exist, and it is bigger than I first thought:

- 44 generic features carry **93.1 %** of all feature firings; a generic-only model still
  reaches **35.40 % MAIN**, above the 28.2 % hand-tuned heuristic.
- **33 of our 60 cards are basic {W} energy (card 3), played via `OPT_ATTACH` — featurized with
  ZERO card-identity features.** Over half our deck is handled by fully transferable signal.
- **40 %** of multi-option decisions (all non-MAIN, 28,274 / 69,966) use **no** card-identity
  feature at all. That entire bucket is deck-agnostic.
- Structurally our deck is the **same archetype shape** as BZ's: a Mega-ex beatdown
  (723 Mega Abomasnow ex + 722 Snover + 721 Kyogre + heavy basic energy) vs BZ's Mega Lucario
  ex + basic {F} energy. Role-level transfer is plausible in principle.

So **option 2 (deck-agnostic ranker) is viable** — it just costs the −11.73 pp card-identity
channel, and it should be gated on cross-deck transfer rather than on an "on-policy fraction"
that is structurally 0 %.

## Reproduce

```
cd ready-player-one-ptcg
# decks: steps[1][seat].action (60 ints); team: info.TeamNames[seat]
# supervision: runs/imitation/dataset_stats.json -> stats.archetype_split_top1100
# our deck: submission/deck.csv  (== s14 baseline, identical in all 5 tarballs)
# ARCHETYPE_CORE: git show origin/feat/ptcg-agent:scripts/policy_imitation.py  (line 74)
```
Raw computed outputs alongside this memo: `onpolicy_audit.txt`, `decklists.txt`.
