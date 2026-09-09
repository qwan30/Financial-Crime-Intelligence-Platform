from __future__ import annotations

import argparse
from datetime import datetime
import json
import os
from pathlib import Path

from sqlalchemy import create_engine, select

from fincrime.agent.tools import TraceEdge, TraceNode
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseConflict
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    canonical_json_bytes,
    compute_sha256_hex,
)
from fincrime.storage.postgres import (
    case_snapshots,
    cases,
    put_case,
    put_evidence,
    put_graph_edge,
    put_graph_node,
)


def import_canvas_case(path: Path, database_url: str) -> str:
    content = json.loads(path.read_text(encoding="utf-8"))

    case_id = content["caseId"]
    seed_entity = content["seedEntity"]
    created_at = datetime.fromisoformat(content["createdAt"])

    # Prepare nodes
    nodes: list[TraceNode] = []
    for nd in content["nodes"]:
        nodes.append(
            TraceNode(
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
        )

    # Prepare edges
    edges: list[TraceEdge] = []
    for ed in content["edges"]:
        ts = datetime.fromisoformat(ed["timestamp"]) if ed.get("timestamp") else None
        edges.append(
            TraceEdge(
                edge_id=ed["edgeId"],
                source=ed["source"],
                target=ed["target"],
                flow_amount=ed["flowAmount"],
                relationship_type=ed["relationshipType"],
                identity_confidence=ed["identityConfidence"],
                currency=ed.get("currency"),
                timestamp=ts,
            )
        )

    # Prepare evidence
    evidence_items_list: list[EvidenceItem] = []
    ev_ids: list[str] = []
    for ev in content.get("evidence", []):
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
        h = compute_sha256_hex(raw_ev)
        item = EvidenceItem(**raw_ev, integrity_hash=h)
        evidence_items_list.append(item)
        ev_ids.append(item.evidence_id)

    # Prepare snapshot
    trace_edge_ids = tuple(sorted(e.edge_id for e in edges))
    snapshot = CaseSnapshot.create_new(
        case_id=case_id,
        seed_entity=seed_entity,
        evidence_ids=tuple(sorted(ev_ids)),
        trace_edge_ids=trace_edge_ids,
        created_at=created_at,
    )
    snapshot_bytes = canonical_json_bytes(snapshot.model_dump(mode="python", by_alias=False))

    engine = create_engine(database_url)
    try:
        with engine.begin() as conn:
            # Check if this exact snapshot already exists in case_snapshots
            check_stmt = select(case_snapshots).where(
                case_snapshots.c.case_id == case_id,
                case_snapshots.c.snapshot_hash == snapshot.snapshot_hash,
            )
            existing_snap = conn.execute(check_stmt).first()
            if existing_snap is not None:
                if bytes(existing_snap.canonical_bytes) == snapshot_bytes:
                    # Idempotent no-op: leave newer pin/unpin snapshot current
                    return snapshot.snapshot_hash
                raise CaseConflict(
                    f"Snapshot '{snapshot.snapshot_hash}' already exists with differing canonical bytes"
                )

            # Insert nodes
            for node in nodes:
                put_graph_node(conn, node)

            # Insert edges
            for edge in edges:
                put_graph_edge(conn, edge)

            # Insert evidence
            for ev_item in evidence_items_list:
                put_evidence(conn, ev_item)

            # Check if case exists in cases table
            case_row = conn.execute(select(cases).where(cases.c.case_id == case_id)).first()
            if case_row is None:
                put_case(conn, snapshot)
            else:
                conn.execute(
                    case_snapshots.insert().values(
                        case_id=case_id,
                        snapshot_hash=snapshot.snapshot_hash,
                        payload=snapshot.model_dump(mode="json"),
                        canonical_bytes=snapshot_bytes,
                    )
                )

        return snapshot.snapshot_hash
    finally:
        engine.dispose()


def main() -> None:
    parser = argparse.ArgumentParser(description="Import forensic canvas fixture into PostgreSQL")
    parser.add_argument("--path", type=str, required=True, help="Path to fixture JSON")
    args = parser.parse_args()

    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        raise ValueError("DATABASE_URL environment variable is required")

    h = import_canvas_case(Path(args.path), db_url)
    print(f"Imported case successfully with snapshot hash: {h}")


if __name__ == "__main__":
    main()
