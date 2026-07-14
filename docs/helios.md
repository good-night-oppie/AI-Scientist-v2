# Helios snapshot checkpointing (optional)

Helios ([good-night-oppie/helios](https://github.com/good-night-oppie/helios)) is a
content-addressable snapshot engine (BLAKE3, whole-file dedup). This fork can use it as an
**optional**, flag-gated checkpoint layer for the BFTS tree search: every node's post-exec
working directory is committed as a snapshot, so any node's file state — including buggy
nodes, whose artifacts the stock pipeline destroys — can be reconstructed byte-for-byte.

**Read the benchmark verdict before enabling.** The pre-registered crossover benchmark
concluded helios does **not** beat `tar` at realistic BFTS workspace sizes
(see [`.supergoal/evidence/M8/verdict.md`](../.supergoal/evidence/M8/verdict.md)):

> RECOMMENDATION: helios beats tar for realistic per-node dirs: NO
>
> PROVENANCE_VERDICT: helios adds provenance value over tar+hash at realistic size: NO

Helios wins only in the **high cross-node-redundancy** regime (e.g. warm-start trees with
large shared artifacts). That is why every helios feature here defaults **OFF** and the
flag-OFF path is regression-gated to be journal-identical to baseline.

## Enabling

All knobs live in the typed `HeliosConfig` (`ai_scientist/treesearch/utils/config.py`).
Add the block to `bfts_config.yaml` (it ships commented out — an untyped/partial key would
raise `ConfigKeyError` at load, so copy the whole block):

```yaml
# helios:
#   enabled: true
#   store_dir: /abs/path/OUTSIDE/workspace_dir   # required: workspace_dir is rmtree'd at exit
#   binary_path: /abs/path/to/helios             # required: built from HEAD, see below
#   isolate_node_dirs: true                      # per-node exec dirs (also fixes metric contamination)
#   warm_start: false                            # children inherit parent filesystem (research flag)
```

## Building the binary (mandatory — never use a prebuilt)

```bash
scripts/build_helios.sh /abs/path/to/helios   # go build from helios HEAD + self-checks
```

The script refuses to hand you a broken binary: it asserts `restore` actually writes files
and that the build has no RocksDB linkage. Do **not** use any committed `helios-cli`,
`bin/helios`, or `dist/helios` from the helios repo — the tracked `helios-cli` ELF silently
no-ops `restore` (exit 0, writes nothing).

## Operational contract (enforced by `ai_scientist/treesearch/helios_store.py`)

- Every call pins `HELIOS_STORE_DIR` to `store_dir` — without it, snapshot ids resolve
  against per-CWD stores and become unreadable.
- Reconstruction uses `materialize --out <fresh dir>` only. `restore` is never used: it
  merges without deleting files absent from the snapshot, so sibling-node files leak in.
- All store writes are serialized with `fcntl.flock` — the pebble backend is single-writer
  and BFTS workers are separate processes.
- Snapshot ids are parsed from the CLI's stdout JSON (`{"snapshot_id": "blake3:<64hex>"}`).
- Imports are lazy and guarded: with helios absent or unconfigured, the treesearch modules
  import and run exactly as baseline (`cfg.helios is None`).

## What each flag buys

| Flag | Effect | Default |
|---|---|---|
| `enabled` | post-exec snapshot of every node's working dir (buggy included) into the store; `Node.snapshot_id` recorded in the journal | OFF |
| `isolate_node_dirs` | node-id-keyed exec dirs instead of pool-worker-keyed shared dirs; eliminates the observed stale-`experiment_data.npy` metric contamination | OFF |
| `warm_start` | children materialize the parent's snapshot before exec (plus a codegen-prompt addition telling the model to reuse cached artifacts) | OFF |

`warm_start` is a research flag: it changes search semantics (a poisoned parent poisons its
subtree, and the debug branch deliberately re-enters buggy parents). The measured synthetic
speedup is prompt-driven — restore alone shows no benefit. Do not enable it for
apples-to-apples comparisons with baseline runs.
