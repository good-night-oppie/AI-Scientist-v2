# AI-Scientist run ledger — PCMM-R1

status: DETERMINISTIC STAGE A + POLICY IMPLEMENTATION + IMMUTABLE PREFLIGHT COMPLETE; GAME SCREEN DEFERRED UNTIL LIVE PRODUCER IDLE
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

## Candidate implementation and immutable packaging

Both clean-room candidate families are complete and independently reviewed:

- PokeChamp-style macro-minimax: source commit `7b6dbb2`, published via PR #13.
  It performs bounded complete-turn max-min over two deterministic hidden-zone
  priors and falls back through the frozen anchor to an emergency legal selection.
  The substrate/candidate suite passes 23 tests. Parent rpo review in A2A `#2940`
  returned `SOUND` and authorized proceeding to the recorded screen.
- MetaMon-style guarded router: source commit `e9a9484`, published via PR #14.
  It accepts only re-derived audited final-prize or conservative-retreat proposals;
  malformed attacker/opponent attachments and effectful off-reference matchups
  fail closed. The final independent review returned `COMMIT`; 49 tests pass.

No-game bundles build and import successfully:

- `runs/pcmm_r1/pokechamp_macro_minimax_r1.tar.gz`: archive SHA-256
  `e5f94f2be8d00fd66868513757efdc6b142be28a40a98b62db2467381b64a5d5`,
  canonical strategy SHA-256
  `58a3fde783c0d7581e2109ee932d926535c9e768b6f0bc818c1a1f28d9576322`.
- `runs/pcmm_r1/metamon_router_r1.tar.gz`: archive SHA-256
  `0b259d61bf1402e07bcd436777a64e065d6fa75d9c508035127d6a36e04f11c9`,
  canonical strategy SHA-256
  `3f3de70e5be2bda8b67cbd3b3050e28050b479605129adfca7eec52f79958266`.

The canonical digest covers `main.py`, `deck.csv`, and every bundled Python
source. `configs/pcmm_r1_portfolio.json` binds both candidates plus all three
baseline archives and records live ladder availability: s14 `54554870` at 580.7,
evolved deck `54585744` at 464.5, and s18 explicitly `not_submitted`.

## Publication and CI evidence

Every ready-player-one change was isolated and babysat through live GitHub CI,
zero review threads, and MERGED state into `feat/ptcg-agent`:

- PR #4 repaired the previously baseline-broken Ruff gate by checking changed
  Python files while retaining full pytest; PR #6 invokes pytest through the
  active interpreter.
- PRs #3, #5, #7-#10 published honest harvest validation, independent rejection,
  deterministic tests, approved-probe state, initial ladder evidence, and the
  post-probe hold as separate units.
- PRs #11-#14 published the PCMM evidence gate, macro substrate, macro candidate,
  and guarded MetaMon candidate.
- PR #15 persisted the s18 N=300 rejection payload (130-170, Wilson
  `[0.378,0.490]`, zero invalids); PR #16 published immutable candidate/baseline
  hashes and per-arm ladder snapshots.

## Weco Observe extension

Observe run `7393d6ae-46a4-4b22-9cb5-a48abbab3d41` now also records:

- step 3: `58c77982cd`, combined independent evidence `0.55625`;
- step 4: `89f76904cf`, combined independent evidence `0.56875`;
- step 5: `f007dbfd89`, combined `0.53375` but `reconfirm_out` after a 198-202
  independent reconfirm.

This was Observe only. No Optimize run or optimization credits were consumed;
the observed account balance remained 62.92.

## Stage-B defer and launch condition

At the 2026-07-12T00:27Z snapshot, deck-search PID `1829394` and harvester PID
`2260719` were alive, the ledger was still advancing at 1,874 rows, three evaluator
children occupied roughly three full CPU cores, and no `HARVEST_RESULT.md` existed.
Running the PCMM screen concurrently would contaminate both latency and win-rate
evidence, so no games were started.

Launch the N=40-per-arm, seat-balanced screen only after the producer and evaluator
children exit, the harvester writes its terminal result (or is explicitly audited
terminal), load settles, and all five archive/canonical hashes re-verify. Any pass
earns parent review for at most one probe; it does not displace the live champion.
The Kaggle no-submit hold remains binding. For evolved decks, in-basin PROMOTABLE
results are auto-HOLD unless independent reconfirm reaches at least 235/400 with
Wilson lower bound above 0.5367; out-of-basin distance greater than 16 remains
reviewable by rpo.
