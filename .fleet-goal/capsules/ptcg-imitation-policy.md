# COLLAB_CAPSULE/v1 — ptcg-imitation-policy

task_id: ptcg-imitation-policy
status: DISPATCHED — AUTH CLEARED (queued behind ptcg-replay-miner; same worker)
dispatcher: ai-scientist (external-loop owner per human:eddie authorization #3084,
  superseding 0-vote #3069; rpo reclaimable)
canonical_owner: ai-scientist
worker: mroute
base: origin/feat/ptcg-agent merged head fca4dc4 (or miner branch head after ptcg-18 merges)
isolation: branch pr/ptcg-19-imitation-policy
allowed_paths:
  - scripts/build_imitation_dataset.py   (new)
  - scripts/policy_imitation.py          (new — the distilled policy)
  - tests/test_imitation_*.py            (new)
  - runs/imitation/                      (data)
non_goals: NO Kaggle submission; NO torch/NN (runner has no torch); NO changes to
  frozen evaluators/builders; NO deck-search edits.
motivation (evidence-backed):
  - Deck-transfer dead end CONFIRMED twice: meta0_1106 deck under our frozen
    policy n40 0.625 → n160 0.450 → n400 0.5075 (confirm_out); meta2_1031
    n400 trending 0.459. The 620-pt ladder gap is POLICY, not deck.
  - Purest signal: ZETADIVISION deck = 0.20 under our policy, 1180+ under theirs.
  - Replays of 1180-1220 sids are auth-free and contain full per-step
    (observation, action) pairs → imitation-grade supervision.
IMPLEMENTATION SPEC NOW EXISTS (2026-07-12, workflow wpgxy045l):
  .fleet-goal/evidence/M1/2026-07-12-policy-divergence-imitation-spec.md
  Our policy agrees with >=1100 play on only 40.6% of 9,267 real decisions.
  4 CODE BUGS found (blind deck/prize search; blind evolve/attach target;
  retreat literally never fires; CTX_TO_DECK misclassified as self-loss) plus
  a MAIN_SCORES ordering that is inverted vs observed play (ability 25 -> 85,
  item above supporter, attach demoted + bench-preferring, retreat gated on).
  START THERE — bugs 1-4 are verifiable by reading policy.py, no stats needed.
  CAVEAT: adversarial verify phase died on a spend limit; findings are
  count-grounded but not independently refuted.

spec:
  1. build_imitation_dataset.py: from mined replays (runs/replay_mining/ +
     miner output), extract per-decision-point records: observation dict,
     legal-options context, chosen action, actor sid/score, game outcome.
     Filter to sids with score >= 1100. Emit JSONL + stats (n_pairs, action
     distribution, archetype split by deck).
  2. policy_imitation.py: DEPLOYABLE (stdlib-only) policy distilled from the
     dataset — e.g. weighted decision rules / option-scoring priorities fit to
     top-player choices (fit offline w/ any local tooling, but the SHIPPED
     artifact must be pure stdlib + engine ctypes like the current heuristic).
     Start scoped: imitate the dominant archetype cluster {6,678,1102,1141,
     1142,1152} pilots on their own deck.
  3. Gate (frozen tools, run by dispatcher or worker): h2h vs live-s14 baseline
     n40→n160→n400→n400 ladder; then mixed-field arms from mined 1180-tier decks.
acceptance (ordered):
  1. offline tests pass (fixtures, no network)
  2. dataset stats: >=5k decision pairs from >=1100-rated actors
  3. imitation policy on its target archetype deck: n160 h2h vs live-s14
     wr >= 0.55 (else return honest negative + analysis of where imitation loses)
  4. ruff clean
curator_budget: 1 round
merge_owner: ai-scientist
a2a_ref: decision #3069; capsule 1 dispatch #3070; ladder verdicts this file's
  motivation; bene-mh benchmark adapter is a FOLLOW-ON capsule once this lands.
ledger:
  - 2026-07-12T06:5xZ DISPATCHED by ai-scientist (queued behind ptcg-replay-miner)
  - 2026-07-12T06:4xZ AUTH-DISPUTED (inherits esc-bc98b337e6 — same authority gap
    as capsule 1, per mroute ACK). DISPATCHED-pending-auth; same resolution paths.
  - 2026-07-12T09:07Z AUTH RESOLVED (inherited): human:eddie #3083 vote + #3084
    authorization + #3085 esc ACK. Capsule is claimable as soon as mroute frees
    up from ptcg-replay-miner.
  - 2026-07-12T10:0xZ NO-DATA-DEPENDENCY NOTE (ai-scientist-6): the existing
    corpus (106 raw replays at ready-player-one-ptcg/runs/replay_mining/raw/,
    from which workflow wpgxy045l extracted 9,267 multi-option decision pairs)
    ALREADY satisfies acceptance #2's >=5k bar. Do NOT block dataset build on
    miner completion — bugs 1-4 in policy.py (spec section 1) are startable
    with zero new data.
