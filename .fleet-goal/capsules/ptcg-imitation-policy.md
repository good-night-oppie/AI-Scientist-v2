# COLLAB_CAPSULE/v1 — ptcg-imitation-policy

task_id: ptcg-imitation-policy
status: PHASES A1+A2 MERGED — B IN PREP (A1 = PR #21 @ca937183, gated: mirror
  regression n800 0.4575 [0.423,0.492], deck-conditional, see evidence
  2026-07-12-a1-gate-results.md; A2 = PR #22 @87eeb9dd, audited: invariants
  exact, 9,269 pairs >= 5k bar)
dispatcher: ai-scientist (external-loop owner per human:eddie authorization #3084,
  superseding 0-vote #3069; rpo reclaimable)
canonical_owner: ai-scientist
worker: mroute
base: origin/feat/ptcg-agent merged head fca4dc4 (or miner branch head after ptcg-18 merges)
isolation: branch pr/ptcg-19-imitation-policy
allowed_paths:
  - src/ready_player_one/ptcg/policy.py  (REVISED 10:5xZ — Phase A1 bug fixes
    ONLY; Phase B may touch MAIN_SCORES values; nothing else in this file)
  - scripts/build_imitation_dataset.py   (new)
  - scripts/policy_imitation.py          (new — the distilled policy, Phase C)
  - tests/test_imitation_*.py            (new)
  - tests/test_policy_bugfix_*.py        (new — Phase A1 regression tests)
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

spec (REVISED 10:5xZ into ablation phases — isolate each variable):
  A1. PATCH src/ready_player_one/ptcg/policy.py: bugs 1-4 ONLY (deck/prize
      resolve, evolve/attach target, retreat gating, CTX_TO_DECK recovery) —
      NO score retuning. Regression tests per bug (fixture states where old
      behavior was blind/wrong). Gate the bug-fix-only variant through the
      h2h ladder. This is the spec's falsifiable acceptance: it measures the
      PURE bug cost, and ~0.50 at n400 falsifies the bug half of the thesis.
  A2. build_imitation_dataset.py: from mined replays (runs/replay_mining/ +
      miner output), extract per-decision-point records: observation dict,
      legal-options context, chosen action, actor sid/score, game outcome.
      Filter to sids with score >= 1100. Emit JSONL + stats (n_pairs, action
      distribution, archetype split by deck). (A2 has no ordering dependency
      on A1 — mroute already started here; fine.)
  B.  MAIN_SCORES reorder ON TOP of the A1-fixed policy (held until the
      coordinator relays adversarial re-verification verdicts). Gate again —
      measures the tuning delta separately from the bug delta.
  C.  policy_imitation.py: DEPLOYABLE (stdlib-only) policy distilled from the
      A2 dataset — weighted decision rules / option-scoring priorities fit to
      top-player choices (fit offline w/ any local tooling, but the SHIPPED
      artifact must be pure stdlib + engine ctypes like the current heuristic).
      Start scoped: imitate the dominant archetype cluster {6,678,1102,1141,
      1142,1152} pilots on their own deck. Compared against BOTH the A1 and
      A1+B variants — three-way ablation.
  Gate (frozen tools, run by dispatcher or worker): h2h vs live-s14 baseline
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
  - 2026-07-12T10:3xZ GREENLIT + SCOPE PIN (ai-scientist-6, answering mroute
    #3090). Base updated: origin/feat/ptcg-agent @ 30ef89fb (post-PR#20).
    PHASE A (build NOW): bugs 1-4 fixes + build_imitation_dataset.py + offline
    tests + h2h gate runs. Bugs 1-4 are source-verifiable; treat the spec's
    fix sketches as the spec.
    PHASE B (MAIN_SCORES rewrite): scope PINNED pending re-verification — the
    coordinator's running analysis workflow (wf_fc1549e0-ff8) is adversarially
    re-verifying the behavioral-inversion stats whose original verify died on
    the spend limit; verdicts will be relayed on the bus before phase B build.
    Rationale: mroute's own caveat in #3090 — low-risk source-verified fixes
    first, unrefuted-stats-based tuning second.
  - 2026-07-12T1x:xxZ A1 MERGED (PR #21 @ca937183; merge race with restore
    force-push resolved, trees identical) and GATED: n40 0.575 mirage ->
    n160 0.500 -> n400 0.4625 -> n400b 0.4525; pooled n800 0.4575
    [0.423,0.492] = MIRROR REGRESSION, deck-conditional (co-adaptation cuts
    both ways). A1 stays as lineage base; NO A1-only promotion. BINDING gate
    change for B/C: paired-with-mined (fixed x mined vs old x mined AND vs
    frozen s14). mroute adds ablation flags (ENABLE_RETREAT_FIX /
    ENABLE_TARGET_TIEBREAKS / ENABLE_DECK_SIGHT) in B for 3x n160 attribution.
  - 2026-07-12T1x:xxZ A2 MERGED (PR #22 @87eeb9dd; Eddie merged, coordinator
    audit passed independently: 8/8 tests, live corpus invariants exact
    1121/1121 + 711/711 + 6071 + 9,269 pairs, exit 0). Non-blocking finding
    for the C PR: --min-score is cosmetic (filter uses hardcoded
    MIN_TOP_SCORE; non-default values mislabel the dataset summary).
  - 2026-07-12T15:4xZ EDDIE DIRECTIVE (binding, in-session): A1+B are ONE
    candidate — gate them TOGETHER; A1 is NEVER shipped/gated alone again.
    Grounded in paired-gate data: A1-alone lost to old policy in the s14
    mirror (n800 0.4575 [0.423,0.492]) AND worse on the meta0 engine deck
    (n800 pooled 0.41; both n400 Wilson-uppers < 0.474) AND collapsed vs
    frozen s14 (n160 0.3688 vs old×meta0 ref 0.5075). Mechanism hypothesis:
    A1's deck-search SIGHT ranks by the INVERTED _card_keep_value (finding #5,
    a Phase-B fix) — sight × wrong values < blind. B's ablation flags remain
    for ATTRIBUTION runs only, not for shipping variants.
  - 2026-07-12T10:5xZ SCOPE CORRECTION (ai-scientist-6, answering mroute #3092):
    mroute's new-files-only reading was faithful to the original allowed_paths
    but collapses the ablation — bugs 1-4 ARE patches to policy.py (Phase A1),
    because the spec's falsifiable gate is defined on the FIXED OLD policy and
    the bug-fix delta must be measured in isolation from retuning (B) and
    distillation (C). allowed_paths revised: policy.py added (A1 fixes + B
    scores only), regression tests added. Dataset-builder-first start is
    unaffected (A2 has no dependency on A1). Live champion s14 is a frozen tar
    — repo patches cannot perturb it.
