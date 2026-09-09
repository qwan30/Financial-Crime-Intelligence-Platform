from __future__ import annotations

import math
import threading
from datetime import UTC, datetime
from typing import Literal, Protocol, Self, runtime_checkable

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fincrime.cases.service import CaseService
from fincrime.evidence.models import EvidenceItem, EvidencePolarity
from fincrime.evidence.store import EvidenceStore

TypologyTag = Literal[
    "SEED_HUB", "SMURFING", "SHELL_CORP", "LAYERING", "CASHOUT", "CRYPTO_OTC", "BENIGN"
]

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
    account_holder_name: str | None = Field(default=None, min_length=1, max_length=200)
    bank_short_name: str | None = Field(default=None, min_length=1, max_length=80)
    account_last4: str | None = Field(default=None, pattern=r"^[0-9]{4}$")
    badge: TypologyTag | None = None


class TraceEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    edge_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    flow_amount: float = Field(ge=0.0)
    relationship_type: str = Field(min_length=1)
    identity_confidence: float = Field(ge=0.0, le=1.0)
    currency: str | None = Field(default=None, pattern=r"^[A-Z]{3}$")
    timestamp: datetime | None = None

    @field_validator("flow_amount", mode="after")
    @classmethod
    def _validate_flow_amount(cls, v: float) -> float:
        if not math.isfinite(v) or v < 0:
            raise ValueError(f"flow_amount must be a finite non-negative number, got {v}")
        return v

    @field_validator("timestamp", mode="after")
    @classmethod
    def _validate_timestamp(cls, v: datetime | None) -> datetime | None:
        if v is None:
            return None
        if not isinstance(v, datetime):
            raise TypeError(f"timestamp must be a datetime object, got {type(v).__name__}")
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("timestamp must be timezone-aware")
        return v.astimezone(UTC)

    @model_validator(mode="after")
    def _validate_currency_and_vnd_amount(self) -> Self:
        if self.currency == "VND":
            if not self.flow_amount.is_integer():
                raise ValueError(f"VND flow_amount must be an integer, got {self.flow_amount}")
            int_amount = int(self.flow_amount)
            if not (0 <= int_amount <= 9007199254740991):
                raise ValueError(
                    f"VND flow_amount must be in [0, 9007199254740991], got {int_amount}"
                )
        return self

class TraceGraphResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    nodes: tuple[TraceNode, ...]
    edges: tuple[TraceEdge, ...]
    is_truncated: bool
    total_hops: int


class ReferentialIntegrityError(Exception):
    pass

@runtime_checkable
class GraphRepository(Protocol):
    def add_node(self, node: TraceNode) -> None: ...
    def add_edge(self, edge: TraceEdge) -> None: ...
    def get_node(self, node_id: str) -> TraceNode: ...
    def get_edges(self, edge_ids: tuple[str, ...]) -> tuple[TraceEdge, ...]: ...
    def get_subgraph_by_edge_ids(
        self,
        edge_ids: tuple[str, ...],
        seed_entity: str,
        max_hops: int = 4,
        max_edges: int = 100,
    ) -> TraceGraphResult: ...


def bounded_trace(
    nodes: dict[str, TraceNode],
    edges: tuple[TraceEdge, ...],
    seed_entity: str,
    max_hops: int = 4,
    max_edges: int = 100,
) -> TraceGraphResult:
    if not (1 <= max_hops <= 4):
        raise ValueError(f"max_hops must be in 1..4, got {max_hops}")
    if not (1 <= max_edges <= 100):
        raise ValueError(f"max_edges must be in 1..100, got {max_edges}")

    if seed_entity not in nodes:
        raise ReferentialIntegrityError(
            f"Seed entity not found in graph nodes: {seed_entity}"
        )

    for edge in edges:
        if edge.source not in nodes or edge.target not in nodes:
            raise ReferentialIntegrityError(f"Edge {edge.edge_id} references missing endpoint node")

    traversed_edges: list[TraceEdge] = []
    visited_nodes: set[str] = {seed_entity}
    current_frontier: set[str] = {seed_entity}
    actual_hops = 0

    edge_pool = list(edges)
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
    is_truncated = len(edges) > len(result_edges)

    needed_node_ids = {seed_entity}
    for edge in result_edges:
        needed_node_ids.add(edge.source)
        needed_node_ids.add(edge.target)

    result_nodes = [nodes[nid] for nid in needed_node_ids]

    return TraceGraphResult(
        nodes=tuple(sorted(result_nodes, key=lambda n: n.node_id)),
        edges=tuple(sorted(result_edges, key=lambda e: e.edge_id)),
        is_truncated=is_truncated,
        total_hops=actual_hops,
    )

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

    def get_node(self, node_id: str) -> TraceNode:
        with self._lock:
            if node_id not in self._nodes:
                raise ReferentialIntegrityError(f"Node not found: {node_id}")
            return self._nodes[node_id]

    def get_edges(self, edge_ids: tuple[str, ...]) -> tuple[TraceEdge, ...]:
        with self._lock:
            missing = [eid for eid in edge_ids if eid not in self._edges]
            if missing:
                raise ReferentialIntegrityError(f"Requested edges not found: {missing}")
            return tuple(self._edges[eid] for eid in edge_ids)

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
            if seed_entity not in self._nodes:
                raise ReferentialIntegrityError(
                    f"Seed entity not found in graph nodes: {seed_entity}"
                )

            all_requested_edges: list[TraceEdge] = []
            for eid in edge_ids:
                if eid not in self._edges:
                    raise ReferentialIntegrityError(f"Requested edge not found: {eid}")
                all_requested_edges.append(self._edges[eid])

            return bounded_trace(
                nodes=self._nodes,
                edges=tuple(all_requested_edges),
                seed_entity=seed_entity,
                max_hops=max_hops,
                max_edges=max_edges,
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
    graph_repo: GraphRepository,
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
