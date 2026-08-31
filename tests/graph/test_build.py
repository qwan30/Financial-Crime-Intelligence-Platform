from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fincrime.graph.build import build_graph
from fincrime.graph.events import TransactionEvent


def test_future_event_is_excluded_from_graph() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC)),
        TransactionEvent("e2", "b", "c", 9.0, datetime(2026, 1, 3, tzinfo=UTC)),
    )
    graph = build_graph(events, cutoff)
    assert {key for _, _, key in graph.edges(keys=True)} == {"e1"}


def test_event_at_exact_cutoff_is_included() -> None:
    cutoff = datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 2, 12, 0, 0, tzinfo=UTC)),
        TransactionEvent("e2", "b", "c", 9.0, datetime(2026, 1, 2, 12, 0, 1, tzinfo=UTC)),
    )
    graph = build_graph(events, cutoff)
    assert {key for _, _, key in graph.edges(keys=True)} == {"e1"}


def test_cutoff_metadata_is_preserved_on_graph() -> None:
    cutoff = datetime(2026, 1, 2, 15, 30, 0, tzinfo=UTC)
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC)),
    )
    graph = build_graph(events, cutoff)
    assert graph.graph["cutoff"] == cutoff.isoformat()


def test_edge_attributes_are_correct() -> None:
    event_time = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    event = TransactionEvent("e1", "acc_1", "acc_2", 123.45, event_time)
    graph = build_graph([event], cutoff)

    assert graph.has_edge("acc_1", "acc_2", key="e1")
    edge_data = graph.get_edge_data("acc_1", "acc_2", key="e1")
    assert edge_data["amount"] == 123.45
    assert edge_data["event_time"] == event_time


def test_deterministic_event_ordering() -> None:
    t1 = datetime(2026, 1, 1, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 1, 1, 11, 0, 0, tzinfo=UTC)
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)

    # Reverse order input
    events = (
        TransactionEvent("e3", "b", "c", 5.0, t2),
        TransactionEvent("e2", "a", "b", 10.0, t1),
        TransactionEvent("e1", "a", "c", 15.0, t1),
    )
    graph = build_graph(events, cutoff)
    edge_keys = [key for _, _, key in graph.edges(keys=True)]
    assert edge_keys == ["e1", "e2", "e3"]


def test_event_immutability() -> None:
    event = TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC))
    with pytest.raises(ValidationError):
        event.amount = 20.0  # type: ignore[misc]


@pytest.mark.parametrize("invalid_amount", [0.0, -1.0, -100.5])
def test_non_positive_amount_raises_validation_error(invalid_amount: float) -> None:
    with pytest.raises(ValidationError):
        TransactionEvent("e1", "a", "b", invalid_amount, datetime(2026, 1, 1, tzinfo=UTC))


def test_timezone_naive_cutoff_with_aware_event_fails_clearly() -> None:
    cutoff_naive = datetime(2026, 1, 2)  # noqa: DTZ001
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC)),
    )
    with pytest.raises((ValueError, TypeError), match="[Tt]imezone|aware|naive"):
        build_graph(events, cutoff_naive)


def test_timezone_aware_cutoff_with_naive_event_fails_clearly() -> None:
    cutoff_aware = datetime(2026, 1, 2, tzinfo=UTC)
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1)),  # noqa: DTZ001
    )
    with pytest.raises((ValueError, TypeError), match="[Tt]imezone|aware|naive"):
        build_graph(events, cutoff_aware)


def test_timezone_naive_both_works() -> None:
    cutoff = datetime(2026, 1, 2)  # noqa: DTZ001
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1)),  # noqa: DTZ001
        TransactionEvent("e2", "b", "c", 9.0, datetime(2026, 1, 3)),  # noqa: DTZ001
    )
    graph = build_graph(events, cutoff)
    assert {key for _, _, key in graph.edges(keys=True)} == {"e1"}


def test_empty_events_creates_empty_graph() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph((), cutoff)
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert graph.graph["cutoff"] == cutoff.isoformat()
