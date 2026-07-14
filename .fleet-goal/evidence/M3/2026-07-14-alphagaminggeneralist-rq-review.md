# AlphaGamingGeneralist-RQ report - primary-source verification + two-goal applicability review

- **Date:** 2026-07-14
- **Provenance:** report supplied by Eddie (`/home/admin/.claude/jobs/6117b7be/tmp/agg-rq-report-input.md`); claims verified against primary sources by an N-agent verification workflow (5 clusters, 19 claims audited); applicability analyzed per goal by dedicated agents; this note is the synthesis.
- **Status:** FINAL for M3 evidence. No gate, spec, or doctrine change is made by this document; adoption items below go through their normal channels (Phase-3 spec amendment / D3 fire-vs-friction ledger).
- **Headline:** the report's factual base is largely sound — 15/19 claims VERIFIED, 3 PARTLY_VERIFIED (with corrections), 1 element UNVERIFIABLE (the report's own "risk-adjusted determinization" formula has no published antecedent). **Nothing was REFUTED.** The Red Queen Gödel Machine paper is REAL and verified (arXiv 2606.26294). The report's failure is not its facts but its framing: "one stone, two birds" is REJECTED for both goals. Harvest ~6 bounded slices (3 per goal, each ~1-2 days); decline the shared architecture.

---

## 1. CLAIM AUDIT

No claim was REFUTED. One prominent caution, in bold, up front:

**The report's "risk-adjusted determinization formula" is NOT an established published method.** ISMCTS, ReBeL, and Player of Games are all real and correctly characterized, but no published paper defines a canonical risk-adjusted determinization weighting — that formula is the report's own construction and must be labeled a novel heuristic inspired by (not cited from) the literature. The report excerpt containing the formula was also unavailable for direct cross-check during verification. If we use it (Section 3), it enters as a pre-registered ablation, never on the report's authority.

The RQGM citation — the pillar we were most suspicious of — **checked out**: arXiv 2606.26294, Cambridge-led, submitted 2026-06-24. It is however a "preliminary preprint, work in progress" with no peer-reviewed venue; treat its numbers as author-reported.

### 1.1 Showdown RL cluster

| Claim | Verdict | Correction | Primary sources |
|---|---|---|---|
| Metagrok (2019): self-play PPO, ~3.8M battles, early systematic deep-RL Showdown agent, some human-level ability, poor vs certain search bots | PARTLY_VERIFIED | 3,840,000 matches exact; 1677 Glicko-1 on gen7randombattle. But "poor vs search bots" is too broad: RL-rb BEAT the pmariglia search bot 612-388 in random battles; it underperformed only in the fixed 3-team metagame, and after format fine-tuning (RL-meta) it won every matchup (55.5%-99%) | [CoG 2019 paper](https://www.yuzeh.com/assets/CoG-2019-Pkmn.pdf), [yuzeh/metagrok](https://github.com/yuzeh/metagrok) |
| Foul Play switched minimax -> Monte Carlo search for simultaneous moves | VERIFIED | Precision: prior algorithm was expectiminimax; new search is MCTS with DUCT (Decoupled UCT) for simultaneous move selection | [pmariglia blog](https://pmariglia.github.io/posts/foul-play/), [foul-play](https://github.com/pmariglia/foul-play), [poke-engine](https://github.com/pmariglia/poke-engine) |
| VGC-Bench surveys PPO self-play / poke-env / MCTS-RL, expert-level claims, mostly singles not VGC doubles | VERIFIED | — | [arXiv 2506.10326](https://arxiv.org/abs/2506.10326), [cameronangliss/vgc-bench](https://github.com/cameronangliss/vgc-bench) |

### 1.2 LLM routes cluster

| Claim | Verdict | Correction | Primary sources |
|---|---|---|---|
| PokeChamp: LLM replaces 3 minimax components; GPT-4o 76%/84% winrates; Llama 3.1 8B 64% vs PokeLLMon; est. Elo 1300-1500, top 30%-10% | VERIFIED | Paper's term is "player action sampling" (report: "action proposal") — substantively identical | [arXiv 2503.04094](https://arxiv.org/abs/2503.04094), [sethkarten/pokechamp](https://github.com/sethkarten/pokechamp) |
| PokeLLMon: in-context RL + knowledge retrieval + consistent action generation; 49% ladder / 56% invitational | VERIFIED | Paper's term is "knowledge-augmented generation" | [arXiv 2402.01118](https://arxiv.org/abs/2402.01118), [project page](https://poke-llm-on.github.io/) |

### 1.3 Metamon cluster (all four VERIFIED — this cluster matters most to us, see Section 2)

| Claim | Verdict | Correction | Primary sources |
|---|---|---|---|
| First-person trajectory reconstruction from replays, sequence Transformer, IL -> offline RL -> synthetic self-play, no search at inference | VERIFIED | — | [arXiv 2504.04395](https://arxiv.org/abs/2504.04395), [UT-Austin-RPL/metamon](https://github.com/UT-Austin-RPL/metamon) |
| SynRL-V2 ~top 10% of active players, high global ranks (early-gen OU) | VERIFIED | #46 Gen1OU peak belongs to SynRL-V1; SynRL-V2's peak is #31 | same |
| Self-play vs own checkpoints: much better vs itself, NOT reliably better vs humans; model implicitly assumes opponent is its old self | VERIFIED | Verbatim: "Battle replays make it clear that the model believes it is playing SynRL-V1." Fix was re-expanding data with diverse/unrealistic teams + IL opponents | same |
| Elo vs Glicko vs GXE distinction; raw winrate is matchmaking-biased (~50% expected unless well below human level) | VERIFIED | — | same |

### 1.4 PTCG-side cluster

| Claim | Verdict | Correction | Primary sources |
|---|---|---|---|
| No credible published competitive pure-AlphaZero PTCG system as of 2026-07 | VERIFIED (negative claim, multi-angle search) | Closest adjacent: MageZero (MtG), TCGJax (env-generation only, no trained agent) | [TCGJax arXiv 2603.12145](https://arxiv.org/abs/2603.12145), [MageZero](https://github.com/WillWroble/MageZero) |
| PTCG-Bench (2026): LLM agents, single-game decisions + self-evolution + harness ablation; self-evolution hard, harness-sensitive | VERIFIED | — | [arXiv 2605.29653](https://arxiv.org/abs/2605.29653) |
| 2026-07 Lean 4 formalization of PTCG metagame Nash/replicator dynamics on real tournament matchup matrices | VERIFIED | Trainer Hill Jan-Feb 2026 data, 14x14 matrix, 2,627 theorems, no sorry/admit; Dragapult "popularity paradox" (15.5% play share, 0% Nash weight) | [arXiv 2607.08692](https://arxiv.org/abs/2607.08692), [IEEE DataPort artifact](https://ieee-dataport.org/documents/formally-verified-pokemon-tcg-metagame-analysis-tournament-data-matchup-matrices-and-lean) |
| Kaggle 'pokemon-tcg-ai-battle' (cabt env) exists; public learned-agent writeups available | PARTLY_VERIFIED | Competition real ($300K, ends Aug 2026, cabt = Matsuo Institute proprietary engine, NOT in public kaggle-environments README). **But no public writeup of a competitive LEARNED agent exists as of 2026-07-14** — the only substantive writeup (wmh/ptcg-abc) is rule-based (best Elo 836; its finding: deck choice > agent complexity). A "PPO Agent" notebook exists but content unretrievable | [competition](https://www.kaggle.com/competitions/pokemon-tcg-ai-battle), [cabt docs](https://matsuoinstitute.github.io/cabt/), [wmh/ptcg-abc](https://github.com/wmh/ptcg-abc/blob/main/README.md) |

### 1.5 RQGM cluster (all four VERIFIED)

| Claim | Verdict | Correction | Primary sources |
|---|---|---|---|
| Red Queen Gödel Machine paper exists (June 2026), co-evolves evaluator with agent | VERIFIED | Preprint only, "work in progress", no peer-reviewed venue | [arXiv 2606.26294](https://arxiv.org/abs/2606.26294) |
| Epoch mechanism: evaluator frozen within epoch; challengers anchor-validated at boundaries; old agents re-scored; epoch-local guarantee | VERIFIED | Nuance: re-scoring after evaluator replacement is LAZY/amortized (erase immediately, re-rank only on revisit; Bounded Recovery Prop. 6), not an immediate full-archive re-rank | [pdf](https://arxiv.org/pdf/2606.26294) |
| Results: 1.35-1.72x fewer tokens vs prior coding SOTA; writer acceptance 1.78-1.86x; proof grading +9% ground-truth accuracy | VERIFIED | +9% is the co-evolved GRADER's accuracy (IMO-GradingBench anchor); writer acceptance judged by agent-as-a-judge panel, not humans | same |
| Paper admits evaluator quality is anchor-limited; guarantees epoch-local only | VERIFIED | Verbatim in Discussion/Limitations | same |

### 1.6 Methods cluster

| Claim | Verdict | Correction | Primary sources |
|---|---|---|---|
| PSRO original paper + guarantees | VERIFIED | Guarantee inheritance is narrow: exact-best-response DO in two-player games converges, possibly only after enumerating the whole strategy space; with approximate RL oracles the guarantee evaporates | [arXiv 1711.00832](https://arxiv.org/abs/1711.00832) |
| AlphaStar league: main / main-exploiter / league-exploiter | VERIFIED | Main exploiters "identify potential exploits in the main agents"; exploiters periodically reinitialized; ~900 league players | [Nature 575:350-354](https://www.nature.com/articles/s41586-019-1724-z) |
| Per-node Nash/regret-matching over payoff matrices in simultaneous-move MCTS | VERIFIED | Convergence to subgame-perfect eps-Nash formally proven (NIPS 2013); shipped in OpenSpiel | [SM-MCTS](https://mlanctot.info/files/papers/wcg13-smmcts.pdf), [NIPS 2013](https://papers.nips.cc/paper/5145-convergence-of-monte-carlo-tree-search-in-simultaneous-move-games), [OpenSpiel](https://arxiv.org/abs/1908.09453) |
| ISMCTS / ReBeL / Player of Games exist; report's belief-state + risk-adjusted determinization reflects published methods | PARTLY_VERIFIED | Method families real. **The specific risk-adjusted determinization formula is UNVERIFIABLE as a citation** — it is the report's own construction (see bold note at top of Section 1); report excerpt was unavailable for cross-check | [ISMCTS 2012](https://ieeexplore.ieee.org/abstract/document/6203567/), [ReBeL](https://arxiv.org/abs/2007.13544), [Player of Games](https://arxiv.org/abs/2112.03178) |
| AlphaZero assumes two-player zero-sum, perfect information, deterministic | VERIFIED | Nuance: the phrases "zero-sum"/"perfect information" appear zero times in arXiv v1 — assumptions are embodied in method+domains; successor papers (MuZero, Student of Games) state the limitation explicitly | [arXiv 1712.01815](https://arxiv.org/abs/1712.01815) |

---

## 2. WHAT THE REPORT GETS RIGHT FOR US

三个重合点，全部是 external validation of doctrine this lane already runs — 报告没有教我们新东西，但它把我们用血换来的规则接到了 published, verified evidence 上:

1. **Kill-only frozen gate = RQGM's frozen-evaluator epoch.** RQGM (VERIFIED) freezes the evaluator within an epoch so the agent improves under stationary utility, and only replaces it via anchor-validated challenger promotion at boundaries. Our pre-registered gate (screen n40 / confirm n400 / independent reconfirm, floors frozen before any number is seen, "gate KILLS but never CROWNS" per faf7d49) IS an epoch-frozen evaluator — implemented as governance instead of machinery. The paper's admitted limits ("evaluator quality is only as good as its anchor"; "guarantees are epoch-local") match our own epistemic posture exactly.

2. **Ladder = immutable ground-truth anchor.** RQGM promotes evaluators only when they raise score on a fixed ground-truth anchor. Our doctrine "only the ladder crowns" is the same structure. The difference — and the reason we cannot run RQGM's full loop — is anchor economics: RQGM assumes cheap anchor evaluations at every epoch boundary; our anchor costs one of Eddie's personal Kaggle slots per probe at 75-100 MMR noise per ~50 episodes (8a20b62 / M3 noise-floor reading). C1 was withdrawn precisely because local-to-ladder calibration is unachievable.

3. **C3 league-overfit is real and measured elsewhere — this is the most valuable single fact in the report.** Metamon (VERIFIED, all four claims) hit exactly our named blind spot: self-play against own checkpoints made the model "significantly better against itself" with "inconsistent improvement against real players", and behaviorally "the model believes it is playing SynRL-V1." Our C3 is not a hypothetical: a top-decile-achieving published system walked into it and had to engineer its way out. Their fix (re-expand the league with diverse AND unrealistic teams plus IL opponents) is the published version of defenses we partially have — and it tells us which missing piece to add (Section 3, item 2).

Also right: the Elo/Glicko/GXE/winrate-bias discussion (VERIFIED) supports our treatment of ladder MMR as noisy and our refusal to over-read single probes.

---

## 3. APPLICABILITY - PTCG KAGGLE LANE (Goal A)

Constraints binding this analysis: ~500 MMR gap, Phase-3 expert-iteration on the exact vendored cabt engine (0.3s/game), one 8-core box + this host, deploy tier ~1M-param numpy+stdlib (no torch, no search at deploy), frozen kill-only gate, first gate-eligible NN candidate ~3-4 weeks out, imitation family 0-for-4 (GBM 0.5181 MAIN agreement / 0.125 vs s14, admissible under liveness).

### ADOPT into Phase-3 spec now (each ~1 day-scale, none touches the frozen gate)

1. **Off-meta league stratum (Metamon's verified C3 mitigation).** Extend the P3.1 per-round deck-refresh hook to sample N off-meta/harvest-tail/deliberately-weird lists alongside the canonical top-6; log the stratum in the round summary JSON. Cost: near zero — a hook extension, no new training, no gate change. We already run the rest of Metamon's fix (IL opponents in pool: linear bundle + killed GBM bundle; frozen s14/s18; recency+diversity checkpoint sampling); the "unrealistic/off-meta" stratum is the one missing piece, now backed by a published measured result. Priority 1 — cheapest defense against our one named-open failure mode.

2. **AlphaStar-style exploiter as a C3 diagnostic (diagnostic-ONLY).** Per gate-eligible candidate: train a cheap best-response against the frozen candidate checkpoint (~50k games ≈ 1 day at the verified 50-70k games/day floor on arena-1), reusing the P3.2 trainer + P3.1 league harness verbatim. If a 1-day exploiter crushes a candidate that dominates the frozen field, the candidate is fragile in a way the league cannot show — hold its probe request. Hard conditions: pre-register as diagnostic BEFORE first use (else it is evaluator drift); it must never become a gate rung or crown signal — only an additional reason to withhold a probe request from Eddie. This is the only policy-side exploitability signal the lane can have locally; G4 catches frozen-field decay, not rising-candidate fragility.

3. **Risk-penalized determinization targets — as a pre-registered ablation, not an adoption.** Q(a) = E_z[Q(a,z)] − λ·Var_z[Q(a,z)] over determinization samples in the P3.2 target generator. Rationale: plain determinization has documented flaws (strategy fusion, non-locality — verified ISMCTS literature) and PTCG's hidden info (prizes, opponent hand, deck order) makes over-optimistic fused targets a real risk. **Caveat that ships with it: this formula is the report's own heuristic, not a published method (Section 1 bold note).** So: few lines of train-time code, A/B at the already-planned 50k-game P3.2 rehearsal round, scored by frozen-field macro, adopted only if the number moves. Zero deploy-tier impact (bundle still ships the distilled net, no search).

### HOLD until Phase-3 data exists

- **Full belief-state world model (learned b_t(z), opponent-conditioned value).** Only justifiable if expert iteration plateaus for target-quality reasons — a numbered finding that does not exist yet. Multi-week model-class bet competing for the same box the rounds need. Revisit only on a plateau finding.
- **Anything Elo-modeling beyond current probe discipline.** The Metamon rating discussion is useful context but changes nothing until we have more than ~1 probe datapoint per candidate.

### REJECT — violates constraints or already killed

- **Unified game IR (L1):** single-game lane, exact vendored engine, tokenizer is one pure function shared by trainer and bundle (train/serve identity, a hard-won lesson). Abstraction cost with zero path to +500 MMR.
- **Simultaneous-move search / per-node Nash (L3):** category error — cabt PTCG is sequential turn-based. The machinery (verified real) solves a problem this game does not have.
- **Full PSRO meta-solver:** verified PSRO fact cuts against it — convergence only with exact best responses in two-player zero-sum, possibly with full enumeration; each iteration = a full multi-day round on the only box; a local Nash mixture cannot represent the ladder (C1 withdrawal). The one PSRO-adjacent idea worth keeping is item 2 above.
- **RQGM evaluator co-evolution:** contra-doctrine (frozen kill-only gate exists because moving evaluators produced mirages — n40 mirage x6, 2c1368bc03 four-rung local pass ladder-rejected, field v2 withdrawn) AND structurally unaffordable (anchor evaluations at RQGM cadence impossible by orders of magnitude given slot economics). We already run the sound half of RQGM as governance; the moving part it adds is the part the doctrine forbids.
- **Offline-RL foundation policy as base pillar:** just killed at n400 — imitation family 0-for-4; GBM's best-in-lane agreement (0.5181) converted to 0.125 vs s14. Nobody on the ladder plays our deck; no off-policy corpus teaches the policy we field. What survives is already spec'd: BC as init prior with asymmetric G1 + pre-registered from-scratch fallback.
- **Cross-game transfer / P4 generalist:** one game, competition ends Aug 2026, deploy cap ~1-20M numpy params; no published system demonstrates the claimed transfer (fact base found none); the report's most speculative layer on its least verified ground.

---

## 4. APPLICABILITY - HARNESS LINEAGE (Goal B)

Context: operational objective (watch-list SoT, M1-M3) DONE; EDITH parked behind agentdex redesign. Standing program: self-improving harness loops under doctrines D1-D24 + EVAL.md (deterministic non-LLM Curator first). Compute: host-local CPU + rationed LLM quota (full mroute outages on record). RQGM here is protocol, not population search.

### ADOPT now (all doctrine-text-level, via the normal D3 fire-vs-friction promotion path)

1. **Anchor-scored challenger-vs-incumbent gate promotion (amend D15).** D15 says "re-evaluate the oracle between campaigns" but gives no acceptance criterion — today a curator/lint/judge rewrite ships on code-review vibes. RQGM's verified mechanic supplies it: score challenger gate vs incumbent on a fixed ground-truth anchor set; promote only if it wins; ties favor incumbent. EVAL.md Classes A-E already name ground-truth datasets, so anchors mostly exist; new work is a small labeled challenger-scoring set per gate class + a promotion script in the `_smoke_*` style. 1-2 days, no compute, recurring cost only when a gate is actually rewritten. This is a protocol amendment, NOT a new eval framework.

2. **Mandatory must-reject fixture suite (anti-Goodhart negative anchors).** Every gate ships with known-BAD artifacts it must FAIL, not just known-good it must accept. The lineage has this failure recorded twice: the blind-ranker defect (empty weights → identity-order pick, never raises, passes any choose()-call counter — s14's guard bug reincarnated, per c-gate-liveness-defect memory). Negative smokes exist for fleet_tree_lint and harness_praxis_lint; the change is universality + a doctrine making it mandatory. Candidate for SKILL.md promotion (maps 1:1 to a recorded failure, satisfying D3 promotion policy). 1-2 days, stdlib-only, zero LLM cost. Highest confidence item in this note — it would have caught a defect we hit twice.

3. **Verdict-staleness rule on gate version bumps.** When a gate/judge/curator version changes, verdicts it issued are marked stale and re-scored LAZILY on next revisit (RQGM's verified erase-then-amortized-re-rank — the lazy variant matters: immediate full re-audit of the append-only evidence corpus would violate D12). Implementation: stamp verdicts with the issuing gate version/hash (extends existing served_by/RUN_ID habit) + protocol text. Trivial cost.

### HOLD

- **Full RQGM population search (agent-genome + evaluator-genome, Pareto archive, mutation).** Premature by our own numbers: the paper's wins came from many-rollout evolutionary search; our LLM budget has had full-chain outages (mroute rc=124 ALL_TIERS_EXHAUSTED) and D12 forbids evolution loops that cannot amortize. The paper's own limit bites hardest here: our scarce resource IS labeled ground truth — spend quota enlarging anchor sets before mutating evaluators. Revisit only if quota economics change materially.

### REJECT

- **Game machinery (L1/L2/L3):** no game environment, no simultaneous moves, no hidden-state opponent in a fleet of cron loops and lint gates. Zero referent.
- **PSRO/league populations over harness variants:** one coordinator + delegated workers under height-4/max-2-children governance; the existing dream/evolution crons are starved (D7) with orphaned outputs (D8) — population search on top optimizes the wrong bottleneck.
- **Adversarial judge leagues:** the 3-lens KAOS-dream panel already sits at EVAL.md order 4, and D5's non-LLM-Curator-first already solves validator monoculture better for this context. Fix the wiring (D7/D8 defects) of the existing adversarial layer before breeding it.
- **Shared foundation model with Goal A:** no shared representation exists or is needed between PTCG episodes and harness eval gates.

---

## 5. ONE STONE TWO BIRDS VERDICT

**REJECT the framing, for both goals.** The report sells one architecture (AlphaGamingGeneralist-RQ) serving the competition and the self-improvement research agenda simultaneously. The verification and applicability passes show:

- For Goal A the causality runs backwards: the lane needs the cheapest possible stone for one bird (beat s14 at Wilson-lo ≥ 0.55 twice at n400, ≤5MB numpy bundle, ~4 weeks, one 8-core box), and the generalist system is a heavier second stone that would consume exactly the compute and weeks the first bird requires. More telling: the lane has already independently converged, under kill-gate pressure, on every load-bearing idea in the report — expert-iteration on an exact engine, a diverse frozen league with deck refresh, an immutable anchor with a frozen kill-only evaluator, and C3 named with defenses on record.
- For Goal B the genuine overlap is one concept — evaluator change under immutable anchors — and the lineage already owns ~80% of it as written doctrine (D15/D16/D5, EVAL.md anchors, BENE hash-locked gates, negative smokes). The residue is a few days of protocol text.
- The single component the report adds that neither goal has — a co-evolving evaluator — is contra-doctrine for Goal A and premature-by-quota for Goal B.

**Is there a smallest concrete shared artifact?** Yes, exactly one, and it is small: a **shared written protocol for evaluator-change-under-anchor** — one page stating (a) evaluator frozen within a campaign/epoch, (b) challenger evaluators scored vs incumbent on a fixed ground-truth anchor before promotion, ties to incumbent, (c) verdicts stamped with issuing evaluator version, staled on replacement, re-scored lazily, (d) every evaluator ships must-reject negative anchors. Goal B adopts it as a D15 amendment through D3; Goal A cites it as external validation of the already-frozen gate doctrine (no gate change — the lane's gate already complies). That is the entire overlap: doctrine-level, ~1 page, citation [arXiv 2606.26294]. Everything else in the report is per-goal slices or rejected.

---

## 6. WHAT WE WOULD TRACK

| What | Why | Link |
|---|---|---|
| Kaggle pokemon-tcg-ai-battle discussion/notebooks | Direct competition intel; **no learned-agent writeup exists yet (verified 2026-07-14)** — first strong one to appear changes our meta read; also watch episode datasets | https://www.kaggle.com/competitions/pokemon-tcg-ai-battle |
| wmh/ptcg-abc | Only substantive public agent writeup so far (rule-based, Elo 836); its "deck choice > agent complexity" finding rhymes with our lever history | https://github.com/wmh/ptcg-abc/blob/main/README.md |
| RQGM (arXiv 2606.26294) | Preprint, "work in progress" — watch for peer-reviewed version, revised numbers, or released code before citing results as load-bearing | https://arxiv.org/abs/2606.26294 |
| Metamon (arXiv 2504.04395 + repo) | The verified C3-in-the-wild case study; repo has 5M+ reconstructed trajectories and the diverse-league mitigation details | https://github.com/UT-Austin-RPL/metamon |
| PTCG-Bench (arXiv 2605.29653) | Only published PTCG agent benchmark; its harness-sensitivity finding is relevant to both goals | https://arxiv.org/abs/2605.29653 |
| Lean 4 PTCG metagame paper (arXiv 2607.08692) | Real tournament 14x14 matchup matrix + Nash/replicator analysis — potential external data for deck-side league stratification (item 3.1) | https://arxiv.org/abs/2607.08692 |
| TCGJax (arXiv 2603.12145) | First Pokemon TCG Pocket env; env-generation only today, but a trained-agent follow-up would be the first published PTCG RL baseline | https://arxiv.org/abs/2603.12145 |
| VGC-Bench (arXiv 2506.10326) | Tracks the Showdown-side SOTA the report leans on; doubles-format results would test the report's transfer claims | https://arxiv.org/abs/2506.10326 |

---

*End of review. Adoption items route through: Goal A -> Phase-3 spec amendment (pre-registration required for items 2 and 3 before first use); Goal B -> D3 fire-vs-friction ledger promotion.*
