# Evidence — PCMM Stage-B screen results (2026-07-12, ai-scientist-5 coordinator)

Both clean-room candidates were run through the frozen immutable phase runner
(`run_pcmm_portfolio.py`, digest `7736b873…` verified; config digest
`d0dc6c305a49…`; all five archive hashes re-verified PASS pre-launch) from
read-only worktree @ merged head `fca4dc4`, N=40/arm seat-balanced, detached +
sequential, uncontaminated CPU (search/harvester terminal before launch).

## VERDICT: BOTH CANDIDATES FAIL THE SCREEN — no probe candidacy earned

### metamon_router_r1 (run 0f6f211e7a604cffb7cfd63134501021, done 05:50:47Z)
- gates_pass: **False** — macro 0.5583 (≥0.55 OK) but **worst arm 0.375 < min_arm 0.40**
- vs live_s14_evolved_deck_2c1368bc03: **15-25 (0.375)** [0.242,0.530] spg 0.349 (seat1 0.25)
- vs live_s14_reference:                25-15 (0.625) [0.470,0.758] spg 0.295
- vs s18_active_reference:              27-13 (0.675) [0.520,0.799] spg 1.695
- candidate search calls 0 (router predeclares search optional — allowed)

### pokechamp_macro_minimax_r1 (run 04adafa0ba4b4e4dadc4e822b7f31a0d, done 05:53:04Z)
- gates_pass: **False** — **macro 0.4667 < 0.55**
- vs live_s14_evolved_deck_2c1368bc03: 18-22 (0.450) [0.307,0.602] spg 0.498, search 976 calls
- vs live_s14_reference:                18-22 (0.450) [0.307,0.602] spg 0.369, search 742 calls
- vs s18_active_reference:              20-20 (0.500) [0.352,0.648] spg 2.369, search 1130 calls
- search genuinely active (calls ≫ games) — the candidate loses WITH working search

## Interpretation (coordinator)
1. The mixed-field gate prevented a fourth overfit promotion: metamon router looks
   strong vs reference-deck arms (0.625/0.675) but collapses vs the evolved deck
   (0.375). A single-arm gate would have promoted it.
2. Working search (pokechamp, s18) keeps losing to heuristic-effective play —
   third independent confirmation that search is not the lever on this engine.
3. The evolved 2c1368bc03 deck arm is the hardest arm for BOTH candidates —
   corroborates deck strength as the live lever, consistent with the deck-search
   terminal result (46 PROMOTABLE, best 58f62b5135 lo .605).
4. Zero invalids, spg within 3.0 budget in all six arms — runs are clean evidence.

## Raw artifacts (immutable, receipt-bound)
- `ready-player-one-ptcg-pcmm-r1/runs/pcmm_r1/screen_metamon_r1/{summary,manifest,rows,config.snapshot}.json` + arms/
- `ready-player-one-ptcg-pcmm-r1/runs/pcmm_r1/screen_pokechamp_r1/…` (same layout)

## Consequence for M1
PCMM candidate stream: CLOSED at screen (negative result, honestly measured).
The deck stream is the sole remaining promotion path → rpo decisions pending:
grant transfer a41403b867 (lo .579) → 58f62b5135 (lo .605)?, reviews #18-#20.
No submission under hold #2872.
