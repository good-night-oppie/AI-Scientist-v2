# Evidence — seed baseline + BFTS wiring (2026-07-10)

## What was learned
- cabt engine (kaggle-environments pip pkg) ships the full local PTCG simulator:
  legal-options agent contract, card DB via AllCard/AllAttack ctypes exports, and an
  (unbound) SearchBegin/Step/End determinized-lookahead API — future lever.
- Trace-driven post-mortem found the baseline's key blunder: stadium ABILITY scored
  above ATTACK benched a charged 200-dmg attacker instead of taking a lethal KO.
  Fix (lethal-attack detection at top priority + ability demotion) moved winrate vs
  'first' from 0.35 → ~0.54.
- Gemini-compatible endpoints reject OpenAI's nonstandard 'strict' field inside tool
  schemas (HTTP 400) — AI-Scientist metric extraction silently degrades to zero
  metrics; fixed by stripping at FunctionSpec boundary.
- AI-Scientist's launch-end psutil sweep kills ANY process with 'python' in cmdline
  — lethal on a shared fleet host; now env-gated (default off).

## What changed (commits)
- ready-player-one-ptcg feat/ptcg-agent: 1a75620 (agent pkg + harnesses + submission
  builder), 8570f2a (LANE_STATE.md)
- AI-Scientist-v2 ptcg-run: 68fa1cd (task wiring + safety patches), 2nd commit
  (strict-field fix)

## Supporting evidence
- Seed eval (80 games/opponent, seat-alternated, this host, .venv python):
  mean_winrate 0.719 — vs_random 0.90, vs_first ~0.54; experiment_data.npy +
  winrate_curves.png reproduced standalone in /tmp/ptcg-seed-test.
- Submission bundle self-play validation: statuses ['DONE','DONE'] via
  scripts/build_submission.py.
- Smoke run #2 (b7xffdw0i): 0 'Error parsing metrics' post-fix; tool_calls flowing.

## What should happen next
- Stage-1 pass → full-scale BFTS run → harvest best_solution → submit (pending
  Kaggle creds, esc-ced2411dbe).

## Addendum 2026-07-10 ~21:2xZ — Kaggle submission VALIDATED (completion-bar item)
- v1 (ref 54539022): ERROR — runner execs main.py without __file__ (reproduced
  locally via file-path agent loading; NameError at import). 
- Fix e629707: self-contained main.py (policy+DECK inline, last-callable contract),
  build now validates through the runner's real load path.
- v1.1 (ref 54539166): SubmissionStatus.COMPLETE, publicScore 600.0 (mu_0), in
  matchmaking pool. Verify: `kaggle competitions submissions -c pokemon-tcg-ai-battle -v`.
- Ladder context: top score ~1325 (2026-07-10). Rating trajectory = ongoing evidence.
