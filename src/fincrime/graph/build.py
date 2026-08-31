from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime

import networkx as nx  # type: ignore[import-untyped]

from fincrime.graph.events import TransactionEvent


def build_graph(
    events: Iterable[TransactionEvent], cutoff: datetime
) -> nx.MultiDiGraph:
    """Build a point-in-time multi-directed graph excluding future events."""
    cutoff_is_aware = cutoff.tzinfo is not None and cutoff.tzinfo.utcoffset(cutoff) is not None
    event_list = list(events)

    for event in event_list:
        event_is_aware = (
            event.event_time.tzinfo is not None
            and event.event_time.tzinfo.utcoffset(event.event_time) is not None
        )
        if cutoff_is_aware != event_is_aware:
            raise ValueError(
                f"Mismatched timezone awareness: cutoff is {'aware' if cutoff_is_aware else 'naive'}, "
                f"but event '{event.edge_id}' is {'aware' if event_is_aware else 'naive'}."
            )

    graph = nx.MultiDiGraph(cutoff=cutoff.isoformat())
    for event in sorted(event_list, key=lambda item: (item.event_time, item.edge_id)):
        if event.event_time > cutoff:
            continue
        graph.add_edge(
            event.source_id,
            event.target_id,
            key=event.edge_id,
            amount=event.amount,
            event_time=event.event_time,
        )
    return graph
