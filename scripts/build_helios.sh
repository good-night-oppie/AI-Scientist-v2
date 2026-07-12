#!/usr/bin/env bash
# build_helios.sh — build the helios CLI from HEAD source to a pinned absolute path,
# and prove the resulting binary actually works (restore writes files, materialize is
# byte-identical). NEVER trusts a prebuilt / git-tracked binary: the committed
# ./helios-cli silently no-ops `restore` (exit 0, zero files written), and bin/helios /
# dist/helios are stale RocksDB-linked corpses that fail to load.
#
# Usage:
#   scripts/build_helios.sh [OUT_PATH]
#     OUT_PATH  absolute path to write the built binary (default: .supergoal/bin/helios)
#
# Refuses to run if HELIOS_BIN is set to a git-tracked helios path (a guard against
# accidentally "building" onto / reusing the broken committed binary).
#
# Exit 0 on a fully-verified build; non-zero (with REFUSING:/FAILED: on stderr) otherwise.
set -euo pipefail

HELIOS_SRC="${HELIOS_SRC:-/home/admin/gh/helios}"
GO="${GO:-/usr/local/go/bin/go}"
OUT="${1:-$PWD/.supergoal/bin/helios}"

# --- Guard: refuse a tracked/prebuilt binary as the build target or source -----------
if [ -n "${HELIOS_BIN:-}" ]; then
  # If HELIOS_BIN points at a git-tracked file inside the helios repo, refuse.
  if ( cd "$HELIOS_SRC" 2>/dev/null && git ls-files --error-unmatch \
        "$(python3 -c 'import os,sys;print(os.path.relpath(sys.argv[1], sys.argv[2]))' \
           "$HELIOS_BIN" "$HELIOS_SRC" 2>/dev/null)" >/dev/null 2>&1 ); then
    echo "REFUSING: HELIOS_BIN=$HELIOS_BIN is a git-tracked helios binary (known broken); build from HEAD instead." >&2
    exit 3
  fi
fi

command -v "$GO" >/dev/null 2>&1 || { echo "FAILED: go not found at $GO" >&2; exit 4; }

mkdir -p "$(dirname "$OUT")"

echo "go version: $("$GO" version)"
HEAD_SHA="$(cd "$HELIOS_SRC" && git rev-parse --short HEAD)"
echo "helios HEAD: $HEAD_SHA"

# --- Build from HEAD ------------------------------------------------------------------
( cd "$HELIOS_SRC" && "$GO" build -o "$OUT" ./cmd/helios-cli )
test -x "$OUT" || { echo "FAILED: build produced no executable at $OUT" >&2; exit 5; }
echo "built: $OUT"

# --- ldd: prove no RocksDB linkage (pure-Go/pebble, not a stale corpse) ---------------
LDD_OUT="$(ldd "$OUT" 2>&1 || true)"
echo "ldd:"
echo "$LDD_OUT" | sed 's/^/  /'
if echo "$LDD_OUT" | grep -qi 'rocksdb'; then
  echo "FAILED: built binary links RocksDB (unexpected for HEAD/pebble)" >&2
  exit 6
fi

# --- Functional self-test: restore actually writes files; materialize byte-identical --
WORK="$(mktemp -d)"
STORE="$(mktemp -d)"        # abs path OUTSIDE any workspace_dir (never rmtree'd here)
trap 'rm -rf "$WORK" "$STORE"' EXIT
export HELIOS_STORE_DIR="$STORE"

mkdir -p "$WORK/sub"
head -c 4096 /dev/urandom > "$WORK/probe.bin"
echo "note-original" > "$WORK/sub/note.txt"
SRC_PROBE="$(sha256sum "$WORK/probe.bin" | cut -d' ' -f1)"
SRC_NOTE="$(sha256sum "$WORK/sub/note.txt" | cut -d' ' -f1)"

SID="$("$OUT" commit --work "$WORK" 2>/dev/null | python3 -c 'import sys,json;print(json.load(sys.stdin)["snapshot_id"])')"
echo "commit snapshot_id=$SID"

# restore write-liveness: mutate + delete, restore into the same dir, assert files return
echo "note-CHANGED" > "$WORK/sub/note.txt"
rm -f "$WORK/probe.bin"
( cd "$WORK" && "$OUT" restore --id "$SID" >/dev/null 2>&1 )
RESTORED=0
[ -f "$WORK/probe.bin" ] && [ "$(sha256sum "$WORK/probe.bin" | cut -d' ' -f1)" = "$SRC_PROBE" ] && RESTORED=$((RESTORED+1))
[ "$(sha256sum "$WORK/sub/note.txt" | cut -d' ' -f1)" = "$SRC_NOTE" ] && RESTORED=$((RESTORED+1))
if [ "$RESTORED" -ge 1 ]; then
  echo "restore wrote $RESTORED file(s): PASS"
else
  echo "FAILED: restore wrote 0 files (this is exactly what the tracked ./helios-cli does)" >&2
  exit 7
fi

# materialize into a FRESH empty dir; assert byte-identical to source
MAT="$(mktemp -d)"
"$OUT" materialize --id "$SID" --out "$MAT" >/dev/null 2>&1
if [ "$(sha256sum "$MAT/probe.bin" | cut -d' ' -f1)" = "$SRC_PROBE" ] && \
   [ "$(sha256sum "$MAT/sub/note.txt" | cut -d' ' -f1)" = "$SRC_NOTE" ]; then
  echo "materialize byte-identical: PASS"
else
  echo "FAILED: materialize output differs from source" >&2
  rm -rf "$MAT"; exit 8
fi
rm -rf "$MAT"

echo "BUILD_HELIOS_OK $OUT"
