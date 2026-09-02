from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.streaming.events import TransactionEnvelope
from fincrime.streaming.replay import (
    BrokerRecord,
    DurableFileQuarantineStore,
    QuarantinedRecord,
    replay_records,
)
from fincrime.streaming.state import ReplayConflict, ReplayState


def test_broker_record_validation() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    payload = b'{"hello": "world"}'

    record = BrokerRecord(
        topic="transactions",
        partition=0,
        offset=0,
        payload=payload,
        timestamp=now,
    )
    assert record.topic == "transactions"
    assert record.partition == 0
    assert record.offset == 0
    assert record.payload == payload
    assert record.timestamp == now

    # Immutability
    with pytest.raises(ValidationError):
        record.topic = "other"  # type: ignore[misc]

    # Extra fields forbidden
    with pytest.raises(ValidationError):
        BrokerRecord(
            topic="tx",
            partition=0,
            offset=0,
            payload=payload,
            timestamp=now,
            extra="forbidden",  # type: ignore[call-arg]
        )

    # Blank topic rejected
    with pytest.raises(ValidationError):
        BrokerRecord(
            topic="   ",
            partition=0,
            offset=0,
            payload=payload,
            timestamp=now,
        )

    # Negative partition / offset rejected
    with pytest.raises(ValidationError):
        BrokerRecord(
            topic="tx",
            partition=-1,
            offset=0,
            payload=payload,
            timestamp=now,
        )

    with pytest.raises(ValidationError):
        BrokerRecord(
            topic="tx",
            partition=0,
            offset=-1,
            payload=payload,
            timestamp=now,
        )

    # Non-UTC timezone rejected
    non_utc = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        BrokerRecord(
            topic="tx",
            partition=0,
            offset=0,
            payload=payload,
            timestamp=non_utc,
        )

    # Naive datetime rejected
    naive = datetime(2026, 9, 2, 12, 0, 0)  # noqa: DTZ001
    with pytest.raises(ValidationError, match="timezone-aware UTC"):
        BrokerRecord(
            topic="tx",
            partition=0,
            offset=0,
            payload=payload,
            timestamp=naive,
        )


def test_quarantined_record_validation() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    valid_hash = "a" * 64

    q = QuarantinedRecord(
        topic="transactions",
        partition=0,
        offset=5,
        reason="INVALID_SCHEMA",
        payload_hash=valid_hash,
        quarantined_at=now,
    )
    assert q.topic == "transactions"
    assert q.partition == 0
    assert q.offset == 5
    assert q.reason == "INVALID_SCHEMA"
    assert q.payload_hash == valid_hash
    assert q.quarantined_at == now

    # Blank reason / topic rejected
    with pytest.raises(ValidationError):
        QuarantinedRecord(
            topic="tx",
            partition=0,
            offset=0,
            reason="  ",
            payload_hash=valid_hash,
        )

    # Invalid payload_hash rejected
    with pytest.raises(ValidationError):
        QuarantinedRecord(
            topic="tx",
            partition=0,
            offset=0,
            reason="INVALID_SCHEMA",
            payload_hash="UPPERCASE" + "0" * 55,
        )

    with pytest.raises(ValidationError):
        QuarantinedRecord(
            topic="tx",
            partition=0,
            offset=0,
            reason="INVALID_SCHEMA",
            payload_hash="short",
        )

    # Default factory sets UTC datetime
    q_default = QuarantinedRecord(
        topic="tx",
        partition=0,
        offset=0,
        reason="INVALID_SCHEMA",
        payload_hash=valid_hash,
    )
    assert q_default.quarantined_at.tzinfo is not None
    assert q_default.quarantined_at.utcoffset() == UTC.utcoffset(q_default.quarantined_at)


def test_durable_file_quarantine_store(tmp_path: Path) -> None:
    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

    # Non-existent returns empty list
    assert store.get_records("tx", 0) == []

    rec1 = QuarantinedRecord(
        topic="tx",
        partition=0,
        offset=1,
        reason="INVALID_SCHEMA",
        payload_hash="1" * 64,
        quarantined_at=now,
    )
    rec2 = QuarantinedRecord(
        topic="tx",
        partition=0,
        offset=2,
        reason="NON_CONTIGUOUS_OFFSET",
        payload_hash="2" * 64,
        quarantined_at=now,
    )
    rec_p1 = QuarantinedRecord(
        topic="tx",
        partition=1,
        offset=0,
        reason="INVALID_SCHEMA",
        payload_hash="3" * 64,
        quarantined_at=now,
    )

    store.append(rec1)
    store.append(rec2)
    store.append(rec_p1)

    records_p0 = store.get_records("tx", 0)
    assert len(records_p0) == 2
    assert records_p0[0] == rec1
    assert records_p0[1] == rec2

    records_p1 = store.get_records("tx", 1)
    assert len(records_p1) == 1
    assert records_p1[0] == rec_p1


def test_invalid_broker_record_is_quarantined_durably_with_coordinates(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    bad_payload = json.dumps({"schema_version": "99", "event_id": "bad_evt"}).encode("utf-8")
    record = BrokerRecord(
        topic="transactions",
        partition=0,
        offset=0,
        payload=bad_payload,
        timestamp=now,
    )
    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records([record], ReplayState.empty(), quarantine_store=store)

    assert outcome.accepted_event_ids == ()
    assert len(outcome.quarantined_records) == 1
    q = outcome.quarantined_records[0]
    assert q.topic == "transactions"
    assert q.partition == 0
    assert q.offset == 0
    assert q.reason == "INVALID_SCHEMA"
    assert outcome.committable_offsets == (("transactions", 0, 0),)

    persisted = store.get_records("transactions", 0)
    assert len(persisted) == 1
    assert persisted[0].payload_hash == q.payload_hash


def test_coordinate_mismatch_in_envelope_is_quarantined(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    # Envelope claims source_partition 1, but broker record is on partition 0
    payload = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_coord_mismatch",
            "source_partition": 1,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 50.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")

    record = BrokerRecord(topic="tx", partition=0, offset=0, payload=payload, timestamp=now)
    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records([record], ReplayState.empty(), quarantine_store=store)

    assert outcome.accepted_event_ids == ()
    assert len(outcome.quarantined_records) == 1
    assert outcome.quarantined_records[0].reason == "INVALID_SCHEMA"
    assert outcome.committable_offsets == (("tx", 0, 0),)


def test_broker_exact_retry_at_already_advanced_state_is_true_noop(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")

    record = BrokerRecord(topic="tx", partition=0, offset=0, payload=valid0, timestamp=now)
    store = DurableFileQuarantineStore(storage_dir=tmp_path)

    env = TransactionEnvelope.model_validate_json(valid0)
    state0 = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_0", payload_hash=env.canonical_hash()
    )

    outcome = replay_records([record], state0, quarantine_store=store)

    # True no-op: no new accepted, no quarantine, state unchanged, committable offset unchanged at 1
    assert outcome.accepted_event_ids == ()
    assert outcome.quarantined_records == ()
    assert outcome.state == state0
    assert outcome.committable_offsets == (("tx", 0, 1),)
    assert len(store.get_records("tx", 0)) == 0


def test_conflicting_retry_raises_replay_conflict(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")
    conflicting_payload = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 999.0,  # different amount -> different hash
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")

    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    env0 = TransactionEnvelope.model_validate_json(valid0)
    state0 = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_0", payload_hash=env0.canonical_hash()
    )

    conflict_record = BrokerRecord(
        topic="tx", partition=0, offset=0, payload=conflicting_payload, timestamp=now
    )

    with pytest.raises(ReplayConflict, match="Conflicting retry"):
        replay_records([conflict_record], state0, quarantine_store=store)


def test_duplicate_event_id_at_different_coordinates_raises_replay_conflict(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")
    diff_coord_payload = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 1,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")

    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    env0 = TransactionEnvelope.model_validate_json(valid0)
    state0 = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_0", payload_hash=env0.canonical_hash()
    )

    record_part1 = BrokerRecord(
        topic="tx", partition=1, offset=0, payload=diff_coord_payload, timestamp=now
    )

    with pytest.raises(ReplayConflict, match="Conflicting retry"):
        replay_records([record_part1], state0, quarantine_store=store)


def test_non_contiguous_offset_is_quarantined_and_halts_partition(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    gap_payload = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_5",
            "source_partition": 0,
            "source_offset": 5,  # Expected 0, got 5
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")

    record = BrokerRecord(topic="tx", partition=0, offset=5, payload=gap_payload, timestamp=now)
    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records([record], ReplayState.empty(), quarantine_store=store)

    assert outcome.accepted_event_ids == ()
    assert len(outcome.quarantined_records) == 1
    q = outcome.quarantined_records[0]
    assert q.reason == "NON_CONTIGUOUS_OFFSET"
    assert q.offset == 5
    assert outcome.committable_offsets == (("tx", 0, 0),)


def test_poison_barrier_freezes_at_expected_offset_and_halts(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")
    poison = b'{"bad_json": true}'
    valid2 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_2",
            "source_partition": 0,
            "source_offset": 2,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 200.0,
            "event_time": "2026-09-02T12:01:00Z",
        }
    ).encode("utf-8")

    records = [
        BrokerRecord(topic="tx", partition=0, offset=0, payload=valid0, timestamp=now),
        BrokerRecord(topic="tx", partition=0, offset=1, payload=poison, timestamp=now),
        BrokerRecord(topic="tx", partition=0, offset=2, payload=valid2, timestamp=now),
    ]

    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records(records, ReplayState.empty(), quarantine_store=store)

    assert outcome.accepted_event_ids == ("evt_0",)
    assert len(outcome.quarantined_records) == 1
    assert outcome.quarantined_records[0].offset == 1
    assert outcome.quarantined_records[0].reason == "INVALID_SCHEMA"
    assert outcome.state.get_offset("tx", 0) == 1
    assert outcome.committable_offsets == (("tx", 0, 1),)


def test_multi_partition_replay_with_isolated_partition_failure(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    p0_valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_p0_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")
    p0_poison = b"invalid payload"
    p0_valid2 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_p0_2",
            "source_partition": 0,
            "source_offset": 2,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 200.0,
            "event_time": "2026-09-02T12:02:00Z",
        }
    ).encode("utf-8")

    p1_valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_p1_0",
            "source_partition": 1,
            "source_offset": 0,
            "source_id": "acc_3",
            "target_id": "acc_4",
            "amount": 300.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")
    p1_valid1 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_p1_1",
            "source_partition": 1,
            "source_offset": 1,
            "source_id": "acc_3",
            "target_id": "acc_4",
            "amount": 400.0,
            "event_time": "2026-09-02T12:01:00Z",
        }
    ).encode("utf-8")

    records = [
        BrokerRecord(topic="tx", partition=0, offset=0, payload=p0_valid0, timestamp=now),
        BrokerRecord(topic="tx", partition=1, offset=0, payload=p1_valid0, timestamp=now),
        BrokerRecord(topic="tx", partition=0, offset=1, payload=p0_poison, timestamp=now),
        BrokerRecord(topic="tx", partition=1, offset=1, payload=p1_valid1, timestamp=now),
        BrokerRecord(topic="tx", partition=0, offset=2, payload=p0_valid2, timestamp=now),
    ]

    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records(records, ReplayState.empty(), quarantine_store=store)

    # Partition 0 accepted evt_p0_0, then failed at offset 1, skipped offset 2
    # Partition 1 accepted evt_p1_0 and evt_p1_1
    assert outcome.accepted_event_ids == ("evt_p0_0", "evt_p1_0", "evt_p1_1")
    assert len(outcome.quarantined_records) == 1
    assert outcome.quarantined_records[0].partition == 0
    assert outcome.quarantined_records[0].offset == 1

    assert outcome.committable_offsets == (("tx", 0, 1), ("tx", 1, 2))
    assert outcome.state.get_offset("tx", 0) == 1
    assert outcome.state.get_offset("tx", 1) == 2


def test_durable_quarantine_store_concurrent_appends(tmp_path: Path) -> None:
    from concurrent.futures import ThreadPoolExecutor

    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)

    records = [
        QuarantinedRecord(
            topic="tx",
            partition=0,
            offset=i,
            reason=f"REASON_{i}",
            payload_hash=f"{i:064x}",
            quarantined_at=now,
        )
        for i in range(50)
    ]

    with ThreadPoolExecutor(max_workers=10) as executor:
        list(executor.map(store.append, records))

    persisted = store.get_records("tx", 0)
    assert len(persisted) == 50
    persisted_offsets = {r.offset for r in persisted}
    assert persisted_offsets == set(range(50))
