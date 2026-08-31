from __future__ import annotations

from datetime import UTC, datetime

import networkx as nx  # type: ignore[import-untyped]

from fincrime.tracing.candidates import (
    TraceRequest,
    generate_candidates,
)


def test_candidate_generation_obeys_edge_budget() -> None:
    graph = nx.MultiDiGraph()
    for index in range(5):
        graph.add_edge(
            "seed",
            f"n{index}",
            key=f"e{index}",
            amount=10 - index,
            event_time=datetime(2026, 1, 1, tzinfo=UTC),
        )
    request = TraceRequest(seed_entity="seed", max_hops=1, max_edges=2)
    result = generate_candidates(graph, request)
    assert len(result.edge_ids) == 2
    assert result.status == "TRACE_TRUNCATED"
    assert result.edge_ids == ("e0", "e1")


def test_candidate_generation_complete_when_within_budget() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("seed", "n1", key="e0", amount=50.0)
    graph.add_edge("n1", "n2", key="e1", amount=40.0)
    request = TraceRequest(seed_entity="seed", max_hops=2, max_edges=10)
    result = generate_candidates(graph, request)
    assert result.edge_ids == ("e0", "e1")
    assert result.status == "COMPLETE"


def test_deterministic_tie_breaking_by_edge_id() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("seed", "n1", key="edge_b", amount=100.0)
    graph.add_edge("seed", "n2", key="edge_a", amount=100.0)
    request = TraceRequest(seed_entity="seed", max_hops=1, max_edges=1)
    result = generate_candidates(graph, request)
    assert result.edge_ids == ("edge_a",)
    assert result.status == "TRACE_TRUNCATED"


def test_cycle_and_revisit_safe_without_duplicate_edges() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("seed", "n1", key="e1", amount=100.0)
    graph.add_edge("n1", "n2", key="e2", amount=90.0)
    graph.add_edge("n2", "seed", key="e3", amount=80.0)
    request = TraceRequest(seed_entity="seed", max_hops=4, max_edges=10)
    result = generate_candidates(graph, request)
    assert result.edge_ids == ("e1", "e2", "e3")
    assert len(set(result.edge_ids)) == len(result.edge_ids)
    assert result.status == "COMPLETE"


def test_seed_not_in_graph_returns_empty_complete() -> None:
    graph = nx.MultiDiGraph()
    graph.add_edge("a", "b", key="e1", amount=10.0)
    request = TraceRequest(seed_entity="unknown_seed", max_hops=2, max_edges=5)
    result = generate_candidates(graph, request)
    assert result.edge_ids == ()
    assert result.status == "COMPLETE"
