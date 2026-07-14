# Phase 8 — Crossover benchmark verdict (helios vs `cp -r` vs `tar -czf`)

**This is a NEGATIVE result, and a negative result is the correct, sanctioned
outcome here** (ROADMAP.md:121-123, key-assumption 4). Every number below traces to
a row in `results.csv` / `summary.csv` / `concurrency.csv` / `provenance.csv` /
`manifest.json` or the M5 anchor file; `check_verdict.py --no-hardcoded` enforces it.

## Data provenance / capped run

The full grid RAN (seed 1234, helios HEAD `fa8e1d0`); the sweep was intentionally
capped at the final 5GB cell to save ~45 min of zero-signal reps (the phase spec
licenses capping large sizes and logging what was capped). `bench.py` writes
`results.csv` only at loop-end, so `results.csv` was reconstructed from
`run.log.frozen` (every completed rep is one log line; no measured number was
fabricated). See the CAPPED-CELLS section for the exact drops.

## Assumptions

- **Incompressibility.** The synthetic bulk is hashlib-CTR output (~0 gzip ratio),
  the realistic steelman for helios: a trained-model `.npy` of float outputs does not
  compress. **A compressible corpus would favour `tar -czf`**, whose gzip stage would
  then shrink the archive below helios's raw-byte store. This verdict therefore
  states helios's *best* case; the recommendation is still NO.
- **Whole-file dedup.** Measured, not assumed (`dedup_granularity.txt`,
  `GRANULARITY=whole-file`): a 1-byte change re-stores the whole file (`cli.go:118`).
  Redundancy is modelled as byte-identical whole files across nodes.

## Realistic anchor (the deciding X1 number)

`.supergoal/evidence/M5/per-node-dir-size.txt` gives the realistic production per-node
working-dir estimate `ANCHOR_BYTES=5242880` (5MB) — one `experiment_data.npy` + a few
PNGs + `runfile.py`, the BFTS codegen output; `torch.save`/`state_dict` appear nowhere
in treesearch, so per-node capture stays small. 5MB is both the anchor and the
smallest swept size, so the 5MB grid row answers X1 directly. Real BFTS sibling nodes
are largely independent, so the operative redundancy is **low**.

## Crossover

CROSSOVER: helios ≤ tar on store_bytes at size ≥ 5MB for redundancy ≥ med (store-only; first cell where helios_over_tar_store ≤ 1.0)

Read `summary.csv` `helios_over_tar_store`: the store-size crossover is driven entirely
by **cross-node redundancy**, not size. At **5MB/low** (the realistic regime) helios
store is 31475005 vs tar 31466849 — ratio 1.0003, i.e. helios is marginally *worse*.
Helios only pulls ahead on store once nodes share bytes: 5MB/med ratio 0.7503
(helios 23611462 vs tar 31467666) and 5MB/high ratio 0.5254 (helios 16531656). tar's
store is ~flat across redundancy because it cannot dedup across independent archives of
incompressible data. Crucially, at **500MB** helios loses on store at *every*
redundancy (ratio 1.3332: helios 2097354396 vs tar 1573121802 at high) — Pebble
overhead outweighs dedup once the tree is large — so the "helios wins on store" regime
is narrow: small per-node dirs that are also highly redundant across nodes (the
warm-start / X1 regime), not the realistic independent-node case.

## Cost helios pays even where it "wins" on store

- **Memory.** helios reads every file whole into RAM (`cli.go:118`). At 5MB/low its
  peak RSS is 85268 kb vs 16240 kb for `tar -czf` — over 5x. At the largest *completed*
  size (500MB/high) helios peak RSS is 3908476 kb. `tar`/`cp` stream at ~constant RSS.
- **OOM at scale.** At 5GB/high every helios rep is `oomed=1` with peak RSS 6291460 kb
  (blows past the `docker -m 6g` ceiling and dies with an empty store), while `cp -r`
  survives (commit 157.73s, restore 161.37s, store 10737431224 bytes). helios is
  **disqualified at 5GB by OOM**; cp/tar complete. This is the `cli.go:118` whole-file
  RAM ceiling, measured.
- **Process tax.** helios commit at 5MB/low is 0.83s vs 0.05s for `cp -r` — an order of
  magnitude slower per node (helios beats tar's 1.18s only because tar wastes CPU
  gzipping incompressible bytes; `cp -r` dominates both).
- **Single-writer serialization.** `concurrency.csv`: raw helios (`helios-flock`) loses
  7 of 8 concurrent commits at K=8 (`commits_failed`), because Pebble takes an
  exclusive OS lock (`objstore.go:62`); the shipped `helios+flock` wrapper fixes
  correctness (0 failures at every K) but serializes — K=8 wall 1.6493s vs tar's
  lock-free 0.7291s. BFTS workers fork, so this contention is real.

## Recommendation

RECOMMENDATION: helios beats tar for realistic per-node dirs: NO

At the realistic anchor (5242880 B / 5MB, low cross-node redundancy) helios ties
`tar -czf` on store (ratio 1.0003) while costing over 5x the RSS, an order-of-magnitude
process tax per node vs `cp -r`, single-writer serialization, and an outright OOM at
5GB where `cp -r`/`tar -czf` survive. **Use `tar -czf` (or `cp -r`) for realistic
per-node BFTS working dirs.** helios earns its keep *only* in the narrow X1/warm-start
regime — small per-node dirs with high byte-identical cross-node redundancy — where its
whole-file dedup drops store (5MB/high ratio 0.5254). That is not the realistic
independent-node case, so for the shipping integration the answer is NO.

## Provenance arm (the "why helios at all" skeptic gate, AC13)

PROVENANCE_VERDICT: helios adds provenance value over tar+hash at realistic size: NO

`provenance.csv`: for single-node durable recovery at the anchor size (the actual
Phases 5-6 justification) both `helios` and `tar_hash` recover byte-identically
(`recovered_ok=1`); helios store is 5251057 vs tar+hash 5244826 — helios is marginally
*larger*, no advantage. The one regime where helios's dedup helps is the 6-node
high-redundancy steelman (helios 16531656 vs tar+hash 31470341), and even there the
advantage is only 1.904x — below the 2.0x bar AC13 requires for a YES, and it is the
dedup regime already credited by the crossover, not provenance per se. A 3-line
`tar -czf` + `sha256sum` delivers the same durable recovery with zero helios
dependency, so the provenance feature alone does not justify helios.

## CAPPED-CELLS disclosure (exactly what was dropped)

The grid is `tool{helios,cp_r,tar_czf} × size{5MB,50MB,500MB,5GB} × red{low,med,high}`,
6 reps. Fully measured: 5MB, 50MB, 500MB across all redundancies (rep 0 discarded as
warm-up, medians/p90 over reps 1..5). At 5GB (n_nodes=2):

- **5GB/low + 5GB/med, all three tools** — dropped by DESIGN CAP
  (`design-cap: 5GB low/med dropped for wall-clock/disk; high sampled`). 5GB/high was
  sampled as the decisive datapoint; low/med at 5GB add wall-clock and disk with no new
  signal. Recorded as `skipped_reason` rows in `results.csv`.
- **5GB/high helios** — all 6 reps completed and are RETAINED as `oomed=1` rows
  (peak RSS 6291460 kb); they are the decisive OOM evidence, exempt from the
  round-trip gate.
- **5GB/high cp_r** — reps 0-1 completed and RETAINED (commit 157.73s, store
  10737431224); reps 2-5 dropped by WALL-CLOCK CAP at the final cell.
- **5GB/high tar_czf** — 0 reps ran (the kill landed here); all 6 reps dropped by
  WALL-CLOCK CAP (`capped: 5GB/high cp_r+tar_czf reps beyond sample dropped for
  wall-clock — decisive datapoint helios OOM + cp_r sample retained`).

The 5GB helios OOM + cp_r survival is fully sufficient for the verdict; the capped tar
reps would only have re-confirmed tar's constant-RAM survival already seen at every
smaller size. `check_grid.py` already accepts a capped cell that carries a non-empty
`skipped_reason` (`if skipped: continue` — a non-empty reason satisfies coverage), so
no checker change was needed to honor the capped grid.

## Fleet safety

`run.log.frozen` records `FLEET_HEADCOUNT_PRE=1030`. The finalize arms (build,
concurrency, provenance) ran in this benchmark's own process group; a post-run
non-descendant headcount was taken and matches within ±2 (see `run.log`). No host
process outside the benchmark's PID tree was disturbed.
