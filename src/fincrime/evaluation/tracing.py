from __future__ import annotations

from collections.abc import Sequence

from pydantic import BaseModel, ConfigDict

from fincrime.contracts.manifests import TraceLabel


class TraceMetrics(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    relevant_recall: float
    confirmed_benign_contamination: float
    unknown_inclusion_rate: float


def trace_metrics(returned: Sequence[str], labels: dict[str, TraceLabel]) -> TraceMetrics:
    """Evaluate trace ranker predictions with separate tri-state metrics."""
    for item in returned:
        if item not in labels:
            raise ValueError(f"Returned edge ID '{item}' not found in labels dictionary")

    relevant_total = sum(label == TraceLabel.RELEVANT for label in labels.values())
    relevant_returned = sum(labels[item] == TraceLabel.RELEVANT for item in returned)
    benign_returned = sum(labels[item] == TraceLabel.CONFIRMED_BENIGN for item in returned)
    unknown_returned = sum(labels[item] == TraceLabel.UNKNOWN for item in returned)
    count = len(returned)

    return TraceMetrics(
        relevant_recall=0.0 if relevant_total == 0 else float(relevant_returned / relevant_total),
        confirmed_benign_contamination=0.0 if count == 0 else float(benign_returned / count),
        unknown_inclusion_rate=0.0 if count == 0 else float(unknown_returned / count),
    )
