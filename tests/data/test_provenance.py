from __future__ import annotations

from datetime import UTC, datetime
from hashlib import sha256
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.data.provenance import (
    DerivedArtifactManifest,
    SourceManifest,
    sha256_file,
    sha256_header,
)


def test_source_manifest_rejects_non_https_and_non_hash_values() -> None:
    with pytest.raises(ValidationError):
        SourceManifest(
            source_id="amlsim-20k-fanin200",
            source_url="http://example.invalid/data",  # type: ignore[arg-type]
            revision="7338a4b",
            license="Apache-2.0",
            retrieved_at=datetime(2026, 8, 31, tzinfo=UTC),
            raw_sha256="not-a-hash",
            schema_sha256="b" * 64,
            extraction_selector="sample/20K_fanin200.tgz",
            intended_use="detection_graph_pilot",
            prohibited_claims=("learned_tracing",),
            limitations=("synthetic",),
        )


def test_source_manifest_rejects_http_url_even_with_valid_hashes() -> None:
    with pytest.raises(ValidationError, match="source_url must use HTTPS"):
        SourceManifest(
            source_id="amlsim-20k-fanin200",
            source_url="http://example.invalid/data",  # type: ignore[arg-type]
            revision="7338a4b",
            license="Apache-2.0",
            retrieved_at=datetime(2026, 8, 31, tzinfo=UTC),
            raw_sha256="a" * 64,
            schema_sha256="b" * 64,
            extraction_selector="sample/20K_fanin200.tgz",
            intended_use="detection_graph_pilot",
            prohibited_claims=("learned_tracing",),
            limitations=("synthetic",),
        )


def test_source_manifest_accepts_valid_https_provenance() -> None:
    manifest = SourceManifest(
        source_id="amlsim-20k-fanin200",
        source_url="https://example.invalid/data",  # type: ignore[arg-type]
        revision="7338a4b",
        license="Apache-2.0",
        retrieved_at=datetime(2026, 8, 31, tzinfo=UTC),
        raw_sha256="a" * 64,
        schema_sha256="b" * 64,
        extraction_selector="sample/20K_fanin200.tgz",
        intended_use="detection_graph_pilot",
        prohibited_claims=("learned_tracing",),
        limitations=("synthetic",),
    )
    assert manifest.source_id == "amlsim-20k-fanin200"
    with pytest.raises(ValidationError):
        manifest.source_id = "mutated"  # type: ignore[misc]


def test_derived_artifact_manifest_valid_and_immutable() -> None:
    manifest = DerivedArtifactManifest(
        source_id="amlsim-20k-fanin200",
        parent_raw_sha256="a" * 64,
        adapter_name="AMLSimSampleAdapter",
        adapter_version="1.0",
        conversion_parameters=(("prefix", "sample_"),),
        output_sha256="b" * 64,
        row_count=100,
        public_columns=("edge_id", "source_id", "target_id", "amount", "event_time"),
    )
    assert manifest.row_count == 100
    with pytest.raises(ValidationError):
        manifest.row_count = 200  # type: ignore[misc]


def test_sha256_helpers(tmp_path: Path) -> None:
    header_hash = sha256_header("sourceNodeId,targetNodeId,value,time")
    assert header_hash == "bcf4051fec5cc957e59a83708120a283144a8621eaebcf3acdc19b3baff031d1"

    test_file = tmp_path / "test.txt"
    test_file.write_bytes(b"hello world")
    assert sha256_file(test_file) == sha256(b"hello world").hexdigest()
