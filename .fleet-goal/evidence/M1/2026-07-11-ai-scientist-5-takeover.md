# M1 evidence — ai-scientist-5 takeover

_Verified: 2026-07-11T20:58Z_

## What's done

- Recovered the active PTCG deck-search goal from Claude session
  `6adb5ba8-e934-46e3-8270-9f17b96885ba` and the durable handoff/project files.
- Completed idempotent fleet enrollment for lineage `ai-scientist`; A2A intent and
  watch-confirmation request landed as shared-log entries `#2794` and `#2795`.
- Ran `fleet_doctor.sh heal` and a post-heal JSON diagnosis. Fleet status is
  `healthy`, bus reachable, `ai-scientist-5` live, and the harness-41 sweep watches
  the exact `ai-scientist` lineage token.
- Registered the external deck evolution in Weco Observe run
  `7393d6ae-46a4-4b22-9cb5-a48abbab3d41` with metric
  `head_to_head_winrate`: A/A control step 0 = `0.495`; candidate step 1 =
  `0.57125` from 457/800 independent confirm plus reconfirm games.
- Recomputed the promotion evidence directly from saved artifacts. Candidate
  `2c1368bc03` remains the only `PROMOTABLE` entry among 587 unique candidates and
  641 ledger rows at the verification snapshot.
- Sent the refreshed evidence and parent-approval request to `rpo,harness` as A2A
  shared-log entry `#2800`.

## Supporting evidence

- Ledger: `/home/admin/gh/ready-player-one-ptcg/runs/deck_search/ledger.jsonl`
- Candidate CSV: `/home/admin/gh/ready-player-one-ptcg/runs/deck_search/decks/2c1368bc03.csv`
  - 60 cards; 2 Kyogre; 34 basic Water Energy; max non-energy name copies = 4
  - SHA-256: `d65f30c88b5c5ba0ea24e073bc38103ac190f2abee5b0839cce8d3eab54ef3e2`
- Confirm: 228-172, win rate 0.570, Wilson `[0.521, 0.618]`
- Independent reconfirm: 229-171, win rate 0.5725, Wilson `[0.524, 0.620]`
- Review bundle: `/home/admin/gh/ready-player-one-ptcg/submission_search_deck_2c1368bc03.tar.gz`
  - SHA-256: `e31d0561ef21237794cd21e06615200a5d64dff24fd9255ec6b7b381da7d7b83`
  - Static inventory contains `main.py`, `deck.csv`, and the vendored `agpkg`
    runtime including `agpkg/cg/libcg.so`.
  - Archive hashes for `main.py`, `agpkg/policy.py`, `agpkg/search_policy.py`, and
    `agpkg/cg/libcg.so` match the frozen s14 baseline; the candidate CSV is the
    intended changed artifact.
- Independent runner-faithful validation is now persisted at
  `evidence/M1/2026-07-11-runner-validation-2c1368bc03.md`: 19-1 versus random,
  zero invalid/forfeit games, and stable artifact hashes. It also corrects the
  prior semantic error: search_begin `20/20` is the known live-s14 dead-search
  signature, so the validated claim is runner load + zero forfeits under the
  heuristic-effective policy, not active search.
- At the original verification snapshot, the search worker and detached harvester
  were both live in independent sessions: search PID 1829394; historical harvester
  PID 2136762. The harvester was later replaced by corrected PID 2260719 so final
  bundles cannot bypass validation.

## What's next

- Let the detached 10-hour search and harvester continue; do not start a competing
  optimizer or session-bound experiment.
- At completion, audit the final summary, identify the best fully reconfirmed
  `PROMOTABLE`, log it as the next Weco Observe step, and refresh the review bundle.
- `rpo` reviews the evidence and decides whether to use a scarce Kaggle latest-two
  slot for a deck-only ladder probe.

## Any blockers

- No infrastructure blocker.
- Promotion/final child-goal completion is gated on parent `rpo` approval by
  `.fleet-goal/PROTOCOL.md`.
