"""MLflow experiment tracking and lineage binding for frozen research runs."""

from __future__ import annotations

import math
import re
from typing import Any

from mlflow.tracking import MlflowClient

_GIT_SHA_REGEX = re.compile(r"^[0-9a-f]{40}$")
_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")


def tracking_tags(git_sha: str, dataset_hash: str, split_hash: str) -> dict[str, str]:
    """Validate git SHA and dataset/split hashes and return standardized MLflow tracking tags."""
    if not _GIT_SHA_REGEX.match(git_sha):
        raise ValueError(
            f"Invalid git_sha: must be 40-character lowercase hex string, got '{git_sha}'"
        )
    if not _HEX64_REGEX.match(dataset_hash):
        raise ValueError(
            f"Invalid dataset_hash: must be 64-character lowercase hex string, got '{dataset_hash}'"
        )
    if not _HEX64_REGEX.match(split_hash):
        raise ValueError(
            f"Invalid split_hash: must be 64-character lowercase hex string, got '{split_hash}'"
        )
    return {
        "git_sha": git_sha,
        "dataset_hash": dataset_hash,
        "split_hash": split_hash,
    }


def log_frozen_run(
    tags: dict[str, str],
    metrics: dict[str, float],
    tracking_uri: str,
    experiment_name: str = "fincrime_research_frozen",
) -> str:
    """Log a frozen experiment run to MLflow with fail-closed read-back verification."""
    for k, v in metrics.items():
        if not math.isfinite(v):
            raise ValueError(f"Metric '{k}' must be finite, got '{v}'")

    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        exp_id = client.create_experiment(experiment_name)
    else:
        exp_id = experiment.experiment_id

    run = client.create_run(experiment_id=exp_id, tags=tags)
    for k, v in metrics.items():
        client.log_metric(run.info.run_id, k, v)
    client.set_terminated(run.info.run_id, status="FINISHED")

    # Internal read-back verification (fail closed on mismatch)
    persisted = client.get_run(run.info.run_id)
    if persisted.info.status != "FINISHED":
        raise RuntimeError(
            f"MLflow run {run.info.run_id} status mismatch: expected FINISHED, got {persisted.info.status}"
        )
    for tk, tv in tags.items():
        if persisted.data.tags.get(tk) != tv:
            raise RuntimeError(
                f"MLflow tag mismatch on '{tk}': expected '{tv}', got '{persisted.data.tags.get(tk)}'"
            )
    for mk, mv in metrics.items():
        persisted_val = persisted.data.metrics.get(mk)
        if persisted_val is None or not math.isclose(persisted_val, mv, abs_tol=1e-6):
            raise RuntimeError(
                f"MLflow metric mismatch on '{mk}': expected {mv}, got {persisted_val}"
            )

    return str(run.info.run_id)


def get_run_metadata(run_id: str, tracking_uri: str) -> dict[str, Any]:
    """Retrieve metadata, status, tags, and metrics for a logged MLflow run."""
    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    return {
        "run_id": run.info.run_id,
        "status": run.info.status,
        "tags": dict(run.data.tags),
        "metrics": dict(run.data.metrics),
    }
