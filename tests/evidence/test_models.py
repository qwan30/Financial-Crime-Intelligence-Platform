from __future__ import annotations

from datetime import UTC, datetime, timedelta, timezone
from enum import Enum

import pytest
from pydantic import ValidationError

from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    canonical_json_bytes,
    compute_sha256_hex,
    normalize_value,
)


class DummyEnum(Enum):
    ALPHA = "ALPHA_VAL"
    BETA = "BETA_VAL"


def test_evidence_category_enum() -> None:
    assert [c.value for c in EvidenceCategory] == [
        "OBSERVED",
        "DERIVED",
        "RULE",
        "MODEL",
        "TRACE",
        "ANALYST",
    ]


def test_evidence_polarity_enum() -> None:
    assert [p.value for p in EvidencePolarity] == [
        "SUPPORTING",
        "MITIGATING",
        "MISSING",
        "UNKNOWN",
    ]


def test_normalize_value_datetime_aware() -> None:
    # UTC datetime
    dt_utc = datetime(2026, 3, 15, 10, 30, 0, tzinfo=UTC)
    assert normalize_value(dt_utc) == "2026-03-15T10:30:00Z"

    # Non-UTC timezone-aware datetime (+07:00)
    tz_plus7 = timezone(timedelta(hours=7))
    dt_tz = datetime(2026, 3, 15, 17, 30, 0, tzinfo=tz_plus7)
    assert normalize_value(dt_tz) == "2026-03-15T10:30:00Z"


def test_normalize_value_naive_datetime_raises() -> None:
    naive_dt = datetime(2026, 3, 15, 10, 30, 0)  # noqa: DTZ001
    with pytest.raises(ValueError, match="Naive datetime is prohibited; timezone required"):
        normalize_value(naive_dt)


def test_normalize_value_nested() -> None:
    data = {
        "z_key": DummyEnum.ALPHA,
        "a_key": [
            datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
            ("nested_tuple_val", DummyEnum.BETA),
        ],
        "num": 42,
    }
    normalized = normalize_value(data)
    assert normalized == {
        "z_key": "ALPHA_VAL",
        "a_key": [
            "2026-01-01T00:00:00Z",
            ["nested_tuple_val", "BETA_VAL"],
        ],
        "num": 42,
    }


def test_canonical_json_bytes_deterministic() -> None:
    dict1 = {
        "b": 2,
        "a": 1,
        "c": [3, 2, 1],
    }
    dict2 = {
        "c": [3, 2, 1],
        "a": 1,
        "b": 2,
    }
    bytes1 = canonical_json_bytes(dict1)
    bytes2 = canonical_json_bytes(dict2)
    assert bytes1 == bytes2
    assert bytes1 == b'{"a":1,"b":2,"c":[3,2,1]}'


def test_compute_sha256_hex() -> None:
    data = {"sample": "value", "count": 10}
    hash_hex = compute_sha256_hex(data)
    assert len(hash_hex) == 64
    assert hash_hex == compute_sha256_hex({"count": 10, "sample": "value"})


def test_evidence_item_valid() -> None:
    snapshot_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    raw_payload = {
        "evidence_id": "ev-001",
        "category": EvidenceCategory.OBSERVED,
        "source_reference": "tx-12345",
        "polarity": EvidencePolarity.SUPPORTING,
        "snapshot_time": snapshot_time,
        "generation_method_version": "v1.0.0",
        "confidence": 0.95,
        "payload_summary": "Large rapid movement of funds",
    }
    expected_hash = compute_sha256_hex(raw_payload)

    item = EvidenceItem(
        **raw_payload,
        integrity_hash=expected_hash,
    )
    assert item.evidence_id == "ev-001"
    assert item.category == EvidenceCategory.OBSERVED
    assert item.integrity_hash == expected_hash

    # Frozen check
    with pytest.raises(ValidationError):
        item.confidence = 0.5  # type: ignore[misc]


def test_evidence_item_naive_datetime_rejected() -> None:
    naive_time = datetime(2026, 3, 1, 12, 0, 0)  # noqa: DTZ001
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev-001",
            category=EvidenceCategory.OBSERVED,
            source_reference="tx-12345",
            polarity=EvidencePolarity.SUPPORTING,
            snapshot_time=naive_time,
            generation_method_version="v1.0.0",
            confidence=0.95,
            payload_summary="Large movement",
            integrity_hash="0" * 64,
        )


def test_evidence_item_invalid_hash_rejected() -> None:
    snapshot_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match="Integrity hash mismatch"):
        EvidenceItem(
            evidence_id="ev-001",
            category=EvidenceCategory.OBSERVED,
            source_reference="tx-12345",
            polarity=EvidencePolarity.SUPPORTING,
            snapshot_time=snapshot_time,
            generation_method_version="v1.0.0",
            confidence=0.95,
            payload_summary="Large movement",
            integrity_hash="a" * 64,
        )


def test_evidence_item_invalid_confidence() -> None:
    snapshot_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev-001",
            category=EvidenceCategory.OBSERVED,
            source_reference="tx-12345",
            polarity=EvidencePolarity.SUPPORTING,
            snapshot_time=snapshot_time,
            generation_method_version="v1.0.0",
            confidence=1.5,
            payload_summary="Large movement",
            integrity_hash="0" * 64,
        )


def test_evidence_item_extra_forbid() -> None:
    snapshot_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    raw = {
        "evidence_id": "ev-001",
        "category": EvidenceCategory.OBSERVED,
        "source_reference": "tx-12345",
        "polarity": EvidencePolarity.SUPPORTING,
        "snapshot_time": snapshot_time,
        "generation_method_version": "v1.0.0",
        "confidence": 0.95,
        "payload_summary": "Large movement",
    }
    hash_val = compute_sha256_hex(raw)
    with pytest.raises(ValidationError):
        EvidenceItem(
            **raw,
            integrity_hash=hash_val,
            extra_field="disallowed",  # type: ignore[call-arg]
        )


def test_evidence_item_id_pattern() -> None:
    snapshot_time = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="invalid id with spaces!",
            category=EvidenceCategory.OBSERVED,
            source_reference="tx-12345",
            polarity=EvidencePolarity.SUPPORTING,
            snapshot_time=snapshot_time,
            generation_method_version="v1.0.0",
            confidence=0.95,
            payload_summary="Large movement",
            integrity_hash="0" * 64,
        )
