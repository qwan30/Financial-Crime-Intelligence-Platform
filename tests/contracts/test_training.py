from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.contracts.training import (
    RESEARCH_SEEDS,
    ModelPackageManifest,
    TrainingRunSpec,
)


def test_training_run_uses_five_fixed_seeds_and_trial_cap() -> None:
    spec = TrainingRunSpec(
        run_id="baseline-001",
        hypothesis="LightGBM improves precision at K",
        model_family="lightgbm",
        dataset_manifest_hash="a" * 64,
        split_manifest_hash="b" * 64,
        feature_schema_hash="c" * 64,
        primary_metric="precision_at_k",
        alert_budget=100,
        search_trial_cap=20,
    )
    assert spec.random_seeds == RESEARCH_SEEDS
    assert spec.random_seeds == (11, 23, 37, 53, 71)
    assert spec.search_trial_cap == 20


def test_baseline_json_is_valid_preregistration_spec() -> None:
    config_path = Path("configs/research/baseline.json")
    assert config_path.exists(), "configs/research/baseline.json must exist"

    raw_text = config_path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    spec = TrainingRunSpec.model_validate(data)

    assert spec.run_id == "baseline-001"
    assert spec.model_family == "lightgbm"
    assert spec.alert_budget == 100
    assert spec.search_trial_cap == 20
    assert spec.random_seeds == RESEARCH_SEEDS


@pytest.mark.parametrize(
    "invalid_hash",
    [
        "a" * 63,
        "a" * 65,
        "g" * 64,
        "A" * 64,
        "",
    ],
)
def test_invalid_sha256_hash_fails_validation(invalid_hash: str) -> None:
    with pytest.raises(ValidationError):
        TrainingRunSpec(
            run_id="baseline-001",
            hypothesis="test",
            model_family="lightgbm",
            dataset_manifest_hash=invalid_hash,
            split_manifest_hash="b" * 64,
            feature_schema_hash="c" * 64,
            primary_metric="precision_at_k",
            alert_budget=100,
            search_trial_cap=20,
        )


@pytest.mark.parametrize("invalid_budget", [0, -1, -100])
def test_invalid_alert_budget_fails_validation(invalid_budget: int) -> None:
    with pytest.raises(ValidationError):
        TrainingRunSpec(
            run_id="baseline-001",
            hypothesis="test",
            model_family="lightgbm",
            dataset_manifest_hash="a" * 64,
            split_manifest_hash="b" * 64,
            feature_schema_hash="c" * 64,
            primary_metric="precision_at_k",
            alert_budget=invalid_budget,
            search_trial_cap=20,
        )


@pytest.mark.parametrize("invalid_cap", [0, -1, 51, 100])
def test_invalid_search_trial_cap_fails_validation(invalid_cap: int) -> None:
    with pytest.raises(ValidationError):
        TrainingRunSpec(
            run_id="baseline-001",
            hypothesis="test",
            model_family="lightgbm",
            dataset_manifest_hash="a" * 64,
            split_manifest_hash="b" * 64,
            feature_schema_hash="c" * 64,
            primary_metric="precision_at_k",
            alert_budget=100,
            search_trial_cap=invalid_cap,
        )


def test_model_package_manifest_validation_and_immutability() -> None:
    manifest = ModelPackageManifest(
        run_id="baseline-001",
        model_family="lightgbm",
        artifact_sha256="a" * 64,
        git_sha="b" * 40,
        selected=True,
        limitations=("Requires tabular features",),
    )
    assert manifest.selected is True
    assert manifest.git_sha == "b" * 40

    with pytest.raises(ValidationError):
        manifest.selected = False  # type: ignore[misc]

    with pytest.raises(ValidationError):
        ModelPackageManifest(
            run_id="baseline-001",
            model_family="lightgbm",
            artifact_sha256="invalid",
            git_sha="b" * 40,
            selected=True,
            limitations=(),
        )

    with pytest.raises(ValidationError):
        ModelPackageManifest(
            run_id="baseline-001",
            model_family="lightgbm",
            artifact_sha256="a" * 64,
            git_sha="invalid_git_sha",
            selected=True,
            limitations=(),
        )


def test_extra_fields_are_forbidden() -> None:
    with pytest.raises(ValidationError):
        TrainingRunSpec(
            run_id="baseline-001",
            hypothesis="test",
            model_family="lightgbm",
            dataset_manifest_hash="a" * 64,
            split_manifest_hash="b" * 64,
            feature_schema_hash="c" * 64,
            primary_metric="precision_at_k",
            alert_budget=100,
            search_trial_cap=20,
            unknown_field="not_allowed",  # type: ignore[call-arg]
        )
