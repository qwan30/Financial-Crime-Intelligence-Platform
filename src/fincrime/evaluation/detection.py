from __future__ import annotations

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict
from sklearn.isotonic import IsotonicRegression  # type: ignore[import-untyped]
from sklearn.metrics import (  # type: ignore[import-untyped]
    average_precision_score,
    brier_score_loss,
)


class DetectionMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    pr_auc: float
    precision_at_k: float
    brier: float


def detection_metrics(
    y_true: NDArray[np.int64], scores: NDArray[np.float64], alert_budget: int
) -> DetectionMetrics:
    """Compute fixed-budget ranking and probability calibration metrics."""
    if type(alert_budget) is not int:
        raise TypeError(f"alert_budget must be an integer, got {type(alert_budget).__name__}")
    if alert_budget <= 0:
        raise ValueError(f"alert_budget must be positive, got {alert_budget}")

    y_arr = np.asarray(y_true, dtype=np.int64)
    if y_arr.ndim != 1:
        raise ValueError(f"y_true must be a 1D array, got {y_arr.ndim}D array")

    scores_arr = np.asarray(scores, dtype=np.float64)
    if scores_arr.ndim != 1:
        raise ValueError(f"scores must be a 1D array, got {scores_arr.ndim}D array")

    if y_arr.shape[0] != scores_arr.shape[0]:
        raise ValueError(
            f"Length mismatch: y_true has {y_arr.shape[0]} elements, scores has {scores_arr.shape[0]} elements"
        )

    unique_y = np.unique(y_arr)
    if len(unique_y) != 2 or not set(unique_y).issubset({0, 1}):
        raise ValueError("y_true must contain binary labels with both classes (0 and 1)")

    if not np.all(np.isfinite(scores_arr)):
        raise ValueError("scores must contain finite values")
    if np.any((scores_arr < 0.0) | (scores_arr > 1.0)):
        raise ValueError("scores must be bounded between 0.0 and 1.0")

    order = np.argsort(-scores_arr, kind="stable")[:alert_budget]
    pr_auc = float(average_precision_score(y_arr, scores_arr))
    precision_at_k = float(y_arr[order].mean())
    brier = float(brier_score_loss(y_arr, scores_arr))

    return DetectionMetrics(
        pr_auc=pr_auc,
        precision_at_k=precision_at_k,
        brier=brier,
    )


def fit_score_calibrator(
    calibration_scores: NDArray[np.float64], calibration_labels: NDArray[np.int64]
) -> IsotonicRegression:
    """Fit an isotonic regression score calibrator strictly on calibration data."""
    scores_arr = np.asarray(calibration_scores, dtype=np.float64)
    if scores_arr.ndim != 1:
        raise ValueError(f"calibration_scores must be a 1D array, got {scores_arr.ndim}D array")
    if not np.all(np.isfinite(scores_arr)):
        raise ValueError("calibration_scores must contain finite values")
    if np.any((scores_arr < 0.0) | (scores_arr > 1.0)):
        raise ValueError("calibration_scores must be bounded between 0.0 and 1.0")

    labels_arr = np.asarray(calibration_labels, dtype=np.int64)
    if labels_arr.ndim != 1:
        raise ValueError(f"calibration_labels must be a 1D array, got {labels_arr.ndim}D array")
    if scores_arr.shape[0] != labels_arr.shape[0]:
        raise ValueError("calibration_scores and calibration_labels must have matching lengths")

    unique_labels = np.unique(labels_arr)
    if len(unique_labels) != 2 or not set(unique_labels).issubset({0, 1}):
        raise ValueError("calibration_labels must contain both classes (0 and 1)")

    return IsotonicRegression(out_of_bounds="clip").fit(scores_arr, labels_arr)
