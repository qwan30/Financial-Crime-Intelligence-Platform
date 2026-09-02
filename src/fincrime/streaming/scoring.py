from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict, Field

from fincrime.features.point_in_time import AccountFeatures, account_features
from fincrime.graph.build import build_graph
from fincrime.graph.events import TransactionEvent


def compute_offline_features(
    events: Sequence[TransactionEvent],
    target_account: str,
    cutoff: datetime,
) -> AccountFeatures:
    """Compute point-in-time account features using the offline graph oracle."""
    graph = build_graph(events, cutoff=cutoff)
    return account_features(graph, target_account)


class OnlineGraphAccumulator(BaseModel):
    """Cumulative online feature accumulator matching NetworkX neighbor-grouped edge iteration."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # Map target -> tuple of (source_neighbor, tuple of amounts in edge insertion order)
    incoming_neighbor_edges: tuple[tuple[str, tuple[tuple[str, tuple[float, ...]], ...]], ...] = (
        Field(default_factory=tuple)
    )
    # Map source -> tuple of (target_neighbor, tuple of amounts in edge insertion order)
    outgoing_neighbor_edges: tuple[tuple[str, tuple[tuple[str, tuple[float, ...]], ...]], ...] = (
        Field(default_factory=tuple)
    )

    seen_edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    last_event_key: tuple[str, str] | None = None

    @classmethod
    def empty(cls) -> OnlineGraphAccumulator:
        return cls(
            incoming_neighbor_edges=(),
            outgoing_neighbor_edges=(),
            seen_edge_ids=(),
            last_event_key=None,
        )

    def ingest(self, event: TransactionEvent) -> OnlineGraphAccumulator:
        if event.edge_id in self.seen_edge_ids:
            raise ValueError(f"Duplicate edge_id detected: {event.edge_id}")

        current_key = (event.event_time.astimezone(UTC).isoformat(), event.edge_id)
        if self.last_event_key is not None and current_key <= self.last_event_key:
            raise ValueError(
                f"Non-monotonic stream order: current {current_key} <= last {self.last_event_key}"
            )

        new_seen = self.seen_edge_ids + (event.edge_id,)

        # Update incoming neighbor groups: target -> source -> amounts
        inc_map = {tgt: list(sources) for tgt, sources in self.incoming_neighbor_edges}
        tgt_sources = inc_map.get(event.target_id, [])
        found_src = False
        new_tgt_sources: list[tuple[str, tuple[float, ...]]] = []
        for src, amts in tgt_sources:
            if src == event.source_id:
                new_tgt_sources.append((src, amts + (event.amount,)))
                found_src = True
            else:
                new_tgt_sources.append((src, amts))
        if not found_src:
            new_tgt_sources.append((event.source_id, (event.amount,)))
        inc_map[event.target_id] = new_tgt_sources

        # Update outgoing neighbor groups: source -> target -> amounts
        out_map = {src: list(targets) for src, targets in self.outgoing_neighbor_edges}
        src_targets = out_map.get(event.source_id, [])
        found_tgt = False
        new_src_targets: list[tuple[str, tuple[float, ...]]] = []
        for tgt, amts in src_targets:
            if tgt == event.target_id:
                new_src_targets.append((tgt, amts + (event.amount,)))
                found_tgt = True
            else:
                new_src_targets.append((tgt, amts))
        if not found_tgt:
            new_src_targets.append((event.target_id, (event.amount,)))
        out_map[event.source_id] = new_src_targets

        sorted_inc = tuple(sorted((tgt, tuple(srcs)) for tgt, srcs in inc_map.items()))
        sorted_out = tuple(sorted((src, tuple(tgts)) for src, tgts in out_map.items()))

        return OnlineGraphAccumulator(
            incoming_neighbor_edges=sorted_inc,
            outgoing_neighbor_edges=sorted_out,
            seen_edge_ids=new_seen,
            last_event_key=current_key,
        )

    def extract_features(self, target_account: str) -> AccountFeatures:
        inc_neighbors: tuple[tuple[str, tuple[float, ...]], ...] = ()
        for tgt, neighbors in self.incoming_neighbor_edges:
            if tgt == target_account:
                inc_neighbors = neighbors
                break

        out_neighbors: tuple[tuple[str, tuple[float, ...]], ...] = ()
        for src, neighbors in self.outgoing_neighbor_edges:
            if src == target_account:
                out_neighbors = neighbors
                break

        incoming_amounts = [amt for _, amts in inc_neighbors for amt in amts]
        outgoing_amounts = [amt for _, amts in out_neighbors for amt in amts]

        incoming_total = sum(incoming_amounts)
        outgoing_total = sum(outgoing_amounts)
        in_degree = len(incoming_amounts)
        out_degree = len(outgoing_amounts)

        if incoming_total <= 0.0:
            pass_through_ratio = 0.0
        else:
            pass_through_ratio = min(outgoing_total / incoming_total, 1.0)

        return AccountFeatures(
            account_id=target_account,
            incoming_amount=incoming_total,
            outgoing_amount=outgoing_total,
            in_degree=in_degree,
            out_degree=out_degree,
            pass_through_ratio=pass_through_ratio,
        )
