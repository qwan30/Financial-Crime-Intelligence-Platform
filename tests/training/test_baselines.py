from __future__ import annotations

import numpy as np
import pytest
from numpy.typing import NDArray

from fincrime.contracts.training import RESEARCH_SEEDS
from fincrime.training.baselines import (
    ProbabilityModel,
    fit_lightgbm,
    fit_logistic,
    predict_scores,
)


@pytest.mark.parametrize("seed", RESEARCH_SEEDS)
def test_logistic_across_five_fixed_seeds(seed: int) -> None:
    x = np.array([[0.0], [0.2], [0.8], [1.0]], dtype=np.float64)
    y = np.array([0, 0, 1, 1], dtype=np.int64)
    model = fit_logistic(x, y, seed=seed)
    scores = predict_scores(model, x)
    assert scores.shape == (4,)
    assert np.all((scores >= 0.0) & (scores <= 1.0))
    assert scores[-1] > scores[0]


def test_lightgbm_smoke_behavior() -> None:
    try:
        import lightgbm  # noqa: F401
    except (ImportError, OSError) as exc:
        pytest.skip(f"LightGBM is not functional in this environment: {exc}")

    x = np.tile([[0.0, 0.1], [0.1, 0.2], [0.8, 0.9], [0.9, 1.0]], (10, 1)).astype(np.float64)
    y = np.tile([0, 0, 1, 1], 10).astype(np.int64)
    model = fit_lightgbm(x, y, seed=11)
    scores = predict_scores(model, x)
    assert scores.shape == (40,)
    assert np.all((scores >= 0.0) & (scores <= 1.0))
    assert scores[-1] > scores[0]


@pytest.mark.parametrize("invalid_dim_x", [np.array([0.0, 1.0]), np.zeros((2, 2, 2))])
def test_non_2d_features_fails_validation(invalid_dim_x: NDArray[np.float64]) -> None:
    y = np.array([0, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="2D|dimension|shape"):
        fit_logistic(invalid_dim_x, y, seed=11)


def test_non_1d_labels_fails_validation() -> None:
    x = np.array([[0.0], [1.0]], dtype=np.float64)
    y = np.array([[0], [1]], dtype=np.int64)
    with pytest.raises(ValueError, match="1D|dimension|shape"):
        fit_logistic(x, y, seed=11)


def test_mismatched_row_counts_fails_validation() -> None:
    x = np.array([[0.0], [0.5], [1.0]], dtype=np.float64)
    y = np.array([0, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="match|row|shape"):
        fit_logistic(x, y, seed=11)


@pytest.mark.parametrize("single_class_y", [np.array([0, 0, 0]), np.array([1, 1, 1])])
def test_single_class_fails_validation(single_class_y: NDArray[np.int64]) -> None:
    x = np.array([[0.0], [0.5], [1.0]], dtype=np.float64)
    with pytest.raises(ValueError, match="both classes|binary"):
        fit_logistic(x, single_class_y, seed=11)


@pytest.mark.parametrize(
    "invalid_labels",
    [
        np.array([0, 2]),
        np.array([-1, 1]),
        np.array([0, 1, 2]),
    ],
)
def test_non_binary_labels_fails_validation(invalid_labels: NDArray[np.int64]) -> None:
    x = np.zeros((len(invalid_labels), 1), dtype=np.float64)
    with pytest.raises(ValueError, match="binary|classes"):
        fit_logistic(x, invalid_labels, seed=11)


@pytest.mark.parametrize("bad_val", [np.nan, np.inf, -np.inf])
def test_non_finite_features_fails_validation(bad_val: float) -> None:
    x = np.array([[0.0], [bad_val], [1.0]], dtype=np.float64)
    y = np.array([0, 0, 1], dtype=np.int64)
    with pytest.raises(ValueError, match="finite|nan|inf"):
        fit_logistic(x, y, seed=11)


@pytest.mark.parametrize("bad_seed", ["11", 11.5, None, True, False])
def test_invalid_seed_type_fails_validation(bad_seed: object) -> None:
    x = np.array([[0.0], [1.0]], dtype=np.float64)
    y = np.array([0, 1], dtype=np.int64)
    with pytest.raises(TypeError, match="seed|integer"):
        fit_logistic(x, y, seed=bad_seed)  # type: ignore[arg-type]


def test_predict_scores_validates_input_and_output() -> None:
    x_train = np.array([[0.0], [1.0]], dtype=np.float64)
    y_train = np.array([0, 1], dtype=np.int64)
    model = fit_logistic(x_train, y_train, seed=11)

    # 1D test input
    with pytest.raises(ValueError, match="2D|dimension|shape"):
        predict_scores(model, np.array([0.5]))

    # Non-finite test input
    with pytest.raises(ValueError, match="finite|nan|inf"):
        predict_scores(model, np.array([[np.nan]]))


def test_custom_probability_model_protocol() -> None:
    class DummyModel:
        def predict_proba(self, x: NDArray[np.float64]) -> NDArray[np.float64]:
            return np.column_stack([1.0 - x[:, 0], x[:, 0]])

    model: ProbabilityModel = DummyModel()
    x = np.array([[0.25], [0.75]], dtype=np.float64)
    scores = predict_scores(model, x)
    assert np.allclose(scores, [0.25, 0.75])
