from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from fincrime.cases.models import (
    AdjudicationStatus,
    AnalystFeedbackEvent,
    CaseSnapshot,
    Disposition,
)
from fincrime.evidence.models import compute_sha256_hex


def test_disposition_enum() -> None:
    assert [d.value for d in Disposition] == [
        "CONFIRMED_SUSPICIOUS",
        "FALSE_POSITIVE",
        "ESCALATE",
        "INSUFFICIENT_EVIDENCE",
    ]


def test_adjudication_status_enum() -> None:
    assert [s.value for s in AdjudicationStatus] == [
        "PENDING",
        "ACCEPTED",
        "REJECTED",
    ]


def test_case_snapshot_valid() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    raw = {
        "case_id": "case-001",
        "seed_entity": "account:12345",
        "evidence_ids": ("ev-001", "ev-002", "ev-003"),
        "trace_edge_ids": ("edge-01", "edge-02"),
        "created_at": created_at,
    }
    h = compute_sha256_hex(raw)
    snapshot = CaseSnapshot(**raw, snapshot_hash=h)

    assert snapshot.case_id == "case-001"
    assert snapshot.seed_entity == "account:12345"
    assert snapshot.evidence_ids == ("ev-001", "ev-002", "ev-003")
    assert snapshot.trace_edge_ids == ("edge-01", "edge-02")
    assert snapshot.snapshot_hash == h

    # Frozen check
    with pytest.raises(ValidationError):
        snapshot.seed_entity = "account:99999"  # type: ignore[misc]


def test_case_snapshot_empty_evidence_and_trace() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    raw = {
        "case_id": "case-empty",
        "seed_entity": "account:00000",
        "evidence_ids": (),
        "trace_edge_ids": (),
        "created_at": created_at,
    }
    h = compute_sha256_hex(raw)
    snapshot = CaseSnapshot(**raw, snapshot_hash=h)
    assert snapshot.evidence_ids == ()
    assert snapshot.trace_edge_ids == ()


def test_case_snapshot_unsorted_evidence_rejected() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    raw = {
        "case_id": "case-unsorted",
        "seed_entity": "account:12345",
        "evidence_ids": ("ev-002", "ev-001"),
        "trace_edge_ids": (),
        "created_at": created_at,
    }
    h = compute_sha256_hex(raw)
    with pytest.raises(ValidationError, match="evidence_ids must be sorted"):
        CaseSnapshot(**raw, snapshot_hash=h)


def test_case_snapshot_duplicate_evidence_rejected() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    raw = {
        "case_id": "case-dup",
        "seed_entity": "account:12345",
        "evidence_ids": ("ev-001", "ev-001"),
        "trace_edge_ids": (),
        "created_at": created_at,
    }
    h = compute_sha256_hex(raw)
    with pytest.raises(ValidationError, match="evidence_ids must be unique"):
        CaseSnapshot(**raw, snapshot_hash=h)


def test_case_snapshot_unsorted_trace_edges_rejected() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    raw = {
        "case_id": "case-edges",
        "seed_entity": "account:12345",
        "evidence_ids": (),
        "trace_edge_ids": ("edge-b", "edge-a"),
        "created_at": created_at,
    }
    h = compute_sha256_hex(raw)
    with pytest.raises(ValidationError, match="trace_edge_ids must be sorted"):
        CaseSnapshot(**raw, snapshot_hash=h)


def test_case_snapshot_naive_datetime_rejected() -> None:
    naive_dt = datetime(2026, 3, 1, 14, 0, 0)  # noqa: DTZ001
    with pytest.raises(ValidationError):
        CaseSnapshot(
            case_id="case-001",
            seed_entity="account:12345",
            evidence_ids=(),
            trace_edge_ids=(),
            created_at=naive_dt,
            snapshot_hash="0" * 64,
        )


def test_case_snapshot_invalid_hash_rejected() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError, match="Snapshot hash mismatch"):
        CaseSnapshot(
            case_id="case-001",
            seed_entity="account:12345",
            evidence_ids=(),
            trace_edge_ids=(),
            created_at=created_at,
            snapshot_hash="f" * 64,
        )


def test_case_snapshot_extra_forbid() -> None:
    created_at = datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC)
    raw = {
        "case_id": "case-001",
        "seed_entity": "account:12345",
        "evidence_ids": (),
        "trace_edge_ids": (),
        "created_at": created_at,
    }
    h = compute_sha256_hex(raw)
    with pytest.raises(ValidationError):
        CaseSnapshot(**raw, snapshot_hash=h, unexpected_field="disallowed")  # type: ignore[call-arg]


def test_analyst_feedback_event_valid() -> None:
    created_at = datetime(2026, 3, 2, 9, 0, 0, tzinfo=UTC)
    event = AnalystFeedbackEvent(
        event_id="fb-001",
        analyst_id="analyst-alice",
        case_id="case-001",
        disposition=Disposition.CONFIRMED_SUSPICIOUS,
        reason="Clear money mule structuring pattern observed across 5 transactions.",
        created_at=created_at,
        model_version="deepseek-v4-flash",
        snapshot_hash="a" * 64,
        adjudication_status=AdjudicationStatus.PENDING,
    )
    assert event.event_id == "fb-001"
    assert event.disposition == Disposition.CONFIRMED_SUSPICIOUS
    assert event.adjudication_status == AdjudicationStatus.PENDING

    # Frozen check
    with pytest.raises(ValidationError):
        event.reason = "Changed reason"  # type: ignore[misc]


def test_analyst_feedback_event_naive_datetime_rejected() -> None:
    naive_dt = datetime(2026, 3, 2, 9, 0, 0)  # noqa: DTZ001
    with pytest.raises(ValidationError):
        AnalystFeedbackEvent(
            event_id="fb-001",
            analyst_id="analyst-alice",
            case_id="case-001",
            disposition=Disposition.CONFIRMED_SUSPICIOUS,
            reason="Clear pattern",
            created_at=naive_dt,
            snapshot_hash="a" * 64,
        )


def test_analyst_feedback_event_extra_forbid() -> None:
    created_at = datetime(2026, 3, 2, 9, 0, 0, tzinfo=UTC)
    with pytest.raises(ValidationError):
        AnalystFeedbackEvent(
            event_id="fb-001",
            analyst_id="analyst-alice",
            case_id="case-001",
            disposition=Disposition.CONFIRMED_SUSPICIOUS,
            reason="Clear pattern",
            created_at=created_at,
            snapshot_hash="a" * 64,
            extra="disallowed",  # type: ignore[call-arg]
        )
