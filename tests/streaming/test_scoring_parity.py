from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from fincrime.graph.events import TransactionEvent
from fincrime.streaming.scoring import OnlineGraphAccumulator, compute_offline_features


def test_streaming_state_matches_offline_graph_and_features_exactly() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)
    t3 = datetime(2026, 9, 2, 10, 10, 0, tzinfo=UTC)

    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=1000.0, event_time=t1
        ),
        TransactionEvent(
            edge_id="e2", source_id="acc_B", target_id="acc_C", amount=800.0, event_time=t2
        ),
        TransactionEvent(
            edge_id="e3", source_id="acc_D", target_id="acc_B", amount=500.0, event_time=t3
        ),
    ]

    cutoff = datetime(2026, 9, 2, 10, 15, 0, tzinfo=UTC)

    # Offline path (actual production oracle using repository signature)
    offline_feats = compute_offline_features(events, target_account="acc_B", cutoff=cutoff)

    # Online accumulator (ingests stream in canonical order up to cutoff)
    acc = OnlineGraphAccumulator.empty()
    for ev in events:
        if ev.event_time <= cutoff:
            acc = acc.ingest(ev)
    online_feats = acc.extract_features(target_account="acc_B")

    # Bitwise exact parity checks across all fields
    assert online_feats.account_id == offline_feats.account_id
    assert online_feats.incoming_amount.hex() == offline_feats.incoming_amount.hex()
    assert online_feats.outgoing_amount.hex() == offline_feats.outgoing_amount.hex()
    assert online_feats.in_degree == offline_feats.in_degree
    assert online_feats.out_degree == offline_feats.out_degree
    assert online_feats.pass_through_ratio.hex() == offline_feats.pass_through_ratio.hex()


def test_duplicate_edge_id_raises_value_error_matching_build_graph() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)

    ev1 = TransactionEvent(
        edge_id="dup_e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    ev2 = TransactionEvent(
        edge_id="dup_e1", source_id="acc_C", target_id="acc_D", amount=200.0, event_time=t2
    )

    acc = OnlineGraphAccumulator.empty().ingest(ev1)
    with pytest.raises(ValueError) as exc_info:
        acc.ingest(ev2)
    assert "Duplicate edge_id" in str(exc_info.value)


def test_non_monotonic_stream_order_rejected() -> None:
    t1 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)

    ev1 = TransactionEvent(
        edge_id="e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    ev2 = TransactionEvent(
        edge_id="e2", source_id="acc_A", target_id="acc_B", amount=200.0, event_time=t2
    )

    acc = OnlineGraphAccumulator.empty().ingest(ev1)
    with pytest.raises(ValueError) as exc_info:
        acc.ingest(ev2)
    assert "Non-monotonic stream order" in str(exc_info.value)


def test_equal_timestamp_different_edge_id_stream_order() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)

    ev1 = TransactionEvent(
        edge_id="e2", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    ev2 = TransactionEvent(
        edge_id="e1", source_id="acc_A", target_id="acc_B", amount=200.0, event_time=t1
    )

    acc = OnlineGraphAccumulator.empty().ingest(ev1)
    # e1 < e2 at same timestamp, so ingesting e1 after e2 is non-monotonic
    with pytest.raises(ValueError) as exc_info:
        acc.ingest(ev2)
    assert "Non-monotonic stream order" in str(exc_info.value)


def test_parity_with_interleaved_multi_edges_and_extreme_magnitude_floats() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 1, 0, tzinfo=UTC)
    t3 = datetime(2026, 9, 2, 10, 2, 0, tzinfo=UTC)

    # Interleaved multi-edges between A->B and C->B with skewed float magnitudes (A: 1e16, C: 2.0, A: 1.0)
    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=1e16, event_time=t1
        ),
        TransactionEvent(
            edge_id="e2", source_id="acc_C", target_id="acc_B", amount=2.0, event_time=t2
        ),
        TransactionEvent(
            edge_id="e3", source_id="acc_A", target_id="acc_B", amount=1.0, event_time=t3
        ),
    ]
    cutoff = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)

    offline_feats = compute_offline_features(events, target_account="acc_B", cutoff=cutoff)

    acc = OnlineGraphAccumulator.empty()
    for ev in events:
        acc = acc.ingest(ev)
    online_feats = acc.extract_features(target_account="acc_B")

    # Bitwise exact float match
    assert online_feats.incoming_amount.hex() == offline_feats.incoming_amount.hex()
    assert online_feats.outgoing_amount.hex() == offline_feats.outgoing_amount.hex()
    assert online_feats.in_degree == offline_feats.in_degree
    assert online_feats.out_degree == offline_feats.out_degree
    assert online_feats.pass_through_ratio.hex() == offline_feats.pass_through_ratio.hex()


def test_absent_account_returns_zeroed_features() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
        ),
    ]
    cutoff = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)

    offline_feats = compute_offline_features(
        events, target_account="acc_NONEXISTENT", cutoff=cutoff
    )

    acc = OnlineGraphAccumulator.empty().ingest(events[0])
    online_feats = acc.extract_features(target_account="acc_NONEXISTENT")

    assert online_feats.account_id == "acc_NONEXISTENT"
    assert online_feats.in_degree == 0
    assert online_feats.out_degree == 0
    assert online_feats.incoming_amount.hex() == (0.0).hex()
    assert online_feats.outgoing_amount.hex() == (0.0).hex()
    assert online_feats.pass_through_ratio.hex() == (0.0).hex()
    assert online_feats == offline_feats


def test_pass_through_ratio_zero_when_no_incoming() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
        ),
    ]
    cutoff = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)

    offline_feats = compute_offline_features(events, target_account="acc_A", cutoff=cutoff)

    acc = OnlineGraphAccumulator.empty().ingest(events[0])
    online_feats = acc.extract_features(target_account="acc_A")

    assert online_feats.incoming_amount == 0.0
    assert online_feats.outgoing_amount == 100.0
    assert online_feats.pass_through_ratio == 0.0
    assert online_feats.pass_through_ratio.hex() == offline_feats.pass_through_ratio.hex()


def test_pass_through_ratio_capped_at_one() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 1, 0, tzinfo=UTC)
    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=50.0, event_time=t1
        ),
        TransactionEvent(
            edge_id="e2", source_id="acc_B", target_id="acc_C", amount=200.0, event_time=t2
        ),
    ]
    cutoff = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)

    offline_feats = compute_offline_features(events, target_account="acc_B", cutoff=cutoff)

    acc = OnlineGraphAccumulator.empty()
    for ev in events:
        acc = acc.ingest(ev)
    online_feats = acc.extract_features(target_account="acc_B")

    assert online_feats.incoming_amount == 50.0
    assert online_feats.outgoing_amount == 200.0
    assert online_feats.pass_through_ratio == 1.0
    assert online_feats.pass_through_ratio.hex() == offline_feats.pass_through_ratio.hex()


def test_self_loops_and_multi_edges_parity() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 9, 2, 10, 1, 0, tzinfo=UTC)
    t3 = datetime(2026, 9, 2, 10, 2, 0, tzinfo=UTC)
    t4 = datetime(2026, 9, 2, 10, 3, 0, tzinfo=UTC)

    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_A", amount=30.0, event_time=t1
        ),
        TransactionEvent(
            edge_id="e2", source_id="acc_B", target_id="acc_A", amount=50.0, event_time=t2
        ),
        TransactionEvent(
            edge_id="e3", source_id="acc_A", target_id="acc_C", amount=40.0, event_time=t3
        ),
        TransactionEvent(
            edge_id="e4", source_id="acc_A", target_id="acc_A", amount=20.0, event_time=t4
        ),
    ]
    cutoff = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)

    offline_feats = compute_offline_features(events, target_account="acc_A", cutoff=cutoff)

    acc = OnlineGraphAccumulator.empty()
    for ev in events:
        acc = acc.ingest(ev)
    online_feats = acc.extract_features(target_account="acc_A")

    assert online_feats.account_id == "acc_A"
    assert online_feats.in_degree == 3  # e1 (self), e2 (from B), e4 (self)
    assert online_feats.out_degree == 3  # e1 (self), e3 (to C), e4 (self)
    assert online_feats.incoming_amount.hex() == offline_feats.incoming_amount.hex()
    assert online_feats.outgoing_amount.hex() == offline_feats.outgoing_amount.hex()
    assert online_feats.pass_through_ratio.hex() == offline_feats.pass_through_ratio.hex()


def test_accumulator_immutability() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=UTC)
    ev = TransactionEvent(
        edge_id="e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    acc = OnlineGraphAccumulator.empty().ingest(ev)

    with pytest.raises(ValidationError):
        acc.seen_edge_ids = ()  # type: ignore[misc]


def test_timezone_normalization_in_stream_order() -> None:
    # 06:00 UTC-4 is 10:00 UTC. 10:05 UTC is later.
    tz_minus_4 = timezone(timedelta(hours=-4))
    t1 = datetime(2026, 9, 2, 6, 0, 0, tzinfo=tz_minus_4)  # 10:00:00 UTC
    t2 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=UTC)  # 10:05:00 UTC

    ev1 = TransactionEvent(
        edge_id="e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    ev2 = TransactionEvent(
        edge_id="e2", source_id="acc_B", target_id="acc_C", amount=200.0, event_time=t2
    )

    acc = OnlineGraphAccumulator.empty().ingest(ev1).ingest(ev2)
    assert acc.extract_features("acc_B").in_degree == 1
    assert acc.extract_features("acc_B").out_degree == 1
