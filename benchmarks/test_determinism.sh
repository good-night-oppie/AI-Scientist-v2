#!/usr/bin/env bash
# AC1: corpus determinism. Generate --seed 1234 --size 5MB --redundancy med --nodes 6
# into two dirs; the diff of their sorted sha256sum manifests must be empty (exit 0).
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
REPO="$(cd "$HERE/.." && pwd)"
PY="$REPO/.venv-test/bin/python"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

"$PY" "$HERE/gen_corpus.py" --size 5MB --redundancy med --nodes 6 --seed 1234 --out "$TMP/a"
"$PY" "$HERE/gen_corpus.py" --size 5MB --redundancy med --nodes 6 --seed 1234 --out "$TMP/b"

( cd "$TMP/a" && find . -type f | sort | xargs sha256sum | sed 's# .*/# #' ) > "$TMP/a.sha"
( cd "$TMP/b" && find . -type f | sort | xargs sha256sum | sed 's# .*/# #' ) > "$TMP/b.sha"

if diff -q "$TMP/a.sha" "$TMP/b.sha" >/dev/null; then
  echo "CORPUS_DETERMINISM_OK: identical sha256 manifests across two --seed 1234 runs"
  exit 0
else
  echo "FAILED: corpus differs across identical-seed runs" >&2
  diff "$TMP/a.sha" "$TMP/b.sha" >&2 || true
  exit 1
fi
