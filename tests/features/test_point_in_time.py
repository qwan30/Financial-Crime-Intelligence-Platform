from __future__ import annotations

from datetime import UTC, datetime

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
        (TransactionEvent("e1", "b", "c", 10.0, cutoff),),
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
        (TransactionEvent("e1", "a", "b", 10.0, cutoff),),
        cutoff,
    )
    features = account_features(graph, "non_existent_account")
    assert features.account_id == "non_existent_account"
    assert features.in_degree == 0
    assert features.out_degree == 0
    assert features.incoming_amount == 0.0
    assert features.outgoing_amount == 0.0
    assert features.pass_through_ratio == 0.0


def test_self_loops_and_multi_edges_are_handled_correctly() -> None:
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
