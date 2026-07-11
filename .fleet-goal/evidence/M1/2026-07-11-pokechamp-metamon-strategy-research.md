# PokeChamp + MetaMon strategy transfer research

Date: 2026-07-11 UTC
Goal thread: `019f52f2-7d79-7ad0-a1c6-d02bdcd3199e`
Status: research complete; deterministic implementation active; game execution preflight-gated
External promotion status: **HOLD** — no further Kaggle submission without new
independent confirm+reconfirm evidence and fresh `rpo` review (A2A `#2872`).

## 1. Problem brief

Identify the strongest released agents in the user's starred PokeChamp and MetaMon
repositories, determine which mechanisms could improve the Pokémon TCG/CABT Kaggle
agent, and define an evidence-gated transfer plan. The goal is not to make a
Pokémon Showdown model run against a different game API. It is to distill the
general decision architecture into a small, legal, CPU-deployable PTCG policy.

Questions:

1. Which exact public agents/checkpoints are strongest in each repository?
2. Which claims are supported by code and evaluation evidence?
3. Which parts transfer to our dynamic `select.option` action space?
4. What is the smallest offline experiment that addresses the observed ladder
   generalization failure without weakening the promotion hold?

Constraints:

- Public professional sources only; no private-person profiling.
- Read-only inspection of upstream repositories. No upstream code was vendored.
- No provider, GPU, checkpoint execution, new battle experiment, or Kaggle submit.
- The running inherited deck search/harvester remains undisturbed.
- PokeChamp's repository license adds a Japan-use prohibition, so this plan is a
  clean conceptual transfer, not a code transplant.
- MetaMon checkpoints are PyTorch pickle files. They were not downloaded or
  loaded; checkpoint deserialization would require a separate trust/sandbox review.

## 2. Research plan

1. Resolve the repositories from the authenticated GitHub account's starred list.
2. Pin current upstream commits and inspect README, implementation, configs,
   licenses, papers, and public checkpoint manifests.
3. Identify the strongest general, specialist, and ensemble agents separately.
4. Compare their observation/action/search assumptions with the CABT engine.
5. Triangulate transferable claims across both upstream families and our own
   local ladder evidence.
6. Produce a PTCG-native architecture and staged offline evaluation proposal.

## 3. Research ledger

| Time (UTC) | Action | Result |
|---|---|---|
| 21:39 | Read parent A2A `#2872` | `54585744` scored 464.5 vs s14 580.7; condition 3 binds; mixed-field/counter-deck overfit is the working concern. |
| 21:42 | Queried authenticated `gh api --paginate user/starred` | Found exact starred repos `sethkarten/pokechamp` and `UT-Austin-RPL/metamon`. |
| 21:43 | Shallow-cloned both repos into `/tmp` | Pinned PokeChamp `0f84c460319ebe733f8c3028e58a2a5452c60d85`; MetaMon `0a00a759c9a4382a2877088d828302ec294a05a5`. |
| 21:44-21:48 | Inspected source, configs, licenses, papers, and public model manifests | Identified the flagship agents, algorithms, action/observation incompatibilities, licensing constraint, and checkpoint format/size. |
| 21:49 | Audited CABT policy/search seams and live search | Current policy is a static option scorer; s14 search is fallback-only; s18 uses active two-select search and a same-deck opponent prior but lost its powered comparison. Deck search and harvester remained live. |
| 21:50 | Independent transfer audit | Confirmed concepts-only transfer and ranked portfolio evaluation above policy changes. No files/games/submissions changed by the auditor. |
| 21:54 | Audited PokeChamp history instead of assuming current HEAD is the paper agent | Pinned the nearest public paper-release commit `b614d787...` (`pokechamp version 1.0.0`). It contains true max-min aggregation. Current v1.2's default optimized path uses max over opponent branches and references undefined logging variables before its fallback. |

### Source table

| ID | Source | Pinned evidence | Use |
|---|---|---|---|
| S1 | https://github.com/sethkarten/pokechamp/commit/b614d787cce9e1761144f49c268c6da40ba7c410 | nearest public paper release, `pokechamp version 1.0.0` | Evidence-backed flagship wiring and genuine max-min search. The repo does not prove this is the exact SHA used for the reported matches. |
| S1b | https://github.com/sethkarten/pokechamp/tree/0f84c460319ebe733f8c3028e58a2a5452c60d85 | current v1.2 commit | Current README/license and a later optimized-search path that should not be copied as the paper algorithm. |
| S2 | https://proceedings.mlr.press/v267/karten25a.html | ICML 2025 paper | Evaluated PokeChamp method/results and ablations/limitations. |
| S3 | https://github.com/UT-Austin-RPL/metamon | commit `0a00a759c9a4382a2877088d828302ec294a05a5` | Current public agent ranking, configs, ensemble router, action/observation spaces. |
| S4 | https://arxiv.org/abs/2504.04395 | v2, 2025-07-30 | Offline-RL, sequence, self-play, long-horizon and distribution-shift evidence. |
| S5 | https://huggingface.co/jakegrigsby/metamon/tree/main | model revision visible as `ac8e88e`; Kakuna folder revision `717dcf8` | Checkpoint availability, format, licensing, and sizes. |
| S6 | `.fleet-goal/evidence/M1/2026-07-11-kaggle-probe-54585744.md` | local immutable evidence | Our same-baseline local edge failed to carry to the mixed ladder. |
| S7 | `/home/admin/gh/ready-player-one-ptcg/artifacts/weco_search_s18_oppmodel.py` | local source | Current same-deck opponent prior and active-search implementation. |
| S8 | `/home/admin/gh/ready-player-one-ptcg/src/ready_player_one/ptcg/policy.py` | local source | Dynamic legal option scoring and integration seam. |

### Evidence table

| Claim | Evidence | Confidence / qualification |
|---|---|---|
| PokeChamp's strongest evaluated flagship is the GPT-4o-backed `pokechamp` minimax agent. | S1's evaluation config is `('gpt-4o', 'pokechamp', 'minimax')`; S2 reports 76% vs the strongest prior LLM bot and 84% vs the rule bot. | High for the paper configuration. S1 is the nearest public paper-code pin, not proof of the private experiment SHA; its reproduction script defaults to only one battle per pairing. |
| PokeChamp's transferable core is candidate-pruned action generation + opponent action modeling + depth-limited value estimation around a simulator. | S2 defines those three LLM-replaced minimax modules; paper-release S1 implements tool proposals, opponent proposals, leaf scoring, and true min-over-opponent then max-over-player selection. | High. The Showdown simulator and tactics are not transferable. Current S1b's default optimized path is not equivalent: it takes max over opponent branches and appears to fall back after an undefined-variable logging error. |
| MetaMon's strongest general public single model is Kakuna; TaurosV0 is its strongest standalone Gen1 specialist; Tauros-family ensembling has reached #1. | S3 README and `pretrained.py` explicitly identify Kakuna and TaurosV0; S5 exposes their checkpoints; S3's ensemble classes/README record the #1 milestone. | High as an upstream self-report. Different formats make Kakuna and Tauros non-comparable as one universal ranking. |
| Diverse exploratory self-play and opponent/team coverage are more robust than narrow self-play against one policy. | S4 reports that self-play against SynRL-V1 improved against itself but transferred inconsistently to humans, while diverse model/variety data produced stronger successors; S6 independently shows 457/800 against one frozen local matchup followed by 464.5 vs s14 580.7 on the mixed ladder. | High for the direction; exact data recipe must be re-derived for PTCG. |
| Long-horizon value and selective search are more promising than always-on shallow enumeration. | S4 reports higher win rate from the long-horizon `gamma=.999` head; S2 uses depth-limited leaf value and routes obvious tactical calculations separately; local S7's active shallow search lost 130-170 to the heuristic-effective s14 baseline. | Medium-high. CABT's sequential selections require macro-turn rollout, not Showdown's simultaneous-turn minimax. |
| Raw MetaMon/PokeChamp policies cannot be dropped into the CABT agent. | S3 uses fixed 13-way move/switch actions and Showdown entity features; S8 consumes a variable legal `select.option` list spanning play/attach/evolve/ability/attack/card/count/yes-no decisions. Both upstreams use different transition engines. | Certain; this is a direct interface mismatch. |
| A guarded anchor/proposer/judge router is a plausible CPU-deployable transfer. | S3's public ensemble uses strength priors, disagreement, shortlist proposals, actor/critic judging, and an anchor guard; S2 uses tool+LLM candidate proposals followed by minimax/value judging. | Medium-high architecture inference, not yet a PTCG result. It requires an approved experiment. |

## 4. Findings and decision

### Strongest upstream agents to learn from

1. **PokeChamp flagship:** paper-release `pokechamp` with the `minimax` algorithm
   and GPT-4o in the published evaluation. Learn from commit `b614d787...`, where
   action values take the minimum over opponent replies before the player argmax.
   The key reusable idea is not the LLM call. It is the decomposition into action
   proposals, opponent proposals, a world-model transition, and a leaf-value judge.
   Do not treat current v1.2's default optimized path as the proven implementation.
2. **MetaMon general model:** `Kakuna`, 142M parameters, default checkpoint 34.
   It is the best general public model in the current repo and was fine-tuned on
   higher-temperature exploratory self-play with reduced weighting on weaker
   human replay data.
3. **MetaMon specialist/deployment:** `TaurosV0`, default checkpoint 62, is the
   best standalone Gen1 specialist, and `TaurosEnsemble` has the strongest
   historical upstream claim. The documented `Exeggcute` preset is broken at the
   pinned commit because it references unregistered `TaurosV5`; the safest
   currently coherent public ensemble alias is Kakuna-family `PastaMittens`.

The raw weights are not useful to the Kaggle package: Kakuna's checkpoints are
about 572 MB each and Tauros checkpoints about 248 MB each, use PyTorch pickle,
encode Showdown observations, and output Showdown action IDs. PokeChamp's best
paper agent requires an external LLM and a Showdown simulator. The correct
deliverable is therefore a clean PTCG-native distillation.

### Decision: propose `PCMM-R1` (PokeChamp/MetaMon Router v1)

The first new policy experiment should be a small deterministic hybrid:

1. **Legal mask:** retain CABT's supplied `select.option` list as the complete
   legal action set. Never map through Showdown action IDs.
2. **Grouped visible state:** extract active/bench entities, visible hand/discard,
   deck/prize counts, energies/evolution, immediate KO/prize threats, and revealed
   opponent cards. Hidden features must be sampled, never read.
3. **Anchor + diverse proposers:** keep the frozen s14-effective heuristic as the
   anchor; add distinct tactical, resource/tempo, and survival scorers. Always
   retain the anchor action and union the proposers' top candidates.
4. **Posterior opponent hypotheses:** replace s18's `Counter(DECK)` same-deck
   assumption with a mixture of legal deck hypotheses updated only by visible
   opponent cards. Sample hand/prize/deck without replacement.
5. **Macro-turn rollout:** evaluate a root option through its follow-up selection
   chain, the remainder of the current turn, and candidate opponent turns. A raw
   `search_step` is a UI selection, not a game ply; fixed two-select lookahead is
   not PokeChamp-style minimax.
6. **Delta leaf value:** score terminal result first, then prize delta, KO swing,
   active survival, attack readiness, energy/evolution progress, bench continuity,
   and resource flow. Do not reward passive hand hoarding.
7. **Guarded override:** use cross-hypothesis mean/lower-tail value plus proposer
   support and disagreement. Override the anchor only with a calibrated robust
   margin; fall back on any timeout/error.
8. **Anti-loop state:** penalize repeated non-progress state/action signatures,
   borrowing the lesson from both PokeChamp's documented excessive-switching
   weakness and MetaMon's ensemble stall tracker.

The highest-priority change is the **evaluation portfolio**, not the router. Any
candidate optimized only against s14 risks repeating the current counter-deck
failure.

## 5. Approval-gated execution plan

No stage below authorizes a Kaggle submission.

### Stage A — deterministic harness work (no games)

- Add portfolio schema around `scripts/eval_search_head2head.py:run` and stratified
  result aggregation.
- Add unit fixtures for legal indices/counts, option permutation, visible-only
  opponent features, posterior normalization/card accounting, terminal-value
  dominance, anchor retention, and deterministic seeds.
- Add a fake search API test proving correct child IDs, all-state release, macro-turn
  stopping, deadline fallback, and no claim of active search on fallback.
- Counterfactually replay existing trace observations through candidate scorers;
  no engine games.

Completed evidence substrate: implementation commit `0ed92d6` freezes three
canonical source+deck-distinct arms, rejects stale module reuse and seat collapse,
and gates on raw per-arm statistics rather than pooled or rounded summaries. The
remaining Stage-A work is the pure router/macro-turn policy and fake-API tests.

### Stage B — one bounded CPU experiment (requires explicit AI-Scientist approval)

Portfolio arms should include distinct policy and deck families, not repeated
seeds of the same matchup. Proposed rungs:

1. N=40 per arm, seat-balanced, zero invalid/forfeit games.
2. Only a screen survivor may advance to a separately bounded N=400 confirm and
   fresh N=400 reconfirm; preserve latency, search/fallback, override, branch, and
   opponent-hypothesis diagnostics.
3. Held-out portfolio check by strategy hash and policy/deck family. Rank on the worst-arm
   or stratified Wilson lower bound, not only pooled point win rate.

Promotion still requires the parent condition: both fresh independent s14 confirm
and reconfirm must have Wilson lower bound >= 0.50, followed by fresh `rpo` review.

### Stage C — optional learning model (separate later approval)

Only after trajectory coverage exists, fit a compact linear/table delta-value
model and export constants. Do not package PyTorch, upstream checkpoints, an LLM
runtime, or untrusted pickle artifacts.

## 6. Open questions

1. Do competition rules permit public replay/episode aggregation for anonymous
   deck-prior statistics? If unclear, use only local generated decks.
2. The inherited deck search is still running. Its final winner should be audited
   before choosing portfolio deck hypotheses, but it does not unblock Stage A.
