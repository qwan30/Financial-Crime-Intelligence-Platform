from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime

import pytest

from fincrime.cases.models import (
    AdjudicationStatus,
    AnalystFeedbackEvent,
    CaseSnapshot,
    Disposition,
)
from fincrime.cases.service import (
    CaseConflict,
    CaseNotFound,
    CaseService,
    FeedbackConflict,
)
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    compute_sha256_hex,
)
from fincrime.evidence.store import (
    EvidenceNotFound,
    EvidenceStore,
)


def create_sample_evidence(evidence_id: str) -> EvidenceItem:
    raw = {
        "evidence_id": evidence_id,
        "category": EvidenceCategory.OBSERVED,
        "source_reference": f"src-{evidence_id}",
        "polarity": EvidencePolarity.SUPPORTING,
        "snapshot_time": datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
        "generation_method_version": "v1.0.0",
        "confidence": 0.9,
        "payload_summary": "Sample evidence payload",
    }
    h = compute_sha256_hex(raw)
    return EvidenceItem(**raw, integrity_hash=h)


def create_sample_case(
    case_id: str = "case-001",
    seed_entity: str = "account:12345",
    evidence_ids: tuple[str, ...] = (),
    trace_edge_ids: tuple[str, ...] = (),
) -> CaseSnapshot:
    raw = {
        "case_id": case_id,
        "seed_entity": seed_entity,
        "evidence_ids": evidence_ids,
        "trace_edge_ids": trace_edge_ids,
        "created_at": datetime(2026, 3, 1, 14, 0, 0, tzinfo=UTC),
    }
    h = compute_sha256_hex(raw)
    return CaseSnapshot(**raw, snapshot_hash=h)


def create_sample_feedback(
    event_id: str = "fb-001",
    case_id: str = "case-001",
    reason: str = "Suspicious behavior confirmed.",
    snapshot_hash: str = "0" * 64,
) -> AnalystFeedbackEvent:
    return AnalystFeedbackEvent(
        event_id=event_id,
        analyst_id="analyst-1",
        case_id=case_id,
        disposition=Disposition.CONFIRMED_SUSPICIOUS,
        reason=reason,
        created_at=datetime(2026, 3, 2, 10, 0, 0, tzinfo=UTC),
        snapshot_hash=snapshot_hash,
        adjudication_status=AdjudicationStatus.PENDING,
    )


def test_case_service_create_and_get() -> None:
    store = EvidenceStore()
    store.put(create_sample_evidence("ev-001"))
    store.put(create_sample_evidence("ev-002"))

    service = CaseService(evidence_store=store)
    case = create_sample_case("case-100", evidence_ids=("ev-001", "ev-002"))

    created = service.create(case)
    assert created == case

    fetched = service.get("case-100")
    assert fetched == case


def test_case_service_create_missing_evidence_raises() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    case = create_sample_case("case-missing-ev", evidence_ids=("ev-missing",))

    with pytest.raises(EvidenceNotFound, match="EvidenceItem 'ev-missing' not found"):
        service.create(case)


def test_case_service_create_idempotent() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    case1 = create_sample_case("case-idem", seed_entity="account:111")
    case2 = create_sample_case("case-idem", seed_entity="account:111")

    res1 = service.create(case1)
    res2 = service.create(case2)
    assert res1 == res2
    assert service.get("case-idem") == case1


def test_case_service_create_conflict() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    case1 = create_sample_case("case-conflict", seed_entity="account:AAA")
    case2 = create_sample_case("case-conflict", seed_entity="account:BBB")

    service.create(case1)
    with pytest.raises(CaseConflict, match="already exists with differing canonical bytes"):
        service.create(case2)


def test_case_service_get_not_found() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    with pytest.raises(CaseNotFound, match="Case 'case-not-exists' not found"):
        service.get("case-not-exists")


def test_case_service_append_feedback_success() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    case = service.create(create_sample_case("case-fb-1"))

    feedback = create_sample_feedback("fb-1", case_id="case-fb-1", snapshot_hash=case.snapshot_hash)
    appended = service.append_feedback(feedback)
    assert appended == feedback


def test_case_service_append_feedback_case_not_found() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    feedback = create_sample_feedback("fb-orphan", case_id="case-nonexistent")

    with pytest.raises(CaseNotFound, match="Case 'case-nonexistent' not found"):
        service.append_feedback(feedback)


def test_case_service_append_feedback_idempotent() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    case = service.create(create_sample_case("case-fb-idem"))

    fb1 = create_sample_feedback(
        "fb-2", case_id="case-fb-idem", reason="Same reason", snapshot_hash=case.snapshot_hash
    )
    fb2 = create_sample_feedback(
        "fb-2", case_id="case-fb-idem", reason="Same reason", snapshot_hash=case.snapshot_hash
    )

    res1 = service.append_feedback(fb1)
    res2 = service.append_feedback(fb2)
    assert res1 == res2


def test_case_service_append_feedback_conflict() -> None:
    store = EvidenceStore()
    service = CaseService(evidence_store=store)
    case = service.create(create_sample_case("case-fb-conflict"))

    fb1 = create_sample_feedback(
        "fb-3", case_id="case-fb-conflict", reason="Reason A", snapshot_hash=case.snapshot_hash
    )
    fb2 = create_sample_feedback(
        "fb-3", case_id="case-fb-conflict", reason="Reason B", snapshot_hash=case.snapshot_hash
    )

    service.append_feedback(fb1)
    with pytest.raises(FeedbackConflict, match="already exists with differing canonical bytes"):
        service.append_feedback(fb2)


def test_case_service_thread_safety() -> None:
    store = EvidenceStore()
    for i in range(50):
        store.put(create_sample_evidence(f"ev-th-{i}"))

    service = CaseService(evidence_store=store)

    def create_worker(idx: int) -> CaseSnapshot:
        case = create_sample_case(f"case-th-{idx}", evidence_ids=(f"ev-th-{idx}",))
        return service.create(case)

    with ThreadPoolExecutor(max_workers=8) as executor:
        cases = list(executor.map(create_worker, range(50)))

    assert len(cases) == 50

    def feedback_worker(idx: int) -> AnalystFeedbackEvent:
        fb = create_sample_feedback(
            f"fb-th-{idx}",
            case_id=f"case-th-{idx}",
            snapshot_hash=cases[idx].snapshot_hash,
        )
        return service.append_feedback(fb)

    with ThreadPoolExecutor(max_workers=8) as executor:
        feedbacks = list(executor.map(feedback_worker, range(50)))

    assert len(feedbacks) == 50
