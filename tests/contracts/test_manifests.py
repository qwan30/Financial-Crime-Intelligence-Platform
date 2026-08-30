from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.contracts.manifests import (
    DatasetManifest,
    SplitManifest,
    TraceEdge,
    TraceGoldManifest,
    TraceLabel,
    sha256_file,
)


def _dataset_manifest(**overrides: object) -> DatasetManifest:
    values: dict[str, object] = {
        "dataset_id": "fixture-v1",
        "source_url": "https://example.invalid/fixture",
        "license": "CC-BY-4.0",
        "sha256": "a" * 64,
        "schema_hash": "b" * 64,
        "created_at": datetime(2026, 8, 30, tzinfo=UTC),
    }
    values.update(overrides)
    return DatasetManifest.model_validate(values)


def _trace_edge(**overrides: object) -> TraceEdge:
    values: dict[str, object] = {
        "edge_id": "edge-1",
        "source_id": "account-1",
        "target_id": "account-2",
        "event_time": datetime(2026, 8, 30, tzinfo=UTC),
        "label": TraceLabel.RELEVANT,
    }
    values.update(overrides)
    return TraceEdge.model_validate(values)


def _trace_gold_manifest(**overrides: object) -> TraceGoldManifest:
    values: dict[str, object] = {
        "dataset_id": "fixture-v1",
        "generator_version": "tracegen-v1",
        "generator_seed": 7,
        "configuration_hash": "c" * 64,
        "case_id": "case-1",
        "typology": "layering",
        "edges": (_trace_edge(),),
        "mandatory_anchors": ("account-1",),
        "visibility_boundary_ids": ("account-2",),
    }
    values.update(overrides)
    return TraceGoldManifest.model_validate(values)


def _split_manifest(**overrides: object) -> SplitManifest:
    values: dict[str, object] = {
        "train_case_ids": ("train-1",),
        "validation_case_ids": ("validation-1",),
        "calibration_case_ids": ("calibration-1",),
        "temporal_test_case_ids": ("temporal-1",),
        "heldout_typology_case_ids": ("heldout-1",),
        "unseen_generator_case_ids": ("unseen-1",),
    }
    values.update(overrides)
    return SplitManifest.model_validate(values)


def test_dataset_manifest_is_frozen() -> None:
    manifest = _dataset_manifest()
    with pytest.raises(ValidationError):
        manifest.dataset_id = "changed"


@pytest.mark.parametrize("field", ["sha256", "schema_hash"])
def test_dataset_manifest_rejects_uppercase_hashes(field: str) -> None:
    with pytest.raises(ValidationError):
        _dataset_manifest(**{field: "A" * 64})


def test_dataset_manifest_rejects_blank_id() -> None:
    with pytest.raises(ValidationError):
        _dataset_manifest(dataset_id="   ")


@pytest.mark.parametrize("value", ["", "   "])
def test_dataset_manifest_rejects_blank_license(value: str) -> None:
    with pytest.raises(ValidationError):
        _dataset_manifest(license=value)


def test_dataset_manifest_rejects_naive_created_at() -> None:
    with pytest.raises(ValidationError):
        _dataset_manifest(created_at=datetime(2026, 8, 30, tzinfo=UTC).replace(tzinfo=None))


def test_unknown_is_a_distinct_trace_label() -> None:
    assert {item.value for item in TraceLabel} == {
        "RELEVANT",
        "CONFIRMED_BENIGN",
        "UNKNOWN",
    }


@pytest.mark.parametrize("field", ["edge_id", "source_id", "target_id"])
def test_trace_edge_rejects_blank_ids(field: str) -> None:
    with pytest.raises(ValidationError):
        _trace_edge(**{field: "   "})


def test_trace_edge_rejects_naive_event_time() -> None:
    with pytest.raises(ValidationError):
        _trace_edge(event_time=datetime(2026, 8, 30, tzinfo=UTC).replace(tzinfo=None))


def test_trace_gold_manifest_accepts_complete_provenance() -> None:
    manifest = _trace_gold_manifest()

    assert manifest.case_id == "case-1"
    assert manifest.edges[0].label is TraceLabel.RELEVANT


def test_trace_gold_manifest_rejects_uppercase_configuration_hash() -> None:
    with pytest.raises(ValidationError):
        _trace_gold_manifest(configuration_hash="C" * 64)


@pytest.mark.parametrize("field", ["dataset_id", "case_id"])
def test_trace_gold_manifest_rejects_blank_ids(field: str) -> None:
    with pytest.raises(ValidationError):
        _trace_gold_manifest(**{field: "   "})


@pytest.mark.parametrize("field", ["generator_version", "typology"])
@pytest.mark.parametrize("value", ["", "   "])
def test_trace_gold_manifest_rejects_blank_provenance(field: str, value: str) -> None:
    with pytest.raises(ValidationError):
        _trace_gold_manifest(**{field: value})


@pytest.mark.parametrize("field", ["mandatory_anchors", "visibility_boundary_ids"])
def test_trace_gold_manifest_rejects_blank_nested_ids(field: str) -> None:
    with pytest.raises(ValidationError):
        _trace_gold_manifest(**{field: ("   ",)})


def test_trace_gold_manifest_rejects_boolean_generator_seed() -> None:
    with pytest.raises(ValidationError):
        _trace_gold_manifest(generator_seed=True)


def test_split_manifest_preserves_all_tracks() -> None:
    manifest = _split_manifest()

    assert manifest.train_case_ids == ("train-1",)
    assert manifest.unseen_generator_case_ids == ("unseen-1",)


@pytest.mark.parametrize(
    "field",
    [
        "train_case_ids",
        "validation_case_ids",
        "calibration_case_ids",
        "temporal_test_case_ids",
        "heldout_typology_case_ids",
        "unseen_generator_case_ids",
    ],
)
def test_split_manifest_rejects_blank_case_ids(field: str) -> None:
    with pytest.raises(ValidationError):
        _split_manifest(**{field: ("   ",)})


def test_sha256_file_hashes_file_contents(tmp_path: Path) -> None:
    source = tmp_path / "fixture.txt"
    source.write_bytes(b"tracebench\n")

    assert sha256_file(source) == "16fec36caeac2250ecf68264da38f599fb4d3dd6e45338ac735ddc46ef635bdb"
