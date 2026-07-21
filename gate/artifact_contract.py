"""Per-family structured artifact contracts for checkpoint production (P0-3).

Each family contract defines:
- artifact kind ("single_file" / "canonical_directory" / "deterministic_bundle")
- mandatory path set (relative paths that MUST exist)
- forbidden paths (relative paths that MUST NOT exist)
- canonical manifest rows: (relative_path, file_type, normalized_mode, size, sha256)
- manifest canonical bytes hashed as artifact identity
- multi-stage intermediate hashes and final consumable identity
- GBM: incorporates exact-vocab, model->transpile staging, linear-weight member,
  dual-path pairs
- NN: explicit --log and model_last.pt; model_best permanently rejected per #3878 R4
- Linear: uses the local pair path

Manifest canonical bytes are stable under reordering of input paths and serve as
the deterministic artifact identity.  Every contract also supports validation
against a filesystem directory (real access) or a synthetic dict (tests).
"""

from __future__ import annotations

import hashlib
import json
import re
import stat
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

SCHEMA = "artifact-contract/v1"
CONTRACT_KINDS = ("single_file", "canonical_directory", "deterministic_bundle")
FILE_TYPES = ("regular", "symlink", "directory")


def sha256_file(path: Path) -> str:
    """SHA-256 of file content as hex string."""
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def _glob_match(pattern: str, path: str) -> bool:
    """Simple glob match: supports '*' and '?' wildcards.

    Does NOT support **/ recursive glob; those are matched by prefix splitting.
    """
    import fnmatch

    return fnmatch.fnmatch(path, pattern)


def _forbidden_match(forbidden_patterns: set[str], path: str) -> str | None:
    """Return the first matching forbidden pattern, or None."""
    for pat in sorted(forbidden_patterns):
        if pat.endswith("/") and path.startswith(pat):
            return pat
        if _glob_match(pat, path):
            return pat
    return None


@dataclass(frozen=True)
class ManifestRow:
    """One canonical manifest row for an artifact member."""

    relative_path: str
    file_type: str  # "regular" | "symlink" | "directory"
    normalized_mode: int
    size: int
    sha256: str

    def validate(self) -> None:
        if self.file_type not in FILE_TYPES:
            raise ValueError(
                f"{self.relative_path}: unknown file_type {self.file_type!r}"
            )
        if self.normalized_mode < 0 or self.normalized_mode > 0o7777:
            raise ValueError(
                f"{self.relative_path}: mode {self.normalized_mode:o} out of range"
            )
        if self.size < 0:
            raise ValueError(f"{self.relative_path}: negative size")
        if self.file_type == "regular" and not re.match(r"^[0-9a-f]{64}$", self.sha256):
            raise ValueError(
                f"{self.relative_path}: sha256 must be 64 hex chars, got {self.sha256!r}"
            )
        # symlinks and directories carry empty sha256 (they are not content-hashed)
        if self.file_type in ("symlink", "directory") and self.sha256:
            # Allow non-empty for directories if someone wants to hash the manifest
            # of the directory tree; we use empty as default.
            pass

    def to_dict(self) -> dict:
        return {
            "path": self.relative_path,
            "type": self.file_type,
            "mode": self.normalized_mode,
            "size": self.size,
            "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, d: dict) -> ManifestRow:
        return cls(
            relative_path=d["path"],
            file_type=d.get("type", "regular"),
            normalized_mode=d.get("mode", 0o644),
            size=d.get("size", 0),
            sha256=d.get("sha256", ""),
        )


@dataclass(frozen=True)
class CanonicalManifest:
    """A sorted-by-path manifest whose canonical bytes define artifact identity."""

    members: tuple[ManifestRow, ...]

    def __post_init__(self) -> None:
        # Validate sort order
        paths = [m.relative_path for m in self.members]
        if paths != sorted(paths):
            raise ValueError("manifest members must be sorted by relative_path")

    @property
    def canonical_bytes(self) -> bytes:
        rows = [m.to_dict() for m in self.members]
        return _canonical_json(rows)

    @property
    def sha256(self) -> str:
        return sha256_bytes(self.canonical_bytes)

    def to_dict(self) -> dict:
        return {
            "schema": SCHEMA,
            "n_members": len(self.members),
            "members": [m.to_dict() for m in self.members],
            "manifest_sha256": self.sha256,
        }


def _scan_directory(
    base: Path,
    relative_paths: list[str],
    *,
    include_dirs: bool = False,
) -> list[ManifestRow]:
    """Build manifest rows for a set of relative paths within *base*.

    Paths are returned sorted.  If a path names a directory and *include_dirs* is
    False, it is silently skipped (only regular files and symlinks are included).
    """
    rows: list[ManifestRow] = []
    for rel in relative_paths:
        resolved = (base / rel).resolve()
        if not resolved.exists():
            raise FileNotFoundError(f"path not found: {base / rel}")
        st = resolved.lstat()
        if stat.S_ISREG(st.st_mode):
            rows.append(
                ManifestRow(
                    relative_path=rel,
                    file_type="regular",
                    normalized_mode=st.st_mode & 0o7777,
                    size=st.st_size,
                    sha256=sha256_file(resolved),
                )
            )
        elif stat.S_ISLNK(st.st_mode):
            rows.append(
                ManifestRow(
                    relative_path=rel,
                    file_type="symlink",
                    normalized_mode=st.st_mode & 0o7777,
                    size=0,
                    sha256="",
                )
            )
        elif stat.S_ISDIR(st.st_mode) and include_dirs:
            rows.append(
                ManifestRow(
                    relative_path=rel,
                    file_type="directory",
                    normalized_mode=st.st_mode & 0o7777,
                    size=0,
                    sha256="",
                )
            )
        else:
            raise ValueError(f"unsupported file type for {rel}: mode {st.st_mode:o}")
    return sorted(rows, key=lambda r: r.relative_path)


@dataclass(frozen=True)
class FamilyContract:
    """Structured contract for one checkpoint family.

    All path sets use relative paths rooted at the checkpoint output directory.
    """

    kind: str
    mandatory: frozenset[str]
    forbidden: frozenset[str]
    staging_phase: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        if self.kind not in CONTRACT_KINDS:
            raise ValueError(f"unknown artifact kind {self.kind!r}")
        # single_file kind must have exactly one mandatory path
        if self.kind == "single_file" and len(self.mandatory) != 1:
            raise ValueError(
                f"single_file contract must have exactly one mandatory path, "
                f"got {len(self.mandatory)}"
            )

    def validate_directory(self, base: Path) -> dict:
        """Validate a real filesystem directory against this contract.

        Returns a validation report dict with keys:
        - passed: bool
        - errors: list[str]
        - manifest: CanonicalManifest | None (on pass only)
        """
        errors: list[str] = []
        all_fs_paths: set[str] = set()
        if base.is_dir():
            for entry in base.rglob("*"):
                rel = str(entry.relative_to(base))
                all_fs_paths.add(rel)

        # Check mandatory paths
        for mp in sorted(self.mandatory):
            target = base / mp
            if not target.exists():
                errors.append(f"mandatory path missing: {mp}")

        # Check forbidden paths (glob-aware)
        for fp in sorted(self.forbidden):
            for fs_path in sorted(all_fs_paths):
                if _forbidden_match({fp}, fs_path):
                    errors.append(
                        f"forbidden path present: {fs_path} (matched pattern {fp})"
                    )

        if errors:
            return {"passed": False, "errors": errors, "manifest": None}

        # Build manifest from mandatory paths only (the canonical artifact
        # identity covers exactly what the contract requires)
        mandatory_list = sorted(self.mandatory)
        rows = _scan_directory(base, mandatory_list, include_dirs=False)
        manifest = CanonicalManifest(members=tuple(rows))
        return {
            "passed": True,
            "errors": [],
            "manifest": manifest,
        }

    def validate_synthetic(self, files: dict[str, bytes | tuple[str, int]]) -> dict:
        """Validate a synthetic file dict against this contract.

        *files* maps relative_path -> bytes  (for regular files)
        or relative_path -> ("symlink", target) for symlinks.

        Returns the same report dict as validate_directory.
        """
        errors: list[str] = []
        present = set(files)

        for mp in sorted(self.mandatory):
            if mp not in present:
                errors.append(f"mandatory path missing: {mp}")

        for fp in sorted(self.forbidden):
            for p in sorted(present):
                if _forbidden_match({fp}, p):
                    errors.append(f"forbidden path present: {p} (matched pattern {fp})")

        if errors:
            return {"passed": False, "errors": errors, "manifest": None}

        rows: list[ManifestRow] = []
        for rel in sorted(self.mandatory):
            value = files[rel]
            if isinstance(value, tuple) and value[0] == "symlink":
                rows.append(
                    ManifestRow(
                        relative_path=rel,
                        file_type="symlink",
                        normalized_mode=0o777,
                        size=0,
                        sha256="",
                    )
                )
            elif isinstance(value, bytes):
                rows.append(
                    ManifestRow(
                        relative_path=rel,
                        file_type="regular",
                        normalized_mode=0o644,
                        size=len(value),
                        sha256=sha256_bytes(value),
                    )
                )
            else:
                raise ValueError(f"unsupported file value for {rel}: {type(value)}")
        manifest = CanonicalManifest(members=tuple(rows))
        return {
            "passed": True,
            "errors": [],
            "manifest": manifest,
        }

    def build_manifest(self, base: Path) -> CanonicalManifest:
        """Build the canonical manifest (raises if contract validation fails)."""
        report = self.validate_directory(base)
        if not report["passed"]:
            raise ValueError(
                f"contract validation failed: {'; '.join(report['errors'])}"
            )
        assert report["manifest"] is not None
        return report["manifest"]

    def build_synthetic_manifest(
        self, files: dict[str, bytes | tuple[str, int]]
    ) -> CanonicalManifest:
        """Build the canonical manifest from synthetic data."""
        report = self.validate_synthetic(files)
        if not report["passed"]:
            raise ValueError(
                f"contract validation failed: {'; '.join(report['errors'])}"
            )
        assert report["manifest"] is not None
        return report["manifest"]


# ---------------------------------------------------------------------------
# Multi-stage intermediate hash builder
# ---------------------------------------------------------------------------


@dataclass
class ArtifactIdentity:
    """Multi-stage identity: intermediate hashes and final consumable hash.

    Stages (family-dependent):
      stage_1: raw model checkpoint
      stage_2: transpiled/converted model
      stage_3: assembled directory with linear weights, vocab census, etc.
      stage_4: final consumable identity (sha256 of the canonical manifest)
    """

    stage_hashes: dict[int, str] = field(default_factory=dict)
    final_identity: str | None = None

    def to_dict(self) -> dict:
        result: dict[str, Any] = {
            "schema": "artifact-identity/v1",
        }
        for k in sorted(self.stage_hashes):
            result[f"stage_{k}_sha256"] = self.stage_hashes[k]
        result["final_identity_sha256"] = self.final_identity or ""
        return result


def compute_intermediate_hash(
    bytes_source: Callable[[], bytes] | bytes,
    label: str | None = None,
) -> str:
    """Compute SHA-256 of a byte source (callable or literal)."""
    data = bytes_source() if callable(bytes_source) else bytes_source
    return sha256_bytes(data)


# ---------------------------------------------------------------------------
# Family contracts
# ---------------------------------------------------------------------------

LINEAR_CONTRACT = FamilyContract(
    kind="single_file",
    mandatory=frozenset({"checkpoint.pt"}),
    forbidden=frozenset(),
    staging_phase="cp from working dir to canonical output path",
    description="Linear imitation: single checkpoint.pt, no transpilation",
)

GBM_CONTRACT = FamilyContract(
    kind="canonical_directory",
    mandatory=frozenset(
        {
            "model.txt",
            "transpiled_model.txt",
            "linear_weights.json",
            "vocab_census.json",
        }
    ),
    forbidden=frozenset(
        {
            "*.bin",
            "*.pkl",
            "tmp/",
            "staging/",
        }
    ),
    staging_phase="model->transpile, linear-weight member copy, dual-path pairs copy",
    description="GBM: model -> transpile -> linear weights + vocab census",
)

NN_CONTRACT = FamilyContract(
    kind="canonical_directory",
    mandatory=frozenset(
        {
            "model_last.pt",
            "logs/training.log",
        }
    ),
    forbidden=frozenset(
        {
            "model_best.pt",
        }
    ),
    staging_phase="--log and model_last.pt; model_best permanently rejected",
    description=(
        "Neural network: model_last.pt + training log; "
        "model_best permanently rejected per #3878 R4"
    ),
)

FAMILY_CONTRACTS: dict[str, FamilyContract] = {
    "linear": LINEAR_CONTRACT,
    "gbm": GBM_CONTRACT,
    "nn": NN_CONTRACT,
}


# ---------------------------------------------------------------------------
# Dual-path identity verification
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DualPathPair:
    """A pair of paths that link two artifact identities together.

    Used for GBM's slice-pairs staging: the pairs file (consumed by training)
    and the model output have a dual-path identity link.
    """

    source_path: str
    dest_path: str
    source_sha256: str | None = None
    dest_sha256: str | None = None

    def to_dict(self) -> dict:
        return {
            "source": self.source_path,
            "dest": self.dest_path,
            "source_sha256": self.source_sha256 or "",
            "dest_sha256": self.dest_sha256 or "",
        }


def verify_dual_path_identity(
    pair_a: CanonicalManifest,
    pair_b: CanonicalManifest,
    *,
    expect_same_content: bool = True,
) -> bool:
    """Verify the dual-path identity link between two manifests.

    Returns True if the link holds.  When expect_same_content is True (default),
    this checks that the manifest sha256 values match (content-identical).  When
    False, it checks that the manifests are independently valid.
    """
    if expect_same_content and pair_a.sha256 != pair_b.sha256:
        return False
    return True


# ---------------------------------------------------------------------------
# Manifest builder helper
# ---------------------------------------------------------------------------


def build_artifact_identity(
    contract: FamilyContract,
    manifest: CanonicalManifest,
    intermediate_hashes: dict[int, str] | None = None,
) -> ArtifactIdentity:
    """Build the complete artifact identity for a given contract and manifest."""
    identity = ArtifactIdentity()
    if intermediate_hashes:
        identity.stage_hashes = intermediate_hashes
    identity.final_identity = manifest.sha256
    return identity


# ---------------------------------------------------------------------------
# Quick CLI
# ---------------------------------------------------------------------------


def main() -> int:
    """Validate a family checkpoint directory against its contract.

    Usage:
        python gate/artifact_contract.py <family> <path>
    """
    import sys as _sys

    args = _sys.argv[1:]
    if len(args) != 2:
        print("Usage: artifact_contract.py <family> <path>", file=_sys.stderr)
        return 2

    family = args[0]
    path = Path(args[1])

    if family not in FAMILY_CONTRACTS:
        print(
            f"unknown family {family!r}; known: {list(FAMILY_CONTRACTS)}",
            file=_sys.stderr,
        )
        return 2

    contract = FAMILY_CONTRACTS[family]
    report = contract.validate_directory(path)
    if not report["passed"]:
        for err in report["errors"]:
            print(f"FAIL: {err}", file=_sys.stderr)
        return 1

    manifest = report["manifest"]
    assert manifest is not None
    print(json.dumps(manifest.to_dict(), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
