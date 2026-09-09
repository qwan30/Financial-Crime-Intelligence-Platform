from __future__ import annotations

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine

from fincrime.agent.tools import ReferentialIntegrityError, TraceEdge, TraceNode
from fincrime.cases.models import AnalystFeedbackEvent, CaseSnapshot, Disposition
from fincrime.cases.service import CaseConflict, CaseNotFound, CaseService, FeedbackConflict
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    canonical_json_bytes,
    compute_sha256_hex,
)
from fincrime.evidence.store import EvidenceConflict, EvidenceNotFound, EvidenceStore
from fincrime.storage.postgres import (
    PostgresCaseRepository,
    PostgresEvidenceRepository,
    PostgresGraphRepository,
)


def make_evidence_item(evidence_id: str, summary: str = "Test summary") -> EvidenceItem:
    raw = {
        "evidence_id": evidence_id,
        "category": EvidenceCategory.OBSERVED,
        "source_reference": f"ref:{evidence_id}",
        "polarity": EvidencePolarity.SUPPORTING,
        "snapshot_time": datetime(2026, 9, 8, 8, 30, 0, 123456, tzinfo=UTC),
        "generation_method_version": "v1.0.0",
        "confidence": 0.95,
        "payload_summary": summary,
    }
    h = compute_sha256_hex(raw)
    return EvidenceItem(**raw, integrity_hash=h)


def test_postgres_repositories_persistence(postgres_url: str) -> None:
    engine1 = create_engine(postgres_url)
    ev_repo1 = PostgresEvidenceRepository(engine1)
    graph_repo1 = PostgresGraphRepository(engine1)
    case_repo1 = PostgresCaseRepository(engine1)

    # 1. Put evidence
    ev = make_evidence_item("ev:pg:001")
    ev_repo1.put(ev)

    # 2. Put nodes and edges
    seed_node = TraceNode(
        node_id="hub",
        entity_type="ACCOUNT",
        account_holder_name="Nguyễn Văn A",
        bank_short_name="Vietcombank",
        account_last4="2891",
        badge="SEED_HUB",
        risk_score=0.88,
        is_seed=True,
    )
    mule_node = TraceNode(
        node_id="mule1",
        entity_type="ACCOUNT",
        account_holder_name="Trần Thị Bình",
        bank_short_name="Sacombank",
        account_last4="9020",
        badge="SMURFING",
        risk_score=0.76,
    )
    graph_repo1.add_node(seed_node)
    graph_repo1.add_node(mule_node)

    ts = datetime(2026, 9, 8, 8, 30, 0, 500000, tzinfo=UTC)
    edge = TraceEdge(
        edge_id="TXN-PG-01",
        source="mule1",
        target="hub",
        flow_amount=10000000.0,
        currency="VND",
        timestamp=ts,
        relationship_type="NAPAS_247",
        identity_confidence=0.98,
    )
    graph_repo1.add_edge(edge)

    # 3. Put case
    created_at = datetime(2026, 9, 8, 8, 0, 0, tzinfo=UTC)
    case = CaseSnapshot.create_new(
        case_id="case_pg_01",
        seed_entity="hub",
        evidence_ids=(ev.evidence_id,),
        trace_edge_ids=(edge.edge_id,),
        created_at=created_at,
    )
    case_repo1.create(case)

    # Dispose first engine
    engine1.dispose()

    # Reopen second engine and verify exact matching facts
    engine2 = create_engine(postgres_url)
    ev_repo2 = PostgresEvidenceRepository(engine2)
    graph_repo2 = PostgresGraphRepository(engine2)
    case_repo2 = PostgresCaseRepository(engine2)

    loaded_ev = ev_repo2.get(ev.evidence_id)
    assert loaded_ev.evidence_id == ev.evidence_id
    assert loaded_ev.integrity_hash == ev.integrity_hash
    assert loaded_ev.snapshot_time == ev.snapshot_time

    loaded_seed = graph_repo2.get_node("hub")
    assert loaded_seed.node_id == "hub"
    assert loaded_seed.account_holder_name == "Nguyễn Văn A"
    assert loaded_seed.badge == "SEED_HUB"

    loaded_edge = graph_repo2.get_edges((edge.edge_id,))
    assert len(loaded_edge) == 1
    assert loaded_edge[0].edge_id == edge.edge_id
    assert loaded_edge[0].currency == "VND"
    assert loaded_edge[0].flow_amount == 10000000.0
    assert loaded_edge[0].timestamp == ts

    loaded_case = case_repo2.get(case.case_id)
    assert loaded_case.case_id == case.case_id
    assert loaded_case.snapshot_hash == case.snapshot_hash
    assert loaded_case.evidence_ids == case.evidence_ids
    assert loaded_case.trace_edge_ids == case.trace_edge_ids

    engine2.dispose()


def test_postgres_repositories_idempotent_duplicate_and_conflict(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    ev_repo = PostgresEvidenceRepository(engine)
    graph_repo = PostgresGraphRepository(engine)
    case_repo = PostgresCaseRepository(engine)

    # Evidence: idempotent same bytes, conflict different bytes
    ev = make_evidence_item("ev:dup:001", summary="Original summary")
    assert ev_repo.put(ev) == ev
    assert ev_repo.put(ev) == ev

    ev_diff = make_evidence_item("ev:dup:001", summary="Differing summary")
    with pytest.raises(EvidenceConflict):
        ev_repo.put(ev_diff)

    # Graph Node: idempotent same bytes, conflict different bytes
    node = TraceNode(node_id="n1", entity_type="ACCOUNT")
    graph_repo.add_node(node)
    graph_repo.add_node(node)

    node_diff = TraceNode(node_id="n1", entity_type="COMPANY")
    with pytest.raises(ReferentialIntegrityError):
        graph_repo.add_node(node_diff)

    # Case: idempotent same bytes, conflict different bytes
    case = CaseSnapshot.create_new(
        case_id="case:dup:001",
        seed_entity="n1",
        evidence_ids=(ev.evidence_id,),
        trace_edge_ids=(),
    )
    assert case_repo.create(case).snapshot_hash == case.snapshot_hash
    assert case_repo.create(case).snapshot_hash == case.snapshot_hash

    case_diff = CaseSnapshot.create_new(
        case_id="case:dup:001",
        seed_entity="n1",
        evidence_ids=(),
    )
    with pytest.raises(CaseConflict):
        case_repo.create(case_diff)

    engine.dispose()


def test_postgres_feedback_persistence_and_conflict(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    ev_repo = PostgresEvidenceRepository(engine)
    case_repo = PostgresCaseRepository(engine)

    ev = make_evidence_item("ev:fb:001")
    ev_repo.put(ev)
    case = CaseSnapshot.create_new(case_id="case:fb:001", seed_entity="s1", evidence_ids=(ev.evidence_id,))
    case_repo.create(case)

    # Feedback on nonexistent case
    nonexistent_fb = AnalystFeedbackEvent.create_new(
        case_id="case:nonexistent",
        analyst_id="analyst_01",
        disposition=Disposition.ESCALATE,
        rationale="Needs review",
    )
    with pytest.raises(CaseNotFound):
        case_repo.append_feedback(nonexistent_fb)

    # Feedback on existing case
    fb = AnalystFeedbackEvent.create_new(
        case_id=case.case_id,
        analyst_id="analyst_01",
        disposition=Disposition.ESCALATE,
        rationale="Legitimate escalation",
    )
    appended = case_repo.append_feedback(fb)
    assert appended.event_id == fb.event_id

    # Idempotent re-append
    assert case_repo.append_feedback(fb).event_id == fb.event_id

    # Conflict on same event_id with different payload
    diff_fb = fb.model_copy(update={"rationale": "Different rationale"})
    with pytest.raises(FeedbackConflict):
        case_repo.append_feedback(diff_fb)

    engine.dispose()


def test_postgres_get_many_order_and_missing(postgres_url: str) -> None:
    engine = create_engine(postgres_url)
    ev_repo = PostgresEvidenceRepository(engine)

    ev1 = make_evidence_item("ev:many:01")
    ev2 = make_evidence_item("ev:many:02")
    ev3 = make_evidence_item("ev:many:03")
    ev_repo.put(ev1)
    ev_repo.put(ev2)
    ev_repo.put(ev3)

    # Order preserved
    res = ev_repo.get_many(["ev:many:03", "ev:many:01", "ev:many:02"])
    assert [x.evidence_id for x in res] == ["ev:many:03", "ev:many:01", "ev:many:02"]

    # Missing raises
    with pytest.raises(EvidenceNotFound):
        ev_repo.get_many(["ev:many:01", "ev:many:missing"])

    engine.dispose()
