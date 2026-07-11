# GOALS — ai-scientist child fleet-agent

status: ACTIVE — child of rpo
goal_thread_id: 019f52f2-7d79-7ad0-a1c6-d02bdcd3199e
inherited_from: ai-scientist-5 / Claude session 6adb5ba8-e934-46e3-8270-9f17b96885ba
parent_agent: rpo
parent_cwd: /home/admin/gh/ready-player-one
tree_level: 3
children: []
may_create_child_fleet_agents: false
completion_requires_parent_approval: true

## Guardrails

- ai-scientist is level 3 and cannot create durable child fleet-agents.
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

## M1 — Harvest and validate a promotable PTCG deck [ACTIVE]

Outcome: deliver to `rpo` the best legal deck that passes independent high-N
confirm and reconfirm against frozen live-s14, together with a reproducible,
runner-faithful Kaggle bundle and complete promotion evidence.

Scope:
- In: monitor/harvest the detached deck search; audit saved metrics and legality;
  track successful candidates in Weco; build and validate the submission bundle;
  preserve s14 until a parent-approved ladder probe.
- Out: auto-submitting to Kaggle; restarting unconstrained BFTS; reviving the
  exhausted search-tuning lever without new evidence; creating child fleet-agents.

Decisions:
- Frozen live-s14 policy and engine are the baseline; the deck is the active lever.
- A local win is a ladder-probe candidate, not proof of leaderboard improvement.
- Final child completion and any Kaggle promotion require explicit `rpo` approval.
- Parent rpo granted one-probe approval in A2A shared-log `#2852`; submission
  `54585744` used that single slot and completed with initial public score `600.0`.
  No chained submission is allowed without a fresh parent review.

Blockers:
- No infrastructure blocker.
- Final harvest waits on the already-running detached search/harvester.
- Final harvest waits on the bounded search; initial ladder-probe validation is complete.

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
- A2A completion-evidence message delivered to parent `rpo`.
- Parent rpo approval recorded before status changes to COMPLETE.
