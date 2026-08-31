from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray
from pydantic import ValidationError

from fincrime.evaluation.detection import (
    DetectionMetrics,
    detection_metrics,
    fit_score_calibrator,
)


def test_precision_at_fixed_budget() -> None:
    y_true = np.array([1, 0, 1, 0], dtype=np.int64)
    scores = np.array([0.9, 0.8, 0.7, 0.1], dtype=np.float64)
    metrics = detection_metrics(y_true, scores, alert_budget=2)
    assert metrics.precision_at_k == 0.5
    assert 0.0 <= metrics.pr_auc <= 1.0
    assert 0.0 <= metrics.brier <= 1.0


def test_stable_tie_breaking_in_ranking() -> None:
    # Elements at index 0 and 1 have tied scores; stable sort preserves index 0 before index 1
    y_true = np.array([1, 0, 0, 1], dtype=np.int64)
    scores = np.array([0.8, 0.8, 0.3, 0.1], dtype=np.float64)
    metrics_k1 = detection_metrics(y_true, scores, alert_budget=1)
    # top 1 selected is index 0 with label 1
    assert metrics_k1.precision_at_k == 1.0


def test_calibrator_is_fit_only_from_supplied_calibration_scores() -> None:
    calibration_scores = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    calibration_labels = np.array([0, 0, 1, 1], dtype=np.int64)
    calibrator = fit_score_calibrator(calibration_scores, calibration_labels)
    calibrated = calibrator.predict(np.array([0.15, 0.85], dtype=np.float64))
    assert calibrated.shape == (2,)
    assert calibrated[1] > calibrated[0]
    assert np.all((calibrated >= 0.0) & (calibrated <= 1.0))


@pytest.mark.parametrize("invalid_budget", [0, -1, -100])
def test_invalid_alert_budget_fails_validation(invalid_budget: int) -> None:
    y_true = np.array([1, 0], dtype=np.int64)
    scores = np.array([0.8, 0.2], dtype=np.float64)
    with pytest.raises(ValueError, match="budget|positive"):
        detection_metrics(y_true, scores, alert_budget=invalid_budget)


@pytest.mark.parametrize("bad_budget_type", [1.5, "2", None, True, False])
def test_invalid_alert_budget_type_fails_validation(bad_budget_type: object) -> None:
    y_true = np.array([1, 0], dtype=np.int64)
    scores = np.array([0.8, 0.2], dtype=np.float64)
    with pytest.raises(TypeError, match="budget|integer"):
        detection_metrics(y_true, scores, alert_budget=bad_budget_type)  # type: ignore[arg-type]


def test_mismatched_scores_and_labels_length() -> None:
    y_true = np.array([1, 0, 1], dtype=np.int64)
    scores = np.array([0.8, 0.2], dtype=np.float64)
    with pytest.raises(ValueError, match="match|length|shape"):
        detection_metrics(y_true, scores, alert_budget=2)


@pytest.mark.parametrize("invalid_labels", [np.array([0, 0]), np.array([1, 1]), np.array([0, 2])])
def test_invalid_label_diversity_fails_validation(invalid_labels: NDArray[np.int64]) -> None:
    scores = np.array([0.8, 0.2], dtype=np.float64)
    with pytest.raises(ValueError, match="both classes|binary"):
        detection_metrics(invalid_labels, scores, alert_budget=1)


@pytest.mark.parametrize("bad_score", [np.nan, np.inf, -np.inf, 1.5, -0.1])
def test_invalid_scores_fails_validation(bad_score: float) -> None:
    y_true = np.array([1, 0], dtype=np.int64)
    scores = np.array([bad_score, 0.2], dtype=np.float64)
    with pytest.raises(ValueError, match="finite|bounded|probability|score"):
        detection_metrics(y_true, scores, alert_budget=1)


def test_calibrator_requires_both_classes() -> None:
    calibration_scores = np.array([0.1, 0.2, 0.8, 0.9], dtype=np.float64)
    calibration_labels = np.array([0, 0, 0, 0], dtype=np.int64)
    with pytest.raises(ValueError, match="both classes|diversity"):
        fit_score_calibrator(calibration_scores, calibration_labels)


def test_detection_metrics_immutability() -> None:
    metrics = DetectionMetrics(pr_auc=0.8, precision_at_k=0.6, brier=0.1)
    with pytest.raises(ValidationError):
        metrics.pr_auc = 0.9  # type: ignore[misc]
