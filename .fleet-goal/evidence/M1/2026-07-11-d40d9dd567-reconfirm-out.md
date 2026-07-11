# Independent reconfirm rejection — `d40d9dd567`

_Verified: 2026-07-11T21:21Z_

## Result

`d40d9dd567` looked stronger than the current candidate at confirm, but failed the
mandatory fresh reconfirm:

| rung | W-L | win rate | Wilson interval | verdict |
|---|---:|---:|---:|---|
| N=40 screen | 25-15 | 0.6250 | `[0.470, 0.758]` | promoted |
| N=160 mid | 90-70 | 0.5625 | `[0.485, 0.637]` | promoted |
| N=400 confirm | 233-167 | 0.5825 | `[0.534, 0.630]` | confirm pass |
| N=400 independent reconfirm | 205-195 | 0.5125 | `[0.464, 0.561]` | **reconfirm out** |

Combined confirm plus reconfirm: `438/800 = 0.5475`. The independent reconfirm
Wilson lower bound `0.464` is below the required `0.50`, so this deck is not
promotable despite the stronger initial confirm.

## Identity

- Parent candidate: `2c1368bc03`
- Mutations: `count_shift:-723+721`, `count_shift:-1227+1145`
- Deck CSV: `/home/admin/gh/ready-player-one-ptcg/runs/deck_search/decks/d40d9dd567.csv`
- Deck SHA-256: `4a11116cf46d76caf73ef88674819a83572883e437fcb4ac287ad07b18a51ef6`
- Saved evals:
  `/home/admin/gh/ready-player-one-ptcg/runs/deck_search/evals/d40d9dd567_r{0,1,2,3}_*.json`
- All four rungs recorded `invalid=0`.

## Weco

Logged as completed step `2`, parent step `1`, in Weco Observe run
`7393d6ae-46a4-4b22-9cb5-a48abbab3d41`. Its combined metric `0.5475` remains
below step `1` (`2c1368bc03`, `0.57125`).

## Decision

Reject `d40d9dd567` for promotion. Keep `2c1368bc03` as the only fully
reconfirmed candidate while the bounded search continues.
