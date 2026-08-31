from __future__ import annotations

import numpy as np
import pytest

from fincrime.contracts.manifests import TraceLabel
from fincrime.tracing.rankers import (
    fit_trace_ranker,
    rank_edges,
    training_mask,
)


def test_unknown_edges_are_excluded_from_ranker_training() -> None:
    labels = np.array([TraceLabel.RELEVANT, TraceLabel.UNKNOWN, TraceLabel.CONFIRMED_BENIGN], dtype=object)
    assert training_mask(labels).tolist() == [True, False, True]


def test_fit_and_rank_edges_deterministic() -> None:
    # Minimal LightGBM dataset with 4 samples: 2 relevant, 2 benign, 1 unknown
    x = np.array(
        [
            [1.0, 5.0],
            [0.1, 0.2],
            [0.9, 4.0],
            [0.2, 0.1],
            [0.5, 0.5],  # unknown
        ],
        dtype=np.float64,
    )
    labels = np.array(
        [
            TraceLabel.RELEVANT,
            TraceLabel.CONFIRMED_BENIGN,
            TraceLabel.RELEVANT,
            TraceLabel.CONFIRMED_BENIGN,
            TraceLabel.UNKNOWN,
        ],
        dtype=object,
    )
    edge_ids = ("e1", "e2", "e3", "e4", "e5")

    model1 = fit_trace_ranker(x, labels, seed=42)
    ranked1 = rank_edges(model1, x, edge_ids)

    model2 = fit_trace_ranker(x, labels, seed=42)
    ranked2 = rank_edges(model2, x, edge_ids)

    assert ranked1 == ranked2
    assert len(ranked1) == len(edge_ids)


def test_empty_known_labels_fails_validation() -> None:
    x = np.array([[1.0], [2.0]], dtype=np.float64)
    labels = np.array([TraceLabel.UNKNOWN, TraceLabel.UNKNOWN], dtype=object)
    with pytest.raises(ValueError, match="known|empty|RELEVANT"):
        fit_trace_ranker(x, labels, seed=42)


def test_mismatched_x_and_labels_length_fails() -> None:
    x = np.array([[1.0], [2.0]], dtype=np.float64)
    labels = np.array([TraceLabel.RELEVANT], dtype=object)
    with pytest.raises(ValueError, match="match|length|shape"):
        fit_trace_ranker(x, labels, seed=42)


@pytest.mark.parametrize("bad_x", [np.array([[np.nan]]), np.array([[np.inf]])])
def test_non_finite_x_fails_validation(bad_x: np.ndarray) -> None:
    labels = np.array([TraceLabel.RELEVANT], dtype=object)
    with pytest.raises(ValueError, match="finite|nan|inf"):
        fit_trace_ranker(bad_x, labels, seed=42)


def test_invalid_label_type_fails_validation() -> None:
    x = np.array([[1.0], [2.0]], dtype=np.float64)
    with pytest.raises(TypeError, match="TraceLabel"):
        fit_trace_ranker(x, ["RELEVANT", "UNKNOWN"], seed=42)  # type: ignore[arg-type]
