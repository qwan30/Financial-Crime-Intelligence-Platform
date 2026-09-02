from __future__ import annotations

from typing import Protocol

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray
from sklearn.linear_model import LogisticRegression  # type: ignore[import-untyped]


class ProbabilityModel(Protocol):
    def predict_proba(self, x: NDArray[np.float64]) -> NDArray[np.float64]: ...


def _validate_fit_inputs(
    x: object, y: object, seed: object
) -> tuple[NDArray[np.float64], NDArray[np.int64]]:
    if type(seed) is not int:
        raise TypeError(f"seed must be an integer, got {type(seed).__name__}")

    try:
        x_arr = np.asarray(x, dtype=np.float64)
    except Exception as exc:
        raise ValueError(f"Failed to convert x to float64 array: {exc}") from exc

    if x_arr.ndim != 2:
        raise ValueError(f"x must be a 2D array, got {x_arr.ndim}D array")
    if x_arr.shape[0] == 0 or x_arr.shape[1] == 0:
        raise ValueError("x must not be empty")
    if not np.all(np.isfinite(x_arr)):
        raise ValueError("x contains non-finite values (NaN or Inf)")

    y_raw = np.asarray(y)
    if y_raw.ndim != 1:
        raise ValueError(f"y must be a 1D array, got {y_raw.ndim}D array")

    try:
        y_arr = y_raw.astype(np.int64)
    except Exception as exc:
        raise ValueError(f"Failed to convert y to int64 array: {exc}") from exc

    if x_arr.shape[0] != y_arr.shape[0]:
        raise ValueError(
            f"Row count mismatch: x has {x_arr.shape[0]} rows, y has {y_arr.shape[0]} elements"
        )

    unique_y = np.unique(y_arr)
    if len(unique_y) != 2 or not set(unique_y).issubset({0, 1}):
        raise ValueError("y must contain binary labels with both classes (0 and 1)")

    return x_arr, y_arr


def fit_logistic(x: NDArray[np.float64], y: NDArray[np.int64], seed: int) -> LogisticRegression:
    """Fit a balanced LogisticRegression baseline on binary tabular features."""
    x_arr, y_arr = _validate_fit_inputs(x, y, seed)
    return LogisticRegression(class_weight="balanced", random_state=seed, max_iter=1000).fit(
        x_arr, y_arr
    )


def fit_lightgbm(x: NDArray[np.float64], y: NDArray[np.int64], seed: int) -> lgb.LGBMClassifier:
    """Fit a balanced LightGBM baseline on binary tabular features."""
    x_arr, y_arr = _validate_fit_inputs(x, y, seed)
    return lgb.LGBMClassifier(
        n_estimators=200,
        learning_rate=0.05,
        num_leaves=31,
        class_weight="balanced",
        random_state=seed,
        verbosity=-1,
    ).fit(x_arr, y_arr)


def predict_scores(model: ProbabilityModel, x: NDArray[np.float64]) -> NDArray[np.float64]:
    """Extract positive class probabilities from a fitted probability model."""
    x_arr = np.asarray(x, dtype=np.float64)
    if x_arr.ndim != 2:
        raise ValueError(f"x must be a 2D array, got {x_arr.ndim}D array")
    if not np.all(np.isfinite(x_arr)):
        raise ValueError("x contains non-finite values (NaN or Inf)")

    proba = model.predict_proba(x_arr)
    if proba.ndim != 2 or proba.shape[1] < 2:
        raise ValueError("predict_proba must return a 2D array with at least 2 class probabilities")

    scores = np.asarray(proba[:, 1], dtype=np.float64)
    if not np.all(np.isfinite(scores)) or np.any((scores < 0.0) | (scores > 1.0)):
        raise ValueError("Predicted probabilities must be finite numbers between 0.0 and 1.0")

    return scores
