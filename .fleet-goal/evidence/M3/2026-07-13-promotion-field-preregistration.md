# PRE-REGISTRATION — promotion field v3 (SUPERSEDES v2 @4d48e4d, which was REFUTED before use)

**v2 is withdrawn. It was a category error and no number was ever produced under it.** v2 proposed
six "meta arms" (kashiwashira 1245.7, Majkel1337 1202.0, …) built as *their deck + OUR policy*.
Those MMRs belong to their **agents** (deck AND policy). We have their decks; we cannot obtain their
policies. So each proposed arm was **our own artifact wearing someone else's ladder rating** — a
worse contamination than the 2c1368bc03 bug it was written to fix (that one admitted a
ladder-rejected artifact; this would have admitted seven un-submitted ones that *looked*
ladder-anchored). Caught by rpo #3332 before any GBM number existed.

**The proof was already in our own data** (sctst-aide's audit): every meta deck, played by our
policy, LOSES to our own 605-MMR champion — meta0 0.489 (n=1000), meta2 0.464 (n=1000), meta1 0.200,
meta4 0.275. **The ~500 MMR gap is not in the decks. It is in the POLICY.**

## THE RULES (sctst-aide #3331, adopted verbatim by rpo #3332)

- **(1a) NECESSARY — ladder-MEASURED.** No ladder standing ⇒ DIAGNOSTIC-ONLY. The standing must be
  that **of the exact artifact as submitted** — never the rating of the player whose deck it borrows.
  (Self-play checkpoints have none by construction.)
- **(1b) SUFFICIENT — ladder-VALIDATED.** A standing BELOW THE CHAMPION ⇒ LADDER-REJECTED ⇒
  DIAGNOSTIC-ONLY regardless of local strength.

## THE PROMOTION FIELD (run the rules honestly and it collapses to one arm — that is correct)

| arm | standing | role |
|---|---|---|
| **live_s14_reference** | **605.4, submitted, IS the champion** | **THE PROMOTION ARM (the only one)** |
| 2c1368bc03 | 567.9 < champion ⇒ ladder-rejected | DIAGNOSTIC (the canary; never resubmit) |
| top-6 meta decks (their deck × our policy) | never submitted ⇒ no standing | DIAGNOSTIC / **LEAGUE** |
| s18, 58f62b5135, armA, B1, B2, all self-play checkpoints | no standing | DIAGNOSTIC |

**The only ladder-valid local test we possess: DOES THE CANDIDATE BEAT s14?** Not a poverty of
imagination — the honest inventory. s14 is the one artifact we own whose ladder standing is real,
measured and current.

## THE AUTHORITY DOCTRINE (C1 WITHDRAWN — replaces it)

rpo withdrew C1 ("prove the local gate predicts the ladder") because the audit shows **it never
can** — the 500 points live in policies we cannot obtain, so no field, however large, can calibrate
against them. A contingency that cannot be discharged is a wall, not a gate. Replaced by the same
asymmetric shape as every correction this cycle:

- **THE LOCAL GATE HAS KILL AUTHORITY.** Cheap, sound, already correct on armA / B1 / B2.
- **THE LOCAL GATE HAS NO CROWN AUTHORITY.** Beating a field 500 MMR below target proves nothing —
  2c1368bc03 is the receipt (four-rung pass, 0.571 over 800 games, still under s14 on the ladder).
- **ONLY THE LADDER CROWNS.** Promotion evidence is a submission, not a gate pass.
- **Phase 3 is NO LONGER gated on an impossible proof** — it is gated on the asymmetric rule plus
  G4 / league discipline. Phase 2 continues.

## WHY THE PROGRAM IS COHERENT (not doomed)

The problem is a ~500 MMR **policy** gap. Deck search attacked the deck — wrong target, and the
audit shows it always was. Imitation attacked the policy correctly but agreement never converted.
**Self-play is the only method that can produce a policy stronger than anything we have** — it copies
no one and bootstraps past its own teachers. Decisively: **self-play does not need a ladder-strength
field.** AlphaZero surpassed all human play training only against itself. The league's job is
DIVERSITY and anti-overfitting, not absolute calibration. The field's 500-MMR gap is fatal to it as a
CROWNING instrument; it was never fatal to the training loop.

**And the noise floor stops being frightening:** gap to close ≈ **500 MMR**; ladder noise floor ≈
**100 MMR**. A real M3 success is ~5× the noise — visible from orbit. The floor only blocks marginal
gains, and marginal gains were never going to be enough.

## THE FIELD WORK IS REPURPOSED, NOT WASTED

The top-6 decks move from the GATE to the **SELF-PLAY LEAGUE** — deck diversity, anti-deck-overfit,
where no ladder standing is required and none is claimed. Keep every deck. Keep the worst-arm
fragility check as DIAGNOSTIC signal. `live_ladder_snapshots` mandatory on every arm, everywhere.

## Floors (unchanged, now KILL-only)

Screen n40 vs s14: kill on failure. Confirm n400 + independent reconfirm vs s14: kill on failure.
n40 = mirage (kills, never crowns). Liveness=LIVE for any learned candidate. Asymmetric
admissibility (#3325). A gate PASS is a licence to *ask Eddie for a probe*, never a promotion.

— ai-scientist-7, 2026-07-13, per rpo #3332 + sctst-aide #3331
