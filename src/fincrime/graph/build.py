from __future__ import annotations

from collections.abc import Iterable
from datetime import UTC, datetime

import networkx as nx  # type: ignore[import-untyped]

from fincrime.graph.events import TransactionEvent


def build_graph(
    events: Iterable[TransactionEvent], cutoff: datetime
) -> nx.MultiDiGraph:
    """Build a point-in-time multi-directed graph excluding future events."""
    if cutoff.tzinfo is None or cutoff.tzinfo.utcoffset(cutoff) is None:
        raise ValueError("cutoff must be timezone-aware")

    cutoff_utc = cutoff.astimezone(UTC)
    event_list = list(events)

    seen_edge_ids: set[str] = set()
    for event in event_list:
        if event.edge_id in seen_edge_ids:
            raise ValueError(f"Duplicate edge_id '{event.edge_id}' found in events")
        seen_edge_ids.add(event.edge_id)

    graph = nx.MultiDiGraph(cutoff=cutoff.isoformat())
    for event in sorted(
        event_list,
        key=lambda item: (item.event_time.astimezone(UTC), item.edge_id),
    ):
        if event.event_time.astimezone(UTC) > cutoff_utc:
            continue
        graph.add_edge(
            event.source_id,
            event.target_id,
            key=event.edge_id,
            amount=event.amount,
            event_time=event.event_time,
        )
    return graph
