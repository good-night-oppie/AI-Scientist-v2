"""Deterministic, version-stable synthetic workspace generator for the Phase 8 sweep.

Corpora must be byte-identical across hosts / numpy versions, so we NEVER use
``/dev/urandom`` or unseeded numpy. Bytes come from a hashlib-CTR stream
(``det_bytes``): SHA-256 over ``"{seed}:{ctr}"`` concatenated until enough bytes.

Redundancy is modelled at **whole-file** granularity because the Phase 8 dedup
probe (``run_bench.sh`` step 2 -> ``dedup_granularity.txt``) measured
``GRANULARITY=whole-file`` on helios HEAD (a 1-byte change re-stores the whole
file; byte-identical files dedup to one object). So a node dir is:

  * SHARED files -- byte-identical across ALL nodes (a "cached dataset" carried
    down a branch: the warm-start / X1 scenario). helios stores these once.
  * UNIQUE files -- distinct per node. helios stores these N times.

``redundancy = shared_bytes / (shared_bytes + unique_bytes)`` per node;
low~=0.0, med~=0.5, high~=0.95. Bulk bytes are INCOMPRESSIBLE (hashlib-CTR output
has ~0 gzip ratio) -- the realistic steelman for helios (a trained-model ``.npy``
of float outputs does not compress). A compressible corpus would favour ``tar``;
the verdict states this assumption explicitly.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os

# Split bulk into files no larger than this so per-file RAM is bounded (helios
# reads every file whole into RAM -- cli.go:118).
MAX_FILE_BYTES = 128 * 1024 * 1024

REDUNDANCY_LEVELS = {"low": 0.0, "med": 0.5, "high": 0.95}


def det_bytes(seed: str, n: int) -> bytes:
    """A deterministic incompressible byte stream of length ``n`` keyed on ``seed``."""
    out = bytearray()
    ctr = 0
    while len(out) < n:
        out += hashlib.sha256(f"{seed}:{ctr}".encode()).digest()
        ctr += 1
    return bytes(out[:n])


def _write_stream(path: str, seed: str, n: int) -> None:
    """Write ``n`` deterministic bytes to ``path`` in bounded-memory chunks."""
    block = (
        1 << 20
    )  # 1 MiB working buffer; never materialise the whole file in RAM here
    written = 0
    ctr = 0
    buf = bytearray()
    with open(path, "wb") as fh:
        while written < n:
            while len(buf) < block and written + len(buf) < n:
                buf += hashlib.sha256(f"{seed}:{ctr}".encode()).digest()
                ctr += 1
            take = min(len(buf), n - written)
            fh.write(bytes(buf[:take]))
            del buf[:take]
            written += take


def _split_sizes(total: int, max_file: int = MAX_FILE_BYTES) -> list[int]:
    """Break ``total`` bytes into a list of file sizes each <= ``max_file``."""
    if total <= 0:
        return []
    sizes = []
    remaining = total
    while remaining > 0:
        take = min(max_file, remaining)
        sizes.append(take)
        remaining -= take
    return sizes


def gen_corpus(
    size_bytes: int,
    redundancy: str,
    n_nodes: int,
    seed: int,
    out_root: str,
    *,
    single_huge_file: bool = False,
) -> dict:
    """Write ``node_000/ ... node_{N-1}/`` under ``out_root`` and return a manifest.

    Each node dir is laid out like a scaled AI-Scientist node working dir: one bulk
    ``experiment_data*.npy`` (split into <=128MB parts unless ``single_huge_file``),
    a couple of small PNGs, and a ``runfile.py``. The bulk carries the shared/unique
    split that encodes ``redundancy``.
    """
    if redundancy not in REDUNDANCY_LEVELS:
        raise ValueError(f"unknown redundancy {redundancy!r}")
    frac = REDUNDANCY_LEVELS[redundancy]
    shared_bytes = int(round(frac * size_bytes))
    unique_bytes = size_bytes - shared_bytes

    os.makedirs(out_root, exist_ok=True)
    # Small fixed-ish overhead files (a few hundred bytes) modelling PNGs + runfile.
    png_a = det_bytes(f"{seed}:png_a", 137)
    runfile = b"# runfile.py (synthetic)\nimport numpy as np\n# node marker\n"

    manifest = {
        "size_bytes": size_bytes,
        "redundancy": redundancy,
        "n_nodes": n_nodes,
        "seed": seed,
        "shared_bytes_target": shared_bytes,
        "unique_bytes_target": unique_bytes,
        "single_huge_file": single_huge_file,
        "nodes": [],
    }

    max_file = size_bytes if single_huge_file else MAX_FILE_BYTES
    shared_split = _split_sizes(shared_bytes, max_file)
    unique_split = _split_sizes(unique_bytes, max_file)

    for node in range(n_nodes):
        nd = os.path.join(out_root, f"node_{node:03d}")
        os.makedirs(nd, exist_ok=True)
        # SHARED bulk: seed does NOT depend on node -> byte-identical across all nodes.
        for i, sz in enumerate(shared_split):
            _write_stream(
                os.path.join(nd, f"shared_data_{i:02d}.npy"), f"{seed}:shared:{i}", sz
            )
        # UNIQUE bulk: seed depends on node -> distinct per node.
        for i, sz in enumerate(unique_split):
            _write_stream(
                os.path.join(nd, f"experiment_data_{i:02d}.npy"),
                f"{seed}:unique:{node}:{i}",
                sz,
            )
        # A shared PNG (identical across nodes) + a unique PNG (per node) + runfile.
        with open(os.path.join(nd, "figure_shared.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + png_a)
        with open(os.path.join(nd, "figure_node.png"), "wb") as fh:
            fh.write(b"\x89PNG\r\n\x1a\n" + det_bytes(f"{seed}:png_node:{node}", 137))
        with open(os.path.join(nd, "runfile.py"), "wb") as fh:
            fh.write(runfile)
        manifest["nodes"].append(nd)

    return manifest


def sha256_tree(root: str) -> dict:
    """Return ``{relpath: sha256hex}`` for every regular file under ``root`` (sorted)."""
    out = {}
    for dirpath, _dirs, files in os.walk(root):
        for name in sorted(files):
            p = os.path.join(dirpath, name)
            rel = os.path.relpath(p, root)
            h = hashlib.sha256()
            with open(p, "rb") as fh:
                for chunk in iter(lambda: fh.read(1 << 20), b""):
                    h.update(chunk)
            out[rel] = h.hexdigest()
    return dict(sorted(out.items()))


def measured_redundancy(out_root: str, n_nodes: int) -> float:
    """Measure the realised whole-file redundancy of a generated corpus.

    Redundancy = (shared bytes counted once) is 0; we report the fraction of total
    per-node bytes that are byte-identical across ALL nodes. Concretely: total unique
    content bytes across the tree, deduped by sha256, vs the summed node sizes; the
    shared fraction = 1 - dedup_total / summed_total, adjusted for n_nodes.
    """
    # Per file, collect (relname-family, sha, size). A "shared" file has the same sha
    # in every node. Compute shared_bytes (one copy) and unique_bytes (per node).
    node_hashes = {}
    for node in range(n_nodes):
        nd = os.path.join(out_root, f"node_{node:03d}")
        node_hashes[node] = sha256_tree(nd)
    # sum per-node total bytes
    per_node_total = 0
    nd0 = os.path.join(out_root, "node_000")
    for dirpath, _d, files in os.walk(nd0):
        for name in files:
            per_node_total += os.path.getsize(os.path.join(dirpath, name))
    # shared bytes: files whose sha is identical across all nodes
    shared = 0
    for rel, sha in node_hashes[0].items():
        if all(node_hashes[n].get(rel) == sha for n in range(n_nodes)):
            shared += os.path.getsize(os.path.join(nd0, rel))
    if per_node_total == 0:
        return 0.0
    return shared / per_node_total


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(
        description="Generate a deterministic benchmark corpus."
    )
    ap.add_argument(
        "--size", required=True, help="per-node size, e.g. 5MB / 50MB / bytes"
    )
    ap.add_argument("--redundancy", required=True, choices=list(REDUNDANCY_LEVELS))
    ap.add_argument("--nodes", type=int, default=6)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--out", required=True)
    ap.add_argument("--single-huge-file", action="store_true")
    ap.add_argument("--manifest", help="optional path to write a JSON manifest")
    ap.add_argument(
        "--selfcheck", action="store_true", help="print measured redundancy"
    )
    args = ap.parse_args(argv)

    size_bytes = parse_size(args.size)
    m = gen_corpus(
        size_bytes,
        args.redundancy,
        args.nodes,
        args.seed,
        args.out,
        single_huge_file=args.single_huge_file,
    )
    if args.selfcheck:
        measured = measured_redundancy(args.out, args.nodes)
        m["measured_redundancy"] = measured
        target = REDUNDANCY_LEVELS[args.redundancy]
        m["redundancy_target"] = target
        m["redundancy_ok"] = abs(measured - target) <= 0.02
        print(
            f"measured_redundancy={measured:.4f} target={target:.4f} ok={m['redundancy_ok']}"
        )
    if args.manifest:
        with open(args.manifest, "w") as fh:
            json.dump(m, fh, indent=2)
    return 0


def parse_size(s: str) -> int:
    """Parse ``5MB`` / ``50MB`` / ``5GB`` / raw byte counts to an int number of bytes."""
    s = str(s).strip().upper()
    mult = 1
    for suffix, m in (("GB", 1024**3), ("MB", 1024**2), ("KB", 1024), ("B", 1)):
        if s.endswith(suffix):
            mult = m
            s = s[: -len(suffix)]
            break
    return int(float(s) * mult)


if __name__ == "__main__":
    raise SystemExit(main())
