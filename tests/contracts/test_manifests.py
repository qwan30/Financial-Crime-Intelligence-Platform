from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fincrime.contracts.manifests import DatasetManifest, TraceLabel


def test_dataset_manifest_is_frozen_and_hash_is_lowercase() -> None:
    manifest = DatasetManifest(
        dataset_id="fixture-v1",
        source_url="https://example.invalid/fixture",
        license="CC-BY-4.0",
        sha256="a" * 64,
        schema_hash="b" * 64,
        created_at=datetime(2026, 8, 30, tzinfo=UTC),
    )
    with pytest.raises(ValidationError):
        manifest.dataset_id = "changed"


def test_unknown_is_a_distinct_trace_label() -> None:
    assert {item.value for item in TraceLabel} == {
        "RELEVANT",
        "CONFIRMED_BENIGN",
        "UNKNOWN",
    }
