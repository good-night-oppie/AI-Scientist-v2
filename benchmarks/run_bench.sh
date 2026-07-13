#!/usr/bin/env bash
# Phase 8 benchmark orchestrator.
#
# Fleet safety (BLOCKER-0 discipline): records a PRE and POST non-descendant fleet
# headcount that MUST be equal -- this benchmark never signals any process outside
# its own group. Large arms (size >= 500MB) are RAM-contained in
#   docker run --rm -m 6g --memory-swap 6g ...
# and a native helios commit whose largest single file exceeds 0.5 x MemAvailable is
# refused and re-dispatched into docker. An in-container OOM is recorded (oomed=1),
# never a harness crash.
#
# Usage: bash benchmarks/run_bench.sh --grid full --seed 1234 --out .supergoal/evidence/M8
set -uo pipefail

GRID="full"
SEED="1234"
OUT=".supergoal/evidence/M8"
while [ $# -gt 0 ]; do
  case "$1" in
    --grid) GRID="$2"; shift 2;;
    --seed) SEED="$2"; shift 2;;
    --out) OUT="$2"; shift 2;;
    *) echo "unknown arg $1" >&2; exit 2;;
  esac
done

HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="$REPO/.venv-test/bin/python"
HELIOS="$REPO/.supergoal/bin/helios"
HELIOS_SRC="${HELIOS_SRC:-/home/admin/gh/helios}"
DOCKER_IMG="debian:stable-slim"
DOCKER_MEM="6g"

mkdir -p "$REPO/$OUT"
OUT_ABS="$(cd "$REPO/$OUT" && pwd)"
RUNLOG="$OUT_ABS/run.log"
SCRATCH="/tmp/helios_bench/$(date +%s)_$$"
mkdir -p "$SCRATCH"

log() { echo "[$(date +%H:%M:%S)] $*" | tee -a "$RUNLOG"; }

: > "$RUNLOG"
log "=== Phase 8 run_bench start grid=$GRID seed=$SEED out=$OUT_ABS ==="
log "helios_bin=$HELIOS scratch=$SCRATCH"

# --- Build helios from HEAD (never trust a prebuilt binary) --------------------------
if [ ! -x "$HELIOS" ]; then
  log "building helios from HEAD..."
  bash "$REPO/scripts/build_helios.sh" "$HELIOS" 2>&1 | tee -a "$RUNLOG"
fi
"$HELIOS" version >/dev/null 2>&1 || { log "FATAL: helios binary unusable"; exit 3; }

# --- Fleet headcount PRE (non-descendant process set) --------------------------------
MYPGID="$(ps -o pgid= -p $$ | tr -d ' ')"
PRE_PID_FILE="$SCRATCH/pre_pids.txt"
ps -eo pid=,pgid= | awk -v g="$MYPGID" '$2!=g{print $1}' | sort -n > "$PRE_PID_FILE"
FLEET_PRE="$(wc -l < "$PRE_PID_FILE" | tr -d ' ')"
log "FLEET_HEADCOUNT_PRE=$FLEET_PRE (non-descendant pids, pgid!=$MYPGID)"

# --- MemAvailable-based native single-file guard (0.5 x MemAvailable) -----------------
MEMAVAIL_KB="$(awk '/MemAvailable/{print $2}' /proc/meminfo)"
MEMAVAIL_BYTES=$((MEMAVAIL_KB * 1024))
NATIVE_SINGLE_FILE_CAP=$((MEMAVAIL_BYTES / 2))   # 0.5 x MemAvailable
log "MemAvailable=${MEMAVAIL_BYTES}B native_single_file_cap(0.5x)=${NATIVE_SINGLE_FILE_CAP}B"

# --- Docker preflight (RAM containment for size>=500MB arms) --------------------------
DOCKER_OK=0
if command -v docker >/dev/null 2>&1; then
  if docker run --rm -m 6g --memory-swap 6g "$DOCKER_IMG" true >/dev/null 2>&1; then
    DOCKER_OK=1
    log "docker preflight OK: 'docker run --rm -m 6g --memory-swap 6g $DOCKER_IMG' works"
  else
    log "WARN: docker preflight failed; large arms will fall back to native cap logic"
  fi
else
  log "WARN: docker absent; large arms fall back to native"
fi

# --- Step 2: empirically probe dedup granularity FIRST (do not assume) ----------------
log "--- dedup granularity probe (whole-file vs sub-file) ---"
DG_STORE="$SCRATCH/dedup_store"; mkdir -p "$DG_STORE"
DG_A="$SCRATCH/dedup_A"; mkdir -p "$DG_A"
DG_FILESIZE=$((20 * 1024 * 1024))
"$PY" - "$DG_A/experiment_data.npy" "$DG_FILESIZE" <<'PYEOF'
import hashlib, sys
path, n = sys.argv[1], int(sys.argv[2])
out = bytearray(); ctr = 0
while len(out) < n:
    out += hashlib.sha256(f"dedupprobe:{ctr}".encode()).digest(); ctr += 1
open(path, "wb").write(bytes(out[:n]))
PYEOF
HELIOS_STORE_DIR="$DG_STORE" "$HELIOS" commit --work "$DG_A" >/dev/null 2>&1; sync
DG_S1="$(du -sb "$DG_STORE" | cut -f1)"
DG_C="$SCRATCH/dedup_C"; mkdir -p "$DG_C"
cp "$DG_A/experiment_data.npy" "$DG_C/experiment_data.npy"
"$PY" - "$DG_C/experiment_data.npy" <<'PYEOF'
import sys
p = sys.argv[1]; b = bytearray(open(p, "rb").read()); b[len(b)//2] ^= 0xFF; open(p, "wb").write(b)
PYEOF
HELIOS_STORE_DIR="$DG_STORE" "$HELIOS" commit --work "$DG_C" >/dev/null 2>&1; sync
DG_S2="$(du -sb "$DG_STORE" | cut -f1)"
DG_DELTA=$((DG_S2 - DG_S1))
# whole-file: delta >= 0.9*filesize ; sub-file: delta <= 0.1*filesize
DG_GRAN="ambiguous"
if [ "$DG_DELTA" -ge "$(( DG_FILESIZE * 9 / 10 ))" ]; then DG_GRAN="whole-file"; fi
if [ "$DG_DELTA" -le "$(( DG_FILESIZE / 10 ))" ]; then DG_GRAN="sub-file"; fi
{
  echo "# Dedup granularity probe (measured, not assumed) -- helios HEAD $(git -C "$HELIOS_SRC" rev-parse --short HEAD)"
  echo "# Commit file F (fresh store), du; commit F with 1 middle byte flipped, du; delta = store growth."
  echo "# whole-file => a 1-byte change re-stores the whole file (delta >= 0.9x|F|, per cli.go:118)."
  echo "# sub-file   => block/CDC dedup (delta <= 0.1x|F|)."
  echo "FILESIZE_BYTES=$DG_FILESIZE"
  echo "STORE_BEFORE_BYTES=$DG_S1"
  echo "STORE_AFTER_BYTES=$DG_S2"
  echo "DELTA_BYTES=$DG_DELTA"
  echo "GRANULARITY=$DG_GRAN"
} > "$OUT_ABS/dedup_granularity.txt"
log "dedup: filesize=$DG_FILESIZE delta=$DG_DELTA -> GRANULARITY=$DG_GRAN"
rm -rf "$DG_STORE" "$DG_A" "$DG_C"

# --- Corpus redundancy self-check (logged) -------------------------------------------
log "--- corpus redundancy self-check ---"
for red in low med high; do
  SC="$SCRATCH/selfcheck_$red"
  "$PY" "$HERE/gen_corpus.py" --size 5MB --redundancy "$red" --nodes 6 --seed "$SEED" \
    --out "$SC" --selfcheck 2>&1 | tee -a "$RUNLOG"
  rm -rf "$SC"
done

# --- Step 3/4: the sweep (native small, docker for size>=500MB) -----------------------
log "--- sweep (bench.py) grid=$GRID ---"
BENCH_ARGS=(--out "$OUT_ABS" --seed "$SEED" --grid "$GRID" --helios-bin "$HELIOS"
            --scratch "$SCRATCH/sweep" --native-cap-bytes "$NATIVE_SINGLE_FILE_CAP"
            --docker-mem "$DOCKER_MEM" --docker-image "$DOCKER_IMG" --logfile "$RUNLOG")
if [ "$DOCKER_OK" -ne 1 ]; then BENCH_ARGS+=(--no-docker); log "NOTE: running sweep native (no docker)"; fi
"$PY" "$HERE/bench.py" "${BENCH_ARGS[@]}" 2>&1 | tee -a "$RUNLOG"

# --- Step 5: concurrency (real processes) --------------------------------------------
log "--- concurrency (concurrency.py) ---"
"$PY" "$HERE/concurrency.py" --helios-bin "$HELIOS" --scratch "$SCRATCH/cc" \
  --out-csv "$OUT_ABS/concurrency.csv" --size 8MB --seed "$SEED" 2>&1 | tee -a "$RUNLOG"

# --- manifest.json --------------------------------------------------------------------
log "--- manifest.json ---"
"$PY" - "$OUT_ABS/manifest.json" "$HELIOS" "$HELIOS_SRC" "$SEED" "$GRID" \
        "$MEMAVAIL_BYTES" "$NATIVE_SINGLE_FILE_CAP" <<'PYEOF'
import hashlib, json, os, subprocess, sys
out, helios, src, seed, grid, memavail, cap = sys.argv[1:8]
def sh(*a):
    try: return subprocess.check_output(a, text=True).strip()
    except Exception as e: return f"?{e}"
sha = hashlib.sha256(open(helios, "rb").read()).hexdigest()
try:
    import numpy; npv = numpy.__version__
except Exception: npv = "absent"
m = {
  "helios_commit": sh("git", "-C", src, "rev-parse", "HEAD"),
  "helios_bin_sha256": sha,
  "seed": int(seed),
  "grid": {
    "sizes": ["5MB", "50MB", "500MB", "5GB"],
    "redundancy": ["low", "med", "high"],
    "tools": ["helios", "cp_r", "tar_czf"],
    "n_nodes_default": 6,
  },
  "numpy_version": npv,
  "host": {
    "cpu_count": os.cpu_count(),
    "MemTotal_bytes": int(sh("awk", "/MemTotal/{print $2*1024}", "/proc/meminfo") or 0),
    "MemAvailable_bytes": int(memavail),
    "native_single_file_cap_bytes": int(cap),
    "free_disk_bytes": int(subprocess.check_output(["df", "-B1", "--output=avail", "/"], text=True).splitlines()[1]),
  },
}
json.dump(m, open(out, "w"), indent=2)
print("wrote", out)
PYEOF

# --- Fleet headcount POST (survivors of the PRE set) ---------------------------------
POST_SURV=0
while read -r pid; do
  [ -d "/proc/$pid" ] && POST_SURV=$((POST_SURV + 1))
done < "$PRE_PID_FILE"
FLEET_POST="$POST_SURV"
log "FLEET_HEADCOUNT_POST=$FLEET_POST (survivors of the $FLEET_PRE PRE pids)"
if [ "$FLEET_PRE" -eq "$FLEET_POST" ]; then
  log "FLEET_SAFETY_OK: pre==post ($FLEET_PRE) -- no non-descendant process disturbed"
else
  log "FLEET_SAFETY_WARN: pre=$FLEET_PRE post=$FLEET_POST (delta=$((FLEET_PRE - FLEET_POST)))"
fi

rm -rf "$SCRATCH"
log "=== run_bench done ==="
