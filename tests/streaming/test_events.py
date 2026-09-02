from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone

import pytest
from pydantic import ValidationError

from fincrime.streaming.events import TransactionEnvelope


def test_valid_transaction_envelope_canonical_hash_and_golden_bytes() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    env = TransactionEnvelope(
        schema_version="1",
        event_id="evt_tx_001",
        source_partition=0,
        source_offset=105,
        source_id="acc_source_1",
        target_id="acc_target_2",
        amount=1500000.0,
        event_time=now,
    )
    assert env.schema_version == "1"
    assert env.event_id == "evt_tx_001"
    assert env.source_partition == 0
    assert env.source_offset == 105
    assert env.source_id == "acc_source_1"
    assert env.target_id == "acc_target_2"
    assert env.amount == 1500000.0
    assert env.event_time == now

    expected_dict = {
        "schema_version": "1",
        "event_id": "evt_tx_001",
        "source_partition": 0,
        "source_offset": 105,
        "source_id": "acc_source_1",
        "target_id": "acc_target_2",
        "amount": 1500000.0,
        "event_time": "2026-09-02T12:00:00Z",
    }
    assert env.to_canonical_dict() == expected_dict

    expected_bytes = (
        b'{"amount":1500000.0,"event_id":"evt_tx_001","event_time":"2026-09-02T12:00:00Z",'
        b'"schema_version":"1","source_id":"acc_source_1","source_offset":105,'
        b'"source_partition":0,"target_id":"acc_target_2"}'
    )
    assert env.to_canonical_bytes() == expected_bytes

    h1 = env.canonical_hash()
    assert len(h1) == 64
    assert h1 == h1.lower()
    assert all(c in "0123456789abcdef" for c in h1)


def test_microsecond_timestamp_rejected() -> None:
    dt_with_us = datetime(2026, 9, 2, 12, 0, 0, 123456, tzinfo=UTC)
    with pytest.raises(ValidationError) as exc_info:
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=dt_with_us,
        )
    assert "microsecond must be 0" in str(exc_info.value)


def test_naive_datetime_and_non_utc_rejected() -> None:
    naive_dt = datetime(2026, 9, 2, 12, 0, 0)  # noqa: DTZ001
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=naive_dt,
        )

    non_utc_dt = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone(timedelta(hours=5)))
    with pytest.raises(ValidationError) as exc_info:
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=non_utc_dt,
        )
    assert "UTC" in str(exc_info.value)


def test_unknown_schema_version_is_rejected() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="2",  # type: ignore[arg-type]
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=now,
        )


def test_non_finite_or_negative_amount_rejected() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    for invalid_amount in [-50.0, 0.0, float("inf"), float("-inf"), float("nan")]:
        with pytest.raises(ValidationError):
            TransactionEnvelope(
                schema_version="1",
                event_id="evt_tx_001",
                source_partition=0,
                source_offset=105,
                source_id="acc_source_1",
                target_id="acc_target_2",
                amount=invalid_amount,
                event_time=now,
            )


def test_negative_coordinates_rejected() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=-1,
            source_offset=0,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=100.0,
            event_time=now,
        )
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=-5,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=100.0,
            event_time=now,
        )


def test_blank_or_invalid_ids_rejected() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="",
            source_partition=0,
            source_offset=0,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=100.0,
            event_time=now,
        )
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_with spaces",
            source_partition=0,
            source_offset=0,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=100.0,
            event_time=now,
        )


def test_immutability_and_forbid_extra() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=UTC)
    env = TransactionEnvelope(
        schema_version="1",
        event_id="evt_tx_001",
        source_partition=0,
        source_offset=105,
        source_id="acc_source_1",
        target_id="acc_target_2",
        amount=1500000.0,
        event_time=now,
    )
    with pytest.raises(ValidationError):
        env.amount = 2000.0

    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=now,
            extra_field="invalid",  # type: ignore[call-arg]
        )


def test_json_roundtrip_canonical_consistency() -> None:
    raw_json = (
        b'{"amount":1500000.0,"event_id":"evt_tx_001","event_time":"2026-09-02T12:00:00Z",'
        b'"schema_version":"1","source_id":"acc_source_1","source_offset":105,'
        b'"source_partition":0,"target_id":"acc_target_2"}'
    )
    env = TransactionEnvelope.model_validate_json(raw_json)
    assert env.to_canonical_bytes() == raw_json
    assert (
        env.canonical_hash() == "145d071296f784ddbda76925a356a1bf862ffb6f5d2752b710fa1576fcf1cfea"
    )
