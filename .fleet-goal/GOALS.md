# GOALS — ai-scientist child fleet-agent

status: ACTIVE — child of rpo
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

## M1 — Produce child work evidence for rpo [ACTIVE]

Outcome: ai-scientist performs its assigned research/coding work and writes concise evidence for rpo review.

Evidence required:
- PROGRESS.md updated with What's done / What's next / Any blockers.
- Evidence artifacts under `.fleet-goal/evidence/M1/`.
- Parent rpo approval recorded before status changes to COMPLETE.
