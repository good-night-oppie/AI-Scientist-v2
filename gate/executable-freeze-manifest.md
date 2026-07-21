# Executable freeze manifest — pre-T0 STEP 0 (BINDING)

- **date:** 2026-07-18 (RR#7 Section 6 local slot-resolution transaction engine: canonical verified evidence, sole lock/CAS/journal/recovery/atomic-replace/resolution-log ownership, and full local-fill reconciliation; Section 5A signed production authorization prior; Option-A jail-contract fold-in prior; RR#7A producer→receipt→fill closure prior; RR#5 authenticity + external-trust-root prior; original 2026-07-16, advisor-ratified order fac 7353fd7; capsule ptcg-pret0-freeze-chain-v1 item 1)
- **machine manifest:** `gate/executable-freeze-manifest.json` — sha256 `f8d3665a22deccb484ed523ec9ccef4a9dd5ddd92376073e767e7df50e8ca52a` (schema v4; regenerated receipts-last below)
- **generator (re-run to audit):** `gate/make_executable_freeze_manifest.py` (deterministic; fail-closed; RR#4: liveness source-hash equality loader, per-tool `tool_runtime` interpreter pins, generator-source/runtime-evidence projection split; RR#5: per-family `checkpoint_command_contract`, item-5 nested pool-integrity recompute + legal-for-preflight)
- **verification receipt:** `gate/step0-verification-receipt.json` — executed checks (280k target, receipt schema v2, 376 committed tests in the guard suite (including P0-v2 surfaces: remote capsule ingress, three-phase TRAIN/LIVENESS/RESOLUTION protocol, per-family artifact contracts, try/finally execution protocol, attempt lease ledger, and per-slice census binding validator), ARM-C entrypoints, I1-I7 liveness markers); manifest pins its core sha256
- **verified at freeze:** 102 files hashed; 17 frozen bundles re-hashed with ZERO drift vs their
  pool-manifest pins; ready-player-one-ptcg @ 5fe2fc0f (feat/ptcg-agent, tracked tree clean; external
  STEP-2 launch verifier + commit-pinned allowed_signers for real anchor signatures);
  armb-pilot suite 142/142 passed. (Counts here are MACHINE-ENFORCED against this document by
  test_rr6_doc_counts_match_machine_truth — the RR#6 doc-drift MUST-FIX.)

## RR#5 authenticity + external-trust-root layer (round 5, this revision)

Byte/hash chain was CLOSED; the round-5 review narrowed to receipt AUTHENTICITY
(hash proves integrity, not that a frozen trainer produced it) + the split
self-authenticating as its own root. This revision binds:

- **Top-level launch stamps (I1):** `validate_receipt.py` REQUIRES top-level
  `launch_mode`/`launch_constructor`/`launch_validation_core_sha256` + cross-level
  agreement with `curriculum.*`; the runner lifts them from the bridge/battery.
  Instrumentation games can no longer be laundered via a nested-only stamp.
- **External trust root (V1):** the STEP-2 launch is entered via the
  rpo-pinned `scripts/step2_launch_verifier.py` (OUTSIDE fac, rpo @ 442d6243),
  which reads a coordinator-signed anchor capsule carrying the EXPECTED split
  sha + the authorized root-verifier sha. `validate_launch_bundles.py` reads the
  anchor from `STEP2_LAUNCH_ANCHOR` and dies fail-closed without it; the expected
  split identity NEVER comes from the current split. Its immutable-projection
  impl is INLINE (no `import fill_checkpoint_slot` before authenticating it).
- **Per-family command contract (item 3) + producer wrapper (F1/F2):** the freeze
  pins a `checkpoint_command_contract` per family (trainer/config/argv/wrapper/
  validator shas). Production/attempt receipts must be emitted by the pinned
  `gate/produce_checkpoint.py`, bind real subprocess evidence + a launch-ledger
  entry, use the contract-derived argv (real trainer path, slot-bound
  slice/seed/output — a fake trainer path is refused), and the frozen family
  config. GBM/NN contracts are UNKNOWN-until-verified (fail-closed) pending
  arena-1 attestation + the coordinator's trichotomy pick.
- **No self-asserted booleans (item 4):** quality-blind liveness is an INDEPENDENT
  receipt re-verified by `gate/validate_liveness_receipt.py` (re-derives the pass
  verdict from planted controls). FAILED derives its signature from
  wrapper-captured stderr; ≥2 attempts with distinct IDs, same command, both in
  the ledger.
- **Cycle-break binding rule (item 5):** the preflight is legal only under a
  current ok=true trust chain OR an anchor-allowlisted predecessor freeze; the
  liveness loader recomputes the full nested `pool_integrity_core` sha and
  requires `legal_for_preflight`. No generic ok=false-but-captured.
- **External final-audit (item 6):** the guard-suite receipt core binds the final
  freeze sha + split sha/projection + generator-source projection + tested-consumer
  hashes; a repo-OUTSIDE final-audit capsule references its core (no
  self-referential cycle back into the freeze).

## RR#4 consumer-hardening layer (round 4, this revision)

The round-4 review closed every extraction/scanning finding and narrowed the
front to CONSUMERS accepting internally-consistent-but-unauthorized evidence.
This revision binds the fixes:

- **Root of trust (V1):** `validate_launch_bundles.py` now walks
  split-manifest → immutable projection → `bound_manifests` freeze sha →
  freeze bytes → validator+engine_guard self-pins, all fail-closed, before any
  pool check. The launch receipt is schema v2 and embeds the chain evidence.
- **Evidence staleness (L1/V2, the round's meta-pattern):** the liveness
  receipt is schema v2 and BINDS its sources (arm_symmetry file hashes, rpo
  HEAD, generator-source projection, freeze-generator identity); the loader
  refuses any receipt whose hashes differ from the pins generated in the same
  run. Receipts are re-generated LAST, on the final tree — never mid-chain.
- **Preflight bootstrap (coordinator ruling #3539):** the liveness preflight
  runs via `HarnessBridge.for_instrumentation_preflight` — pool/bundle/engine
  integrity FATAL, trust-chain state captured into the receipt; every battery
  is stamped `launch_mode`/`launch_constructor` at the bridge and
  `validate_receipt.py` refuses instrumentation-mode games as experiment
  evidence.
- **Q-A dispatch:** both arms obtain the battery via
  `harness_bridge.resolve_curriculum_battery` / `run_arm_generation` — the
  ONE dispatch point, exercised by committed tests through
  `run_arm_{b,c}_with_stub_harness` (same injected battery/counter object,
  identical accounting receipts). The AST scan stays supplementary and now
  distinguishes raise-only membership guards from counting forks.
- **Fill tool (F1/F2/F3):** production AND attempt receipts are schema-bound
  and verified FIELD-BY-FIELD (freeze identity == split-bound freeze, expected
  host, config re-hashed from named bytes, interpreter identity + argv ==
  `tool_runtime` pin — arena-1 rows refuse until attested; FAILED needs signed
  cores + frozen failure_category vocabulary); fills are serialized by a lock,
  parent-sha CAS on a fresh read, and a transactional journal with
  deterministic crash recovery.
- **`tool_runtime` (interpreter ruling):** per-CLI interpreter pins
  (realpath, binary sha, sys_version, dependency lock, command template);
  arena-1 environments are UNKNOWN-until-verified rows carrying per-script
  probe contracts (bus #3532, binding via #3536): the four inherited arena-1
  scripts have NO argparse — argv-garbage exit-2 probes are INVALID for them,
  and `gbm_transpile` exit 2 means fidelity-STOP with artifacts written.
- **Projection split:** `fac_source_projection` covers GENERATOR SOURCE only;
  `gate/receipts/` + `gate/split-manifest.json` form the runtime-evidence
  namespace, each bound explicitly (core-sha references / immutable
  projection / root-of-trust chain) so legitimate runtime evidence never
  forces a re-freeze.
- **Test receipt:** `gate/make_test_receipt.py` emits
  `gate/receipts/guard-suite-receipt.json` binding test-file hashes,
  interpreter identity, and pass counts for both committed suites.

## What is frozen (coverage)

| Group | Contents |
|---|---|
| Engine | cabt `libcg.so` sha256 `7acbfc7bc61d4f8233515c63debcfa454b8f804f138a6c395c599decc3dd17d0` (sha16 == Kaggle runner fingerprint, C2 BYTE-IDENTICAL), libcg-arm64.so / libcg.dylib / cg.dll, cabt.py, cabt.json, cg/{__init__,game,sim}.py wrappers (lib selection + battle marshaling), kaggle_environments 1.32.0 (`__init__.py` hashed). No version string exported — the byte hash IS the engine version. |
| Trainer/runner (fac gate/armb-pilot) | pilot_run.py (ARM-B entrypoint), harness_bridge.py (battery + counters), pfsp.py, armc_evolution.py (ARM-C node-5b), promotion.py, cutoff.py (280k pair-completion), validate_receipt.py (receipt schema v2, fail-closed), weighted_bc.py (Lock-2 trainer), config.json / config_pilot.json, both opponent-pool manifests |
| Evaluation battery | rpo scripts/eval_search_head2head.py (bundle loader, search_begin instrumentation, liveness I1–I7) |
| Checkpoint production | rpo scripts/policy_imitation.py, build_submission_search.py, build_imitation_dataset.py; teacher corpus imitation_pairs.jsonl; gate/slice-definition.json + generator (19 disjoint slices) |
| R-DIV / T_freeze tooling (D1a pin) | rpo scripts/mine_replays.py (extract_decks 60-card predicate, deck_key/write_deck_csv ordering, team_name_map), gate/tfreeze_snapshot.py, gate/rdiv_mine.py, harvester topup.py/harvest.py (index producers) |
| Vendored src tree | rpo src/ready_player_one/{__init__.py, ptcg/{__init__,cards,enums,policy,deck}.py, ptcg/cg/*} — featurizer dependencies + files build_submission_search vendors into bundles; src-tree libcg.so pinned with an explicit different-build note (ffd89bf9… ≠ runner 7acbfc7b…) |
| Trainer side-inputs | runs/replay_mining/inline_harvest{,_hop2}_20260712.json (archetype_teams inputs; STEP-2 linear training BOUND to --archetype-core-min=0) |
| Lockfiles | uv.lock, pyproject.toml, .venv/pyvenv.cfg |
| Arena-1 | gate/arena1_provenance_procedure.sh (BINDING VCS-less provenance: snapshot + record_launch ledger), arena1-recovery MANIFEST.sha256 (75 files, sha256sum -c 75/75) + all 15 recovered trainer/league scripts |
| Analysis interfaces | validate_receipt CLI, verify_differential CLI (the 1dec9b9 non-semantic escape hatch), armc_evolution gate analysis (d_gate_from_blocks / matched-block bootstrap / confirm_adoption), promotion scoring |
| Tests (interface-pinned) | armb-pilot tests/ (142 tests) |

## ARM entrypoints (file + callable + hash in JSON)

- **ARM-B:** `gate/armb-pilot/pilot_run.py` — `PilotRunner` generation loop, CLI `main()` (ARM="B").
- **ARM-C:** `gate/armb-pilot/armc_evolution.py` — `run_epoch()` (propose → guards → select → confirm); `shadow_promotion_recommendation()` is a separate per-generation callable (logging-only); `load_rotation_schedule()`.

## Search-call counter definition (identical semantics, both arms)

Primitive: `eval_search_head2head._load_agent` wraps each extracted bundle's
`agpkg.cg.api.search_begin`; +1 per invocation, per-bundle isolated counter.
Assembly: `harness_bridge.HarnessBridge.curriculum_battery` emits per-generation
`search_calls = {learner_search_begin, per_opponent_search_begin (post−pre delta),
per_family_search_begin}`. B and C share this ONE arm-agnostic implementation —
there is no arm-specific counting code to diverge; STEP 4 preflight still asserts
equality live on the real engine.

## Binding rules

1. **Semantic change** to any tier=execution-path file after this commit ⇒ all downstream
   pre-T0/decisive artifacts INVALID (redo affected steps + downstream).
2. **Non-semantic patches** only via the fixed-input differential pass
   (`verify_differential.py`, rev 1dec9b9 pattern) + trainer output equivalence + launch
   manifest hash + fresh A/A reconfirmation.
3. **arena-1**: run `arena1_provenance_procedure.sh snapshot` before every launch and
   `record_launch` for every training command; any arena-1 artifact without a matching
   launch-ledger line is a post-T0 invalidator ("not reconstructible to source/environment").
4. Interface-pinned tier (tests, differential tooling, index producers): hashes recorded for
   audit; semantic change there requires re-ratification but does not by itself invalidate
   game artifacts.
5. **Runtime revision**: every pre-T0/decisive execution runs with the harness repo at head
   `f8d2caf` and a CLEAN tracked tree; a launch-provenance head/dirty mismatch vs this freeze
   is a post-T0 invalidator.
6. **STEP-2 linear training** is bound to `--archetype-core-min=0` (archetype filter off);
   the val_archetype6 report slice is non-binding diagnostics.
7. **Search-bundle guard (executable)**: while the vendored src-libcg differs from the runner
   engine, any search tarball not byte-matching the frozen allowlist ABORTS generation — new
   search-family bundle builds are FORBIDDEN until reconciled.
8. **Environment asserts**: engine sha == runner sha, rpo HEAD == `f8d2caf`, full status
   (incl. untracked; allowlist = `.fleet-goal/` only, content hashed) asserted at START and
   END of every generation; explicit-list coverage aborts on any new/removed file.

## RR#2 repair round 2 (this revision)

Reviewer verdict on the prior revision: R1+R2 PASS-CLOSED, remainder HOLD. Folded here:

- **N1** — `no_training_preflight.py` silently dropped nonexistent roots, so `--roots
  /tmp/does-not-exist` yielded a VACUOUS PASS. The `--roots` override is gone entirely; roots
  derive from a frozen table keyed by `--host-label`, are asserted non-empty/existing/dirs,
  `find` exit 0 is asserted, and the tool's own sha is recorded in every receipt core.
- **R3.2** — `validate_no_training_receipt.py`: receipts are untrusted input. Schema, core-sha,
  scanner pin, host label, expected roots, exit semantics, counts, count/array consistency and an
  EARNED pass flag are all fail-closed. A fabricated `pass: true` is rejected.
- **T1** — `tfreeze_snapshot.py`'s `--allow-gaps` escape hatch is REMOVED; any gap always aborts.
  `rdiv-decklists.json` now records positive gap-free evidence + an invocation receipt.
- **D-seat** — the seat join was FAIL-OPEN when a payload lacked `rewards`. Now: absent /
  non-list / short-coverage rewards ABORT (measured 0 occurrences, so the strict rule costs
  nothing); a seat is VERIFIED only if its index reward is non-None and equals the payload's;
  UNVERIFIABLE seats are EXCLUDED from deck extraction. **R-DIV was RE-RUN, and slot 1
  materially changed** — kashiwashira's previous deck came from an unverifiable seat.
- **D3** — exclusion now aggregates over connected components of the (team string ↔ team_id)
  graph, so an ID-excluded team is excluded under every name.
- **E1.1** — the FAC tree is asserted at start AND end (content-addressed staging snapshot); it is
  deliberately NOT recorded in the manifest, which would destroy reproducibility. The tree is
  pinned by CONTENT instead: every gate tool now has its own file hash here.
- **Q4** — the filename-prefix search guard is replaced by `gate/engine_guard.py`, which OPENS each
  bundle and hashes any vendored engine. Sunk into three enforcement points: freeze time, launch
  time (`validate_launch_bundles.py`), and build time (rpo `build_submission_search.py` @ 1649f30).
- **R5** — `fill_checkpoint_slot.py` is the only admissible writer of `artifact_sha256`/
  `slot_status`; it verifies the parent sha and proves the immutable projection is UNCHANGED
  across the edit, refusing any other delta.
- **step 3** — `armc_liveness_preflight.py` replaces the CLAIM of liveness with an EXECUTED
  receipt: ARM-C transitions all fire and are seed-deterministic; real games prove search
  counters fire WITH a negative control (`linear_armA` = 0); arm symmetry is machine-proven as
  semantic identity (zero arm-conditional branches) — numeric equality of two batteries is NOT
  asserted because the engine RNG makes it unsatisfiable.

## RR#2 round 3 — RQ navigator rulings (2026-07-16 ~21:40Z)

**Interpretation boundary (navigator, binding):** the liveness receipt's
`armc_branch_liveness.transitions.deterministic_given_seed` asserts ONLY that ARM-C's
transition / rotation / control logic (`run_epoch`) reproduces given fixed inputs and a fixed
seed. It must NEVER be read — here or in any downstream document — as a claim that the cabt
**engine trajectory** is seed-deterministic: the closed engine seeds from `std::random_device`
and no seed pin is possible. The receipt already carries this in
`arm_symmetry.numeric_equality_claim`; this note is the interpretation guard, deliberately
placed in prose rather than by editing a hash-pinned execution tool for a documentation
constraint.

**Scope boundary (navigator, binding):** the seven inherited arena-1 recovery scripts are the
same argv-blind class but are NOT fixed here merely for that. Any one of them that actually
participates in STEP-2 checkpoint training, packaging, transfer, recovery, hashing or
verification enters the validity boundary the moment it does, and MUST have an explicit argv
contract that rejects unknown arguments BEFORE the first checkpoint outcome exists. Scripts never
called by STEP 2 or by decisive provenance stay out of scope.

Four decision forks were put to the RQ navigator channel (the same channel that issued the
pre-T0 binding order and the G1-G4 refinements). Its rulings, executed here:

- **FORK 1 — semantic identity DISCHARGES the arm-symmetry requirement; do NOT build a
  double-count.** Rationale (navigator): the >10% total-search-calls requirement is that B and C
  use the same counting semantics and the same instrumentation path — NOT that two independent
  stochastic batteries produce equal numbers. B/C counts that differ are a REAL
  algorithmic-compute difference and are exactly what the sensitivity trigger measures; they are
  not a counter failure. Live corroboration: two runs of the identical battery produced s18
  search_begin = 96 and 600 (14 vs 16 games) while the negative control stayed exactly 0 in both
  — the semantic property is stable, the numbers are not.
- **FORK 2 — per-seat EXCLUSION adopted, and that ruling IS the final ratification of the deck
  change** (zero-outcome, externally-triggered correctness amendment, not the outcome-driven
  reinterpretation D1a forbids). `25c6e394…` is authoritative; `070d81bd…` is explicitly recorded
  as SUPERSEDED in `superseded_artifacts` inside the R-DIV artifact. Rule text, miner/parser
  hashes, deck hashes and evidence counts are re-frozen in this same atomic recommit.
- **FORK 3 — fix the WHOLE argv-blind class and re-run the chain once; may NOT be downgraded to a
  noted limitation** (a historical invocation cannot prove whether its args were honored =
  provenance ambiguity). All 7 chain CLIs now declare zero arguments and reject unknown ones
  (exit 2, verified on each; `armc_liveness_preflight` verified under its pinned venv). Treated as
  a non-semantic instrumentation correction — and demonstrated as such: `slice-definition.json`,
  the T_freeze snapshot (086fb8b1) and all 4 deck hashes reproduce byte-identically across the fix.
- **FORK 4 — PRIOR RULING VOID / SUPERSEDED; re-ruled by the RQ navigator after I corrected the
  premise.** Recorded exactly as the navigator required:

  ```
  Prior FORK-4 ruling: VOID / SUPERSEDED
  Reason: artifact-population census used non-frozen same-name tarballs
  Correct S1 fact: both frozen S1 artifacts are bare .py files and vendor no engine
  ```

  The S1 engine limitation is **deleted, not shortened or softened** — S1 has no
  vendored-engine mismatch to disclose. S1 remains thin and high-variance (exactly two single
  opponents), but that is a pre-existing *representativeness* limitation and **no engine-version
  explanation may attach to it**.

  **My error, on record:** I claimed "8 engine-vendoring bundles including both S1 sealed". I had
  globbed every `*.tar.gz` on disk instead of enumerating the 17 pinned entries, and hit a
  same-name-different-artifact collision — `runs/pcmm_r1/metamon_router_r1.tar.gz` (`0b259d61…`)
  is not the frozen `artifacts/metamon_router_r1.py` (`ceaf1113…`). The manifest's own per-bundle
  `vendored_engines` fields already held the truth. Found by coordinator ai-scientist-10.

  **The measured fact (D_train scope note — methods/provenance, NOT an internal-validity
  failure):** of the 17 frozen opponent bundles, three D_train opponents —
  `heur_deck_2c1368bc03`, `heur_s14_refdeck`, `search_s18_oppmodel` — use vendored engine
  `ffd89bf9` for opponent-side internal lookahead. All actual match state transitions, legality
  and results are decided by the runner engine `7acbfc7b`. B and C share the identical frozen
  opponent universe and artifact definitions, but produce different *realized exposure* per their
  own curriculum. This is therefore **not** an evaluator mismatch, a match-integrity failure, a
  B/C instrumentation asymmetry, or sealed-S1 contamination — it is an implementation property of
  a frozen opponent policy. So long as the final action is still validated by the runner legality
  path, what internal world model an opponent uses is part of that opponent's identity, exactly
  like its heuristic, search depth or value function.

  **The limitation that actually survives (navigator's, and the one the false claim was hiding):**
  the three vendored-engine opponents are not scattered at random — they **covary with the
  `heuristic-ref-deck` and `live-search` family identities**, and C's treatment *is* changing
  family-level sampling weights, so realized exposure to `ffd89bf9` opponents may correlate with
  arm, epoch and adoption dynamics. This does **not** break the primary estimand (differing
  exposure is part of the curriculum treatment, not uncontrolled execution bias), but it bounds
  two stronger readings — family-level adoption cannot be read as a pure strategy-family effect
  (family and internal-engine version are not separately manipulated), and the observed C-vs-B
  effect cannot be claimed to transfer unchanged to a runner-matched opponent pool. Binding shape:

  > The causal comparison is internally valid for the frozen mixed-implementation D_train opponent
  > pool. However, opponent family and internal lookahead-engine version are not separately
  > identified for three training opponents, so mechanism-level attribution and generalization to
  > a runner-matched opponent pool remain limited.

  No new sensitivity arm; no change to the confirmatory design. The writeup text itself is
  coordinator-owned and is not written here.

## RR#3 round-3 repair (BLOCK verdict) — the battlefront moved to the consumer layer

Every RR#2 original finding is CLOSED. What remained was the **consumer/wiring/binding** layer:
the tools that READ receipts, the validator that GATES launch, the tool that FILLS slots, and the
hash edges BETWEEN manifests. My receipts were fine; the things reading them were not.

- **(2) Hermetic committed tests** — `gate/tests/test_freeze_guards.py` + `gate/tests/test_rr7_primitives.py` + `gate/tests/test_step2_attempt_policy.py` + `gate/tests/test_step2_fill_ordering_guard.py` + `gate/tests/test_step2_attempt_lease.py` + `gate/tests/test_artifact_contract.py` + `gate/tests/test_execution_protocol.py` + `gate/tests/test_fill_remote_checkpoint_slot.py` + `gate/tests/test_three_phase_protocol.py` + `gate/tests/test_validate_census_in_split.py`, 376 committed tests — grown
  outward from the six probes a reviewer or the coordinator actually executed against a real commit
  (plus Q-A's replacement) through the RR#4–RR#7 layers: receipt authenticity, anchor trust, projection
  reproducibility, execution_context fail-closed, the two-phase terminal-ledger boundary, and the RR#7
  producer-closure primitives (slice derivation, canonical USTAR, failure classifier, runtime closure,
  bounded capture, orphan quarantine). C2 was "zero committed tests": every guard had been verified by an ad-hoc shell
  probe I ran once and reported — not re-runnable evidence, and not a regression barrier (the T1
  regression happened exactly that way). The suite is **negative-controlled**: re-adding the
  `--manifest` surface makes probe 3 fail, removing it makes it pass again.
- **(3) FAC content projection** — the status-hash form was REJECTED and the reviewer was right:
  it hashed `git status` PATHS/TEXT, so a dirty1→dirty2 content mutation was invisible.
  `fac_source_projection_sha256 = sha256(sorted(relpath, mode, size, content_sha256))` over
  generator INPUTS, asserted start==end, **written into the manifest** (232 files).
- **(5) Liveness loader** — the reviewer's fake receipt (deadbeef tool sha, 0 invocations,
  NON-empty branch list, `pass:true`) was ACCEPTED, and the loader **hardcoded branch-count 0**
  into its own output. Now fail-closed on core-sha recompute, schema, tool pin vs the frozen tool
  (this also discharges C6's pattern), invocations>0, every transition flag, positive AND negative
  counter controls, decisions>0 — and the branch list is **READ FROM the receipt**.
- **(6) Launch validator** — the arbitrary `--manifest` surface is GONE (the reviewer pointed it
  at an unfrozen bundle and got PASS). Pool manifests now come FROM the freeze, by hash; exact set
  + count==17 + duplicate-ID refusal; a launch receipt is emitted. **Wiring proof:** the barrier
  lives in `HarnessBridge.__init__`, and every game in every arm goes through a HarnessBridge, so
  no path reaches the engine unvalidated — a validator nobody is proven to call is not a gate.
- **(7) Structured bindings inside the immutable projection** — closes C5+C7+Q-B's tooth at once:
  `executable_freeze_manifest_sha256` and `rdiv_decklists_sha256` (the manifest-to-manifest edge
  was OPEN), plus the slot-1 block binding `25c6e394…` STRUCTURALLY NOW rather than deferring to
  STEP 3, because a deferred binding is an unbound one. Verified covered: tampering the bound deck
  hash moves the projection.
- **(8) Fill tool REBUILT** — `--artifact-sha256` accepted `000…0` for a non-existent artifact and
  marked a slot FILLED, exit 0, while the projection still "verified" (it excludes those fields by
  design). That reopened two selection channels. The operator-supplied-hash surface is GONE: the
  tool takes `--artifact-path` and hashes the bytes itself; FILLED requires a production receipt
  bound to the slot's own frozen row plus a quality-BLIND liveness bar; FAILED requires bounded
  same-seed attempt receipts with a reproduced deterministic-failure signature; every resolution
  appends to an append-only log; the write is atomic.
- **(9)** Fresh create-only re-freeze from the exact parent `423ec1bc`. T_freeze re-ran
  byte-identical (`086fb8b1`) and all four deck hashes are unchanged — stated explicitly because
  the ruling asked to be told if they were not.

**Q-A resolution:** the numeric-equality requirement is WITHDRAWN; my AST scan was ruled
INCOMPLETE (If/IfExp + token matching misses alias, match, dict-dispatch, helper-selection forks)
and is now SUPPLEMENTARY only. The binding replacement is committed as tests: B/C resolve to the
same `curriculum_battery` **function object** (identity, not name), `armc_evolution` references no
counter symbol at all, and a **deterministic stub battery** through both arms' paths yields equal
counts — assertable precisely because no engine is involved.

**Finding surfaced by writing the suite:** the chain spans **two interpreters**. `rdiv_mine`
imports `zstandard` (system python only); `armc_liveness_preflight` imports `kaggle_environments`
(pinned venv only). Under the wrong interpreter each dies at module import with rc=1 **before
argparse runs** — so an argv guard inside `main()` is only reachable under the right one. Probing
all seven under a single interpreter would have silently proved nothing for one of them; the suite
now probes each CLI under the interpreter it is actually invoked with.
