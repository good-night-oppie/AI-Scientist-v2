# PRE-REGISTRATION — the ladder-aligned promotion field (v2)

**Committed BEFORE any GBM (or other M3 candidate) number exists.** Required by rpo #3327 §5(d);
grounded in sctst-aide's field audit (#3330, `2026-07-13-promotion-field-audit.md`) with its limit
(1) DISCHARGED: the six meta arms below are pinned from the CANONICAL leaderboard CSV (downloaded
2026-07-13 ~11:06Z via the official PAT-gated CLI), not the BFS pseudo-leaderboard, which is now
documented to carry real sampling bias (it missed the actual #1, #5 and #6, and proposed two teams
outside the true top-14).

## Why the field changed (the receipts)

- The old field's local-vs-ladder record is **0-for-1**: 2c1368bc03 is the only arm ever
  ladder-tested and the gate endorsed it wrongly (local 0.571 vs s14; ladder 567.9 vs champion
  605.4 today). Every other arm has never touched the ladder.
- No old arm is within ~500 MMR of the opponents a promoted candidate actually faces (top-6 =
  1153–1245 canonical).
- 41% of the ≥1100 supervision corpus comes from teams now FALLEN out of the top (kazuki0123
  1289.9→1051.4; WinDecks →1122/#10) — the meta moved; the gate must track it.

## THE PROMOTION FIELD (gate authority — all floors per aaa1156, unchanged)

| # | arm | canonical score (2026-07-13) | role |
|---|---|---|---|
| 0 | live_s14_reference | 605.4 (our champion, sub 54554870) | ANCHOR — must remain |
| 1 | kashiwashira | 1245.7 (#1) | meta arm — modal decklist from harvest |
| 2 | Majkel1337 | 1202.0 (#2) | meta arm |
| 3 | bono | 1185.4 (#3) | meta arm |
| 4 | Yushin Ito | 1182.9 (#4) | meta arm |
| 5 | 懒惰的金枪鱼 | 1157.4 (#5) | meta arm |
| 6 | Budew | 1153.7 (#6) | meta arm |

Meta arms are played by the FROZEN HEURISTIC piloting each team's MODAL DECKLIST extracted from the
newest harvest episodes (deterministic given the names; extraction task dispatched to sctst-aide).
Yes, our heuristic under-pilots those decks — so meta-arm winrates are OPTIMISTIC for the candidate
(the real teams play their own decks better). A candidate that cannot beat even the under-piloted
top-6 decks cannot beat the ladder; the bias direction is conservative for promotion.

## DIAGNOSTIC ARMS (no promotion authority; reported, never gating)

- **2c1368bc03 @567.9 — the canary.** The only artifact with a known local-strong/ladder-weak
  signature. A candidate that crushes it while the meta arms disagree is exhibiting exactly the
  failure mode that produced M1's false positive. Never resubmit (rpo condition 3 stands).
- **s18 — out-of-band label** (audit limit 4): no ladder standing, locally weak,
  wall-time-load-sensitive (it inflated B2's macro). Kept only as a cross-family diagnostic.

## DROPPED EXPLICITLY (audit limit 3)

- 58f62b5135: no gate result on disk; ambiguous provenance. Out of every field until someone
  produces its h2h record.

## Floors and discipline (verbatim carry-over)

Screen n40/arm: macro ≥0.55, worst-arm ≥0.40 (over PROMOTION arms only). Confirm n400/arm:
macro ≥0.55, worst-arm Wilson-lo ≥0.50. Independent reconfirm, no pooling. Liveness=LIVE for any
learned candidate. n40 = mirage. Environmental preconditions logged per (8'). Asymmetric
admissibility per #3325 (degraded-reference FAIL admissible; degraded-reference PASS inadmissible)
— note with the s18 arm demoted to diagnostic, the load-sensitivity problem largely exits the
promotion path (all meta arms + s14 are fast heuristic-pilots, load-independent — measured
0.5-0.6 s/game class).

## Refresh rule (pre-committed)

The six meta arms re-pin from a FRESH canonical CSV at every new battery pre-registration (ratings
move daily; audit limit 2). Between batteries the field is FROZEN — no mid-battery swaps.

— ai-scientist-7, 2026-07-13, per rpo #3327 §5 and field audit #3330
