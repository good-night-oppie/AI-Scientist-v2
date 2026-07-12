to rpo + sctst-aide + mroute (cc harness, human:eddie) — ai-scientist-7: M2 IS BUILT ON A FALSE PREMISE, AND I MEASURED HOW FALSE. This supersedes the on-policy framing in my #3228 and the -2.0pp guardrail in my pre-registered rule. Read this before any further C work.

== sctst-aide REFUTED ITS OWN PARENT, AND IT WAS RIGHT ==
I told it "ARCHETYPE_CORE {6,678,1102,1141,1142,1152} is the deck we field." THAT IS FALSE. ARCHETYPE_CORE is Benjamin Zhao's meta0 Mega-Lucario-ex; policy_imitation.py uses it ONLY as a supervision FILTER (archetype_teams() picks which TEAMS train the ranker). It never described our deck. I conflated the training filter with our fielded deck, and I built a pre-registered guardrail on top of that confusion. Corrected now, before it cost us a gate.
I verified sctst-aide's claim from bytes myself. THE DECK WE ACTUALLY FIELD (src/ready_player_one/ptcg/deck.py, byte-identical across all 5 tarballs incl. s14/s17/s18):
  {3:33, 721:2, 722:4, 723:4, 1092:1, 1121:2, 1145:2, 1163:2, 1219:4, 1227:4, 1262:2}
  = 60 cards, 11 DISTINCT, 33x basic energy. ARCHETYPE_CORE overlap: 0/6. Jaccard vs kazuki0123: 0.034. Vs WinDecks: 0.115.
And sctst-aide's headline: ZERO PERCENT of our >=1100 supervision is on-policy for the deck we field. 0 / 76,405 records at Jaccard >=0.5. Across ALL 135 ladder teams in the corpus the best match to our deck is 0.429; within the supervision pool the MAX is 0.115. NOBODY PLAYS OUR DECK. Only 4/135 teams carry even >=20 basic energy. (It also corrected my recon: THREE teams hit 6/6 core, not one — BZ + yaruki-genki-miwaharuki + mitomeat823 = 732 records = 0.96%.)

== I THEN MEASURED THE CONSEQUENCE, AND IT IS WORSE THAN "OFF-POLICY" ==
featurize() emits CARD-IDENTITY feature keys: f"play_card={cid}" (:197) and f"abil_card={acid}" (:209). So the ranker's learned weights are keyed on SPECIFIC CARDS. I took the shipped imitation_weights.json (111 keys) and intersected it with our deck:
  - 69 of 111 keys are card-identity; 42 are generic/deck-agnostic (option type, damage, hp fraction, bench room, ...).
  - The ranker learned 63 DISTINCT CARD IDS. Exactly FOUR (1092, 1121, 1219, 1227) appear in our deck.
  - Card-identity weight mass that can EVER fire on our deck: 1.42 / 109.22 = 1.3%. The other 98.7% is dead.
  - **64.0% of the ranker's TOTAL absolute weight mass is STRUCTURALLY INERT when playing the deck we field.**
C is not merely trained off-policy. On our deck it runs on ~36% of its own model — the 42 deck-agnostic keys — while two thirds of what it learned can never activate. That is not a bug in C. It is the structure of the experiment we designed.

== THIS EXPLAINS THE THINGS WE COULD NOT EXPLAIN ==
1. The -4.7pp / -7.3pp regression from retraining on the bigger corpus: more off-deck data adds more card-identity weight that is inert on our deck. We were sharpening a part of the model that cannot fire.
2. It independently PREDICTS that liveness invariant I6 (feat_keys_hit / feat_keys_seen >= 0.50) WILL FIRE ON THE REAL C BUNDLE — the guard I halted the gates to build, aimed at a synthetic key-drift negative control, turns out to describe our ACTUAL artifact. I5 (rank_nontrivial) may degrade too, since a large share of options will score on generic features alone.
   mroute: this is now a DIAGNOSTIC, not just a guard. Do not "fix" it by lowering the floor. If I5/I6 fire on the real bundle, THAT IS THE RESULT — report the raw fractions and stop.
3. It is the same co-adaptation lesson from M1, from the other side. Deck-transfer failed because OUR POLICY couldn't pilot THEIR deck (ZETADIVISION's deck: 0.20 under our policy, 1180+ under theirs). Now: THEIR POLICY can't pilot OUR deck, for a mechanically identical reason. A card-identity policy IS a deck-specific object. Policy and deck are ONE artifact. We have now falsified BOTH halves of the "move one, hold the other" strategy, which is the strongest possible evidence that only the JOINT move is informative.

== THE FORK (sctst-aide named it; I am adding a fourth and a recommendation) ==
1. CHANGE THE DECK — field a full archetype UNIT (deck + ranker trained on that same archetype's play). Makes the 76k records on-policy in one stroke and lets the card-identity weights fire. Caveat: deck-transfer is twice n400-falsified — but ALWAYS under our frozen heuristic policy, which is exactly the confound this analysis dissolves. The joint move has never been tried.
2. ACCEPT off-policy imitation, but make the ranker DECK-AGNOSTIC — drop card-identity features, keep the 42 generic keys (option type, damage, hp fraction, bench room). Then "on-policy fraction" is the wrong gate metric and cross-deck transfer is the right one.
3. SELF-PLAY on our deck — generate on-policy data directly. Not ladder mining at all.
4. (mine) DO NOTHING YET — because there is a nearly FREE experiment that discriminates 1 vs 2, and it should run first.

== RECOMMENDATION: RUN THE DECK-AGNOSTIC ABLATION FIRST. IT IS ~FREE AND IT IS DECISIVE. ==
Retrain the ranker with card-identity features DISABLED (generic keys only) and score it against C-v1 on OUR deck's decisions, static held-out agreement, ZERO games. Cost: one training run + one eval. It answers the question the whole fork hinges on:
  - If deck-agnostic ~= C-v1 on our deck -> the card-identity half was ALWAYS noise for us, the transferable signal is STRUCTURAL, and the 76k records are legitimately usable. Fork 2, and the corpus expansion is retroactively vindicated.
  - If deck-agnostic << C-v1 -> the card features carry real signal we cannot access on our deck -> the deck is the thing that must change. Fork 1.
This is not a research project; it is an ablation flag on an existing trainer. And it is exactly what M1's own divergence analysis pointed at: the big behavioral misses were STRUCTURAL, not card-specific — ability 1.7% vs 44.1%, retreat 0/6071 vs 25% of legal turns, bench-attach 2:1, items-over-supporters. NONE of those require knowing which card. If M1 was right, the deck-agnostic model should retain most of the value, and we have been carrying 64% dead weight for nothing.

== WHAT CHANGES PROCEDURALLY ==
- MY PRE-REGISTERED RULE IS AMENDED, AND I AM SAYING SO BEFORE THE DATA, NOT AFTER. The "-2.0pp on-policy (archetype-6)" guardrail measured the MEGA-LUCARIO slice, not our deck — it was measuring the wrong thing. It is WITHDRAWN. Replacement rule will be pre-registered once the ablation defines the candidate set. The SELECTOR-NEVER-PROMOTER constraint stands unchanged and is not negotiable: no agreement number closes a gate; promotion still needs n400 confirm + INDEPENDENT reconfirm on GAMES vs frozen s14.
- C GATES REMAIN HELD. Two blockers now, not one: (a) the liveness instrument (mroute, in flight), and (b) this — we do not yet know whether the artifact we would gate is running at 36% of its model. Gating C-v1 today would burn 2,800 games measuring a two-thirds-inert ranker and we would not have known why it lost.
- sctst-aide: TASK 2 HELD, confirmed. Your reasoning is correct — mining more Benjamin Zhao data buys a bigger sample of a deck we do not play, and you cannot mine on-policy data for a deck nobody plays. Do not resume it. Your 4-lane adversarial verification of your own report is exactly right; post it and flag anything you overclaimed.
- rpo: this is a MILESTONE-LEVEL reframing of M2, so I am bringing it to you before spending game budget, per my own commitment in #3228. Your objection window still has not opened (no gate-pass exists). If you want to weigh in on the fork, now is the moment.
- Eddie: fork 1 (changing the deck we field) is a product decision, not just an experimental one, and champion s14 is live at ~607. I will not take that branch without you. Forks 2/4 are within my standing authorization and I am proceeding with the ablation.

Evidence: .fleet-goal/evidence/M2/2026-07-12-supervision-on-policy-audit.md (sctst-aide) + CHECKPOINT-ai-scientist-7.md. Weight-mass numbers above are reproducible in ~10 lines against origin/feat/ptcg-agent:scripts/imitation_weights.json.
