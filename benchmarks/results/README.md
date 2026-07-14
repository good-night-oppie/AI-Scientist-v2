# Benchmark results (frozen Phase 8 artifacts)

`verdict.md` is the frozen, pre-registered crossover-benchmark verdict — committed
verbatim; its internal `.supergoal/evidence/*` references point to the run's local
evidence tree (not in-repo). The measured data behind every number is committed here:
`summary.csv` (grid aggregates), `provenance.csv` (single-node + 6-node steelman arms),
`concurrency.csv` (K=1..8 writers), `dedup_granularity.txt` (whole-file probe), and
`crossover.svg` (the crossover curve). Reproduce with `benchmarks/run_bench.sh`
(seed-pinned; see `benchmarks/bench.py --help`).
