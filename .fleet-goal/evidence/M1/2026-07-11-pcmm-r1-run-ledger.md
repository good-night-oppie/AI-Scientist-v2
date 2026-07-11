# AI-Scientist run ledger — PCMM-R1

status: DETERMINISTIC STAGE A COMPLETE; POLICY IMPLEMENTATION IN PROGRESS; GAME SCREEN PENDING FINAL PREFLIGHT
approval evidence: user said `go with $ai-scientist and $weco and $andrej-karpathy-perspective` on 2026-07-11 UTC
goal thread: `019f52f2-7d79-7ad0-a1c6-d02bdcd3199e`
AI-Scientist repo: `/home/admin/gh/AI-Scientist-v2` (`ptcg-run`)
implementation worktree: `/home/admin/gh/ready-player-one-ptcg-pcmm-r1` (`feat/ptcg-pcmm-r1`)
implementation base: `5d89227f8d44f37b53fe6b4eafbf85e45c8b074d`
mode: deterministic local harness + Weco Observe
idea: `pcmm_r1` — PokeChamp max-min proposals plus MetaMon guarded ensemble and portfolio evaluation
provider/models: none
provider budget: USD 0; Weco Optimize credits must not be consumed
stage-A wall clock: <= 10 minutes per command; standard-library tests only
proposed stage-B screen: N=40 per frozen portfolio arm, seat-balanced; hard wall clock <= 15 minutes total
GPU policy: disabled/not used
network policy: no network during tests or game evaluation
filesystem policy: isolated git worktree; exact-path edits only; no writes to the live search worktree
external policy: no Kaggle submission, no leaderboard probe, no upstream write
stop criteria: any invalid/forfeit, search exception, artifact mismatch, p95/timeout breach, live producer interference, or missing reproducibility metadata
disclosure: distinguish upstream self-reports, local deterministic tests, local games, and external ladder evidence

## Required approvals

- [x] Provider/API cost: not applicable; no provider call and USD 0.
- [x] Deterministic Stage-A code execution: authorized by the user's explicit `go`; limited to isolated standard-library checks.
- [x] GPU budget: no GPU use.
- [x] Data/network/filesystem policy: public pinned sources, no network during execution, isolated worktree.
- [x] Stage-B arm list frozen in `configs/pcmm_r1_portfolio.json`; re-verify bundle hashes and record the final candidate hash immediately before games.
- [ ] Any later generated-code/provider/GPU AI-Scientist or Weco Optimize run requires a new explicit approval.

## Preflight evidence

`ai_scientist_operator.py preflight --repo /home/admin/gh/AI-Scientist-v2` at
2026-07-11 UTC reported the expected repo/config/launcher surfaces. The repo is
dirty with nine pre-existing/unrelated entries; work is therefore isolated. TeX
tools and provider credentials are absent, which is acceptable because this run
does not perform ideation, writeup, review, provider, or GPU stages. The launcher
contains broad cleanup/termination logic, so `launch_scientist_bfts.py` will not be
used for this experiment.

Weco is authenticated with 62.92 credits, but this lineage stays in Observe mode.
Only successful experiments with a real metric may be logged to Observe run
`7393d6ae-46a4-4b22-9cb5-a48abbab3d41`.

## Frozen evidence and correctness gates

- Research design:
  `.fleet-goal/evidence/M1/2026-07-11-pokechamp-metamon-strategy-research.md`
- PokeChamp paper-code source: `b614d787cce9e1761144f49c268c6da40ba7c410`
- MetaMon source: `0a00a759c9a4382a2877088d828302ec294a05a5`
- Frozen ladder champion remains s14.
- Parent A2A `#2872` no-submit condition remains binding.
- Portfolio aggregate must never use pooled/micro win rate as a promotion gate.
- Correctness must come from frozen runner results/tests, never from candidate
  self-reference.

## Stage-A artifact plan

1. A standard-library portfolio result validator/aggregator with exact arm,
   candidate, baseline, game-count, search-activity, latency, and zero-invalid
   bindings.
2. Deterministic tests showing a strong pooled result still fails when one arm is
   weak, equality at the search-call boundary is inactive, and reordered input
   normalizes identically.
3. A compact PCMM-R1 design seam; no copied upstream code or weights.
4. Test transcript and exact commit hash.

## Stage-A result

Completed in the isolated implementation worktree and committed as
`0ed92d62aedc6fd30ad24b529ee68bc7ac7b9dc5` (`test(ptcg): harden mixed-field
evidence portfolio`). No games, provider calls, network calls, model execution,
GPU work, or external submissions occurred.

The resulting gate:

- binds exact tar SHA-256 and a metadata-independent canonical source+deck
  fingerprint;
- requires three semantically distinct arms and unique run IDs;
- isolates and purges each in-process bundle namespace so later arms cannot run
  cached first-arm code;
- validates seat-balanced outcomes, raw rather than rounded win-rate/Wilson
  boundaries, zero invalids, latency, and optional search activity;
- fails pathological seat asymmetry, pooled wins that hide a weak arm, artifact
  mutation, duplicate strategies, and confirm/reconfirm pooling.

Verification:

- 17/17 portfolio aggregation tests passed under system Python.
- 4/4 no-game runner producer/isolation tests passed using the existing PTCG
  virtualenv with environment creation mocked.
- 4/4 inherited deck-harvest validation tests passed.
- `py_compile`, Ruff check/format, JSON validation, and `git diff --check` passed.
- Independent evidence audit returned `COMMIT verdict: yes` with no blockers.

Frozen mixed field (`configs/pcmm_r1_portfolio.json`):

1. live s14 heuristic-effective policy + reference deck;
2. mechanically active s18 search + reference deck;
3. live s14 heuristic-effective policy + evolved `2c1368bc03` deck.

All three archive and canonical strategy hashes were re-read from disk and are
distinct. The router candidate may predeclare search as optional; a macro-minimax
candidate must predeclare active search. Zero calls are preserved as evidence,
not treated as a runner crash.

## Stage-B artifact plan

Before any game screen, re-verify the manifest, then record the immutable candidate
bundle archive/strategy hashes, selected candidate mode, game count, seat gates,
timeout, CPU load, and output paths. Preserve each per-arm raw JSON and a normalized
portfolio summary. A confirm and reconfirm must remain separate datasets and
separate decisions.
