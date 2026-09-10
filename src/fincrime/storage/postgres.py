from __future__ import annotations

import json
from collections.abc import Sequence

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    LargeBinary,
    MetaData,
    PrimaryKeyConstraint,
    String,
    Table,
    Text,
    insert,
    select,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.engine import Connection, Engine

from fincrime.agent.tools import (
    ReferentialIntegrityError,
    TraceEdge,
    TraceGraphResult,
    TraceNode,
    bounded_trace,
)
from fincrime.cases.models import AnalystFeedbackEvent, CaseSnapshot
from fincrime.cases.service import CaseConflict, CaseNotFound, FeedbackConflict
from fincrime.evidence.models import (
    EvidenceItem,
    canonical_json_bytes,
)
from fincrime.evidence.store import EvidenceConflict, EvidenceNotFound

metadata = MetaData()

evidence_items = Table(
    "evidence_items",
    metadata,
    Column("evidence_id", Text, primary_key=True),
    Column("payload", JSONB, nullable=False),
    Column("canonical_bytes", LargeBinary, nullable=False),
)

graph_nodes = Table(
    "graph_nodes",
    metadata,
    Column("node_id", Text, primary_key=True),
    Column("payload", JSONB, nullable=False),
    Column("canonical_bytes", LargeBinary, nullable=False),
)

graph_edges = Table(
    "graph_edges",
    metadata,
    Column("edge_id", Text, primary_key=True),
    Column("source", Text, ForeignKey("graph_nodes.node_id"), nullable=False),
    Column("target", Text, ForeignKey("graph_nodes.node_id"), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("canonical_bytes", LargeBinary, nullable=False),
    Index("graph_edges_source_idx", "source"),
    Index("graph_edges_target_idx", "target"),
)

cases = Table(
    "cases",
    metadata,
    Column("case_id", Text, primary_key=True),
    Column("payload", JSONB, nullable=False),
    Column("canonical_bytes", LargeBinary, nullable=False),
)

case_snapshots = Table(
    "case_snapshots",
    metadata,
    Column("case_id", Text, ForeignKey("cases.case_id"), nullable=False),
    Column("snapshot_hash", String(64), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("canonical_bytes", LargeBinary, nullable=False),
    PrimaryKeyConstraint("case_id", "snapshot_hash"),
)

case_evidence = Table(
    "case_evidence",
    metadata,
    Column("case_id", Text, ForeignKey("cases.case_id"), nullable=False),
    Column("edge_id", Text, ForeignKey("graph_edges.edge_id"), nullable=False),
    Column("evidence_id", Text, ForeignKey("evidence_items.evidence_id"), nullable=False),
    Column("is_pinned", Boolean, nullable=False),
    Column("typology_tag", Text, nullable=True),
    Column("analyst_id", Text, nullable=False),
    Column("updated_at", DateTime(timezone=True), nullable=False),
    PrimaryKeyConstraint("case_id", "edge_id"),
    CheckConstraint("length(trim(analyst_id)) > 0", name="case_evidence_analyst_id_check"),
    CheckConstraint(
        "typology_tag IS NULL OR typology_tag IN ('SEED_HUB', 'SMURFING', 'SHELL_CORP', 'LAYERING', 'CASHOUT', 'CRYPTO_OTC', 'BENIGN')",
        name="case_evidence_typology_tag_check",
    ),
)

case_feedback = Table(
    "case_feedback",
    metadata,
    Column("event_id", Text, primary_key=True),
    Column("case_id", Text, ForeignKey("cases.case_id"), nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("canonical_bytes", LargeBinary, nullable=False),
)


# Transaction-sharing functions (no commit)
def put_evidence(conn: Connection, item: EvidenceItem) -> EvidenceItem:
    item_bytes = canonical_json_bytes(item.model_dump(mode="python", by_alias=False))
    stmt = select(evidence_items).where(evidence_items.c.evidence_id == item.evidence_id)
    existing = conn.execute(stmt).first()
    if existing is not None:
        if bytes(existing.canonical_bytes) == item_bytes:
            return item
        raise EvidenceConflict(
            f"EvidenceItem '{item.evidence_id}' already exists with differing canonical bytes."
        )
    conn.execute(
        insert(evidence_items).values(
            evidence_id=item.evidence_id,
            payload=item.model_dump(mode="json"),
            canonical_bytes=item_bytes,
        )
    )
    return item


def put_graph_node(conn: Connection, node: TraceNode) -> TraceNode:
    node_bytes = canonical_json_bytes(node.model_dump(mode="json"))
    stmt = select(graph_nodes).where(graph_nodes.c.node_id == node.node_id)
    existing = conn.execute(stmt).first()
    if existing is not None:
        if bytes(existing.canonical_bytes) == node_bytes:
            return node
        raise ReferentialIntegrityError(
            f"Node '{node.node_id}' already exists with differing canonical bytes."
        )
    conn.execute(
        insert(graph_nodes).values(
            node_id=node.node_id,
            payload=node.model_dump(mode="json"),
            canonical_bytes=node_bytes,
        )
    )
    return node


def put_graph_edge(conn: Connection, edge: TraceEdge) -> TraceEdge:
    edge_bytes = canonical_json_bytes(edge.model_dump(mode="json"))
    s_stmt = select(graph_nodes.c.node_id).where(graph_nodes.c.node_id == edge.source)
    t_stmt = select(graph_nodes.c.node_id).where(graph_nodes.c.node_id == edge.target)
    if (
        conn.execute(s_stmt).scalar_one_or_none() is None
        or conn.execute(t_stmt).scalar_one_or_none() is None
    ):
        raise ReferentialIntegrityError(f"Edge {edge.edge_id} references missing endpoint node")

    stmt = select(graph_edges).where(graph_edges.c.edge_id == edge.edge_id)
    existing = conn.execute(stmt).first()
    if existing is not None:
        if bytes(existing.canonical_bytes) == edge_bytes:
            return edge
        raise ReferentialIntegrityError(
            f"Edge '{edge.edge_id}' already exists with differing canonical bytes."
        )
    conn.execute(
        insert(graph_edges).values(
            edge_id=edge.edge_id,
            source=edge.source,
            target=edge.target,
            payload=edge.model_dump(mode="json"),
            canonical_bytes=edge_bytes,
        )
    )
    return edge


def put_case(conn: Connection, case: CaseSnapshot) -> CaseSnapshot:
    case_bytes = canonical_json_bytes(case.model_dump(mode="python", by_alias=False))
    stmt = select(cases).where(cases.c.case_id == case.case_id)
    existing = conn.execute(stmt).first()
    if existing is not None:
        if bytes(existing.canonical_bytes) == case_bytes:
            return case
        raise CaseConflict(f"Case '{case.case_id}' already exists with differing canonical bytes.")

    conn.execute(
        insert(cases).values(
            case_id=case.case_id,
            payload=case.model_dump(mode="json"),
            canonical_bytes=case_bytes,
        )
    )
    conn.execute(
        insert(case_snapshots).values(
            case_id=case.case_id,
            snapshot_hash=case.snapshot_hash,
            payload=case.model_dump(mode="json"),
            canonical_bytes=case_bytes,
        )
    )
    return case


def put_feedback(conn: Connection, event: AnalystFeedbackEvent) -> AnalystFeedbackEvent:
    event_bytes = canonical_json_bytes(event.model_dump(mode="python", by_alias=False))
    case_stmt = select(cases.c.case_id).where(cases.c.case_id == event.case_id)
    if conn.execute(case_stmt).scalar_one_or_none() is None:
        raise CaseNotFound(f"Case '{event.case_id}' not found.")

    stmt = select(case_feedback).where(case_feedback.c.event_id == event.event_id)
    existing = conn.execute(stmt).first()
    if existing is not None:
        if bytes(existing.canonical_bytes) == event_bytes:
            return event
        raise FeedbackConflict(
            f"Feedback event '{event.event_id}' already exists with differing canonical bytes."
        )
    conn.execute(
        insert(case_feedback).values(
            event_id=event.event_id,
            case_id=event.case_id,
            payload=event.model_dump(mode="json"),
            canonical_bytes=event_bytes,
        )
    )
    return event


# Postgres Repository Implementations
class PostgresEvidenceRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def put(self, item: EvidenceItem) -> EvidenceItem:
        with self._engine.begin() as conn:
            return put_evidence(conn, item)

    def get(self, evidence_id: str) -> EvidenceItem:
        with self._engine.connect() as conn:
            stmt = select(evidence_items).where(evidence_items.c.evidence_id == evidence_id)
            row = conn.execute(stmt).first()
            if row is None:
                raise EvidenceNotFound(f"EvidenceItem '{evidence_id}' not found.")
            return EvidenceItem.model_validate_json(json.dumps(row.payload))

    def get_many(self, evidence_ids: Sequence[str]) -> list[EvidenceItem]:
        if not evidence_ids:
            return []
        with self._engine.connect() as conn:
            stmt = select(evidence_items).where(evidence_items.c.evidence_id.in_(evidence_ids))
            rows = conn.execute(stmt).all()
            items_by_id = {
                row.evidence_id: EvidenceItem.model_validate_json(json.dumps(row.payload))
                for row in rows
            }
            results: list[EvidenceItem] = []
            for eid in evidence_ids:
                if eid not in items_by_id:
                    raise EvidenceNotFound(f"EvidenceItem '{eid}' not found.")
                results.append(items_by_id[eid])
            return results


class PostgresGraphRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def add_node(self, node: TraceNode) -> None:
        with self._engine.begin() as conn:
            put_graph_node(conn, node)

    def add_edge(self, edge: TraceEdge) -> None:
        with self._engine.begin() as conn:
            put_graph_edge(conn, edge)

    def get_node(self, node_id: str) -> TraceNode:
        with self._engine.connect() as conn:
            stmt = select(graph_nodes).where(graph_nodes.c.node_id == node_id)
            row = conn.execute(stmt).first()
            if row is None:
                raise ReferentialIntegrityError(f"Node not found: {node_id}")
            return TraceNode.model_validate_json(json.dumps(row.payload))

    def get_edges(self, edge_ids: tuple[str, ...]) -> tuple[TraceEdge, ...]:
        if not edge_ids:
            return ()
        with self._engine.connect() as conn:
            stmt = select(graph_edges).where(graph_edges.c.edge_id.in_(edge_ids))
            rows = conn.execute(stmt).all()
            edges_by_id = {
                row.edge_id: TraceEdge.model_validate_json(json.dumps(row.payload)) for row in rows
            }
            missing = [eid for eid in edge_ids if eid not in edges_by_id]
            if missing:
                raise ReferentialIntegrityError(f"Requested edges not found: {missing}")
            return tuple(edges_by_id[eid] for eid in edge_ids)

    def get_subgraph_by_edge_ids(
        self,
        edge_ids: tuple[str, ...],
        seed_entity: str,
        max_hops: int = 4,
        max_edges: int = 100,
    ) -> TraceGraphResult:
        if not (1 <= max_hops <= 4):
            raise ValueError(f"max_hops must be in 1..4, got {max_hops}")
        if not (1 <= max_edges <= 100):
            raise ValueError(f"max_edges must be in 1..100, got {max_edges}")

        with self._engine.connect() as conn:
            # Check seed
            seed_row = conn.execute(
                select(graph_nodes).where(graph_nodes.c.node_id == seed_entity)
            ).first()
            if seed_row is None:
                raise ReferentialIntegrityError(
                    f"Seed entity not found in graph nodes: {seed_entity}"
                )

            requested_edges = self.get_edges(edge_ids)

            needed_node_ids = {seed_entity}
            for e in requested_edges:
                needed_node_ids.add(e.source)
                needed_node_ids.add(e.target)

            node_rows = conn.execute(
                select(graph_nodes).where(graph_nodes.c.node_id.in_(needed_node_ids))
            ).all()
            nodes_by_id = {
                r.node_id: TraceNode.model_validate_json(json.dumps(r.payload)) for r in node_rows
            }
            for nid in needed_node_ids:
                if nid not in nodes_by_id:
                    raise ReferentialIntegrityError(f"Missing endpoint node: {nid}")

            return bounded_trace(
                nodes=nodes_by_id,
                edges=requested_edges,
                seed_entity=seed_entity,
                max_hops=max_hops,
                max_edges=max_edges,
            )


class PostgresCaseRepository:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def create(self, case: CaseSnapshot) -> CaseSnapshot:
        with self._engine.begin() as conn:
            return put_case(conn, case)

    def get(self, case_id: str) -> CaseSnapshot:
        with self._engine.connect() as conn:
            stmt = select(cases).where(cases.c.case_id == case_id)
            row = conn.execute(stmt).first()
            if row is None:
                raise CaseNotFound(f"Case '{case_id}' not found.")
            return CaseSnapshot.model_validate_json(json.dumps(row.payload))

    def append_feedback(self, event: AnalystFeedbackEvent) -> AnalystFeedbackEvent:
        with self._engine.begin() as conn:
            return put_feedback(conn, event)
