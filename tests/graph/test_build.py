from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

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


# ── Regression Test 1: Canonical Boundary Validations ────────────────
def test_timezone_naive_datetime_in_event_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1))  # noqa: DTZ001


def test_string_coercion_for_datetime_in_event_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TransactionEvent("e1", "a", "b", 10.0, "2026-01-01T00:00:00Z")  # type: ignore[arg-type]


def test_string_coercion_for_amount_in_event_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TransactionEvent("e1", "a", "b", "10.0", datetime(2026, 1, 1, tzinfo=UTC))  # type: ignore[arg-type]


@pytest.mark.parametrize("invalid_amount", [0.0, -1.0, -100.5, float("inf"), float("-inf"), float("nan")])
def test_non_finite_or_non_positive_amount_raises_validation_error(invalid_amount: float) -> None:
    with pytest.raises(ValidationError):
        TransactionEvent("e1", "a", "b", invalid_amount, datetime(2026, 1, 1, tzinfo=UTC))


@pytest.mark.parametrize("blank_id", ["", "   ", "\t"])
def test_blank_identifier_in_event_is_rejected(blank_id: str) -> None:
    with pytest.raises(ValidationError):
        TransactionEvent(blank_id, "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC))


# ── Regression Test 2: Reject Duplicate edge_id ──────────────────────
def test_duplicate_edge_id_in_events_is_rejected() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC)),
        TransactionEvent("e1", "x", "y", 20.0, datetime(2026, 1, 1, tzinfo=UTC)),
    )
    with pytest.raises(ValueError, match="[Dd]uplicate.*edge_id"):
        build_graph(events, cutoff)


def test_duplicate_edge_id_across_cutoff_is_rejected() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    # e1 before cutoff, second e1 after cutoff
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC)),
        TransactionEvent("e1", "x", "y", 20.0, datetime(2026, 1, 3, tzinfo=UTC)),
    )
    with pytest.raises(ValueError, match="[Dd]uplicate.*edge_id"):
        build_graph(events, cutoff)


# ── Regression Test 3: UTC Normalization and DST / Offset Handling ───
def test_dst_fold_and_differing_tz_offsets_are_normalized_to_utc() -> None:
    # tz_minus_4: UTC-4 (e.g. EDT) -> 01:30-04:00 is 05:30 UTC
    tz_minus_4 = timezone(timedelta(hours=-4))
    # tz_minus_5: UTC-5 (e.g. EST) -> 01:30-05:00 is 06:30 UTC
    tz_minus_5 = timezone(timedelta(hours=-5))

    # Cutoff at 05:45 UTC (specified as 00:45-05:00)
    cutoff = datetime(2026, 11, 1, 0, 45, 0, tzinfo=tz_minus_5)

    # e1 (01:30-04:00 = 05:30 UTC) is BEFORE cutoff (05:45 UTC) -> included
    # e2 (01:30-05:00 = 06:30 UTC) is AFTER cutoff (05:45 UTC) -> excluded
    # Note: Wall-clock times for e1 and e2 are identical ("01:30"), but e2 is 1 hour in the future in UTC!
    events = (
        TransactionEvent("e2", "b", "c", 9.0, datetime(2026, 11, 1, 1, 30, 0, tzinfo=tz_minus_5)),
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 11, 1, 1, 30, 0, tzinfo=tz_minus_4)),
    )

    graph = build_graph(events, cutoff)
    assert {key for _, _, key in graph.edges(keys=True)} == {"e1"}


def test_timezone_naive_cutoff_fails_clearly() -> None:
    cutoff_naive = datetime(2026, 1, 2)  # noqa: DTZ001
    events = (
        TransactionEvent("e1", "a", "b", 10.0, datetime(2026, 1, 1, tzinfo=UTC)),
    )
    with pytest.raises((ValueError, TypeError), match="[Tt]imezone|aware"):
        build_graph(events, cutoff_naive)


def test_empty_events_creates_empty_graph() -> None:
    cutoff = datetime(2026, 1, 2, tzinfo=UTC)
    graph = build_graph((), cutoff)
    assert graph.number_of_nodes() == 0
    assert graph.number_of_edges() == 0
    assert graph.graph["cutoff"] == cutoff.isoformat()
