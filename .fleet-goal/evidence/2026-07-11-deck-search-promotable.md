# Evidence — deck search PROMOTABLE + search-tuning lever exhausted (2026-07-11)

_Author: ai-scientist-5 (successor of ai-scientist-4). Time ~20:27Z._

## Headline
The evolutionary **deck search** (the #2717/#2715 diversified lever) produced its
first fully-vetted PROMOTABLE deck. Independently, the **s18 search-tuning lever is
exhausted** (mechanically-correct search still loses to the heuristic-effective
champion). Champion **s14 remains live on Kaggle at publicScore 580.7**.

## 1. Deck search PROMOTABLE — `2c1368bc03`
Policy FROZEN (byte-identical to live-s14 bundle); only the 60-card DECK evolved.
Fitness = trusted h2h harness vs the frozen live-s14 baseline tar, fresh games/rung.

Full 4-rung ladder (all rungs passed):

| rung | games | W-L | winrate | Wilson | verdict |
|---|---|---|---|---|---|
| screen | 40 | 25-15 | 0.625 | [0.470, 0.758] | promoted |
| mid | 160 | 89-71 | 0.556 | [0.479, 0.631] | promoted |
| confirm | 400 | 228-172 | 0.570 | [0.521, 0.618] | confirm_pass |
| **reconfirm** (independent fresh) | **400** | **229-171** | **0.5725** | **[0.524, 0.62]** | **PROMOTABLE** |

Combined confirm+reconfirm: **457/800 = 0.571** vs live-s14, Wilson-lo ≥ 0.52 on both
independent N=400 batches. Diff from reference deck: `count_shift:-1240+3` (one card
1240 → one basic {W} energy) + `add_new_trainer:+1x1114`. Legal 60-card deck.

Ledger: `ready-player-one-ptcg/runs/deck_search/ledger.jsonl` (grep `2c1368bc03`).
Deck csv: `runs/deck_search/decks/2c1368bc03.csv`.

### Review-ready bundle (built + validated by ai-scientist-5)
`ready-player-one-ptcg/submission_search_deck_2c1368bc03.tar.gz` (502 KB).
`build_submission_search.py --deck-path <csv>` = frozen champion policy + new deck.
Runner-faithful validation: **self-play 20-0-0, search_begin 20/20,
zero forfeits, 60 legal cards, VALIDATION OK.** The 20/20 equality is the known
live-s14 first-move failure followed by heuristic fallback, not active search.
This candidate intentionally isolates the deck contribution under the same
deployment-faithful heuristic-effective policy as live-s14.

### Validity check — the result is REAL, not a harness artifact (ai-scientist-5)
Given the lane's history of false positives (s14's search never fired; s15/s16 were
unknowingly A/A tests), the deck-search result was validity-checked before offering
it for a Kaggle slot:
- **A/A control PASSES:** ref deck vs the same frozen live-s14 baseline, N=400 =
  198-202, **wr 0.495** [0.446, 0.544] — essentially 0.50. The h2h harness is
  UNBIASED (no seat/determinization inflation); this is the built-in falsification
  guard, and it sits *below* 0.50 → rules out any candidate-side inflation bug.
- **~4σ signal:** combined confirm+reconfirm 457/800 = 0.571 is ≈4σ above the 0.495
  null (SE≈0.018), held across TWO independent N=400 batches (228-172 then 229-171 —
  distinct counts ⇒ fresh games, not a cached duplicate).
- **Ladder calibration:** 8 decks reached N=400; only 2c1368bc03 cleared confirm AND
  reconfirm; the rest regressed to 0.48–0.53. Candidate winrates spread 0.48→0.57
  (a same-deck-both-sides bug would pin all to ~0.50) → the candidate deck genuinely
  changes play. Verdict: PROMOTABLE is a genuine deck-level improvement.

### Caveat for the promotion decision (rpo/Eddie)
Deck-vs-deck h2h under identical policy isolates the DECK contribution cleanly, but
(winner's-curse lesson) local h2h does NOT guarantee ladder improvement. This is a
**candidate for a ladder-probe**, not a certain win. Per protocol: rpo review →
ladder-probe decision. Do NOT burn a latest-2 slot on in-loop numbers without
approval. Champion s14 is live and accruing rating — must not be carelessly displaced.

## 2. s18 search-tuning lever EXHAUSTED (powered N=300 h2h landed)
s18 = reference-deck opponent model over the now-ALIVE search (s17 fixed the ABI
misuse where s14's `search_step` was rejected on the first move of every game →
silent heuristic fallback). Powered result:

`s18 vs s14 baseline, N=300: 130-170, winrate 0.4333, Wilson [0.378, 0.49]`
- `candidate_search_begin_calls: 43333` (≈144/game — the search genuinely fires now)
- `baseline_search_begin_calls: 300` (= games — the s14 dead-search signature)

Wilson-UPPER 0.49 < 0.50 → s18 is significantly WORSE than the heuristic-effective
s14. **Mechanically-correct determinized search does not beat the heuristic on this
engine/opponent-model.** The search-constant space is now measurable but the first
powered probe says the heuristic-effective policy is the one to keep. The productive
lever is the DECK, not the search internals.

## 3. Champion s14 — live Kaggle status (fresh poll ~20:2xZ)
- `54554870` s14 search champion: **publicScore 580.7, COMPLETE** (μ evolving on ladder)
- `54539166` seed v1.1: publicScore 526.0, COMPLETE
- s14 leads seed by **+54.7**; no privateScore yet; both inside the demonstrated
  ~182-pt low-game volatility band → "search>seed on ladder" remains ladder-SUPPORTED,
  not settled. Stance: KEEP s14 live, do not react to noise.

## What's next
- Deck search still running (PID 1829394, own session, 10h cap → ~05:31Z, 376 evals
  so far, actively promoting more candidates past n=160). A better deck may emerge;
  re-harvest `verdict==PROMOTABLE` rows at run end and rebuild for the best.
- rpo/Eddie: review `2c1368bc03` bundle; decide whether to spend a Kaggle latest-2
  slot on a deck-swap ladder-probe (vs keeping s14 live to accrue privateScore data).
