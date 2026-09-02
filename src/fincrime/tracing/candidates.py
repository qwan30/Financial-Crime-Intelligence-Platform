from __future__ import annotations

import heapq
import math
from typing import Literal

import networkx as nx  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field


class TraceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seed_entity: str = Field(min_length=1)
    max_hops: int = Field(default=4, ge=1, le=4)
    max_edges: int = Field(default=100, ge=1, le=100)


class TraceResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_ids: tuple[str, ...]
    status: Literal["COMPLETE", "TRACE_TRUNCATED"]


def _edge_amount(data: dict[str, object] | None) -> float:
    if data is None or "amount" not in data:
        raise ValueError("Edge missing required data or amount attribute")
    amount = float(data["amount"])  # type: ignore[arg-type]
    if not math.isfinite(amount):
        raise ValueError("Edge amount must be finite")
    return amount


def generate_candidates(graph: nx.MultiDiGraph, request: TraceRequest) -> TraceResult:
    """Generate deterministic amount-prioritized bounded causal trace candidates."""
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError(f"graph must be a networkx.MultiDiGraph, got {type(graph).__name__}")
    if not isinstance(request, TraceRequest):
        raise TypeError(f"request must be a TraceRequest, got {type(request).__name__}")

    if request.seed_entity not in graph:
        return TraceResult(edge_ids=(), status="COMPLETE")

    queue: list[tuple[float, str, str, int]] = []
    visited_edges: set[str] = set()

    for _, target, key, data in graph.out_edges(request.seed_entity, keys=True, data=True):
        heapq.heappush(queue, (-_edge_amount(data), str(key), str(target), 1))

    selected: list[str] = []

    while queue and len(selected) < request.max_edges:
        _, edge_id, target, hop = heapq.heappop(queue)
        if edge_id in visited_edges:
            continue
        visited_edges.add(edge_id)
        selected.append(edge_id)

        if len(selected) == request.max_edges:
            break

        if hop < request.max_hops:
            for _, next_target, key, data in graph.out_edges(target, keys=True, data=True):
                next_edge_id = str(key)
                if next_edge_id not in visited_edges:
                    heapq.heappush(
                        queue, (-_edge_amount(data), next_edge_id, str(next_target), hop + 1)
                    )

    has_remaining = any(item[1] not in visited_edges for item in queue)
    status: Literal["COMPLETE", "TRACE_TRUNCATED"] = (
        "TRACE_TRUNCATED" if has_remaining else "COMPLETE"
    )

    return TraceResult(
        edge_ids=tuple(selected),
        status=status,
    )
