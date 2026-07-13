# C2 ENGINE VERDICT — MATCH (CONCLUSIVE). 2026-07-13.

Source: probe 54634503, episode 85694950, agent-1 stderr log (fetched via
`kaggle competitions logs 85694950 1` after 429 decay; raw log committed alongside).

## The verdict, per the amended ladder (addendum 3, e1e582c)

| Fingerprint | Kaggle runner | Local | Verdict |
|---|---|---|---|
| `libcg.so` sha16 | `7acbfc7bc61d4f82` | `7acbfc7bc61d4f82` | **BYTE-IDENTICAL** |
| `libcg-arm64.so` sha16 | `2e39f8cab281c3b0` | `2e39f8cab281c3b0` | **BYTE-IDENTICAL** |
| kaggle_environments | 1.32.0 | 1.32.0 | MATCH |

sha MATCH = the CONCLUSIVE branch: same engine, same build. **Every local gate resolves games on
the exact bytes the Kaggle runner executes. Local gates are ADMISSIBLE for ladder inference.
rpo C1(ii) is LIVE.** No semantic canary needed for admissibility (the self-prediction canary
remains boarded for the search-vs-env build-equivalence question only — non-blocking).

Consequences:
- The "local instrument measures a different game" hypothesis for M1's local→ladder gap is DEAD.
  The surviving explanation is FIELD COMPOSITION (single-arm vs mixed-field) — exactly what the
  pre-registered mixed-field worst-arm gate already addresses.
- **M3 Phase-2/3 training spend: rpo's C1 contingency is SATISFIABLE via (ii)** — the calibration
  point accrues as the probe's rating stabilizes (~50 episodes; early trajectory 600→466→499,
  placement variance large as expected; do NOT read the noise floor yet).

## Runner environment (bonus intelligence)

- **torch 2.6.0+cu124 PRESENT on the runner** (absent locally!) — the deployment tier ladder gains
  a full-torch option; numpy tier (2.4.6 runner / 2.5.1 local) remains the planned path; jax 0.5.2
  also present. Python 3.11 on runner vs 3.13 local (pure-python bundles unaffected; no compiled
  wheels shipped).
- Behavior channel validated end-to-end in the same log: `decision=2 ENCODE idx=1 numpy=True`.
- Latency: decisions 0.01–16.8ms (max on decision 1) — G0 formally CLOSED, ~5 orders of magnitude
  under the ~6s/decision budget.
