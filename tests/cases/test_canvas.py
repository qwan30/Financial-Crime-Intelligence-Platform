from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.agent.tools import InMemoryGraphRepository, ReferentialIntegrityError, TraceEdge, TraceNode
from fincrime.cases.canvas import CanvasService, CanvasTrace, InvalidExpansion, SnapshotConflict
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService
from fincrime.evidence.models import EvidenceCategory, EvidenceItem, EvidencePolarity
from fincrime.evidence.store import EvidenceStore


def load_fixture_data() -> dict:
    fixture_path = Path("tests/fixtures/forensic_canvas.json")
    return json.loads(fixture_path.read_text(encoding="utf-8"))


def build_canvas_setup(data: dict | None = None) -> tuple[CanvasService, str, str, InMemoryGraphRepository, CaseService]:
    if data is None:
        data = load_fixture_data()

    node_dict: dict[str, TraceNode] = {}
    for nd in data["nodes"]:
        node = TraceNode(
            node_id=nd["nodeId"],
            entity_type=nd["entityType"],
            risk_score=nd.get("riskScore"),
            is_seed=nd.get("isSeed", False),
            is_context=nd.get("isContext", False),
            account_holder_name=nd.get("accountHolderName"),
            bank_short_name=nd.get("bankShortName"),
            account_last4=nd.get("accountLast4"),
            badge=nd.get("badge"),
        )
        node_dict[node.node_id] = node

    edge_dict: dict[str, TraceEdge] = {}
    for ed in data["edges"]:
        ts = datetime.fromisoformat(ed["timestamp"]) if ed.get("timestamp") else None
        edge = TraceEdge(
            edge_id=ed["edgeId"],
            source=ed["source"],
            target=ed["target"],
            flow_amount=ed["flowAmount"],
            relationship_type=ed["relationshipType"],
            identity_confidence=ed["identityConfidence"],
            currency=ed.get("currency"),
            timestamp=ts,
        )
        edge_dict[edge.edge_id] = edge

    graph_repo = InMemoryGraphRepository(nodes=node_dict, edges=edge_dict)

    ev_store = EvidenceStore()
    ev_ids: list[str] = []
    for ev in data.get("evidence", []):
        ts = datetime.fromisoformat(ev["snapshotTime"])
        raw_ev = {
            "evidence_id": ev["evidenceId"],
            "category": EvidenceCategory(ev["category"]),
            "source_reference": ev["sourceReference"],
            "polarity": EvidencePolarity(ev["polarity"]),
            "snapshot_time": ts,
            "generation_method_version": ev["generationMethodVersion"],
            "confidence": ev.get("confidence"),
            "payload_summary": ev["payloadSummary"],
        }
        from fincrime.evidence.models import compute_sha256_hex
        real_hash = compute_sha256_hex(raw_ev)
        item = EvidenceItem(
            **raw_ev,
            integrity_hash=real_hash,
        )
        ev_store.put(item)
        ev_ids.append(item.evidence_id)

    case_service = CaseService(evidence_store=ev_store)

    created_at = datetime.fromisoformat(data["createdAt"])
    trace_edge_ids = tuple(ed["edgeId"] for ed in data["edges"])
    snapshot = CaseSnapshot.create_new(
        case_id=data["caseId"],
        seed_entity=data["seedEntity"],
        evidence_ids=tuple(sorted(ev_ids)),
        trace_edge_ids=tuple(sorted(trace_edge_ids)),
        created_at=created_at,
    )
    case_service.create(snapshot)

    canvas_service = CanvasService(cases=case_service, graph=graph_repo)
    return canvas_service, data["caseId"], snapshot.snapshot_hash, graph_repo, case_service


def test_canvas_initial_one_hop_boundary() -> None:
    canvas_service, case_id, snapshot_hash, _, _ = build_canvas_setup()
    trace = canvas_service.initial(case_id)

    assert isinstance(trace, CanvasTrace)
    node_ids = {n.node_id for n in trace.graph.nodes}
    assert node_ids == {"hub", "mule1", "mule2", "mule3", "mule4", "mule5", "evn", "shell"}
    assert "atm" not in node_ids
    assert "crypto" not in node_ids
    assert "exit3" not in node_ids
    assert "exit4" not in node_ids

    edge_ids = {e.edge_id for e in trace.graph.edges}
    assert edge_ids == {
        "TXN-2026-8800",
        "TXN-2026-8801",
        "TXN-2026-8802",
        "TXN-2026-8803",
        "TXN-2026-8808",
        "TXN-2026-8809",
        "TXN-2026-8804",
    }
    assert trace.hop_by_node_id["hub"] == 0
    for nid in ["mule1", "mule2", "mule3", "mule4", "mule5", "evn", "shell"]:
        assert trace.hop_by_node_id[nid] == 1

    # time_min and time_max across <= 3 hops (Tmax should be 09:55 UTC equivalent, not 10:00 because 8810 is hop 4)
    expected_tmin = datetime.fromisoformat("2026-09-08T08:15:00+07:00").astimezone(UTC)
    expected_tmax = datetime.fromisoformat("2026-09-08T09:55:00+07:00").astimezone(UTC)
    assert trace.time_min == expected_tmin
    assert trace.time_max == expected_tmax
    assert trace.unknown_time_edge_count == 0


def test_canvas_expand_shell_and_atm_never_reaches_hop_four() -> None:
    canvas_service, case_id, snapshot_hash, _, _ = build_canvas_setup()
    initial_trace = canvas_service.initial(case_id)
    known_edges = tuple(sorted(e.edge_id for e in initial_trace.graph.edges))

    # Expand shell (hop 1 -> hop 2: atm, crypto)
    trace_shell = canvas_service.expand(
        case_id=case_id,
        node_id="shell",
        known_edge_ids=known_edges,
        snapshot_hash=snapshot_hash,
    )
    node_ids_shell = {n.node_id for n in trace_shell.graph.nodes}
    assert "atm" in node_ids_shell
    assert "crypto" in node_ids_shell
    assert trace_shell.hop_by_node_id["atm"] == 2
    assert trace_shell.hop_by_node_id["crypto"] == 2
    assert "exit3" not in node_ids_shell
    assert "exit4" not in node_ids_shell

    shell_known_edges = tuple(sorted(e.edge_id for e in trace_shell.graph.edges))
    assert "TXN-2026-8805" in shell_known_edges
    assert "TXN-2026-8806" in shell_known_edges

    # Expand atm (hop 2 -> hop 3: exit3)
    trace_atm = canvas_service.expand(
        case_id=case_id,
        node_id="atm",
        known_edge_ids=shell_known_edges,
        snapshot_hash=snapshot_hash,
    )
    node_ids_atm = {n.node_id for n in trace_atm.graph.nodes}
    assert "exit3" in node_ids_atm
    assert trace_atm.hop_by_node_id["exit3"] == 3
    assert "exit4" not in node_ids_atm

    atm_known_edges = tuple(sorted(e.edge_id for e in trace_atm.graph.edges))
    assert "TXN-2026-8807" in atm_known_edges

    # Expand exit3 (hop 3) - candidate edge is TXN-2026-8810 to exit4, but exit4 is hop 4!
    # Distance 4 must NEVER be returned
    trace_exit3 = canvas_service.expand(
        case_id=case_id,
        node_id="exit3",
        known_edge_ids=atm_known_edges,
        snapshot_hash=snapshot_hash,
    )
    node_ids_exit3 = {n.node_id for n in trace_exit3.graph.nodes}
    assert "exit4" not in node_ids_exit3
    assert "TXN-2026-8810" not in {e.edge_id for e in trace_exit3.graph.edges}


def test_canvas_expansion_validation_and_conflicts() -> None:
    canvas_service, case_id, snapshot_hash, _, _ = build_canvas_setup()
    initial_trace = canvas_service.initial(case_id)
    known_edges = tuple(sorted(e.edge_id for e in initial_trace.graph.edges))

    # Stale hash
    with pytest.raises(SnapshotConflict):
        canvas_service.expand(
            case_id=case_id,
            node_id="shell",
            known_edge_ids=known_edges,
            snapshot_hash="a" * 64,
        )

    # Node not in known view
    with pytest.raises(InvalidExpansion):
        canvas_service.expand(
            case_id=case_id,
            node_id="atm",  # not in initial view yet
            known_edge_ids=known_edges,
            snapshot_hash=snapshot_hash,
        )

    # Foreign edge ID in known_edge_ids
    with pytest.raises(InvalidExpansion):
        canvas_service.expand(
            case_id=case_id,
            node_id="shell",
            known_edge_ids=known_edges + ("TXN-FOREIGN-999",),
            snapshot_hash=snapshot_hash,
        )


def test_canvas_empty_seeded_case() -> None:
    data = load_fixture_data()
    # Keep only seed node, empty edges
    data["nodes"] = [n for n in data["nodes"] if n["nodeId"] == "hub"]
    data["edges"] = []
    canvas_service, case_id, _, _, _ = build_canvas_setup(data)

    trace = canvas_service.initial(case_id)
    assert len(trace.graph.nodes) == 1
    assert trace.graph.nodes[0].node_id == "hub"
    assert len(trace.graph.edges) == 0
    assert trace.time_min is None
    assert trace.time_max is None
    assert trace.unknown_time_edge_count == 0


def test_canvas_missing_endpoint_integrity_error() -> None:
    data = load_fixture_data()
    # Remove one endpoint node
    data["nodes"] = [n for n in data["nodes"] if n["nodeId"] != "shell"]
    canvas_service, case_id, _, _, _ = build_canvas_setup(data)

    with pytest.raises(ReferentialIntegrityError):
        canvas_service.initial(case_id)


def test_canvas_deterministic_ordering_with_reordered_inputs() -> None:
    data1 = load_fixture_data()
    data2 = load_fixture_data()
    data2["edges"] = list(reversed(data1["edges"]))
    data2["nodes"] = list(reversed(data1["nodes"]))

    service1, case_id1, _, _, _ = build_canvas_setup(data1)
    service2, case_id2, _, _, _ = build_canvas_setup(data2)

    t1 = service1.initial(case_id1)
    t2 = service2.initial(case_id2)

    assert [n.node_id for n in t1.graph.nodes] == [n.node_id for n in t2.graph.nodes]
    assert [e.edge_id for e in t1.graph.edges] == [e.edge_id for e in t2.graph.edges]
