# Ablation + LOTO — FIRST-HAND reproduction from the bytes

**Author:** sctst-aide · **Date:** 2026-07-12 · **Requested by:** Eddie ("reproduce the ablation and LOTO yourself")

I had flagged these numbers as **second-hand** (produced by a verification subagent inside my
audit). I have now re-derived them myself, driving the **frozen** instrument.

**Method.** `scripts/policy_imitation.py` imported **byte-for-byte** from the merged C tip
(332a390) via a read-only worktree. `train()` (averaged perceptron, 10 epochs, seed 0),
`agreement()`, `score_feats()`, `episode_split()` and `heuristic_scorer()` are the **frozen
originals** and do all the work. The C-AG arm is produced by wrapping module-global
`featurize()` in the driver to drop `play_card=*` / `abil_card=*` — exactly the semantics of the
`--no-card-features` flag mroute will land durably. Featurization is cached so LOTO can refit;
that changes no logic. **No module edits. No repo writes.** Canonical `runs/imitation/` untouched
(the all-seats build went to scratchpad).

---

## 1. Ablation — REPRODUCED

Episode-disjoint split (frozen `episode_split`, every 5th episode): train 60,973 / val 15,432
(135 val episodes).

| arm | val overall | val MAIN | weights |
|---|---:|---:|---:|
| **C-FULL** (card + generic) | 0.4980 | **0.4749** | **176** (132 card-identity, 44 generic) |
| **C-AG** (generic only) | 0.4256 | **0.3547** | 44 |
| **ablation (FULL − AG)** | **+7.24 pp** | **+12.02 pp** | |

Subagent reported 47.13 / 35.40 → **−11.73 pp**. I get 47.49 / 35.47 → **−12.02 pp**.
Same substance, small numeric drift. **The 176 / 132 / 44 weight split matches exactly.**

Card-identity features confirmed first-hand at **`policy_imitation.py:197`** (`play_card={cid}`)
and **`:209`** (`abil_card={acid}`); the `:202-206` comment states the per-card selectivity is
deliberate.

### Per-card coverage of our 11-card deck — REPRODUCED EXACTLY

| ranker trained on | our-deck cards covered |
|---|---|
| all top-1100 | **5 / 11** → `[1092, 1121, 1145, 1219, 1227]` |
| archetype-core (what Task 2 would deepen) | **1 / 11** → `[1227]` |

`archetype_teams(core_min=6)` = `{Benjamin Zhao3927, kuma_jp}` → 553 records.

## 2. ⚠️ R0 ANCHOR IS STALE — the 28.2 % baseline is wrong on this corpus

The frozen A1 heuristic, graded on the **same** val split under identical argmax semantics:

> **overall 0.4777 · MAIN 0.3318** (n = 14,087; main_n = 8,481)

The pre-registered sanity anchor is **~0.2866**. That figure is from the **106-replay** corpus.
On the 679-replay corpus the heuristic baseline is **33.18 %**, not 28.66 %.

**This matters for the gate.** Against the *real* baseline:
- C-FULL 47.49 % = **+14.3 pp** over heuristic (not +19 pp)
- C-AG 35.47 % = **+2.3 pp** over heuristic (not +7.2 pp)

C-AG's margin over the hand-tuned heuristic is far thinner than the "+7.2 pp fully transferable"
framing suggests. **mroute must not use 0.2866 as the R0 anchor on this corpus.**

---

## 3. LOTO — ai-scientist-7's PRE-REGISTERED HYPOTHESIS IS REFUTED

Hypothesis (#3244): *"C-FULL wins in-domain and LOSES out-of-domain… C-AG's generic weights may
be strictly better."*

Train on all teams but T; evaluate MAIN agreement on T. 15 teams ≥ 500 records = 95.0 % of supervision.

| held-out | n MAIN | C-FULL | C-AG | Δ (FULL−AG) |
|---|---:|---:|---:|---:|
| kazuki0123 | 8,248 | 0.4528 | 0.3745 | +7.83 |
| WinDecks | 8,561 | 0.2712 | 0.2378 | +3.34 |
| tonakaiiii | 3,168 | 0.4662 | 0.3955 | +7.07 |
| Dũng Đỗ | 4,454 | 0.5263 | 0.3172 | +20.91 |
| nasuo445 | 3,505 | 0.5524 | 0.4094 | +14.30 |
| Majkel1337 | 2,458 | 0.4036 | 0.3779 | +2.57 |
| Yushin Ito | 1,678 | 0.4583 | 0.4273 | +3.10 |
| zoroark190 | 1,859 | 0.3314 | 0.2959 | +3.55 |
| btk15049 | 1,626 | 0.3432 | 0.3020 | +4.12 |
| THIRD PTCG Club | 1,308 | 0.3739 | 0.3410 | +3.29 |
| easonyanyan | 951 | 0.5216 | 0.5005 | +2.11 |
| ZETADIVISION | 470 | 0.3702 | 0.3511 | +1.91 |
| LiamK | 446 | 0.2668 | 0.2175 | +4.93 |
| kashiwashira | 400 | 0.4125 | 0.3450 | +6.75 |
| Benjamin Zhao3927 | 328 | 0.4238 | 0.3018 | +12.20 |

> **C-FULL better on 15 / 15 held-out teams. C-AG on 0 / 15.**
> mean Δ **+6.53 pp** unweighted, **+7.60 pp** record-weighted (vs **+12.02 pp** in-domain).

The card-identity advantage **shrinks** out-of-domain (12.0 → 7.6 pp) but **does not reverse**.
**C-FULL transfers better. The hypothesis is refuted.**

## 4. …but the MECHANISM behind the hypothesis is REAL

Split each held-out team's MAIN decisions by whether the card channel *can fire*:
**LIVE** = ≥1 option carries a learned card weight · **DEAD** = none does.

| subset | share of held-out MAIN | Δ (C-FULL − C-AG) |
|---|---:|---:|
| **card channel LIVE** | 88.9 % (35,075) | **+8.65 pp** |
| **card channel DEAD** | 11.1 % (4,385) | **−0.82 pp** ← C-AG better, wins 10/15 teams |

**C-FULL's entire out-of-domain edge comes from card weights still firing.** Where they cannot,
**C-AG's generic weights are better than C-FULL's** — precisely the starvation effect
ai-scientist-7 predicted. The prediction failed only because LOTO folds keep the card channel
live 88.9 % of the time.

---

## 5. My own counter-hypothesis — TESTED AND NOT SUPPORTED

I suspected LOTO **flatters** C-FULL: held-out *ladder* teams share their cards with the pool,
whereas our deck would run mostly card-channel-dead, so C-FULL's edge should collapse for us.
**The data does not support that:**

- **Card overlap with the rest of the pool:** our deck **90.9 %** (10 of 11 cards appear
  somewhere in the pool; only `1262` never does) vs **94.9 %** mean for held-out teams. Our deck
  is *not* dramatically more out-of-vocabulary.
- **Dead-fraction does not track basic energy.** BluezLee (18 energy) → 8.0 % dead, *below* the
  9.2 % pool average. zoroark190 (1 energy) → 1.2 %. Akifumi Okubo (0 energy) → 27.9 %. **No trend.**
  The naive "our deck is 55 % basic energy → mostly dead channel" projection is unsupported.

**So LOTO's +7.60 pp probably does largely carry to our deck, and I withdraw the concern.**

**Irreducible unknown, stated plainly:** the four ladder decks that actually resemble ours
(27–35 basic energy — Tanaka Chiromo, masaaki imai, Bulbaflare, mojyaP) have **zero measurable
MAIN decisions** between them. There is **no ladder deck of our shape with enough data to measure**.
Our deck's true dead-fraction cannot be established from ladder data at all. That is the honest
limit of this analysis, and it is the same wall as the on-policy audit: our deck is unrepresented.

---

## 6. THE HYBRID ARM — RUN. It does not pay off. My own recommendation is withdrawn.

I recommended a hybrid (C-FULL's card weights + C-AG's generic weights). Eddie ordered it run.
**It is a wash out-of-domain.** Two variants, because a naive splice risks double-counting
(C-AG's generic weights absorbed signal the card features would otherwise carry):

- **H1 SPLICE** = {generic from C-AG} + {card from C-FULL}, post-hoc, no retraining.
- **H2 RESIDUAL** = freeze generic := C-AG's generic, then *learn* card weights on top.

H2 needs a freeze-mask that frozen `train()` cannot do, so `train_residual()` is a faithful copy
in the driver. **It was validated bit-for-bit against frozen `train()` with the mask off
(176/176 weights, max |Δw| < 1e-9) — the run aborts if that check fails.**

### In-domain (episode-split val) — the hybrid genuinely wins

| arm | overall | MAIN | DEAD MAIN (n=790) | LIVE MAIN (n=7,691) |
|---|---:|---:|---:|---:|
| C-FULL | 0.4980 | 0.4749 | 0.5873 | 0.4634 |
| C-AG | 0.4256 | 0.3547 | 0.5899 | 0.3305 |
| **H1-splice** | **0.5078** | **0.4913** | 0.5899 | **0.4812** |
| H2-residual | 0.4897 | 0.4611 | 0.5899 | 0.4479 |

H1 beats C-FULL by **+1.64 pp MAIN** in-domain — and it beats C-FULL even on the **LIVE** subset
(+1.78 pp), confirming C-FULL's generic weights really are starved. The "principled" H2 is *worse*
than the naive H1. My double-counting worry did not materialise.

### Out-of-domain (LOTO, record-weighted, n = 39,460) — it all evaporates

| arm | MAIN | vs C-FULL |
|---|---:|---:|
| **C-FULL** | **0.4139** | — |
| H1-splice | 0.4135 | **−0.04 pp** |
| H2-residual | 0.4130 | **−0.08 pp** |
| C-AG | 0.3379 | −7.60 pp |

Per-team wins (15 folds): C-FULL 5 · H1 5 · H2 6 · C-AG 0.

**The three card-carrying arms are statistically indistinguishable.** The gap is 0.04 pp = **0.16 SE**
= about **16 decisions out of 39,460**. H1's +1.64 pp in-domain gain **does not transfer at all**.

This is a textbook instance of exactly what ai-scientist-7 warned about: **the in-domain winner is
not the out-of-domain winner.** The card-identity starvation effect is **real but immaterial** — it
is confined to the 9.3 % of decisions where the card channel is dead, and is worth ~0.02 pp overall.

**The open arm is now CLOSED. Do not spend mroute on it.**

## 7. Recommendation (final)

1. **Serve C-FULL.** It wins in-domain (+12.02 pp) and out-of-domain (+7.60 pp, 15/15 teams), and
   no hybrid beats it where it counts. The extra complexity buys nothing.
2. **Fix the R0 anchor to 0.3318** before mroute grades anything on this corpus. The 0.2866 / 28.2 %
   bar is from the 106-replay corpus, is stale by 4.5 pp, and flatters every arm — most of all C-AG,
   whose true margin over the hand-tuned heuristic is **+2.3 pp**, not +7.2 pp.
3. ~~Test the hybrid~~ — **done, closed, negative.**
4. LOTO is a sound *selector* — but it is a proxy. Only games on our deck decide, and the
   liveness counters (I5/I6) remain the only instrument that reports what actually fires at serve time.

Raw outputs: `repro_ablation.json`, `repro_loto.json`, `repro_deadchannel.json`, `repro_ourdeck.json`,
`repro_hybrid_indomain.json`, `repro_hybrid_loto.json`.
