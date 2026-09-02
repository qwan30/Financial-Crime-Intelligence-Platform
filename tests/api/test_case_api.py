from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi.testclient import TestClient

from apps.case_api.main import app, get_case_service, get_evidence_store
from fincrime.cases.service import CaseService
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    compute_sha256_hex,
)
from fincrime.evidence.store import EvidenceStore


@pytest.fixture
def test_setup() -> tuple[TestClient, EvidenceStore, CaseService]:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)

    app.dependency_overrides[get_evidence_store] = lambda: evidence_store
    app.dependency_overrides[get_case_service] = lambda: case_service

    client = TestClient(app)
    return client, evidence_store, case_service


def test_healthz(test_setup: tuple[TestClient, EvidenceStore, CaseService]) -> None:
    client, _, _ = test_setup
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_get_case_not_found(test_setup: tuple[TestClient, EvidenceStore, CaseService]) -> None:
    client, _, _ = test_setup
    response = client.get("/cases/nonexistent-case-123")
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["data"] is None
    assert data["error"]["code"] == "CASE_NOT_FOUND"


def test_create_and_get_case_success(
    test_setup: tuple[TestClient, EvidenceStore, CaseService],
) -> None:
    client, evidence_store, _ = test_setup

    # Put prerequisite evidence in evidence store
    ev_raw = {
        "evidence_id": "ev-api-01",
        "category": EvidenceCategory.OBSERVED,
        "source_reference": "tx-999",
        "polarity": EvidencePolarity.SUPPORTING,
        "snapshot_time": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        "generation_method_version": "v1.0.0",
        "confidence": 0.88,
        "payload_summary": "High risk transfer",
    }
    ev_hash = compute_sha256_hex(ev_raw)
    evidence_store.put(EvidenceItem(**ev_raw, integrity_hash=ev_hash))

    created_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    case_hash = compute_sha256_hex(
        {
            "case_id": "case-api-01",
            "seed_entity": "account:api-01",
            "evidence_ids": ("ev-api-01",),
            "trace_edge_ids": ("edge-01",),
            "created_at": created_at,
        }
    )

    payload = {
        "caseId": "case-api-01",
        "seedEntity": "account:api-01",
        "evidenceIds": ["ev-api-01"],
        "traceEdgeIds": ["edge-01"],
        "createdAt": "2026-03-01T12:00:00Z",
        "snapshotHash": case_hash,
    }

    create_res = client.post("/cases", json=payload)
    assert create_res.status_code == 200
    res_data = create_res.json()
    assert res_data["success"] is True
    assert res_data["data"]["caseId"] == "case-api-01"
    assert res_data["data"]["seedEntity"] == "account:api-01"
    assert res_data["data"]["evidenceIds"] == ["ev-api-01"]
    assert res_data["data"]["snapshotHash"] == case_hash

    # Now GET /cases/{case_id}
    get_res = client.get("/cases/case-api-01")
    assert get_res.status_code == 200
    get_data = get_res.json()
    assert get_data["success"] is True
    assert get_data["data"]["caseId"] == "case-api-01"
    assert get_data["data"]["snapshotHash"] == case_hash


def test_create_case_missing_evidence(
    test_setup: tuple[TestClient, EvidenceStore, CaseService],
) -> None:
    client, _, _ = test_setup
    created_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    case_hash = compute_sha256_hex(
        {
            "case_id": "case-missing",
            "seed_entity": "account:999",
            "evidence_ids": ("ev-missing",),
            "trace_edge_ids": (),
            "created_at": created_at,
        }
    )
    payload = {
        "caseId": "case-missing",
        "seedEntity": "account:999",
        "evidenceIds": ["ev-missing"],
        "traceEdgeIds": [],
        "createdAt": "2026-03-01T12:00:00Z",
        "snapshotHash": case_hash,
    }
    response = client.post("/cases", json=payload)
    assert response.status_code == 404
    data = response.json()
    assert data["success"] is False
    assert data["error"]["code"] == "EVIDENCE_NOT_FOUND"


def test_create_case_conflict(test_setup: tuple[TestClient, EvidenceStore, CaseService]) -> None:
    client, _, _ = test_setup
    created_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

    hash1 = compute_sha256_hex(
        {
            "case_id": "case-conflict-api",
            "seed_entity": "account:111",
            "evidence_ids": (),
            "trace_edge_ids": (),
            "created_at": created_at,
        }
    )
    payload1 = {
        "caseId": "case-conflict-api",
        "seedEntity": "account:111",
        "evidenceIds": [],
        "traceEdgeIds": [],
        "createdAt": "2026-03-01T12:00:00Z",
        "snapshotHash": hash1,
    }
    res1 = client.post("/cases", json=payload1)
    assert res1.status_code == 200

    hash2 = compute_sha256_hex(
        {
            "case_id": "case-conflict-api",
            "seed_entity": "account:222",
            "evidence_ids": (),
            "trace_edge_ids": (),
            "created_at": created_at,
        }
    )
    payload2 = {
        "caseId": "case-conflict-api",
        "seedEntity": "account:222",
        "evidenceIds": [],
        "traceEdgeIds": [],
        "createdAt": "2026-03-01T12:00:00Z",
        "snapshotHash": hash2,
    }
    res2 = client.post("/cases", json=payload2)
    assert res2.status_code == 409
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "CASE_CONFLICT"


def test_create_case_validation_error(
    test_setup: tuple[TestClient, EvidenceStore, CaseService],
) -> None:
    client, _, _ = test_setup
    payload = {
        "caseId": "case-bad-hash",
        "seedEntity": "account:111",
        "evidenceIds": [],
        "traceEdgeIds": [],
        "createdAt": "2026-03-01T12:00:00Z",
        "snapshotHash": "badhash" * 8,  # incorrect 64-char hash
    }
    res = client.post("/cases", json=payload)
    assert res.status_code == 422
    data = res.json()
    assert data["success"] is False
    assert data["error"]["code"] == "VALIDATION_ERROR"


def test_create_feedback_success(test_setup: tuple[TestClient, EvidenceStore, CaseService]) -> None:
    client, _, _ = test_setup
    created_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    case_hash = compute_sha256_hex(
        {
            "case_id": "case-fb-api",
            "seed_entity": "account:fb",
            "evidence_ids": (),
            "trace_edge_ids": (),
            "created_at": created_at,
        }
    )
    client.post(
        "/cases",
        json={
            "caseId": "case-fb-api",
            "seedEntity": "account:fb",
            "evidenceIds": [],
            "traceEdgeIds": [],
            "createdAt": "2026-03-01T12:00:00Z",
            "snapshotHash": case_hash,
        },
    )

    fb_payload = {
        "eventId": "fb-001",
        "analystId": "analyst-1",
        "disposition": "CONFIRMED_SUSPICIOUS",
        "reason": "Clear structuring",
        "createdAt": "2026-03-02T10:00:00Z",
        "snapshotHash": case_hash,
        "adjudicationStatus": "PENDING",
    }
    fb_res = client.post("/cases/case-fb-api/feedback", json=fb_payload)
    assert fb_res.status_code == 200
    fb_data = fb_res.json()
    assert fb_data["success"] is True
    assert fb_data["data"]["eventId"] == "fb-001"
    assert fb_data["data"]["caseId"] == "case-fb-api"


def test_create_feedback_case_not_found(
    test_setup: tuple[TestClient, EvidenceStore, CaseService],
) -> None:
    client, _, _ = test_setup
    fb_payload = {
        "eventId": "fb-orphan",
        "analystId": "analyst-1",
        "disposition": "FALSE_POSITIVE",
        "reason": "Benign merchant activity",
        "createdAt": "2026-03-02T10:00:00Z",
        "snapshotHash": "0" * 64,
        "adjudicationStatus": "PENDING",
    }
    fb_res = client.post("/cases/nonexistent-case/feedback", json=fb_payload)
    assert fb_res.status_code == 404
    fb_data = fb_res.json()
    assert fb_data["success"] is False
    assert fb_data["error"]["code"] == "CASE_NOT_FOUND"


def test_create_feedback_conflict(
    test_setup: tuple[TestClient, EvidenceStore, CaseService],
) -> None:
    client, _, _ = test_setup
    created_at = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    case_hash = compute_sha256_hex(
        {
            "case_id": "case-fb-conf",
            "seed_entity": "account:fb",
            "evidence_ids": (),
            "trace_edge_ids": (),
            "created_at": created_at,
        }
    )
    client.post(
        "/cases",
        json={
            "caseId": "case-fb-conf",
            "seedEntity": "account:fb",
            "evidenceIds": [],
            "traceEdgeIds": [],
            "createdAt": "2026-03-01T12:00:00Z",
            "snapshotHash": case_hash,
        },
    )

    fb_payload1 = {
        "eventId": "fb-conflict-id",
        "analystId": "analyst-1",
        "disposition": "CONFIRMED_SUSPICIOUS",
        "reason": "Reason 1",
        "createdAt": "2026-03-02T10:00:00Z",
        "snapshotHash": case_hash,
    }
    res1 = client.post("/cases/case-fb-conf/feedback", json=fb_payload1)
    assert res1.status_code == 200

    fb_payload2 = {
        "eventId": "fb-conflict-id",
        "analystId": "analyst-1",
        "disposition": "CONFIRMED_SUSPICIOUS",
        "reason": "Reason 2 (Conflicting)",
        "createdAt": "2026-03-02T10:00:00Z",
        "snapshotHash": case_hash,
    }
    res2 = client.post("/cases/case-fb-conf/feedback", json=fb_payload2)
    assert res2.status_code == 409
    data = res2.json()
    assert data["success"] is False
    assert data["error"]["code"] == "FEEDBACK_CONFLICT"
