from __future__ import annotations

from datetime import UTC, datetime

import networkx as nx
import pytest
from pydantic import ValidationError

from fincrime.features.point_in_time import AccountFeatures, account_features
from fincrime.graph.build import build_graph
from fincrime.graph.events import TransactionEvent


def test_account_features_are_amount_and_degree_aware() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph(
        (
            TransactionEvent("e1", "a", "b", 10.0, cutoff),
            TransactionEvent("e2", "b", "c", 8.0, cutoff),
        ),
        cutoff,
    )
    features = account_features(graph, "b")
    assert features.account_id == "b"
    assert features.in_degree == 1
    assert features.out_degree == 1
    assert features.incoming_amount == 10.0
    assert features.outgoing_amount == 8.0
    assert features.pass_through_ratio == 0.8


def test_pass_through_ratio_is_capped_at_one() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph(
        (
            TransactionEvent("e1", "a", "b", 10.0, cutoff),
            TransactionEvent("e2", "b", "c", 25.0, cutoff),
        ),
        cutoff,
    )
    features = account_features(graph, "b")
    assert features.incoming_amount == 10.0
    assert features.outgoing_amount == 25.0
    assert features.pass_through_ratio == 1.0


def test_pass_through_ratio_is_zero_when_no_incoming() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph(
        (
            TransactionEvent("e1", "b", "c", 10.0, cutoff),
        ),
        cutoff,
    )
    features = account_features(graph, "b")
    assert features.in_degree == 0
    assert features.out_degree == 1
    assert features.incoming_amount == 0.0
    assert features.outgoing_amount == 10.0
    assert features.pass_through_ratio == 0.0


def test_absent_account_returns_zeroed_features() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph(
        (
            TransactionEvent("e1", "a", "b", 10.0, cutoff),
        ),
        cutoff,
    )
    features = account_features(graph, "non_existent_account")
    assert features.account_id == "non_existent_account"
    assert features.in_degree == 0
    assert features.out_degree == 0
    assert features.incoming_amount == 0.0
    assert features.outgoing_amount == 0.0
    assert features.pass_through_ratio == 0.0


def test_self_loops_are_handled_correctly() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph(
        (
            TransactionEvent("e1", "a", "a", 50.0, cutoff),
            TransactionEvent("e2", "b", "a", 30.0, cutoff),
            TransactionEvent("e3", "a", "c", 20.0, cutoff),
        ),
        cutoff,
    )
    features = account_features(graph, "a")
    assert features.in_degree == 2
    assert features.out_degree == 2
    assert features.incoming_amount == 80.0
    assert features.outgoing_amount == 70.0
    assert features.pass_through_ratio == pytest.approx(70.0 / 80.0)


def test_multi_edges_between_same_nodes() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph(
        (
            TransactionEvent("e1", "a", "b", 10.0, cutoff),
            TransactionEvent("e2", "a", "b", 25.0, cutoff),
            TransactionEvent("e3", "b", "c", 15.0, cutoff),
        ),
        cutoff,
    )
    features_a = account_features(graph, "a")
    assert features_a.in_degree == 0
    assert features_a.out_degree == 2
    assert features_a.outgoing_amount == 35.0

    features_b = account_features(graph, "b")
    assert features_b.in_degree == 2
    assert features_b.out_degree == 1
    assert features_b.incoming_amount == 35.0
    assert features_b.outgoing_amount == 15.0
    assert features_b.pass_through_ratio == pytest.approx(15.0 / 35.0)


def test_invalid_graph_type_raises_type_error() -> None:
    with pytest.raises(TypeError, match="[Gg]raph|MultiDiGraph"):
        account_features(nx.DiGraph(), "a")  # type: ignore[arg-type]


@pytest.mark.parametrize("blank_id", ["", "   ", "\t"])
def test_blank_account_id_raises_validation_error(blank_id: str) -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph((), cutoff)
    with pytest.raises((ValueError, ValidationError)):
        account_features(graph, blank_id)


def test_missing_edge_amount_fails_data_integrity_check() -> None:
    graph = nx.MultiDiGraph(cutoff=datetime(2026, 1, 2, tzinfo=UTC).isoformat())
    graph.add_edge("a", "b", key="e1")  # missing "amount"
    with pytest.raises((ValueError, KeyError), match="amount"):
        account_features(graph, "b")


def test_non_numeric_edge_amount_fails_data_integrity_check() -> None:
    graph = nx.MultiDiGraph(cutoff=datetime(2026, 1, 2, tzinfo=UTC).isoformat())
    graph.add_edge("a", "b", key="e1", amount="not_a_number")
    with pytest.raises(TypeError, match="amount"):
        account_features(graph, "b")


@pytest.mark.parametrize("non_finite_val", [float("inf"), float("-inf"), float("nan")])
def test_non_finite_edge_amount_fails_data_integrity_check(non_finite_val: float) -> None:
    graph = nx.MultiDiGraph(cutoff=datetime(2026, 1, 2, tzinfo=UTC).isoformat())
    graph.add_edge("a", "b", key="e1", amount=non_finite_val)
    with pytest.raises(ValueError, match="non-finite|finite|amount"):
        account_features(graph, "b")


def test_negative_edge_amount_fails_data_integrity_check() -> None:
    graph = nx.MultiDiGraph(cutoff=datetime(2026, 1, 2, tzinfo=UTC).isoformat())
    graph.add_edge("a", "b", key="e1", amount=-10.0)
    with pytest.raises(ValueError, match="negative|positive|amount"):
        account_features(graph, "b")


def test_account_features_immutability() -> None:
    features = AccountFeatures(
        account_id="acc1",
        in_degree=1,
        out_degree=1,
        incoming_amount=10.0,
        outgoing_amount=5.0,
        pass_through_ratio=0.5,
    )
    with pytest.raises(ValidationError):
        features.in_degree = 2  # type: ignore[misc]
