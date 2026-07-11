# Runner-faithful validation — `2c1368bc03`

_Verified: 2026-07-11T21:05Z_

## Artifact identity

- Bundle: `/home/admin/gh/ready-player-one-ptcg/submission_search_deck_2c1368bc03.tar.gz`
- Bundle SHA-256: `e31d0561ef21237794cd21e06615200a5d64dff24fd9255ec6b7b381da7d7b83`
- Deck: `/home/admin/gh/ready-player-one-ptcg/runs/deck_search/decks/2c1368bc03.csv`
- Deck SHA-256: `d65f30c88b5c5ba0ea24e073bc38103ac190f2abee5b0839cce8d3eab54ef3e2`
- Machine-persisted validator output:
  `/home/admin/gh/ready-player-one-ptcg/runs/deck_search/validation_2c1368bc03.log`

## Command

```bash
cd /home/admin/gh/ready-player-one-ptcg
.venv/bin/python -c 'from pathlib import Path; from scripts.build_submission_search import validate; validate(Path("submission_search_deck_2c1368bc03.tar.gz").resolve(), 20)'
```

Exit status: `0`.

The environment import preamble emitted unrelated LiteLLM cost-map and optional
Kaggle-environment warnings. The exact validator result was:

```text
self-play vs random: 19W 1L 0D inv0 | winrate 95.0% over 20 | 0.22s/game
SEARCH BEGIN CALLS: 20 across 20 games
SEARCH INACTIVE/FALLBACK: calls <= games; for live-s14, calls == games is the known first-move failure signature
VALIDATION OK — runner-faithful load, zero forfeits, search_active=False
```

## Strict search-active gate

The same validator with `require_search_active=True` over two games produced
`SEARCH BEGIN CALLS: 2 across 2 games` and exited `1`, proving the strengthened
gate rejects the known dead-search signature.

## Interpretation

- Proven: the archive loads through the Kaggle file-path runner, completes games,
  exposes the intended agent entrypoint, and has zero forfeits in this sample.
- Not proven, and explicitly false for frozen live-s14: active tree search. Exactly
  one `search_begin` per game is the known first-move exception followed by
  heuristic fallback.
- The candidate's promotion evidence is therefore a deck-only improvement under
  the deployment-faithful heuristic-effective live-s14 policy. It must not be
  described as a search-active agent.
- The detached harvester was upgraded and restarted as PID `2260719`; final
  selection now validates both pre-existing and newly built bundles and persists
  the corresponding `validation_<candidate>.log` before reporting success.
