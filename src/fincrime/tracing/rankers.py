from __future__ import annotations

from collections.abc import Sequence

import lightgbm as lgb
import numpy as np
from numpy.typing import NDArray

from fincrime.contracts.manifests import TraceLabel


def training_mask(labels: NDArray[np.object_] | Sequence[TraceLabel | str]) -> NDArray[np.bool_]:
    """Exclude UNKNOWN labels from training mask so they are never treated as negative."""
    return np.array([label != TraceLabel.UNKNOWN for label in labels], dtype=bool)


def fit_trace_ranker(
    x: NDArray[np.float64], labels: NDArray[np.object_] | Sequence[TraceLabel | str], seed: int
) -> lgb.LGBMRanker:
    """Fit a LightGBM LambdaRank model on known candidate edge features."""
    if type(seed) is not int:
        raise TypeError(f"seed must be an integer, got {type(seed).__name__}")

    x_arr = np.asarray(x, dtype=np.float64)
    if x_arr.ndim != 2:
        raise ValueError(f"x must be a 2D matrix, got {x_arr.ndim}D array")
    if not np.all(np.isfinite(x_arr)):
        raise ValueError("x must contain only finite float values")

    labels_list = list(labels)
    if x_arr.shape[0] != len(labels_list):
        raise ValueError(
            f"Length mismatch: x has {x_arr.shape[0]} rows, labels has {len(labels_list)} elements"
        )

    mask = training_mask(labels_list)
    known_count = int(mask.sum())
    if known_count == 0:
        raise ValueError("At least one known label (RELEVANT or CONFIRMED_BENIGN) is required for training")

    y = np.array(
        [1 if label == TraceLabel.RELEVANT else 0 for label, is_known in zip(labels_list, mask, strict=True) if is_known],
        dtype=np.int32,
    )
    model = lgb.LGBMRanker(objective="lambdarank", random_state=seed, verbosity=-1)
    model.fit(x_arr[mask], y, group=[known_count])
    return model


def rank_edges(
    model: lgb.LGBMRanker, x: NDArray[np.float64], edge_ids: Sequence[str]
) -> tuple[str, ...]:
    """Rank edges deterministically by model score with stable tie-breaking by edge ID."""
    x_arr = np.asarray(x, dtype=np.float64)
    if x_arr.ndim != 2:
        raise ValueError(f"x must be a 2D matrix, got {x_arr.ndim}D array")
    if x_arr.shape[0] != len(edge_ids):
        raise ValueError(
            f"Length mismatch: x has {x_arr.shape[0]} rows, edge_ids has {len(edge_ids)} elements"
        )
    if len(edge_ids) == 0:
        return ()

    scores = np.asarray(model.predict(x_arr), dtype=np.float64)
    order = sorted(range(len(edge_ids)), key=lambda i: (-float(scores[i]), str(edge_ids[i])))
    return tuple(edge_ids[i] for i in order)
