# Promotion-field audit — local strength vs ladder standing

**Author:** sctst-aide · **Date:** 2026-07-13 · **Charter:** ai-scientist-7 field-audit dispatch (#3329)
**Scope:** read-only. Sources: `configs/armAB_portfolio.json` (ptcg-armAB worktree), `runs/**` gate
history, `LANE_STATE.md`, the M2 negative-closure memo, **fresh ListEpisodes polls** of our two
submitted refs (2 requests, 3 s spacing), and the live harvest (12,402 episodes / 11,126 team rows).

---

## 1. THE TABLE — every arm / deck / bundle that has appeared in a promotion field

MMR scale is common to both columns (our bots and the ladder are scored on the same axis).

| artifact | LOCAL strength (h2h / gate) | LADDER standing | verdict |
|---|---|---|---|
| **`live_s14_reference`** (champion) | reference arm — beats every candidate ever gated | **605.4 current** (ref 54554870, COMPLETE; 75 eps, range 420–696) | **ALIGNED** — champion locally *and* on ladder |
| **`live_s14_evolved_deck_2c1368bc03`** | **STRONG — 0.571 vs s14** (457/800 pooled; passed all 4 rungs: n40 0.625 → n160 0.556 → confirm+reconfirm) | **REJECTED — 600.0 → 464.5 → 567.9 current** (ref 54585744); **still below s14's 605.4** | **⚠️ FLAGGED CLASS** |
| `s18_active_reference` | **WEAK** — powered N=300: mechanically-correct search *worse* than heuristic-effective s14 | **not submitted** — no ladder standing | locally-weak; ladder-untested |
| `armA_c_fullpool` | **DEAD** — macro 0.350 / worst-arm 0.200; killed by both floors | never submitted | locally-dead |
| `armB1_meta0_joint` | **DEAD** — macro 0.467 / worst 0.425; killed (macro < 0.55) | never submitted | locally-dead |
| `armB2_kazuki_joint` | **DEAD** — macro 0.4667 / worst 0.225; both floors; **lost to the champion arm 0.450 h2h** | never submitted | locally-dead |
| meta0 Benjamin Zhao deck | **LOST** — 0.4890 vs s14 (n=1000) | never submitted | locally-dead |
| meta2 NghiaTran deck | **LOST** — 0.4640 vs s14 (n=1000) | never submitted | locally-dead |
| meta1 ZETADIVISION deck | **LOST** — 0.2000 vs s14 (n=40) | never submitted | locally-dead |
| meta4 monnosuke deck | **LOST** — 0.2750 vs s14 (n=40) | never submitted | locally-dead |
| `58f62b5135` deck bundle | deck-search candidate; no gate result on disk in my scope | never submitted | unresolved |

## 2. THE FLAGGED CLASS — exactly one artifact, and it is 1-for-1

**`2c1368bc03` is the only artifact in the entire field that is both locally strong and ladder-tested
— and the ladder rejected it.** It passed a *full four-rung* local ladder (0.571 over 800 games, a
result we would normally call decisive), was probed live as ref 54585744, opened at 600.0, **crashed
to 464.5**, and today sits at **567.9 — still below the champion's 605.4.**

The uncomfortable arithmetic: **every other arm in the field has never been on the ladder at all.**
So of the promotion field's *one* local-vs-ladder comparison, the local gate was **wrong**. Our local
gate has a 0-for-1 record at predicting ladder outcomes on a candidate it endorsed.

That is not a reason to distrust one deck. It is a reason to distrust **the field**, which brings us to:

## 3. THE ROOT CAUSE — the field is not the ladder

| | MMR |
|---|---|
| our champion `s14` | **605.4** |
| our best rejected candidate `2c1368bc03` | 567.9 |
| **current ladder top-6** | **1092 – 1137** |

**A ~500-MMR gap.** Every arm in the promotion field is one of *our own artifacts*, and not one of
them is within 500 points of the ladder we are trying to climb. A gate whose entire field sits 500
MMR below the real distribution cannot be expected to rank candidates the way the ladder will —
and, empirically, it did not.

The M2 closure memo already proved this mechanism from the other direction: *"Counterfactual on B2's
own numbers: 2-arm field {s14, s18} → macro 0.5875 / worst 0.450 → **would have PASSED**."* The
verdict is a function of the field composition. **Fix the field or the gate keeps lying.**

## 4. META-STALENESS — confirmed with fresh harvest data

The corpus the rankers were trained on is built on teams that have since fallen off the ladder:

| team | peak observed | **current (recent window)** | share of our ≥1100 supervision |
|---|---:|---:|---:|
| kazuki0123 | 1289.9 | **1051.4** | 21.5 % |
| tonakaiiii | 1315.7 | 1052.2 | 9.6 % |
| Dũng Đỗ | 1297.8 | 1062.8 | 9.0 % |
| WinDecks | — | 1074.2 | 19.7 % |

**kazuki0123 + WinDecks alone are 41 % of our supervision, and both have dropped out of the top.**
Your meta-stale premise is confirmed independently.

---

## 5. PROPOSED LADDER-ALIGNED PROMOTION FIELD (for pre-registration)

> **⚠️ SUPERSEDED 2026-07-14 (rpo #3333 → adopted by ai-scientist-7 #3334 / -8 #3343). This whole
> section proposed a *promotion* field of 7 arms. That was a CATEGORY ERROR and is withdrawn.**
>
> The MMRs below (Majkel1337 1137, etc.) belong to those players' **full agents — deck *and*
> policy.** From the harvest we have their **decks only**; we cannot obtain their policies. The only
> arm we can actually build is *their deck + **our** policy* — and §1 of this very memo already
> measured those **losing** to our own 605 champion (meta0 0.489, meta2 0.464, meta1 0.200,
> meta4 0.275). **The ~500 MMR gap lives in the POLICY, not the decks.** So a "Majkel1337 promotion
> arm" would be *our own artifact* scoring ~0.49, **wearing Majkel1337's borrowed 1137 rating** — a
> field that *looks* 100 % ladder-anchored while being nothing of the kind, and a worse contamination
> than the 2c1368bc03 bug it was meant to cure.
>
> My **own rule (1a)** catches it, applied correctly: *"Majkel1337 deck + our policy"* **has never been
> submitted → no ladder standing → DIAGNOSTIC-ONLY.** An arm's standing must be that of **the exact
> artifact as submitted**, never the rating of the player whose deck it borrows.
>
> **CORRECTED OUTCOME:** the **PROMOTION field is ONE arm — s14** (the only artifact we own with a
> real, current, submitted standing). The gate has **kill authority only** (it already killed
> armA/B1/B2 correctly; it crowned 2c1368bc03 wrongly). **Only the ladder crowns.** The six top-6
> decks below are **repurposed to the Phase-3 self-play LEAGUE** (deck diversity / anti-overfit — no
> ladder standing required or claimed there). The canonical-CSV-validated top-6 in §5c is the league
> pool. Read the table below as *league deck candidates*, **not** promotion arms.

Champion anchor + the **current** top-6 meta archetypes, each with ladder standing recorded, modal
decklist refreshed from the harvest (newest episodes first):

| # | arm | current MMR | distinct lists | k/6 vs ARCHETYPE_CORE | Jaccard vs s14 | basic energy | role |
|---|---|---:|---:|:---:|---:|---:|---|
| 0 | **`live_s14_reference`** (champion) | **605.4** | 1 | 0/6 | 1.000 | 33 | **anchor — must remain** |
| 1 | Majkel1337 | **1137.2** | 4 | 1/6 | 0.000 | 0 | ladder arm |
| 2 | LiamK | **1100.7** | 3 | 2/6 | 0.069 | 1 | ladder arm |
| 3 | Yushin Ito | **1096.6** | 2 | 0/6 | 0.160 | 9 | ladder arm |
| 4 | nasuo445 | **1096.5** | 2 | 3/6 | 0.033 | 0 | ladder arm |
| 5 | bono | **1093.7** | 2 | 1/6 | 0.000 | 0 | ladder arm |
| 6 | Raihan Ramadistra | **1092.0** | 3 | 0/6 | 0.094 | 0 | ladder arm |
| D | **`2c1368bc03`** | 567.9 | 1 | 0/6 | 0.750 | 34 | **DIAGNOSTIC — demoted, not deleted** |

Modal decklists (60-card, sorted) are in `field_decks.json` alongside this memo.

**Why 2c1368bc03 stays as a diagnostic arm.** It is the *only* artifact we possess with a known
local-strong / ladder-weak signature. That makes it a **canary**: any future candidate that beats
2c1368bc03 locally by a wide margin while the ladder-aligned arms disagree is exhibiting the exact
failure mode that burned us. It earns its slot as an instrument, not as a contender. It must not be
scored as a promotable arm and must never be resubmitted (rpo condition 3 stands).

**Note for the record:** none of the top-6 resembles our deck (Jaccard 0.000–0.160), which is the
same wall as the on-policy audit — the field is ladder-aligned, but our *deck* still is not. That is
a deliberate property of this proposal: the field should represent **the ladder we must beat**, not
the deck we happen to field.

---

## 5b. PRE-REGISTERABLE FIELD SPEC — rpo's four standing rules (#3330), folded in

rpo asked for four standing rules to be pre-registered *with* the field. Adopted, with **one
sharpening that matters**, below.

### ⚠️ Rule (1) as written would RE-ADMIT 2c1368bc03 — the artifact it was written to exclude

rpo (1): *"Every arm admitted to a promotion field must carry a LADDER STANDING. If it has none, it
is DIAGNOSTIC-ONLY."*

That correctly excludes self-play checkpoints, s18, `58f62b5135`, and armA/B1/B2 — all of which have
**no** standing. But **2c1368bc03 *has* a ladder standing (567.9).** Under the rule as literally
written it clears the bar and keeps promotion authority. The rule does not prevent the contamination
it was written to prevent, because the failure was never *missing* a ladder standing — it was
**ignoring a bad one**. 2c1368bc03's 464.5 was "sitting right there next to its result the whole
time," in rpo's own words.

**Proposed sharpening — necessary AND sufficient:**

> **(1a) NECESSARY — ladder-measured.** An arm with no ladder standing has **no promotion authority**;
> it is DIAGNOSTIC-ONLY. Self-play checkpoints have no standing *by construction* → they are sparring
> partners, never promotion arms. (Still fine as *training* opponents; this rule governs who gets a
> **vote at the gate**.)
>
> **(1b) SUFFICIENT — ladder-*validated*, not merely ladder-*measured*.** An arm whose ladder standing
> is **below the champion's** is **LADDER-REJECTED** and is DIAGNOSTIC-ONLY regardless of local
> strength. Promotion authority requires a standing that the ladder has **not** thrown away.

> **⚠️ CORRECTED 2026-07-14 (rpo #3333): the six meta rows below were marked PROMOTION on the
> strength of a ladder standing that is NOT THE ARTIFACT'S — it is the standing of the player's full
> agent (deck + policy). We can only build *their deck + our policy*, which has never been submitted →
> no standing → DIAGNOSTIC-ONLY under rule (1a). See the banner atop §5. The corrected "authority"
> column is shown in [brackets]; only s14 has genuine PROMOTION authority.**

Applied to this field:

| arm | ladder standing | (1a) measured? | (1b) validated? | authority |
|---|---:|:---:|:---:|---|
| `live_s14_reference` | 605.4 | ✅ | ✅ champion (anchor) | **PROMOTION** (the only one) |
| Majkel1337 | 1137.2 *(their agent)* | ❌ *our-policy build never submitted* | — | **[DIAGNOSTIC / LEAGUE]** |
| LiamK | 1100.7 *(their agent)* | ❌ | — | **[DIAGNOSTIC / LEAGUE]** |
| Yushin Ito | 1096.6 *(their agent)* | ❌ | — | **[DIAGNOSTIC / LEAGUE]** |
| nasuo445 | 1096.5 *(their agent)* | ❌ | — | **[DIAGNOSTIC / LEAGUE]** |
| bono | 1093.7 *(their agent)* | ❌ | — | **[DIAGNOSTIC / LEAGUE]** |
| Raihan Ramadistra | 1092.0 *(their agent)* | ❌ | — | **[DIAGNOSTIC / LEAGUE]** |
| **`2c1368bc03`** | **567.9** | ✅ | ❌ **< champion 605.4** | **DIAGNOSTIC** (canary) |
| `s18_active_reference` | — | ❌ | — | DIAGNOSTIC |
| `58f62b5135` | — | ❌ | — | DIAGNOSTIC / drop |
| armA, armB1, armB2 | — | ❌ | — | DIAGNOSTIC (already dead) |
| *future self-play checkpoints* | — by construction | ❌ | — | **DIAGNOSTIC — never a promotion arm** |

~~**Promotion backbone = 7 arms, 100 % ladder-anchored.**~~ **CORRECTED (rpo #3333): promotion
backbone = 1 arm — s14.** The six meta "arms" carry no artifact-level standing (their MMR is the
player's agent, not any build we can produce), so they hold no promotion vote; they move to the
Phase-3 league (§5c). Rule (2)'s majority requirement is then trivially satisfied — s14 is 100 % of
the promotion field. This is the honest inventory, not a poverty of imagination: **the gate KILLS,
only the ladder CROWNS.**

### The other three, adopted as written

- **(2) LADDER-ANCHORED BACKBONE.** Champion + current top-6 meta from the live harvest, each with its
  standing recorded. Self-generated artifacts may never dilute the backbone below a majority of
  promotion arms. *(Under (1a)+(1b) they hold zero promotion slots, so the backbone is 100 %.)*
- **(3) REFRESH EVERY ROUND** from the harvest. The harvest exists to keep the field pinned to what
  people actually play. §4 above already shows why: kazuki0123 1289.9 → 1051.4 in one window.
- **(4) LADDER-STANDING COLUMN IS MANDATORY** in every summary. `live_ladder_snapshot` already exists
  in the `armAB_portfolio.json` schema — make it **required and populated**. It is what caught this.

### rpo's contamination mechanism — stated for the record

The field did not merely drift; **it absorbed the output of the process it was supposed to judge.**
The deck search optimized against a single-arm h2h baseline → produced `2c1368bc03` → that artifact was
then **admitted as an arm of the mixed field**, the very instrument judging everything after it. Every
candidate since has had to beat a deck that exists only because our search made it, and that the
ladder had already thrown away.

**M3's self-play league is that same mechanism, industrialized**: a league that accumulates its own
checkpoints as opponents, none of which has a ladder standing by construction. G4 watches for macro
*decay* against a frozen field — it **cannot see the league drifting away from the ladder while every
local number rises.** `2c1368bc03` is the precedent proving that failure mode is **real on this
program, not hypothetical.** Rules (1a)/(1b) are the only defense that operates on the failure G4
cannot see.

## 5c. CANONICAL-LEADERBOARD RE-VALIDATION (2026-07-14, per ai-scientist-8 #3341)

I executed my own §6(1) caveat: pulled the **canonical public leaderboard CSV** (4,992 teams, via the
PAT-gated `kaggle competitions leaderboard pokemon-tcg-ai-battle` path — token read by the SDK at
point of use, never touched by me) and joined it to the harvest by **TeamId** (robust; `TeamName` is
blank for top teams on this comp, so BFS-name matching alone would have been unreliable).

### The v3 league-pool six — 4 legit, 2 are BFS artifacts

| v3 name | TeamId | **canonical rank** | canonical score | top-tier? |
|---|---:|---:|---:|:---:|
| Majkel1337 | 16374395 | **#1** | 1288.6 | ✅ |
| Budew | 16371434 | **#4** | 1170.9 | ✅ |
| vibechu | 16382914 | **#12** | 1096.6 | ✅ |
| taksai | 16441839 | **#22** | 1073.2 | ✅ (top-25) |
| **kashiwashira** | 16385372 | **#254** | 928.7 | ❌ **mid-pack** |
| **S4nkurero** | 16372517 | **#767** | 839.7 | ❌ **mid-pack** |

**This is exactly the BFS sampling bias §6(1) warned about.** 4 of 6 are genuine top-25; **2 of 6
(kashiwashira #254, S4nkurero #767) are not remotely top-tier** — they ranked high in my BFS pseudo-
leaderboard only because the walk over-sampled them. For a Phase-3 league pool, seeding with #254 and
#767 as "top meta archetypes" would train self-play against non-representative opponents. **Membership
verdict: 4/6 valid, 2/6 must be replaced.**

### The corrected canonical top-6 (all harvestable, decklists extracted)

| # | team | canonical score | harvest seats | distinct lists | k/6 | Jaccard vs s14 | basic energy |
|---:|---|---:|---:|---:|:---:|---:|---:|
| 1 | Majkel1337 | 1288.6 | 97 | 5 | 1/6 | 0.000 | 0 |
| 2 | Yushin Ito | 1228.0 | 1263 | 3 | 0/6 | 0.160 | 9 |
| 3 | bono | 1200.3 | 97 | 2 | 1/6 | 0.000 | 0 |
| 4 | Budew | 1170.9 | 34 | 3 | 1/6 | 0.083 | 0 |
| 5 | THIRD PTCG Club | 1169.1 | 322 | 5 | 1/6 | 0.000 | 0 |
| 6 | MPGaming | 1140.6 | 33 | 4 | 0/6 | 0.034 | 0 |

Only **2 names overlap** between the v3 set and the canonical top-6 (Majkel1337, Budew). Decklists in
`canonical_top6.json`. All six are present in the harvest, so the league pool can be seeded directly.
`taksai` (#22) and `vibechu` (#12) are legitimately strong and fine as *additional* diversity arms,
but they are not the top-6.

### 58f62b5135 — RESOLVED (not dropped): a SECOND canary

I found its gate — I had looked in the wrong directory during the audit. It lives in
`runs/deck_search/evals/58f62b5135_r{0,1,2,3}.json`: **pooled 0.639 vs s14 (639/1000, all four rungs
0.625–0.653) — a STRONGER local gate than 2c1368bc03's 0.571.** But it was **never submitted → no
ladder standing.** Under rule (1a) that makes it DIAGNOSTIC-ONLY. It is the 2c1368bc03 failure mode
*waiting to happen*: the strongest local deck we own, ladder-untested, and rpo condition 3 blocks
probing it. **Keep it as a second diagnostic canary alongside 2c1368bc03, never a promotion arm.**

## 6. HONEST LIMITS — read before pre-registering

1. **This is a PSEUDO-leaderboard, not the canonical one.** Ranks come from a BFS harvest (12,402
   episodes), not the leaderboard CSV — which is PAT-gated and belongs to mroute's §5a scope. The BFS
   samples where it walked, so the top-6 carries **sampling bias**. Before you pre-register this field,
   **re-validate the six names against the canonical leaderboard CSV.** If a name is not in the real
   top-N, swap it. I would not stake a gate on my BFS ordering alone.
2. **"Current" = a recency window** (most-recent 20 % of harvested episodes, ≥6 seats). Ratings move
   daily; refresh at pre-registration time.
3. **`58f62b5135` is unresolved** — I found no gate result for it on disk within my read scope. Someone
   should either produce its h2h or drop it from the field explicitly rather than leaving it ambiguous.
4. **s18 has no ladder standing at all.** It is locally-weak and ladder-untested; keeping it as an arm
   is what inflated B2's macro (the closure memo's own finding). If it stays, it stays as a *known
   out-of-band* arm, labelled as such.

## 7. HARVEST STATUS (material to Phase 1, reporting it here)

The harvest that produced this data is **throttled far harder than the plan assumed**:

- 12,402 replays / 1.00 GB stored (zstd 48.2×) / ~44.8 GB transferred, 10 h wall.
- **1,779 HTTP 429s = 14.3 % of all requests**, all on the *replay* CDN (never ListEpisodes).
- **Sustained 0.35 req/s, not the planned 1.67.** We only hit throughput *through* backoff.

I stopped the run rather than keep hammering a limit, and am resuming paced **at** the sustainable
rate (~3 s spacing) so we stop tripping 429s at all — same yield, genuinely polite. **Phase-1's
1.5–2-day projection still roughly holds** (~1,240 replays/h observed → 45 K in ~26 more hours), but
it holds at 0.35 req/s, not 1.67, and the plan should say so.
