from __future__ import annotations

import threading
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fincrime.cases.service import CaseService
from fincrime.evidence.models import EvidenceItem, EvidencePolarity
from fincrime.evidence.store import EvidenceStore


class CaseSummary(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    case_id: str = Field(min_length=1)
    seed_entity: str = Field(min_length=1)
    evidence_count: int = Field(ge=0)
    trace_edge_count: int = Field(ge=0)
    created_at: datetime
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")


class TraceNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    node_id: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_seed: bool = False
    is_context: bool = False


class TraceEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    edge_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    flow_amount: float = Field(ge=0.0)
    relationship_type: str = Field(min_length=1)
    identity_confidence: float = Field(ge=0.0, le=1.0)


class TraceGraphResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    nodes: tuple[TraceNode, ...]
    edges: tuple[TraceEdge, ...]
    is_truncated: bool
    total_hops: int


class ReferentialIntegrityError(Exception):
    pass


class InMemoryGraphRepository:
    def __init__(
        self,
        nodes: dict[str, TraceNode] | None = None,
        edges: dict[str, TraceEdge] | None = None,
    ) -> None:
        self._nodes: dict[str, TraceNode] = dict(nodes or {})
        self._edges: dict[str, TraceEdge] = dict(edges or {})
        self._lock = threading.Lock()

    def add_node(self, node: TraceNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node

    def add_edge(self, edge: TraceEdge) -> None:
        with self._lock:
            self._edges[edge.edge_id] = edge

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

        with self._lock:
            # 1. Referential integrity check
            if seed_entity not in self._nodes:
                raise ReferentialIntegrityError(
                    f"Seed entity not found in graph nodes: {seed_entity}"
                )

            all_requested_edges: list[TraceEdge] = []
            for eid in edge_ids:
                if eid not in self._edges:
                    raise ReferentialIntegrityError(f"Requested edge not found: {eid}")
                edge = self._edges[eid]
                if edge.source not in self._nodes or edge.target not in self._nodes:
                    raise ReferentialIntegrityError(f"Edge {eid} references missing endpoint node")
                all_requested_edges.append(edge)

            # 2. Strict BFS traversal rooted at seed_entity
            traversed_edges: list[TraceEdge] = []
            visited_nodes: set[str] = {seed_entity}
            current_frontier: set[str] = {seed_entity}
            actual_hops = 0

            edge_pool = list(all_requested_edges)
            for hop in range(1, max_hops + 1):
                next_frontier: set[str] = set()
                new_edges_in_hop: list[TraceEdge] = []
                for e in list(edge_pool):
                    if e.source in current_frontier or e.target in current_frontier:
                        new_edges_in_hop.append(e)
                        next_frontier.add(e.source)
                        next_frontier.add(e.target)
                        edge_pool.remove(e)
                if not new_edges_in_hop:
                    break
                traversed_edges.extend(new_edges_in_hop)
                current_frontier = next_frontier
                visited_nodes.update(next_frontier)
                actual_hops = hop
                if len(traversed_edges) >= max_edges:
                    break

            result_edges = traversed_edges[:max_edges]
            is_truncated = len(all_requested_edges) > len(result_edges)

            needed_node_ids = {seed_entity}
            for edge in result_edges:
                needed_node_ids.add(edge.source)
                needed_node_ids.add(edge.target)

            result_nodes = [self._nodes[nid] for nid in needed_node_ids]

            return TraceGraphResult(
                nodes=tuple(sorted(result_nodes, key=lambda n: n.node_id)),
                edges=tuple(sorted(result_edges, key=lambda e: e.edge_id)),
                is_truncated=is_truncated,
                total_hops=actual_hops,
            )


def get_case_summary(case_id: str, case_service: CaseService) -> CaseSummary:
    case = case_service.get(case_id)
    return CaseSummary(
        case_id=case.case_id,
        seed_entity=case.seed_entity,
        evidence_count=len(case.evidence_ids),
        trace_edge_count=len(case.trace_edge_ids),
        created_at=case.created_at,
        snapshot_hash=case.snapshot_hash,
    )


def get_supporting_evidence(
    case_id: str,
    case_service: CaseService,
    evidence_store: EvidenceStore,
    limit: int = 50,
) -> list[EvidenceItem]:
    if not (1 <= limit <= 50):
        raise ValueError(f"limit must be in 1..50, got {limit}")
    case = case_service.get(case_id)
    items = evidence_store.get_many(case.evidence_ids)
    supporting = [it for it in items if it.polarity == EvidencePolarity.SUPPORTING]
    supporting.sort(key=lambda x: x.evidence_id)
    return supporting[:limit]


def get_mitigating_evidence(
    case_id: str,
    case_service: CaseService,
    evidence_store: EvidenceStore,
    limit: int = 50,
) -> list[EvidenceItem]:
    if not (1 <= limit <= 50):
        raise ValueError(f"limit must be in 1..50, got {limit}")
    case = case_service.get(case_id)
    items = evidence_store.get_many(case.evidence_ids)
    mitigating = [it for it in items if it.polarity == EvidencePolarity.MITIGATING]
    mitigating.sort(key=lambda x: x.evidence_id)
    return mitigating[:limit]


def get_fund_trace(
    case_id: str,
    case_service: CaseService,
    graph_repo: InMemoryGraphRepository,
    max_hops: int = 4,
    max_edges: int = 100,
) -> TraceGraphResult:
    case = case_service.get(case_id)
    return graph_repo.get_subgraph_by_edge_ids(
        edge_ids=case.trace_edge_ids,
        seed_entity=case.seed_entity,
        max_hops=max_hops,
        max_edges=max_edges,
    )
