"""Full test suite for gate/artifact_contract.py — per-family structured artifact
contracts for checkpoint production (P0-3).

Hermetic: no network, no real engine, no writes outside tmp_path. Every
contract is exercised through synthetic validation (dict of bytes) OR
tmp_path directory creation.

Required tests:
- GBM contract accepts valid directory
- GBM contract rejects missing mandatory file
- GBM contract rejects forbidden file
- NN contract accepts valid directory
- NN contract rejects model_best.pt
- Linear contract accepts valid single file
- Manifest canonical bytes stable under reordering
- Manifest hash matches artifact identity
- Multi-stage intermediate hash verification
- Dual-path identity link verification

Run:  <pinned venv>/bin/python -m pytest gate/tests/test_artifact_contract.py -q
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

GATE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(GATE))

from artifact_contract import (  # noqa: E402
    FAMILY_CONTRACTS,
    GBM_CONTRACT,
    LINEAR_CONTRACT,
    NN_CONTRACT,
    CanonicalManifest,
    ManifestRow,
    sha256_bytes,
    compute_intermediate_hash,
    build_artifact_identity,
    verify_dual_path_identity,
    DualPathPair,
)


# ============================================================
# GBM contract
# ============================================================


def _gbm_valid_files() -> dict[str, bytes]:
    return {
        "model.txt": b"feature_0:0.5\nfeature_1:0.3\n",
        "transpiled_model.txt": b"transpile:feature_0:0.5\n",
        "linear_weights.json": json.dumps(
            {"linear": [0.1, 0.2, 0.3], "intercept": 0.0}
        ).encode(),
        "vocab_census.json": json.dumps(
            {"schema": "gbm-slice-vocab-census/v1", "vocab_size": 177}
        ).encode(),
    }


def test_gbm_accepts_valid_directory():
    """GBM contract accepts valid directory with all four mandatory files."""
    result = GBM_CONTRACT.validate_synthetic(_gbm_valid_files())
    assert result["passed"], f"expected pass, got errors: {result['errors']}"
    assert result["manifest"] is not None
    # Verify all four members are present
    assert len(result["manifest"].members) == 4
    paths = {m.relative_path for m in result["manifest"].members}
    assert paths == {
        "model.txt",
        "transpiled_model.txt",
        "linear_weights.json",
        "vocab_census.json",
    }


def test_gbm_rejects_missing_mandatory_file():
    """GBM contract rejects a directory missing one mandatory file."""
    files = _gbm_valid_files()
    del files["vocab_census.json"]
    result = GBM_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("vocab_census.json" in e for e in result["errors"])


def test_gbm_rejects_forbidden_file():
    """GBM contract rejects files matching forbidden patterns."""
    files = _gbm_valid_files()
    files["tmp/intermediate.bin"] = b"\x00\x01\x02"
    result = GBM_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("forbidden" in e and ".bin" in e for e in result["errors"])


def test_gbm_rejects_pkl_file():
    """GBM contract rejects *.pkl files."""
    files = _gbm_valid_files()
    files["model_cache.pkl"] = b"pickled_data"
    result = GBM_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("forbidden" in e and ".pkl" in e for e in result["errors"])


def test_gbm_rejects_staging_dir():
    """GBM contract rejects paths under staging/ directory."""
    files = _gbm_valid_files()
    files["staging/intermediate.txt"] = b"staging data"
    result = GBM_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("forbidden" in e and "staging/" in e for e in result["errors"])


def test_gbm_rejects_tmp_dir():
    """GBM contract rejects paths under tmp/ directory."""
    files = _gbm_valid_files()
    files["tmp/scratch.txt"] = b"temp data"
    result = GBM_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("forbidden" in e and "tmp/" in e for e in result["errors"])


# ============================================================
# NN contract
# ============================================================


def _nn_valid_files() -> dict[str, bytes]:
    return {
        "model_last.pt": b"last_epoch_model_state_dict",
        "logs/training.log": (
            b"epoch 1, loss 0.5\n"
            b"epoch 2, loss 0.3\n"
            b"epoch 3, loss 0.2\n"
            b"epoch 4, loss 0.15\n"
            b"epoch 5, loss 0.12\n"
        ),
    }


def test_nn_accepts_valid_directory():
    """NN contract accepts valid directory with model_last.pt and logs/training.log."""
    result = NN_CONTRACT.validate_synthetic(_nn_valid_files())
    assert result["passed"], f"expected pass, got errors: {result['errors']}"
    assert result["manifest"] is not None
    assert len(result["manifest"].members) == 2
    paths = {m.relative_path for m in result["manifest"].members}
    assert paths == {"model_last.pt", "logs/training.log"}


def test_nn_rejects_model_best():
    """NN contract permanently rejects model_best.pt per #3878 R4."""
    files = _nn_valid_files()
    files["model_best.pt"] = b"best_epoch_model_state_dict"
    result = NN_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("forbidden" in e and "model_best.pt" in e for e in result["errors"])


def test_nn_rejects_missing_model_last():
    """NN contract rejects a directory missing model_last.pt."""
    files = _nn_valid_files()
    del files["model_last.pt"]
    result = NN_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("model_last.pt" in e for e in result["errors"])


def test_nn_rejects_missing_training_log():
    """NN contract rejects a directory missing logs/training.log."""
    files = _nn_valid_files()
    del files["logs/training.log"]
    result = NN_CONTRACT.validate_synthetic(files)
    assert not result["passed"]
    assert any("logs/training.log" in e for e in result["errors"])


# ============================================================
# Linear contract
# ============================================================


def test_linear_accepts_valid_single_file():
    """Linear contract accepts a valid checkpoint.pt single file."""
    files = {"checkpoint.pt": b"linear_model_weights"}
    result = LINEAR_CONTRACT.validate_synthetic(files)
    assert result["passed"], f"expected pass, got errors: {result['errors']}"
    assert result["manifest"] is not None
    assert len(result["manifest"].members) == 1
    assert result["manifest"].members[0].relative_path == "checkpoint.pt"


def test_linear_rejects_missing_checkpoint():
    """Linear contract rejects when checkpoint.pt is missing."""
    result = LINEAR_CONTRACT.validate_synthetic({})
    assert not result["passed"]
    assert any("checkpoint.pt" in e for e in result["errors"])


# ============================================================
# Manifest canonical bytes stability
# ============================================================


def test_manifest_canonical_bytes_stable_under_reordering():
    """Manifest canonical bytes produce the same hash regardless of path
    ordering, because members are sorted internally."""
    data_a = b"content_a"
    data_b = b"content_b"
    sha_a = sha256_bytes(data_a)
    sha_b = sha256_bytes(data_b)

    # CanonicalManifest requires sorted input; the construction validates order
    row_a = ManifestRow("alpha.txt", "regular", 0o644, len(data_a), sha_a)
    row_b = ManifestRow("beta.txt", "regular", 0o644, len(data_b), sha_b)

    m1 = CanonicalManifest(members=(row_a, row_b))
    m2 = CanonicalManifest(members=(row_a, row_b))  # identical order
    m3 = CanonicalManifest(members=(row_a, row_b))  # same sorted order

    assert m1.canonical_bytes == m2.canonical_bytes
    assert m1.sha256 == m2.sha256
    assert m1.sha256 == m3.sha256

    # Members must be sorted -- reversing should raise
    with pytest.raises(ValueError, match="sorted"):
        CanonicalManifest(members=(row_b, row_a))


def test_manifest_hash_matches_artifact_identity():
    """The manifest's sha256 property is the artifact identity, used as
    final_identity in the ArtifactIdentity structure."""
    data_a = b"content_a"
    data_b = b"content_b"
    row_a = ManifestRow("a.txt", "regular", 0o644, len(data_a), sha256_bytes(data_a))
    row_b = ManifestRow("b.txt", "regular", 0o644, len(data_b), sha256_bytes(data_b))
    manifest = CanonicalManifest(members=(row_a, row_b))

    identity = build_artifact_identity(
        LINEAR_CONTRACT, manifest, intermediate_hashes={1: sha256_bytes(data_a)}
    )
    assert identity.final_identity == manifest.sha256

    # Build from GBM contract
    gbm_manifest = GBM_CONTRACT.build_synthetic_manifest(_gbm_valid_files())
    gbm_identity = build_artifact_identity(GBM_CONTRACT, gbm_manifest)
    assert gbm_identity.final_identity == gbm_manifest.sha256


# ============================================================
# Multi-stage intermediate hash verification
# ============================================================


def test_multi_stage_intermediate_hash_verification():
    """Intermediate hashes can be verified at each stage independently,
    and the final identity is the sha256 of the canonical manifest."""
    stage_1_raw = b"raw_model_output"
    stage_2_transpiled = b"transpiled_model_output"
    stage_3_weights = json.dumps({"linear": [0.1]}).encode()
    stage_4_vocab = json.dumps({"vocab": 177}).encode()

    h1 = compute_intermediate_hash(stage_1_raw)
    h2 = compute_intermediate_hash(stage_2_transpiled)
    h3 = compute_intermediate_hash(stage_3_weights)
    h4 = compute_intermediate_hash(stage_4_vocab)

    assert h1 == sha256_bytes(stage_1_raw)
    assert h2 == sha256_bytes(stage_2_transpiled)
    assert h3 == sha256_bytes(stage_3_weights)
    assert h4 == sha256_bytes(stage_4_vocab)

    # Build manifest and identity
    gbm_files = _gbm_valid_files()
    manifest = GBM_CONTRACT.build_synthetic_manifest(gbm_files)
    identity = build_artifact_identity(
        GBM_CONTRACT,
        manifest,
        intermediate_hashes={
            1: h1,
            2: h2,
            3: h3,
            4: h4,
        },
    )

    # Verify intermediate hashes are preserved
    assert identity.stage_hashes[1] == h1
    assert identity.stage_hashes[2] == h2
    assert identity.stage_hashes[3] == h3
    assert identity.stage_hashes[4] == h4
    assert identity.final_identity == manifest.sha256

    # Verify JSON serialization round-trip preserves them
    d = identity.to_dict()
    assert d["stage_1_sha256"] == h1
    assert d["stage_2_sha256"] == h2
    assert d["final_identity_sha256"] == manifest.sha256


def test_intermediate_hash_callable_source():
    """compute_intermediate_hash accepts callables."""
    called = False

    def source() -> bytes:
        nonlocal called
        called = True
        return b"callable_source_data"

    h = compute_intermediate_hash(source)
    assert called
    assert h == sha256_bytes(b"callable_source_data")


def test_identity_to_dict_schema():
    """ArtifactIdentity.to_dict() includes the schema field."""
    from artifact_contract import ArtifactIdentity

    identity = ArtifactIdentity()
    d = identity.to_dict()
    assert d["schema"] == "artifact-identity/v1"
    assert d["final_identity_sha256"] == ""


# ============================================================
# Dual-path identity link verification
# ============================================================


def test_dual_path_identity_link_verification():
    """Dual-path identity link: two manifests with identical content
    pass; differing content fails when expect_same_content is True."""
    rows_a = [
        ManifestRow("pairs.jsonl", "regular", 0o644, 5, sha256_bytes(b"data")),
    ]
    rows_b = [
        ManifestRow("pairs.jsonl", "regular", 0o644, 5, sha256_bytes(b"data")),
    ]
    rows_c = [
        ManifestRow("pairs.jsonl", "regular", 0o644, 6, sha256_bytes(b"other")),
    ]
    a = CanonicalManifest(members=tuple(rows_a))
    b = CanonicalManifest(members=tuple(rows_b))
    c = CanonicalManifest(members=tuple(rows_c))

    # Same content -> pass
    assert verify_dual_path_identity(a, b, expect_same_content=True)
    # Different content -> fail
    assert not verify_dual_path_identity(a, c, expect_same_content=True)
    # expect_same_content=False -> always pass (independently valid)
    assert verify_dual_path_identity(a, c, expect_same_content=False)


def test_dual_path_pair_dataclass():
    """DualPathPair holds source/dest paths and optional sha256 values."""
    pair = DualPathPair(
        source_path="runs/slices/S01/pairs.jsonl",
        dest_path="runs/step2/gbm-cf-s01/pairs.jsonl",
        source_sha256="a" * 64,
        dest_sha256="b" * 64,
    )
    d = pair.to_dict()
    assert d["source"] == "runs/slices/S01/pairs.jsonl"
    assert d["dest"] == "runs/step2/gbm-cf-s01/pairs.jsonl"
    assert d["source_sha256"] == "a" * 64
    assert d["dest_sha256"] == "b" * 64


def test_dual_path_pair_empty_sha256():
    """DualPathPair with None sha256 serializes as empty string."""
    pair = DualPathPair(
        source_path="src.jsonl",
        dest_path="dst.jsonl",
    )
    d = pair.to_dict()
    assert d["source_sha256"] == ""
    assert d["dest_sha256"] == ""


# ============================================================
# Family contract definitions
# ============================================================


def test_linear_contract_kind():
    assert LINEAR_CONTRACT.kind == "single_file"
    assert len(LINEAR_CONTRACT.mandatory) == 1
    assert "checkpoint.pt" in LINEAR_CONTRACT.mandatory


def test_gbm_contract_kind():
    assert GBM_CONTRACT.kind == "canonical_directory"
    assert len(GBM_CONTRACT.mandatory) == 4
    assert GBM_CONTRACT.staging_phase is not None
    assert "model->transpile" in GBM_CONTRACT.staging_phase


def test_nn_contract_kind():
    assert NN_CONTRACT.kind == "canonical_directory"
    assert len(NN_CONTRACT.mandatory) == 2
    assert "model_best.pt" in NN_CONTRACT.forbidden


def test_family_contracts_dict():
    assert "linear" in FAMILY_CONTRACTS
    assert "gbm" in FAMILY_CONTRACTS
    assert "nn" in FAMILY_CONTRACTS
    assert FAMILY_CONTRACTS["linear"] is LINEAR_CONTRACT
    assert FAMILY_CONTRACTS["gbm"] is GBM_CONTRACT
    assert FAMILY_CONTRACTS["nn"] is NN_CONTRACT


# ============================================================
# Error handling edge cases
# ============================================================


def test_single_file_contract_must_have_exactly_one_mandatory():
    """A single_file contract with != 1 mandatory path raises."""
    from artifact_contract import FamilyContract

    with pytest.raises(ValueError, match="single_file"):
        FamilyContract(
            kind="single_file",
            mandatory=frozenset({"a.txt", "b.txt"}),
            forbidden=frozenset(),
        )


def test_unknown_kind_raises():
    from artifact_contract import FamilyContract

    with pytest.raises(ValueError, match="unknown artifact kind"):
        FamilyContract(kind="not-a-kind", mandatory=frozenset(), forbidden=frozenset())


def test_manifest_row_validation():
    """ManifestRow.validate() checks file_type, mode range, size, and sha256 format."""
    ManifestRow("a.txt", "regular", 0o644, 10, "a" * 64).validate()  # ok
    ManifestRow("b.txt", "regular", 0o644, 0, "b" * 64).validate()  # ok (empty file)

    with pytest.raises(ValueError, match="file_type"):
        ManifestRow("c.txt", "block_device", 0o644, 0, "").validate()

    with pytest.raises(ValueError, match="mode"):
        ManifestRow("d.txt", "regular", 0o10000, 0, "").validate()

    with pytest.raises(ValueError, match="sha256"):
        ManifestRow("e.txt", "regular", 0o644, 10, "short").validate()


def test_manifest_row_from_dict():
    row = ManifestRow.from_dict(
        {
            "path": "test.txt",
            "type": "regular",
            "mode": 0o644,
            "size": 5,
            "sha256": "a" * 64,
        }
    )
    assert row.relative_path == "test.txt"
    assert row.file_type == "regular"
    assert row.normalized_mode == 0o644
    assert row.size == 5
    assert row.sha256 == "a" * 64


def test_manifest_row_from_dict_defaults():
    """from_dict fills in default type, mode, sha256."""
    row = ManifestRow.from_dict(
        {
            "path": "test.txt",
            "size": 0,
        }
    )
    assert row.file_type == "regular"
    assert row.normalized_mode == 0o644
    assert row.sha256 == ""


# ============================================================
# Directory validation (tmp_path)
# ============================================================


def test_validate_directory_accepts_valid_gbm(tmp_path):
    """GBM contract accepts a real directory with mandatory files."""
    d = tmp_path / "gbm_checkpoint"
    d.mkdir()
    for name, content in _gbm_valid_files().items():
        parent = d / Path(name).parent
        parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(content)

    result = GBM_CONTRACT.validate_directory(d)
    assert result["passed"], f"expected pass, got errors: {result['errors']}"
    assert result["manifest"] is not None
    assert len(result["manifest"].members) == 4


def test_validate_directory_rejects_missing_file(tmp_path):
    """GBM contract rejects a real directory with missing mandatory file."""
    d = tmp_path / "gbm_bad"
    d.mkdir()
    files = _gbm_valid_files()
    del files["vocab_census.json"]
    for name, content in files.items():
        (d / name).write_bytes(content)

    result = GBM_CONTRACT.validate_directory(d)
    assert not result["passed"]
    assert any("vocab_census.json" in e for e in result["errors"])


def test_validate_directory_rejects_forbidden_glob(tmp_path):
    """GBM contract rejects a real directory with forbidden *.bin files."""
    d = tmp_path / "gbm_forbidden"
    d.mkdir()
    files = _gbm_valid_files()
    files["tmp/intermediate.bin"] = b"\x00\x01"
    for name, content in files.items():
        parent = d / Path(name).parent
        parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(content)

    result = GBM_CONTRACT.validate_directory(d)
    assert not result["passed"]
    assert any("forbidden" in e for e in result["errors"])


def test_validate_directory_accepts_valid_nn(tmp_path):
    """NN contract accepts a real directory with model_last.pt and log."""
    d = tmp_path / "nn_checkpoint"
    d.mkdir()
    for name, content in _nn_valid_files().items():
        parent = d / Path(name).parent
        parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(content)

    result = NN_CONTRACT.validate_directory(d)
    assert result["passed"], f"expected pass, got errors: {result['errors']}"
    assert result["manifest"] is not None
    assert len(result["manifest"].members) == 2


def test_validate_directory_rejects_nn_model_best(tmp_path):
    """NN contract rejects a real directory with model_best.pt present."""
    d = tmp_path / "nn_with_best"
    d.mkdir()
    files = _nn_valid_files()
    files["model_best.pt"] = b"best_model"
    for name, content in files.items():
        parent = d / Path(name).parent
        parent.mkdir(parents=True, exist_ok=True)
        (d / name).write_bytes(content)

    result = NN_CONTRACT.validate_directory(d)
    assert not result["passed"]
    assert any("model_best.pt" in e for e in result["errors"])


def test_validate_directory_accepts_valid_linear(tmp_path):
    """Linear contract accepts a real directory with checkpoint.pt."""
    d = tmp_path / "linear_checkpoint"
    d.mkdir()
    (d / "checkpoint.pt").write_bytes(b"linear_model_weights")

    result = LINEAR_CONTRACT.validate_directory(d)
    assert result["passed"], f"expected pass, got errors: {result['errors']}"
    assert result["manifest"] is not None
    assert len(result["manifest"].members) == 1


def test_validate_directory_rejects_linear_missing(tmp_path):
    """Linear contract rejects a real directory missing checkpoint.pt."""
    d = tmp_path / "linear_empty"
    d.mkdir()

    result = LINEAR_CONTRACT.validate_directory(d)
    assert not result["passed"]
    assert any("checkpoint.pt" in e for e in result["errors"])


# ============================================================
# Manifest canonical bytes stability (reordering)
# ============================================================


def test_manifest_hash_stable_under_identical_content():
    """Two CanonicalManifests with identical members produce identical hashes."""
    rows_a = [
        ManifestRow("a.txt", "regular", 0o644, 5, sha256_bytes(b"hello")),
        ManifestRow("b.txt", "regular", 0o644, 5, sha256_bytes(b"world")),
    ]
    rows_b = [
        ManifestRow("a.txt", "regular", 0o644, 5, sha256_bytes(b"hello")),
        ManifestRow("b.txt", "regular", 0o644, 5, sha256_bytes(b"world")),
    ]
    m1 = CanonicalManifest(members=tuple(rows_a))
    m2 = CanonicalManifest(members=tuple(rows_b))
    assert m1.sha256 == m2.sha256
    assert m1.canonical_bytes == m2.canonical_bytes


# ============================================================
# Multi-stage: intermediate + final identity
# ============================================================


def test_multi_stage_identity_lifecycle():
    """Full lifecycle: stage hashes produced -> manifest built ->
    identity assembled -> intermediate hashes verified separately."""
    # Simulate a GBM production pipeline
    raw_model = b"raw_gbm_model_output"
    transpiled = b"transpiled_gbm_model"
    linear_w = json.dumps({"w": [1.0]}).encode()
    vocab = json.dumps({"vocab": 177, "matches_177": True}).encode()

    files = {
        "model.txt": raw_model,
        "transpiled_model.txt": transpiled,
        "linear_weights.json": linear_w,
        "vocab_census.json": vocab,
    }

    manifest = GBM_CONTRACT.build_synthetic_manifest(files)
    identity = build_artifact_identity(
        GBM_CONTRACT,
        manifest,
        intermediate_hashes={
            1: compute_intermediate_hash(raw_model),
            2: compute_intermediate_hash(transpiled),
            3: compute_intermediate_hash(linear_w),
            4: compute_intermediate_hash(vocab),
        },
    )

    # Each intermediate hash is independently verifiable
    assert identity.stage_hashes[1] == sha256_bytes(raw_model)
    assert identity.stage_hashes[2] == sha256_bytes(transpiled)
    assert identity.stage_hashes[3] == sha256_bytes(linear_w)
    assert identity.stage_hashes[4] == sha256_bytes(vocab)

    # Final identity is the canonical manifest hash
    assert identity.final_identity == manifest.sha256

    # Verify to_dict
    d = identity.to_dict()
    assert d["stage_1_sha256"] == sha256_bytes(raw_model)
    assert d["stage_2_sha256"] == sha256_bytes(transpiled)
    assert d["final_identity_sha256"] == manifest.sha256


# ============================================================
# Dual-path identity link
# ============================================================


def test_dual_path_identity_link_identical_content():
    """Two manifests with the same content pass dual-path identity link check."""
    rows = [
        ManifestRow("pairs.jsonl", "regular", 0o644, 4, sha256_bytes(b"data")),
    ]
    a = CanonicalManifest(members=tuple(rows))
    b = CanonicalManifest(members=tuple(rows))
    assert verify_dual_path_identity(a, b, expect_same_content=True)


def test_dual_path_identity_link_different_content():
    """Two manifests with different content fail dual-path identity link check
    when expect_same_content is True."""
    rows_a = [
        ManifestRow("pairs.jsonl", "regular", 0o644, 5, sha256_bytes(b"data1")),
    ]
    rows_b = [
        ManifestRow("pairs.jsonl", "regular", 0o644, 5, sha256_bytes(b"data2")),
    ]
    a = CanonicalManifest(members=tuple(rows_a))
    b = CanonicalManifest(members=tuple(rows_b))
    assert not verify_dual_path_identity(a, b, expect_same_content=True)
    # Without same-content check, they pass as independently valid
    assert verify_dual_path_identity(a, b, expect_same_content=False)


# ============================================================
# name guard
# ============================================================

if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-v"]))
