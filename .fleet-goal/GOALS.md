# GOALS — ai-scientist child fleet-agent

status: ACTIVE — child of rpo
goal_thread_id: (UNSET by Eddie 2026-07-12 via /goal; former 019f52f2-7d79-7ad0-a1c6-d02bdcd3199e.
  Goal anchored on THIS .fleet-goal/ + A2A intents + the ai-scientist-6 session
  Monitor loop. Eddie confirmed continuation in-session 2026-07-12 ~11:4xZ:
  "同意，开始干" — M2 approved to execute.)
inherited_from: ai-scientist-5 / Claude session 6adb5ba8-e934-46e3-8270-9f17b96885ba
parent_agent: rpo
parent_cwd: /home/admin/gh/ready-player-one
tree_level: 3
children: [sctst-aide]  # level-4 leaf, corpus-expansion worker (Eddie order + height-4 decree #3158, 2026-07-12)
may_create_child_fleet_agents: true (LIMITED — height-4 decree #3158/#3159: max 2 durable level-4 leaf children; sctst-aide is #1; each requires an Eddie order or parent-approval-gated capsule)
completion_requires_parent_approval: true
operating_mode: COORDINATOR (orch-proj doctrine; Eddie directive 2026-07-12) —
  no direct coding/editing by this agent; implementation delegated to mroute
  execution tier (COLLAB_CAPSULE for cross-lineage writes). Running frozen,
  merged, immutable evaluators and polling/monitoring remain coordinator ops.

## Guardrails

- ai-scientist is level 3; per height-4 decree #3158 it may run <=2 durable level-4 LEAF children (current: sctst-aide). Children cannot create children.
- ai-scientist may use ad-hoc/one-time subagents for bounded work, but those do not become tree nodes.
- ai-scientist completion is not final until rpo reviews and approves evidence.
- Keep this `.fleet-goal/` cross-linked with rpo's `.fleet-goal/`.

## Inherited objective

Conquer Kaggle `pokemon-tcg-ai-battle` through the AI-Scientist-v2
research/evolution workflow: safely continue the detached legal-deck search,
harvest reproducible improvements over the frozen live-s14 baseline, produce a
runner-faithful submission bundle, and coordinate any ladder-probe promotion with
parent `rpo`.

The active optimization metric is head-to-head win rate versus live-s14, tracked
in Weco Observe run `7393d6ae-46a4-4b22-9cb5-a48abbab3d41`. The current fully
reconfirmed candidate is `2c1368bc03`; the detached search and harvester may
replace it only with stronger fully reconfirmed evidence.

## M2 — Imitation joint intervention: fixed-policy × mined-deck [ACTIVE]

Approved by Eddie in-session 2026-07-12 ("同意，开始干") on the verified
root-cause analysis (evidence/M1/2026-07-12-plateau-root-cause-analysis.md:
31 agents, 24 adversarial verdicts). Supersedes M1's "deck is the active
lever" premise — deck-transfer was twice n400-falsified; the verified levers
are the policy bugs + MAIN-level scheduling, deployed JOINTLY with a mined
meta deck (deck↔policy co-adaptation is the system-level difference).

Outcome: a candidate agent (bug-fixed / retuned / imitation-distilled policy ×
mined 1180-tier deck) that passes n400 h2h vs frozen s14 AND self-play vs >=2
mined meta decks, then ONE Kaggle probe slot with Eddie/rpo notice; a per-poll
delta < +100 pts is recorded as UNRESOLVED (rating resolution limit), not failed.

Execution pipeline (mroute, capsules in .fleet-goal/capsules/):
- A1 policy.py bug patches (trimmed scope: bug1 DECK half, bug3, bug4
  area-aware) + regression tests + bug-fix-only h2h gate  [IN PROGRESS]
- A2 build_imitation_dataset.py (t+1 alignment per bus #3098 invariants)
- B  MAIN_SCORES reorder per verified verdicts (NO BENCH_TARGET change;
  ability 25→85 w/ deny-list; item>supporter; conditional retreat;
  bench-preferring attach w/ target quality)
- C  policy_imitation.py distilled from A2 dataset; 3-way ablation A1 / A1+B / C
- ptcg-mh-surrogate-adapter: proposer forced through surrogate (static
  pre-screen, evidence cards, k>1 n600/alpha-spending, racing arms)
- ptcg-deck-search-uncage: remove/parameterize deck_search.py is_legal floors
  (Kyogre>=2, {W}energy>=15) that exclude all 14 meta decks — prerequisite for
  any future deck-mutation operator in the mh loop.

Evidence required: per-phase gate results in evidence/M1/ (ablation table),
frontier.jsonl evidence cards once the adapter lands, probe decision memo
before any slot consumption. Champion s14 stays live until full reconfirm.

## M1 — Resolve ladder generalization failure and harvest bounded search [CLOSED 2026-07-12]

Closing outcome: bounded deck search harvested (2,857 decks, 46 local
PROMOTABLE — all within the is_legal cage, max Jaccard 0.11 to meta decks);
probe 54585744 (548.1 < s14 607.6) falsified the local→ladder link; PCMM
3-arm mixed-field gate delivered (commit 0ed92d6); deck-transfer twice
n400-falsified; root cause of the 607.6 plateau verified and published
(evidence/M1/2026-07-12-plateau-root-cause-analysis.md). The deck-only lever
is DEAD; M2 carries the verified successor plan. Original M1 text preserved
below for the record.

Outcome: deliver to `rpo` (a) the final best legal deck from the already-running
bounded search and (b) a clean-room PTCG-native agent candidate evaluated against
a strategy/deck-diverse local portfolio, with runner-faithful artifacts and an
honest no-submit/promotion decision.

Scope:
- In: monitor/harvest the detached deck search; audit saved metrics and legality;
  distill public PokeChamp/MetaMon mechanisms into deterministic PTCG-native
  candidates; evaluate against a frozen mixed policy/deck portfolio; track only
  successful metric-bearing experiments in Weco; preserve s14 until a
  parent-approved ladder probe.
- Out: auto-submitting to Kaggle; restarting unconstrained BFTS; reviving the
  exhausted search-tuning lever without new evidence; creating child fleet-agents.

Decisions:
- Frozen live-s14 policy and engine are the baseline; the deck is the active lever.
- A local win is a ladder-probe candidate, not proof of leaderboard improvement.
- Final child completion requires explicit `rpo` review of completion evidence. [ANNOTATED 2026-07-12 per rpo #3203: the PROMOTION/submission half is SUPERSEDED by Eddie authorization #3084 (notice-at-submission model, rpo objection window, silence=proceed) — this line no longer gates probes.]
- [M1-HISTORICAL, SUPERSEDED-BY-#3084 for the probe path] Parent rpo granted one-probe approval in A2A shared-log `#2852`; submission
  `54585744` used that single slot and completed with initial public score `600.0`.
  Its early follow-up score moved to `464.5`, below s14 `580.7`, activating the
  parent hold: no further deck submission without new reconfirmed evidence and a
  fresh rpo review.
- The ladder contradiction makes single-opponent optimization insufficient.
  PCMM-R1 therefore gates candidates against three canonical source+deck-distinct
  arms before any confirm/reconfirm claim. Evidence gate commit: `0ed92d6`.
- Clean-room transfer only: no upstream code, model weights, LLM runtime, provider,
  GPU, or untrusted checkpoint enters the Kaggle package.

Blockers:
- No infrastructure blocker.
- Final harvest waits on the bounded search; search/harvester remain healthy.
- [STRUCK 2026-07-12 per rpo #3203: the former "parent hold #2872" line was doubly stale — #2872 was an unrelated mail; the real hold was #2852 cond(3), lifted by Eddie #3084. No submission hold exists; the probe path runs notice-at-submission per #3084.]

Evidence required:
- PROGRESS.md updated with What's done / What's next / Any blockers.
- Evidence artifacts under `.fleet-goal/evidence/M1/`.
- Saved confirm and independent reconfirm results with zero invalid games and
  Wilson lower bound at least `0.50` in both N=400 batches.
- Legal 60-card candidate CSV plus stable SHA-256.
- Runner-faithful bundle inventory, stable SHA-256, and a persisted raw validation
  transcript showing load success, agent execution, zero forfeits, and an honest
  search-active classification (`calls == games` must be recorded as fallback,
  never as active search).
- Weco Observe updated with baseline and the final selected candidate.
- Mixed-field manifest with distinct archive and canonical source+deck hashes;
  raw per-arm/seat evidence; unique run IDs; no pooled promotion gate.
- ~~Pure counterfactual tests for dynamic legal options, guarded router overrides,
  macro-turn stopping, max-min order, deadline abstention, and search-state release.~~
  **[WAIVED 2026-07-12 per rpo #3202/#3204/#3217 — N/A to a negative closure.]** These six
  counterfactual tests exist to protect a PROMOTION decision for a PCMM candidate. BOTH PCMM
  candidates FAILED the Stage-B gates and were never promoted or probed — `metamon_router_r1`
  worst-arm 0.375 < 0.40 min (despite macro 0.5583); `pokechamp_macro_minimax_r1` macro
  0.4667 < 0.55 with search genuinely active. There is therefore no promotion decision for
  these tests to protect. Evidence: `evidence/M1/2026-07-12-pcmm-stageB-screen-results.md`.
  The aggregate suites (23 macro / 49 metamon / 17 portfolio / 45 runner) cover the mechanics
  and remain on record. Waiver substance accepted by rpo in #3217; this annotation is the
  repo-side record that #3217 required before M1 can be recorded COMPLETE.
- A2A completion-evidence message delivered to parent `rpo`.
- Parent rpo approval recorded before status changes to COMPLETE. [SCOPE NOTE 2026-07-12: this gates M1 completion-evidence ONLY — decoupled from submission per #3084/#3203.]
