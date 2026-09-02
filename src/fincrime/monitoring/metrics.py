from __future__ import annotations

from prometheus_client import Counter, Histogram

EVENTS_PROCESSED = Counter(
    "fincrime_events_processed",
    "Total validated transaction events processed",
)

EVENTS_QUARANTINED = Counter(
    "fincrime_events_quarantined",
    "Total invalid transaction events quarantined",
)

SCORING_LATENCY = Histogram(
    "fincrime_scoring_latency_seconds",
    "Latency of incremental transaction scoring in seconds",
)
