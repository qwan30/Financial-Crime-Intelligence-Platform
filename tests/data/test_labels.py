from __future__ import annotations

import polars as pl
import pytest

from fincrime.data.labels import account_labels
from fincrime.data.tracebench import public_transactions


def test_node_labels_cannot_enter_public_transactions() -> None:
    labels = account_labels(pl.DataFrame({"nodeid": ["a"], "isFraud": [1], "fraudStep": [7]}))
    assert labels.columns == ["account_id", "is_fraud", "label_provenance"]
    public = public_transactions(
        pl.DataFrame(
            {
                "edge_id": ["e"],
                "source_id": ["a"],
                "target_id": ["b"],
                "amount": [1.0],
                "event_time": ["2026-01-01T00:00:00Z"],
                "isFraud": [1],
                "fraudStep": [7],
            }
        )
    )
    assert {"isFraud", "fraudStep"}.isdisjoint(public.columns)


def test_account_labels_validates_required_columns() -> None:
    with pytest.raises(ValueError, match="missing required columns"):
        account_labels(pl.DataFrame({"nodeid": ["a"], "isFraud": [1]}))


def test_account_labels_rejects_blank_or_null_node_id() -> None:
    with pytest.raises(ValueError, match="null or blank identifier"):
        account_labels(pl.DataFrame({"nodeid": [None], "isFraud": [1], "fraudStep": [1]}))

    with pytest.raises(ValueError, match="null or blank identifier"):
        account_labels(pl.DataFrame({"nodeid": ["   "], "isFraud": [1], "fraudStep": [1]}))


def test_account_labels_rejects_invalid_is_fraud_values() -> None:
    with pytest.raises(ValueError, match="isFraud"):
        account_labels(pl.DataFrame({"nodeid": ["a"], "isFraud": [2], "fraudStep": [1]}))

    with pytest.raises(ValueError, match="isFraud"):
        account_labels(pl.DataFrame({"nodeid": ["a"], "isFraud": [None], "fraudStep": [1]}))


def test_account_labels_preserves_fraud_step_as_label_provenance() -> None:
    raw = pl.DataFrame(
        {
            "nodeid": ["acc_0", "acc_1"],
            "isFraud": [0, 1],
            "fraudStep": [-1, 42],
        }
    )
    labels = account_labels(raw)
    assert labels.columns == ["account_id", "is_fraud", "label_provenance"]
    assert labels["account_id"].to_list() == ["acc_0", "acc_1"]
    assert labels["is_fraud"].to_list() == [0, 1]
    assert labels["label_provenance"].to_list() == ["-1", "42"]


@pytest.mark.parametrize(
    "invalid_fraud_value",
    [0.5, 0.1, 0.9, 1.5, -0.5, 1.0001, -0.0001, "0.5", "1.2"],
)
def test_account_labels_rejects_fractional_is_fraud_values(invalid_fraud_value: object) -> None:
    with pytest.raises(ValueError, match="isFraud"):
        account_labels(
            pl.DataFrame({"nodeid": ["a"], "isFraud": [invalid_fraud_value], "fraudStep": [1]})
        )
