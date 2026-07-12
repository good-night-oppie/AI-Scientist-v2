# M3 — first-principles idea slate (Eddie's challenge, 2026-07-12)

Eddie's challenge: "use deep RL + deep-learning game theory + Dynamic Theory to design an LLM or an
orchestration of models to WIN; give me the wildest ideas grounded in first principles that nobody
dared/cared to use" — plus an explicit invitation to challenge back with simpler crossovers.

## THE FOUNDING FACT (everything grows from this)

**The ladder is a static-population ecosystem, not a game against adaptive adversaries.** Every
opponent is a frozen program; their replays ARE samples of their policy. Game theory's conclusion
inverts: against a static population, Nash equilibrium is the wrong target — **maximal exploitation
(best response to the empirical population) is optimal.** Libratus/Pluribus needed unexploitability
against humans; against frozen bots you want to be the perfect predator.

## Tier 1 — asymmetric advantages only we hold (replays + exact engine + full state access + PAT)

1. **Opponent Simulacra Legion.** Behavior-clone EACH top team from its replays (kazuki0123 alone:
   16,426 decisions) into per-opponent simulacra. Train a best-response policy against the
   matchmaking-weighted simulacra ensemble. Textbook EGTA; nobody on Kaggle sim comps does
   per-opponent BC because nobody treats replays as brain slices of the opponents.
2. **Cheating-Teacher Distillation.** We own the engine: at TRAINING time expose full hidden state
   (opponent hand, deck order, prizes) to a perfect-information teacher search; train the student on
   partial observations to imitate it. The student learns hidden-state-marginalized optimal play
   (DeepStack counterfactual values / AlphaStar centralized critic principle). Kagglers can't — no
   engine internals. We can — vendored engine, full state readable.
3. **Ladder fixed-point simulator.** The rating system is a dynamical system; our final score is the
   fixed point of E[win | matched at r*] = 0.5. Measure per-bracket winrates vs simulacra locally,
   solve for the convergence rating BEFORE submitting. The slot stops being the instrument (rpo
   guardrail 7' satisfied by construction). Nobody does this; everyone gambles the slot.

## Tier 2 — orthodox deep RL × game theory × dynamics

4. **Expert Iteration, deployment-safe.** Train-time search (policy+value-guided MCTS on the 0.3s/game
   engine) → distill into a pure policy net → bundle ships the distilled net ONLY, no search. The s14
   silent-search-death class becomes structurally impossible. Runtime budget (runTimeout=2000s,
   actTimeout=0, ~6s/decision avg) fits numpy inference of a 1–10M model comfortably.
5. **Deck-conditional policy.** Condition on (own deck embedding, inferred opponent archetype); train
   across all harvested + self-play decks. One model plays any deck ⇒ deck choice becomes a searchable
   deploy-time parameter; the co-adaptation trap (both directions falsified in M1/M2) dissolves by
   construction.
6. **Replicator-dynamics meta forecast.** Episode ids are time-ordered ⇒ archetype frequency series ⇒
   fit replicator dynamics (freq × winrate → flow), forecast the meta's attractor, best-respond to the
   FORECAST, not the snapshot. Literal Dynamic Theory.
7. **Opponent-ID router** ("fugu ultra" orchestration, corrected): first ~10 observed actions →
   archetype classifier → switch to the anti-archetype specialist. metamon-router failed routing WEAK
   policies; routing TRAINED specialists with a mandatory generalist fallback is different. The
   mixed-field worst-arm gate exists precisely to punish brittle routers — it stays.
8. **Opponent-prediction auxiliary head.** A linear model already predicts top players at ~47% top-1;
   a trained head does better and powers 1-ply lookahead with a learned opponent model inside the
   deploy budget.

## Tier 3 — further but grounded

9. **Endgame tablebase.** Last-1/2-prize endgames are small enough for retrograde analysis on the real
   engine; ship a compressed value table. Chess first principles no card-game bot bothers with.
10. **Information-maximizing probes.** Our live submissions keep generating episodes vs the real field
    (121 downloadable already). Design future probes to maximize information gain about the population,
    not just rating. (Slots remain Eddie's decision.)

## THE CHALLENGE-BACK (Eddie invited it): the simpler crossover that may beat the LLM to the punch

**The model class was never the bottleneck — the data and the target were.** Evidence: a 176-weight
LINEAR ranker already beats our champion's brain by +14.3pp MAIN agreement over the heuristic anchor
(0.4749 vs 0.3318, triple-verified today). Below ~50% agreement, capacity is not what's binding.

Therefore, BEFORE the transformer:

- **T1. Gradient-boosted trees (LightGBM) on the existing featurized decisions.** Tabular ML routinely
  beats deep nets at 10⁵–10⁶ rows on structured features — Kaggle's own most-repeated lesson, applied
  to Kaggle's sim comp. Trains in minutes on 8 CPU cores. **Deployability is trivial: trees compile to
  pure-python if/else — stdlib-only bundle, the torch/numpy question disappears entirely.** Slots into
  the existing --imitation bundle + liveness (I1–I7) + mixed-field gate infra TODAY.
- **T2. Dynamic Theory as FEATURES, not architecture:** trajectory derivatives — prize-race
  differential and its velocity, energy-tempo momentum, board-development rate, hand-size delta —
  hand-computed history features give the tabular model the sequence context an LLM would learn,
  at zero architectural cost.
- **T3. The Tier-1 exploitation stack needs NO neural network:** simulacra can be linear/GBM clones;
  best-response can be weco/evolution over ranker weights vs the simulacra pool; the fixed-point
  simulator is pure measurement + root-finding.

**Pre-registered decision rule (before any of it runs):** GBM(+dynamic features) is the Phase-2
baseline. The transformer is built ONLY if (a) GBM's held-out MAIN agreement plateaus below the level
the simulacra-exploitation loop needs, or (b) deck-conditioning/history-conditioning demonstrably
exceed what engineered features capture (measured, not asserted). "LLM" is the escalation tier, not
the starting point. If GBM + exploitation + fixed-point forecasting reach 900+ projected rating, we
may never need the GPU at all.

## Discipline (unchanged, non-negotiable)

Phase-0 deployability probe before ANY training; promotion only via the pre-registered mixed-field
gate (aaa1156 floors verbatim); liveness invariants extended to every new bundle kind; n40 = mirage;
the Kaggle slot is Eddie's alone. Every idea above carries a kill condition when it becomes a phase.
