from __future__ import annotations

import pytest
from pydantic import ValidationError

from fincrime.contracts.manifests import TraceLabel
from fincrime.evaluation.tracing import TraceMetrics, trace_metrics


def test_trace_metrics_report_unknown_separately() -> None:
    metrics = trace_metrics(
        returned=("e1", "e2", "e3"),
        labels={
            "e1": TraceLabel.RELEVANT,
            "e2": TraceLabel.CONFIRMED_BENIGN,
            "e3": TraceLabel.UNKNOWN,
        },
    )
    assert metrics.relevant_recall == 1.0
    assert metrics.confirmed_benign_contamination == pytest.approx(1 / 3)
    assert metrics.unknown_inclusion_rate == pytest.approx(1 / 3)


def test_empty_returned_edges_yields_zero_rates() -> None:
    metrics = trace_metrics(
        returned=(),
        labels={
            "e1": TraceLabel.RELEVANT,
            "e2": TraceLabel.CONFIRMED_BENIGN,
        },
    )
    assert metrics.relevant_recall == 0.0
    assert metrics.confirmed_benign_contamination == 0.0
    assert metrics.unknown_inclusion_rate == 0.0


def test_missing_edge_in_labels_fails_validation() -> None:
    with pytest.raises(ValueError, match="not found|missing"):
        trace_metrics(
            returned=("e1", "e_unknown"),
            labels={"e1": TraceLabel.RELEVANT},
        )


def test_trace_metrics_immutability() -> None:
    metrics = TraceMetrics(
        relevant_recall=1.0,
        confirmed_benign_contamination=0.2,
        unknown_inclusion_rate=0.1,
    )
    with pytest.raises(ValidationError):
        metrics.relevant_recall = 0.5  # type: ignore[misc]
