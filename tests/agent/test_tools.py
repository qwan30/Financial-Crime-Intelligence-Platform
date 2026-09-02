from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from pydantic import ValidationError

from fincrime.agent.tools import (
    CaseSummary,
    InMemoryGraphRepository,
    ReferentialIntegrityError,
    TraceEdge,
    TraceGraphResult,
    TraceNode,
    get_case_summary,
    get_fund_trace,
    get_mitigating_evidence,
    get_supporting_evidence,
)
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    compute_sha256_hex,
)
from fincrime.evidence.store import EvidenceStore


def create_sample_evidence_item(
    evidence_id: str,
    polarity: EvidencePolarity = EvidencePolarity.SUPPORTING,
) -> EvidenceItem:
    raw: dict[str, Any] = {
        "evidence_id": evidence_id,
        "category": EvidenceCategory.RULE,
        "source_reference": f"rule_engine:{evidence_id}",
        "polarity": polarity,
        "snapshot_time": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        "generation_method_version": "v1.0.0",
        "confidence": 0.95,
        "payload_summary": f"Evidence payload for {evidence_id}",
    }
    h = compute_sha256_hex(raw)
    return EvidenceItem(**raw, integrity_hash=h)


def create_sample_case_snapshot(
    case_id: str,
    seed_entity: str,
    evidence_ids: tuple[str, ...] = (),
    trace_edge_ids: tuple[str, ...] = (),
) -> CaseSnapshot:
    raw: dict[str, Any] = {
        "case_id": case_id,
        "seed_entity": seed_entity,
        "evidence_ids": evidence_ids,
        "trace_edge_ids": trace_edge_ids,
        "created_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
    }
    h = compute_sha256_hex(raw)
    return CaseSnapshot(**raw, snapshot_hash=h)


def test_trace_node_and_edge_models() -> None:
    node = TraceNode(
        node_id="acc:001",
        entity_type="account",
        risk_score=0.85,
        is_seed=True,
        is_context=False,
    )
    assert node.node_id == "acc:001"
    assert node.risk_score == 0.85

    with pytest.raises(ValidationError):
        TraceNode(node_id="", entity_type="account")

    with pytest.raises(ValidationError):
        TraceNode(node_id="acc:001", entity_type="account", risk_score=1.5)

    edge = TraceEdge(
        edge_id="tx:101",
        source="acc:001",
        target="acc:002",
        flow_amount=50000.0,
        relationship_type="WIRE_TRANSFER",
        identity_confidence=0.9,
    )
    assert edge.edge_id == "tx:101"
    assert edge.flow_amount == 50000.0

    with pytest.raises(ValidationError):
        TraceEdge(
            edge_id="tx:101",
            source="acc:001",
            target="acc:002",
            flow_amount=-10.0,
            relationship_type="TRANSFER",
            identity_confidence=0.5,
        )


def test_graph_repo_referential_integrity_seed_missing() -> None:
    repo = InMemoryGraphRepository()
    with pytest.raises(ReferentialIntegrityError, match="Seed entity not found"):
        repo.get_subgraph_by_edge_ids(edge_ids=(), seed_entity="missing:seed")


def test_graph_repo_referential_integrity_edge_or_endpoint_missing() -> None:
    repo = InMemoryGraphRepository()
    repo.add_node(TraceNode(node_id="acc:001", entity_type="account", is_seed=True))

    with pytest.raises(ReferentialIntegrityError, match="Requested edge not found"):
        repo.get_subgraph_by_edge_ids(edge_ids=("tx:missing",), seed_entity="acc:001")

    # Edge present but endpoint missing
    repo.add_edge(
        TraceEdge(
            edge_id="tx:101",
            source="acc:001",
            target="acc:missing_endpoint",
            flow_amount=100.0,
            relationship_type="TRANSFER",
            identity_confidence=1.0,
        )
    )
    with pytest.raises(ReferentialIntegrityError, match="missing endpoint node"):
        repo.get_subgraph_by_edge_ids(edge_ids=("tx:101",), seed_entity="acc:001")


def test_graph_repo_bfs_traversal_and_deterministic_sorting() -> None:
    repo = InMemoryGraphRepository()
    # Nodes: acc:001 (seed), acc:002 (hop 1), acc:003 (hop 2), acc:004 (hop 3), acc:005 (disconnected)
    repo.add_node(TraceNode(node_id="acc:001", entity_type="account", is_seed=True))
    repo.add_node(TraceNode(node_id="acc:002", entity_type="account"))
    repo.add_node(TraceNode(node_id="acc:003", entity_type="account"))
    repo.add_node(TraceNode(node_id="acc:004", entity_type="account"))
    repo.add_node(TraceNode(node_id="acc:005", entity_type="account"))

    # Edges
    repo.add_edge(
        TraceEdge(
            edge_id="tx:001",
            source="acc:001",
            target="acc:002",
            flow_amount=100.0,
            relationship_type="TRANSFER",
            identity_confidence=1.0,
        )
    )
    repo.add_edge(
        TraceEdge(
            edge_id="tx:002",
            source="acc:002",
            target="acc:003",
            flow_amount=200.0,
            relationship_type="TRANSFER",
            identity_confidence=1.0,
        )
    )
    repo.add_edge(
        TraceEdge(
            edge_id="tx:003",
            source="acc:003",
            target="acc:004",
            flow_amount=300.0,
            relationship_type="TRANSFER",
            identity_confidence=1.0,
        )
    )

    # 1 hop traversal
    res_1hop = repo.get_subgraph_by_edge_ids(
        edge_ids=("tx:001", "tx:002", "tx:003"),
        seed_entity="acc:001",
        max_hops=1,
    )
    assert len(res_1hop.edges) == 1
    assert res_1hop.edges[0].edge_id == "tx:001"
    assert [n.node_id for n in res_1hop.nodes] == ["acc:001", "acc:002"]
    assert res_1hop.total_hops == 1
    assert res_1hop.is_truncated is True

    res_2hop = repo.get_subgraph_by_edge_ids(
        edge_ids=("tx:001", "tx:002", "tx:003"),
        seed_entity="acc:001",
        max_hops=2,
    )
    assert len(res_2hop.edges) == 2
    assert [e.edge_id for e in res_2hop.edges] == ["tx:001", "tx:002"]
    assert [n.node_id for n in res_2hop.nodes] == ["acc:001", "acc:002", "acc:003"]
    assert res_2hop.total_hops == 2


def test_graph_repo_edge_truncation_limit() -> None:
    repo = InMemoryGraphRepository()
    repo.add_node(TraceNode(node_id="seed:root", entity_type="account", is_seed=True))
    edge_ids = []
    for i in range(10):
        nid = f"leaf:{i:02d}"
        repo.add_node(TraceNode(node_id=nid, entity_type="account"))
        eid = f"edge:{i:02d}"
        repo.add_edge(
            TraceEdge(
                edge_id=eid,
                source="seed:root",
                target=nid,
                flow_amount=10.0,
                relationship_type="FANOUT",
                identity_confidence=1.0,
            )
        )
        edge_ids.append(eid)

    # Limit to max_edges=4
    res = repo.get_subgraph_by_edge_ids(
        edge_ids=tuple(sorted(edge_ids)),
        seed_entity="seed:root",
        max_hops=2,
        max_edges=4,
    )
    assert len(res.edges) == 4
    assert res.is_truncated is True
    assert len(res.nodes) == 5  # root + 4 leaf nodes


def test_graph_repo_bounds_validation() -> None:
    repo = InMemoryGraphRepository()
    with pytest.raises(ValueError, match="max_hops must be in 1..4"):
        repo.get_subgraph_by_edge_ids(edge_ids=(), seed_entity="acc:001", max_hops=0)

    with pytest.raises(ValueError, match="max_hops must be in 1..4"):
        repo.get_subgraph_by_edge_ids(edge_ids=(), seed_entity="acc:001", max_hops=5)

    with pytest.raises(ValueError, match="max_edges must be in 1..100"):
        repo.get_subgraph_by_edge_ids(edge_ids=(), seed_entity="acc:001", max_edges=0)

    with pytest.raises(ValueError, match="max_edges must be in 1..100"):
        repo.get_subgraph_by_edge_ids(edge_ids=(), seed_entity="acc:001", max_edges=101)


def test_bounded_read_tools_evidence_and_summary() -> None:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)

    # Insert 3 supporting and 2 mitigating evidence items
    evidence_store.put(create_sample_evidence_item("ev:sup:001", EvidencePolarity.SUPPORTING))
    evidence_store.put(create_sample_evidence_item("ev:sup:002", EvidencePolarity.SUPPORTING))
    evidence_store.put(create_sample_evidence_item("ev:sup:003", EvidencePolarity.SUPPORTING))
    evidence_store.put(create_sample_evidence_item("ev:mit:001", EvidencePolarity.MITIGATING))
    evidence_store.put(create_sample_evidence_item("ev:mit:002", EvidencePolarity.MITIGATING))

    case = create_sample_case_snapshot(
        case_id="case-tools-01",
        seed_entity="acc:root",
        evidence_ids=("ev:mit:001", "ev:mit:002", "ev:sup:001", "ev:sup:002", "ev:sup:003"),
        trace_edge_ids=(),
    )
    case_service.create(case)

    # 1. get_case_summary
    summary = get_case_summary("case-tools-01", case_service)
    assert isinstance(summary, CaseSummary)
    assert summary.case_id == "case-tools-01"
    assert summary.evidence_count == 5
    assert summary.trace_edge_count == 0
    assert summary.seed_entity == "acc:root"

    # 2. get_supporting_evidence
    sups = get_supporting_evidence("case-tools-01", case_service, evidence_store, limit=2)
    assert len(sups) == 2
    assert [e.evidence_id for e in sups] == ["ev:sup:001", "ev:sup:002"]

    # 3. get_mitigating_evidence
    mits = get_mitigating_evidence("case-tools-01", case_service, evidence_store, limit=50)
    assert len(mits) == 2
    assert [e.evidence_id for e in mits] == ["ev:mit:001", "ev:mit:002"]

    # 4. Limit bounds check
    with pytest.raises(ValueError, match="limit must be in 1..50"):
        get_supporting_evidence("case-tools-01", case_service, evidence_store, limit=0)
    with pytest.raises(ValueError, match="limit must be in 1..50"):
        get_mitigating_evidence("case-tools-01", case_service, evidence_store, limit=51)


def test_bounded_read_tool_get_fund_trace() -> None:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()

    graph_repo.add_node(TraceNode(node_id="seed:01", entity_type="account", is_seed=True))
    graph_repo.add_node(TraceNode(node_id="target:01", entity_type="account"))
    graph_repo.add_edge(
        TraceEdge(
            edge_id="edge:trace:01",
            source="seed:01",
            target="target:01",
            flow_amount=12000.0,
            relationship_type="TRANSFER",
            identity_confidence=0.98,
        )
    )

    case = create_sample_case_snapshot(
        case_id="case-trace-01",
        seed_entity="seed:01",
        evidence_ids=(),
        trace_edge_ids=("edge:trace:01",),
    )
    case_service.create(case)

    trace_result = get_fund_trace("case-trace-01", case_service, graph_repo)
    assert isinstance(trace_result, TraceGraphResult)
    assert len(trace_result.edges) == 1
    assert trace_result.edges[0].edge_id == "edge:trace:01"
    assert len(trace_result.nodes) == 2
