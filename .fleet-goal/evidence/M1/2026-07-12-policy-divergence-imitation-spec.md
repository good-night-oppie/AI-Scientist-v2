# Evidence — POLICY DIVERGENCE vs 1100+ ladder play (the imitation spec)

_ai-scientist-5, 2026-07-12. Workflow wpgxy045l over 106 mined replays._

## HEADLINE — the imitation thesis is CONFIRMED, and the gap is mostly BUGS

Our heuristic (`src/ready_player_one/ptcg/policy.py`) was replayed against the actual
decision states of >=1100-rated players (team-filtered, alignment-validated):

| metric | value |
|---|---|
| decisions evaluated (0 exceptions) | **9,931** |
| forced (1-option) — alignment check | 664/664 = 100% agree |
| **REAL multi-option decisions** | **9,267** |
| **our choice == their choice** | **3,765 = 40.6%** |
| robustness (strict >=1100 episodes only) | 1,449 decisions, 42.2% — consistent |
| MAIN/MAIN bucket (62% of all decisions) | **28.2% agreement**; mean rank of THEIR pick under our scorer = **4.57** |

**We disagree with top players on ~60% of real decisions.** Imitation is not a
marginal lever — our policy is playing a different game.

## Root causes — 2 are outright BUGS (verifiable by reading the source)

**BUG 1 — deck/prize searches are BLIND.** `_resolve_card_id()` has no branch for
`AREA_DECK(1)` or `AREA_PRIZE(6)` → every option resolves to `None`,
`_score_card_pick` returns 0.0 for all, `choose()` degenerates to **index 0**.
- CARD/TO_HAND: 1,498/1,676 (89.4%) score all-identical (1,482 all-zero).
  CARD/TO_BENCH: 169/169 = **100% blind**. Overall **1,838/9,267 = 19.8% of top-player
  decisions are coin-flips for us.**
- The data is already present: `sel['deck']` is a list of `{id, playerIndex, serial}`
  and `option['index']` indexes straight into it.
- FIX: `if area == AREA_DECK: return (sel or {}).get('deck',[])[index].get('id')`
  (same for PRIZE). Requires threading `sel` — not just `cur` — into
  `_score_option`/`_score_card_pick`.

**BUG 2 — we never choose the TARGET on EVOLVE/ATTACH_TO.** All options share the
same `area`+`index` (the card being played) and differ ONLY in
`inPlayArea`/`inPlayIndex` (which Pokémon receives it). `_resolve_card_id` reads
`area`/`index` → all options score identically → we take index 0.
- EVOLVE/EVOLVE: 45/45 = **100% blind ties**. CARD/ATTACH_TO: 34/34 = **100% blind**.
- FIX: when `inPlayArea`/`inPlayIndex` are present, resolve the TARGET and score by
  target quality.

**BUG 3 — `OPT_RETREAT: 0.0` is below `OPT_END: 1.0` → we retreat 0/6,071 times, ever.**
Top players retreat in **25% of retreat-legal turns**; **68.2% of their retreats are
FREE** (retreatCost 0). 79 states where they retreat and we attack. Even LOW-rated
players retreat at the same rate — **we are below the floor**, this is table stakes.

**BUG 4 — `CTX_TO_DECK(9)` misclassified as a SELF_LOSS context.** It's a RECOVERY
effect (Sacred Ash: discard → deck). Two bugs compound: `choose()` caps k at
`minCount`, and `_score_card_pick` scores `100 - keep_value`. Result: we recover the
**fewest** and the **worst** Pokémon. Top players took the MAX count 38/38 = 100%;
they recovered 79 Pokémon where we'd recover 19, and ours is the lowest-value card
19/19 = 100% of the time.

## Behavioral inversions (grounded in counts, tuning not bugs)

1. **ABILITY is the single biggest miss.** Top players fire an ability on **44.1%** of
   MAIN decisions where one is available; **we fire on 1.7%** (31/6,071 = 0.5% by the
   second analyst's count). In 918 states where BOTH ability and attack were legal:
   they took ABILITY 345x (37.6%), we took it **0/918**. `OPT_ABILITY(25) < OPT_ATTACK(30)`
   and attack ends the turn → **we are structurally incapable of using an ability
   whenever any attack is legal. We have disabled the deck's entire draw/search engine.**
   Their engine: Cynthia's Gabite 432x, Dudunsparce 162x, Munkidori 43x, Drakloak 36x.
   The code comment ("abilities can self-sabotage, e.g. Surfing Beach") is an
   over-correction from ONE bad card → replace the global demotion with a per-card
   DENY-list.
2. **Score order IS the intra-turn schedule** (attack ends the turn, everything else is
   free). Top cadence by mean turnActionCount: ABILITY 5.57 → EVOLVE 5.97 → ITEM 6.02 ≈
   SUPPORTER 6.03 → POKEMON/ATTACH 6.82 → ATTACK 10.17. **They run the engine first and
   attach LAST** (so the turn's draws reveal the right attach target). Ours is the
   reverse: EVOLVE 80 > ATTACH 70 > basic 66 > SUPPORTER 55 > ITEM 50 > ATTACK 30 > ABILITY 25.
   Action-mix delta over the identical 6,071 states: PLAY −16.5pp, ATTACH **+17.2pp**,
   EVOLVE +11.1pp, ATTACK +5.0pp. Top confusion edge: **they PLAY / we ATTACH (879)**.
3. **Energy goes to the BENCH 2:1** (pre-charging the next attacker) — 557/846 = 65.8%;
   67.0% when both targets were legal. When the active could already pay its best
   attack, they went bench **86.1%**. We attach to ACTIVE **100%** by construction
   (`+2.0` bonus for AREA_ACTIVE, no target-quality term). Attaching to the active is a
   **low-ladder tell** (LOW players: 55.6% active).
4. **ITEMS over SUPPORTERS.** `_score_main` has no CARD_ITEM branch → items fall through
   to 50.0, BELOW supporters at 55.0. Their PLAY mix: ITEM 1039 / POKE 652 / SUPPORTER 512.
   Ours inverts it (SUPPORTER 619 / ITEM 425). Ratio: theirs 2.03:1, ours 0.69:1.
   Supporters burn the once-per-turn slot; items are free and repeatable.
5. **`_card_keep_value` is inverted on the two extremes.** We rank BASIC_ENERGY lowest
   (20.0, "cheapest to lose") and POKEMON highest (60+). Top decks run **~13 energy in 60**
   — energy is their SCARCEST resource. Give-up rates (them vs us, same options):
   POKEMON 54.3% vs 16.8%; BASIC_ENERGY 41.5% (their lowest) vs 71.2%.
   **They protect energy and shed spare Pokémon; we do the exact opposite.**
6. **Role-blind body selection.** The `hp + best_attack_damage` fallback = "biggest body
   wins". They use utility/sacrificial actives (Cynthia's Spiritomb 70x on SWITCH where
   we pick Garchomp ex 148x) and pre-charge bench pre-evolutions.
7. **Bench target too low.** benchMax is 5 (6,071/6,071 obs); top players reach a full
   5-bench in **81.3%** of games, mean bench 4.04 by turn 3. Our `BENCH_TARGET = 3`.

## Proposed MAIN_SCORES rewrite (both analysts converged independently)
```
OPT_ABILITY  85   (was 25 — allowlist/denylist per source card)
OPT_PLAY(ITEM) ~75, OPT_PLAY(SUPPORTER) ~58   (was: item 50 < supporter 55)
OPT_EVOLVE   70-80
OPT_PLAY(basic Pokémon) ~60
OPT_ATTACH   45-55  (target-quality term; bench-preferring; saturation penalty)
OPT_ATTACK   30     (KO_SCORE 95 override UNCHANGED — cannot cost us a lethal)
OPT_RETREAT  ~45 when retreatCost==0 AND active undercharged/damaged AND bench can attack
OPT_END      1
BENCH_TARGET 3 -> 5
```

## ⚠️ VERIFICATION CAVEAT (read before acting)
The workflow's adversarial verify phase **died on a monthly spend limit** — 25 of 30
verifier agents errored. So `survived=1` is an ARTIFACT of the outage, **not** a
refutation result. Status of these findings: **grounded in exact counts from 106
replays with a validated action/observation alignment (664/664 forced-select check),
but NOT independently refuted.** Both analysts independently converged on the same
top-3 conclusions (ability demotion, attach-to-active, order-is-schedule), which is
meaningful corroboration. BUGS 1-4 are **cheap to verify directly by reading
policy.py** — do that first; they need no statistics.

## Falsifiable acceptance (unchanged gates)
Fix bugs 1-4 + reorder MAIN_SCORES → h2h vs live-s14: n40 screen → n160 → n400 confirm
→ independent n400 reconfirm; then mixed-field arms vs mined 1180-tier decks.
**A result near 0.50 at n400 means the imitation hypothesis is WRONG** and the gap lives
elsewhere (deck-policy interaction or search depth).

## Trap watch (5 false promotions so far)
- n40 mirages: 2c1368bc03 (0.625→0.5075) and meta0_1106 (0.625→0.5075). **Never trust n40.**
- The 40.6% agreement is measured against *their* decks. Our policy must be paired with a
  deck that supports the engine (their decks run 0 basic-energy card-3; ours ran 33).
  **Policy and deck must move together** — that is why deck-transfer alone failed.
