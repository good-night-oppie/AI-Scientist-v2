# BFTS relaunch run ledger — 2026-07-11 (ai-scientist-2)

**Repo/branch:** /home/admin/gh/AI-Scientist-v2 @ ptcg-run
**Phase:** x-roocky taxonomy #4 (bounded BFTS experiment), rerun after b9faasveg died
**Generated code executed:** YES (LLM writes Python policies; runs cabt games via make("cabt"))

## Approval basis
- Established lane mandate (Eddie: "drive it THROUGH the AI-Scientist-v2 BFTS pipeline")
  + user standing policy to continue autonomously. Predecessor was running this exact
  full-run config (commit 79441bb); this relaunch continues it after a session-retirement kill.

## Budget / cost
- **Compute: LOCAL gemini proxy only (127.0.0.1:8319) — ZERO paid API.** No GPU.
- Config bounds (bfts_config.yaml): num_workers 3, exec timeout 3600s/node,
  stages 20/12/12/18 iters, num_drafts 3, num_seeds 3, generate_report False.
- Wall-clock: ~3h to reach stage 4 last time; full run several hours. Detached, so it
  survives session handoffs.

## Safety gates applied
- **AI_SCIENTIST_BROAD_KILL never set** (explicitly `unset`) — the launcher's psutil
  sweep would otherwise kill fleet processes. rmtree guard patch in place.
- summary/select_node pinned to gemini-3-flash + --model_agg_plots gemini-3-flash
  (avoids gpt-4o default → proxy 502 → infinite backoff).
- No `claude-*` model names in config (bedrock-only backend NotImplementedError trap).
- Detached via `setsid nohup` → own session; session retirement can't SIGHUP it.
  Log: /home/admin/gh/AI-Scientist-v2/bfts_fullrun2.log
- Residual risk: runs on the shared fleet host (not an isolated VM). Mitigated by the
  two guards above; generated code is bounded to cabt game-play + experiment-dir writes.

## Idea change this run (vs the dead run)
- Added HARD DEPLOYMENT & DEPENDENCY CONSTRAINT to idea.json: policy must be
  stdlib+numpy only, NO torch/NN/learned weights, self-contained choose/agent+DECK,
  save deployable source as best_solution. Root-cause fix for the torch-drift that made
  the prior run's stage 1/2/3 bests undeployable/unverifiable. idea-check verdict OK.

## Human-verified vs automated
- Champion remains s14 (weco search, fresh-seed 0.7917, Kaggle 600.0 validated) — BFTS
  (heuristic-only in this repo, no vendored good-libcg) is NOT expected to beat it; value
  is methodology completion + a deployable heuristic fallback.

## Next safe action
- Monitor bfts_fullrun2.log across handoffs; on completion run operator `artifacts`
  audit, then fresh-seed verify the best heuristic vs s14 before any second Kaggle slot.
