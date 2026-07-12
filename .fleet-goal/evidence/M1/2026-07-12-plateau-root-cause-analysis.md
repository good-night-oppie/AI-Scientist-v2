# Evidence — Plateau root-cause analysis (why 607.6; fundamental diffs vs top ladder)

_ai-scientist-6, 2026-07-12. Workflow wf_fc1549e0-ff8: 31 agents, 0 errors,
89 findings, 55 claims, 24 adversarial verdicts (12 claims x 2 lenses:
source-check + alternative-explanation). Requested by Eddie via /ai-scientist._

# Root-Cause Report: Why Our PTCG Agents Plateau at ~607.6

**Synthesis of 6 analyst findings + adversarially-verified claims. 2026-07-12. All numbers are OBSERVED (file-grounded) unless marked DERIVED.**

---

## 1. TL;DR

Top ladder agents (1100–1232) are **co-adapted deck+policy systems**: evolution-line engine decks (8–14 energy, 15–20 search items) operated by policies that fire draw/search abilities on 44.1% of opportunities. Our s14 is a degenerate mono-attacker deck (33 energy, 11 distinct cards, Jaccard ≤0.11 to any meta deck) driven by a heuristic that agrees with 1100+ players on only 40.6% of real decisions and *structurally cannot* fire an ability while an attack is legal (0/918), retreat (0/6,071), or see cards during deck searches (index-0 blind). Every optimization lever we ran — search fix, BFTS, weco, deck evolution — moved *within* this degenerate region, because our deck-search legality floors (`Kyogre>=2`, `Water energy>=15`) exclude all 14 observed meta decks, and our local gate (h2h vs frozen s14) measures self-similarity, not ladder fitness. The plateau at ~607 is the rating of "slightly better than the 600-entry pool, structurally unable to play the meta game" — and no local h2h vs ourselves could ever detect that.

---

## 2. Fundamental Differences, Ranked by Estimated Rating Impact

Ranking is DERIVED (frequency × behavioral-divergence severity × interaction with meta decks); every underlying number is OBSERVED.

### R1. Ability/draw-engine incapacity (MAIN_SCORES inversion: ABILITY 25 < ATTACK 30)

- **Difference:** Top players fire abilities 44.7% of the time one is available (798/1,786) and choose ability over attack in 37.6% of both-legal states (345/918). We fire abilities 1.7% overall and **0/918** when any attack is legal — structurally inevitable, since `_score_main` only ever *adds* to attack and never touches ability.
- **Evidence:** `src/ready_player_one/ptcg/policy.py:43-46,51,119-148` (OPT_ABILITY 25.0 < OPT_ATTACK 30.0, comment "unknown abilities can self-sabotage"); replay counts in `scratchpad/plateau/replay_quant_results.json` (918/345 EXACT match to spec); spec at `.fleet-goal/evidence/M1/2026-07-12-policy-divergence-imitation-spec.md`.
- **Verification:** ordering1 — CONFIRMED × 2 lenses (one empirically re-executed choose() paths; all 1,556 card-DB attack damages ≥0, so ability can never outrank a legal attack).
- **Impact rationale (DERIVED):** Largest single behavioral divergence, and it compounds with R2: meta decks *are* ability engines (400+ activations/game class), so an ability-mute policy cannot operate any meta deck — this is the likely mechanism behind ZETADIVISION's deck scoring 0.20 under our policy (`runs/replay_mining/eval_meta1_1106_ZETADIVISION_n40.json`). Caveat carried from verdict: both-legal frequency under OUR current deck is unquantified (our deck has no ability engine to mute).
- **Falsifiable prediction:** Reordered MAIN_SCORES + per-card DENY-list, paired with an ability-engine mined deck, beats frozen s14 with Wilson-lo > 0.50 at n400; and ability-fire rate in our own logs rises from ~1.7% toward 40%+. If it fails n400, the ordering is not the binding constraint.

### R2. Deck architecture outlier + the search-space cage that guaranteed it

- **Difference:** Ours: 33 basic Water energy, 11 distinct cards, 5 items, 4-of playsets ×4; five of our 11 cards appear in ZERO meta decks. Meta (14 unique decks, ratings 977.8–1219.8): energy median 10 (T1 range 8–14), distinct median 19, items median 17, 5–6 near-universal staples (Boss's Orders 12/14, Poke Pad 11/14, Night Stretcher 11/14, Buddy-Buddy Poffin 10/14) of which we run exactly one (Lillie's Determination). Max Jaccard to any meta deck: 0.11. **Root cause:** `scripts/deck_search.py` `is_legal()` enforces `Kyogre>=2` and `Basic {W} Energy>=15` (lines ~192-196, mutation floor line 307) — the entire 2,857-deck search archive lives in a region containing zero of the 14 meta decks.
- **Evidence:** `submission_search_s14_baseline.tar.gz -> deck.csv`; `runs/replay_mining/*.csv` + `inline_harvest*.json`; `scratchpad/plateau/deck_struct_analysis.py` output; `runs/deck_search/decks/` (2,857 files).
- **Verification:** Analyst-observed structural counts (not adversarially lensed, but directly recomputed from raw deck files); consistent across two independent analysts.
- **Impact rationale (DERIVED):** Large — but **only jointly with R1/R3**. Deck-transfer alone was twice n400-falsified (meta0 0.4725, meta2 0.460 under our policy), and our locally-best deck 2c1368bc03 is the *same archetype* as s14 (34 energy, same Abomasnow core — `runs/deck_search/decks/2c1368bc03.csv`), explaining its ladder non-transfer. The bidirectional transfer failure (their decks lose under our policy; our decks lose on their ladder) is the signature of deck↔policy co-adaptation: the difference is the *system*, not either component.
- **Falsifiable prediction:** (a) Remove the is_legal floors and the deck search discovers ≥10-energy engine decks that beat s14 *under a fixed policy*; (b) mined-deck + fixed-policy pair wins n400 where mined-deck + old-policy was parity. If a meta deck still loses under the bug-fixed policy, the gap is deeper than these 4 bugs + ordering.

### R3. Blind deck-search selection (bug 1, deck half)

- **Difference:** `_resolve_card_id` has no AREA_DECK(1)/AREA_PRIZE(6) branch (falls to `return None`), all options score 0.0, tie-break picks index 0. 19.8% of top-player decisions (1,838/9,267) land in buckets we pick blind; verifier re-measured 1,855 actor deck-search decisions (mean 6.1 options) with our degenerate output matching top play only 32.2%, and confirmed `sel['deck']` resolves every area-1 option id (1961/1961) — the fix is real and requires threading `sel` into scoring (currently only `cur` is passed, `policy.py:190,219`).
- **Evidence:** `policy.py:60-80,187,219-220`; `enums.py:36,41`; spec lines 14-17, 28.
- **Verification:** bug1 — CONFIRMED × 2, with a material correction: **the PRIZE half is a no-op** (prize ids are hidden from ALL policies; 1100+ actors match index-0 at near-noise 37.3% on 614 prize picks), so fixable headroom is the deck share only (~75% of affected decisions).
- **Impact rationale (DERIVED):** Medium-high, strongly interacting with R2: it neuters exactly the search items (Ultra Ball, Dusk Ball, Poffin) that make engine decks work. Under our current 5-item deck it binds rarely; under a mined 17-item deck it would bind ~17 times/game.
- **Falsifiable prediction:** After threading `sel`, deck-search pick agreement with 1100+ play rises from 32.2% toward ≥70% on the same replay corpus; combined with a mined deck it contributes to an n400 win. Prize-select changes should show no effect (control).

### R4. Retreat structurally impossible (bug 3)

- **Difference:** OPT_RETREAT 0.0 < OPT_END 1.0, no branch ever raises it; END is present on 16,208/16,208 MAIN selects → retreat can never rank first. We retreat 0/6,071 MAIN decisions; 1100+ players retreat on 25.0% of retreat-legal turns (173/693), and 77.5% of their retreats cost zero energy.
- **Evidence:** `policy.py:47-48,119-148`; `replay_quant_results.json` retreat block.
- **Verification:** bug3 — CONFIRMED × 2 (one lens executed choose() over all 7,217 retreat-offering states: 0 retreat picks). Carried caveat: low-rated players retreat at the same ~25% rate, so this is **table stakes, not a top-tier discriminator** — necessary, not differentiating.
- **Impact rationale (DERIVED):** Medium. An agent that can never rescue a damaged/stranded active loses games any 600-rated opponent wins; fixes a floor, doesn't buy the ceiling.
- **Falsifiable prediction:** Post-fix self-play logs show retreats at a nonzero rate on retreat-legal turns; losses via active-lock decline. Measured only jointly (n400 gate), per verdict guidance.

### R5. Within-turn scheduler and targeting preferences (ordering 2 & 3, MAIN-level)

- **Difference:** (a) Items 50.0 < supporters 55.0 (no CARD_ITEM branch) — experts play item-before-supporter in 61.9% of both-turns; but verifier bounded this: it's a *scheduler*, items still get played the same turn, and only 16.5% of expert supporter-first turns mutate the hand. (b) Attach-to-active is a strict +2.0 dominance → we attach active 100% by construction; top players attach to BENCH 65.8% (557/846). (c) Flat EVOLVE 80.0 → 24.7% MAIN evolve-target mismatch.
- **Evidence:** `policy.py:41-42,133-147`; `replay_quant_results.json` energy_attach/play_mix; `scratchpad/plateau/ordering2_verify.py`.
- **Verification:** ordering2 CONFIRMED × 2 (bounded small); ordering3 CONFIRMED × 2 (the +2.0 provably fires on real payloads, 10,663/10,663 ATTACH options carry inPlayArea).
- **Impact rationale (DERIVED):** Small-to-medium; the attach-to-bench inversion (100% vs 34.2% active) is the meaningful part — bench charging is how engine decks develop attackers.
- **Falsifiable prediction:** Attach-target agreement on the replay corpus rises from 37.9% toward ~66% bench-preferring; item:supporter play ratio moves from 0.69:1 toward 2:1 *only if* paired with an item-rich deck (deck-composition confound predicted by verifier).

### R6. Sacred Ash / CTX_TO_DECK recovery inversion (bug 4) — confirmed mechanism, negligible weight

- **Evidence:** `enums.py:59,110-123`; `policy.py:76-77,175-177,222-225`; top players took max recovery 19/19 (our re-count; spec 38/38).
- **Verification:** bug4 — CONFIRMED × 2, mechanism only. ~0.4% of observed decisions; fires only if our deployed deck runs discard→deck recovery (current deck doesn't). Fix must be area-aware (discard-origin TO_DECK = recovery), NOT removal from SELF_LOSS_CONTEXTS; minCount=0 edge recovers zero.
- **Impact (DERIVED):** Negligible standalone; matters only after adopting a Night-Stretcher-class meta deck (11/14 meta decks run it).

### R7. EVOLVE/ATTACH_TO select-level target blindness (bug 2) — **DOWNGRADED**

- **Verification:** bug2 — split verdict (CONFIRMED on code reading, **REFUTED on materiality**). The adversarial lens measured: ctx-22 selects never carry inPlay\* fields (0/103; 100/103 offer identical-card options — nothing at stake), and on the 73 real ctx-37 selects, engine ordering makes blind index-0 replicate 1100-tier targeting 93–94% → **~3 divergent decisions per 106 games**. The real target-choice damage lives in R5's MAIN-level scoring, not this bug.
- **Action:** Deprioritize within the capsule; do not credit it rating impact.

---

## 3. Why the Plateau Is STABLE at ~607

**Rating mechanics (OBSERVED):**
- Every submission enters at publicScore 600.0 (mu0) — `LANE_STATE.md:195-204`, `PROGRESS.md:39`. Only the latest 2 submissions stay scored; 5/day cap (`LANE_STATE.md:196`).
- Demonstrated volatility band ~182 pts (s14: 600→420→607.6; probe: 600→464.5→548.1; seed: 600→521.0). No privateScore ever observed — every ladder number is a provisional point-in-time poll.
- **DERIVED:** 607.6 is ~7.6 pts above entry. That is the equilibrium rating of an agent near parity with the pool it gets matched against around 600. All three of our scored agents (seed 521, probe 548, s14 607) landed in one band because all are the same archetype-region system with near-identical fitness vs the pool. Climbing to 1100+ requires *winning* against engine decks our policy is 40.6%-aligned with — a capability difference, not a tuning difference.

**Why local gates were blind (OBSERVED mechanisms, DERIVED conclusion):**
1. **The yardstick was ourselves.** Every gate was h2h vs frozen s14. The A/A control (0.495 [0.446,0.544], n400 — `weco-observe-7393d6ae-results.json` step 0) proves the harness is unbiased, but unbiased at measuring the wrong quantity: improvement *within* our archetype region, not fitness vs the meta pool.
2. **Direct falsification of the local→ladder link:** 2c1368bc03 won 0.571 vs s14 over n800 combined, then probed at 548.1 — *below* s14's same-poll 602.4/607.6 (`evidence/M1/2026-07-11-kaggle-probe-54585744.md`). It is structurally the same deck as s14 (34 energy), so beating s14 at its own game bought nothing against the real opponent distribution.
3. **Winner's curse compounded it:** ≥5 confirmed small-N mirages (0.625→0.4725 meta0; 0.600→0.460 meta2; two confirm-pass→reconfirm-out decks; candidate batch 1.0@n8→0.475@n40) — every apparent escape from the plateau was noise until n400.
4. **The search cage guaranteed no candidate could differ enough to matter:** with `is_legal()` pinning ≥15 Water energy + Kyogre, every one of 2,857 searched decks — including all 46 "PROMOTABLE" — was a variation on the deck the ladder already rates at ~607. Every confirmed local gain was ≤ +0.15 winrate vs our own baseline (`PROGRESS.md:326-327`), i.e., intra-region noise from the ladder's perspective.

---

## 4. Already Falsified — Do Not Re-litigate

| Lever | Outcome | Evidence |
|---|---|---|
| Determinized search, fixed (s17/s18) | LOSES to heuristic: n300 wr 0.4333, Wilson-upper 0.49 < 0.50; search genuinely alive (43,333 calls) | `LANE_STATE.md:88-101` |
| Search-constant "evolution" pre-s17 | Tuned dead code — search never fired (2-elem select bug, silent fallback); never validly measured | `LANE_STATE.md:61-87`; memory `search-dead-silent-fallback.md` |
| BFTS | Undeployable torch-NN drift; weights never saved; smoke best 0.743 < seed 0.767; fullrun2 no terminal outcome on record | `LANE_STATE.md:222-238`; memory `bfts-torch-drift.md` |
| weco round-2 derive | In-loop 0.7125 < s14 0.7917, died with session | `LANE_STATE.md:240-243` |
| Deck transfer (their decks, our policy) | Twice n400-falsified: meta0 0.4725, meta2 0.460; ZETADIVISION 0.20@n40 | `runs/replay_mining/eval_meta*_n*.json` |
| Deck search within the cage | 46 PROMOTABLE local (best 0.6525) but same archetype region; probe transfer failed (548.1 < 607.6) | `runs/deck_search/HARVEST_RESULT.md`; probe evidence |
| PCMM (metamon router, pokechamp minimax) | Both fail Stage-B gates (worst-arm 0.375; macro 0.4667 with search active) | `evidence/M1/2026-07-12-pcmm-stageB-screen-results.md` |
| Small-N candidate promotion | Systematic mirage; nothing survives n≥160 without n400 reconfirm | `LANE_STATE.md:145-151,193-195` |

Note per caveats: BFTS and weco were falsified for *artifact/deployment* reasons, not measured mechanism losses — but neither has a path to a valid ladder-relevant measurement without the R1–R3 fixes landing first.

---## 5. Residual Unknowns and Capsule Coverage

**Capsule `ptcg-imitation-policy` (fix bugs 1–4 + MAIN_SCORES reorder + pair with mined deck) addresses:**

| Difference | Covered? | Notes |
|---|---|---|
| R1 ability inversion | YES | Reorder + per-card DENY-list (Surfing Beach self-sabotage was real — keep the deny mechanism, gate on n400) |
| R2 deck architecture | PARTIALLY | Pairing with a mined deck sidesteps the cage for the deployed agent; does NOT fix `deck_search.py` floors, so the search infrastructure remains caged for future iteration |
| R3 blind deck search | YES (deck half) | Requires threading `sel` into scoring (`policy.py:190,219`); prize half is a no-op — spend nothing there |
| R4 retreat | YES | |
| R5 scheduler/attach targeting | PARTIALLY | MAIN_SCORES reorder covers item/supporter and can cover attach-to-bench; flat-EVOLVE target quality needs a scoring term, verify it's in scope |
| R6 CTX_TO_DECK | YES, if fix is area-aware | Wrong fix (removing from SELF_LOSS_CONTEXTS) introduces a new bug; minCount=0 edge must take max |
| R7 select-level target blindness | Deprioritize | Empirically ~3 decisions/106 games (REFUTED as material) |

**What the capsule does NOT address:**
1. **The transfer gate itself.** Local divergence-reduction → ladder rating is unproven and has failed twice (s17/s18 search fix; 2c1368bc03 probe). The capsule's n400 h2h is necessary but cannot certify a ladder gain — only a Kaggle probe can, inside a ~182-pt volatility band with no privateScore, meaning effects smaller than ~100 pts may be unmeasurable per poll (DERIVED).
2. **Card-level knowledge / 28.2% MAIN agreement.** Four bug fixes + reordering are hand-repairs to a scorer whose MAIN-bucket agreement is 28.2% with their pick at mean rank 4.57 — closing that likely requires actual imitation (replay-trained scoring), not constant surgery (DERIVED).
3. **Co-adaptation risk in the pairing.** Meta decks were parity under the *old* policy; whether the *fixed* policy unlocks them is the capsule's central untested hypothesis. If mined-deck + fixed-policy still fails n400, the gap includes something we have not measured (e.g., sequencing/lookahead — their attack-last cadence, tac 10.17, is only partially induced by scheduler reorder).
4. **Search-space cage** (`scripts/deck_search.py` is_legal floors) — needs its own change before any future deck search can help.
5. **Opponent-pool composition** at the 600 band vs 1100 band is unobserved; rating attribution of any single fix will remain confounded.

**Decision-relevant bottom line (DERIVED):** ship the capsule as one joint intervention (policy fixes × mined deck), gate at n400 vs frozen s14 AND vs ≥2 mined meta decks under self-play, then spend one Kaggle probe slot — and treat anything short of a >+100-pt sustained poll delta as unresolved, not failed.