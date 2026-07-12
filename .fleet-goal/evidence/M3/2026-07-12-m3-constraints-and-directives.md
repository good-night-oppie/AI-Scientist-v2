# M3 — design constraints + Eddie's directives (ground truth, 2026-07-12)

## Eddie's directives (verbatim intent, four messages, 2026-07-12 ~23:00Z)

1. "we are keep scoring 5-600. that means your method sucks" — correct: ~600 vs top tier 978–1220;
   search-tuning, deck search, deck transfer, off-policy imitation all failed to move the ladder.
2. "use kaggle pat download all the replay, and let's design and train our own llm" — the Metamon
   recipe: mass harvest + own neural policy + self-play.
3. Compute: "if kaggle's resource is not enough we have aws cli to get gpu h100" — see prior art below.
4. "Based on the rules of the competition, we need to design LLM that meets the requirements, then
   train it with first-principles-deduced out-of-the-box ideas" — **rules-first design; the model is
   designed INTO the deployment envelope, not adapted to it after training** (the s14/BFTS lesson).

## Hard constraints from the REAL competition env (vendored `kaggle_environments/envs/cabt/cabt.json`)

- `actTimeout = 0` (no per-move timeout), `runTimeout = 2000` s per episode, `episodeSteps` unbounded
  (games end by rules; observed 96–305 steps, ~43 decisions/seat/game).
- ⇒ per-decision budget ≈ seconds, not milliseconds. Inference tier can be numpy or even careful
  pure-python for a 1–10M-param model. The BINDING unknown is the runner image's importable set
  (torch? numpy?) — settled only by the Phase-0 dummy-bundle probe (submit a bundle that logs
  `import torch/numpy` versions to agent stderr; Eddie can download agent logs — screenshot flow).
- Local engine = the exact competition engine: 0.305–0.566 s/game measured (PR #28 evidence JSONs).
  8 cores ⇒ order 10⁵ self-play games/day is realistic (subject to the compute-verify lane's audit).

## Auth + compute ladder (verified on this host)

- Kaggle token: `/home/admin/.kaggle-pokemon-token` (Eddie-confirmed; 2.4KB, Jul 8). Also
  `~/.kaggle/access_token` (37B). **Read at point of use only; never echoed/printed/committed.**
- No local GPU (8 cores / 31GB RAM, ~23GB in use; 309GB disk free).
- Compute ladder: (1) local CPU for tiny models + all self-play generation; (2) Kaggle free GPU
  notebooks (~30h/wk) — corpus (2.3GB now) uploadable as a private dataset via PAT;
  (3) **AWS via `/home/admin/aws-openmythos`** — existing launch/bootstrap/teardown/status scripts,
  currently g5.xlarge (A10G 24GB, ~$1/hr; spot cheaper), Deep Learning AMI PyTorch 2.4, us-west-2;
  H100 (p5) is a config change if model size ever demands it. aws-cli 2.34.50 installed (creds
  currently inactive — reactivation is an Eddie step when Phase 2 needs it).

## First-principles design seeds (to be tested by the M3 workflow's model lane, not assumed)

1. **The game is a ranking problem over VARIABLE legal option sets** (select k of n, n varies per
   decision, options are structured objects) ⇒ pointer/scoring architecture over option tokens, not
   a fixed action vocabulary.
2. **Deck-CONDITIONAL policy** — the lane's central finding is policy×deck co-adaptation (both
   directions falsified). Condition the model on (own deck, inferred opponent archetype) as a
   prompt prefix; train across ALL harvested decks + self-play decks. One model plays any deck ⇒
   deck choice becomes a searchable deploy-time parameter instead of a co-adaptation trap.
3. **Expert iteration (AlphaZero-shape, deployment-safe)**: at TRAINING time use the fast exact
   engine for search (MCTS/rollouts guided by the policy+value net); distill the improved play back
   into the policy. **Deployment ships the distilled policy only — no search in the bundle**, so
   the s14 "search never fired" class of failure is structurally impossible.
4. **Winner-prediction pretraining**: every harvested episode carries terminal rewards; pretrain the
   trajectory encoder on "who wins from here" before policy fine-tune (cheap signal, all replays).
5. **Hidden information**: hands/decks/prizes are partially observed ⇒ history-conditioned encoder
   (the transformer's context IS the belief state); no explicit belief modeling in v1.
6. **League self-play** vs a pool (s14, s18, linear imitation bundles, mined-deck heuristic bots,
   past checkpoints) to prevent self-play collapse; evaluation ONLY through the pre-registered
   mixed-field gate (aaa1156 floors verbatim — screen n40 macro≥0.55/worst≥0.40; confirm n400
   worst-arm Wilson-lo≥0.50; independent reconfirm; liveness=LIVE extended to the NN bundle).

## Non-negotiables carried from M1/M2 (so M3 does not re-learn them)

- Deployability verified BEFORE training (Phase 0 gate). No training run until the probe bundle
  returns the importable set from the real runner.
- n40 = mirage (six recorded, both directions). Gates per aaa1156 only. Probe slot = Eddie's alone.
- Agreement numbers: heuristic anchor on the 679-corpus split is **MAIN 0.3318** (stale 0.2866 is
  106-corpus). Any new dataset build re-derives its own anchor first.
- The 679-corpus + built dataset live ONLY in `ready-player-one-ptcg/runs/` (divergent worktree,
  sole copy, read-only, never rebase). Mass harvest lands in a NEW dedicated location with space
  checks (309GB free; full harvest estimate pending census lane).
- Coordinator does not code; mroute builds, sctst-aide harvests; capsule discipline for cross-lineage.
