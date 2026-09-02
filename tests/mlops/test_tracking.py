from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import pytest

from fincrime.mlops.tracking import get_run_metadata, log_frozen_run, tracking_tags


def test_tracking_tags_bind_and_validate_hashes() -> None:
    git_sha = "a" * 40
    dataset_hash = "b" * 64
    split_hash = "c" * 64

    tags = tracking_tags(git_sha=git_sha, dataset_hash=dataset_hash, split_hash=split_hash)
    assert tags == {
        "git_sha": git_sha,
        "dataset_hash": dataset_hash,
        "split_hash": split_hash,
    }


@pytest.mark.parametrize(
    "invalid_git_sha",
    [
        "a" * 39,
        "a" * 41,
        "A" * 40,
        "g" * 40,
        "",
        "not-a-sha",
    ],
)
def test_invalid_git_sha_rejected(invalid_git_sha: str) -> None:
    with pytest.raises(ValueError, match="Invalid git_sha"):
        tracking_tags(git_sha=invalid_git_sha, dataset_hash="b" * 64, split_hash="c" * 64)


@pytest.mark.parametrize(
    "invalid_dataset_hash",
    [
        "b" * 63,
        "b" * 65,
        "B" * 64,
        "g" * 64,
        "",
        "not-a-sha",
    ],
)
def test_invalid_dataset_hash_rejected(invalid_dataset_hash: str) -> None:
    with pytest.raises(ValueError, match="Invalid dataset_hash"):
        tracking_tags(git_sha="a" * 40, dataset_hash=invalid_dataset_hash, split_hash="c" * 64)


@pytest.mark.parametrize(
    "invalid_split_hash",
    [
        "c" * 63,
        "c" * 65,
        "C" * 64,
        "g" * 64,
        "",
        "not-a-sha",
    ],
)
def test_invalid_split_hash_rejected(invalid_split_hash: str) -> None:
    with pytest.raises(ValueError, match="Invalid split_hash"):
        tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash=invalid_split_hash)


def test_log_frozen_run_records_and_reads_back_cleanly(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags = tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash="c" * 64)
    metrics = {"roc_auc": 0.885, "pr_auc": 0.652, "loss": 0.123}

    run_id = log_frozen_run(
        tags=tags,
        metrics=metrics,
        tracking_uri=tracking_uri,
        experiment_name="test_frozen_exp",
    )
    assert isinstance(run_id, str) and len(run_id) > 0

    meta = get_run_metadata(run_id, tracking_uri=tracking_uri)
    assert meta["run_id"] == run_id
    assert meta["status"] == "FINISHED"
    assert meta["tags"]["git_sha"] == "a" * 40
    assert meta["tags"]["dataset_hash"] == "b" * 64
    assert meta["tags"]["split_hash"] == "c" * 64
    assert meta["metrics"]["roc_auc"] == pytest.approx(0.885)
    assert meta["metrics"]["pr_auc"] == pytest.approx(0.652)
    assert meta["metrics"]["loss"] == pytest.approx(0.123)


def test_log_frozen_run_creates_or_reuses_experiment(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags1 = tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash="c" * 64)
    tags2 = tracking_tags(git_sha="d" * 40, dataset_hash="e" * 64, split_hash="f" * 64)

    run1_id = log_frozen_run(
        tags=tags1,
        metrics={"acc": 0.9},
        tracking_uri=tracking_uri,
        experiment_name="reused_exp",
    )
    run2_id = log_frozen_run(
        tags=tags2,
        metrics={"acc": 0.95},
        tracking_uri=tracking_uri,
        experiment_name="reused_exp",
    )

    assert run1_id != run2_id
    meta1 = get_run_metadata(run1_id, tracking_uri=tracking_uri)
    meta2 = get_run_metadata(run2_id, tracking_uri=tracking_uri)
    assert meta1["status"] == "FINISHED"
    assert meta2["status"] == "FINISHED"


@pytest.mark.parametrize("bad_val", [float("nan"), float("inf"), float("-inf")])
def test_log_frozen_run_rejects_non_finite_metrics(tmp_path: Path, bad_val: float) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags = tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash="c" * 64)
    with pytest.raises(ValueError, match="must be finite"):
        log_frozen_run(
            tags=tags,
            metrics={"roc_auc": bad_val},
            tracking_uri=tracking_uri,
            experiment_name="bad_metric_exp",
        )


def test_log_frozen_run_fails_closed_on_status_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mlflow.tracking import MlflowClient

    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags = tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash="c" * 64)

    original_get_run = MlflowClient.get_run

    def mock_get_run(self: MlflowClient, run_id: str) -> Any:
        run = original_get_run(self, run_id)
        # Create a mock run info with FAILED status
        mock_info = MagicMock()
        mock_info.run_id = run.info.run_id
        mock_info.status = "FAILED"
        mock_run = MagicMock()
        mock_run.info = mock_info
        mock_run.data = run.data
        return mock_run

    monkeypatch.setattr(MlflowClient, "get_run", mock_get_run)

    with pytest.raises(RuntimeError, match="status mismatch"):
        log_frozen_run(
            tags=tags,
            metrics={"roc_auc": 0.8},
            tracking_uri=tracking_uri,
            experiment_name="fail_status_exp",
        )


def test_log_frozen_run_fails_closed_on_tag_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mlflow.tracking import MlflowClient

    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags = tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash="c" * 64)

    original_get_run = MlflowClient.get_run

    def mock_get_run(self: MlflowClient, run_id: str) -> Any:
        run = original_get_run(self, run_id)
        mock_data = MagicMock()
        mock_data.tags = {"git_sha": "wrong_sha"}
        mock_data.metrics = run.data.metrics
        mock_run = MagicMock()
        mock_run.info = run.info
        mock_run.data = mock_data
        return mock_run

    monkeypatch.setattr(MlflowClient, "get_run", mock_get_run)

    with pytest.raises(RuntimeError, match="tag mismatch"):
        log_frozen_run(
            tags=tags,
            metrics={"roc_auc": 0.8},
            tracking_uri=tracking_uri,
            experiment_name="fail_tag_exp",
        )


def test_log_frozen_run_fails_closed_on_metric_mismatch(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from mlflow.tracking import MlflowClient

    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags = tracking_tags(git_sha="a" * 40, dataset_hash="b" * 64, split_hash="c" * 64)

    original_get_run = MlflowClient.get_run

    def mock_get_run(self: MlflowClient, run_id: str) -> Any:
        run = original_get_run(self, run_id)
        mock_data = MagicMock()
        mock_data.tags = run.data.tags
        mock_data.metrics = {"roc_auc": 0.5}  # Mismatched metric
        mock_run = MagicMock()
        mock_run.info = run.info
        mock_run.data = mock_data
        return mock_run

    monkeypatch.setattr(MlflowClient, "get_run", mock_get_run)

    with pytest.raises(RuntimeError, match="metric mismatch"):
        log_frozen_run(
            tags=tags,
            metrics={"roc_auc": 0.8},
            tracking_uri=tracking_uri,
            experiment_name="fail_metric_exp",
        )
