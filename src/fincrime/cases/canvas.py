from __future__ import annotations

from collections import deque
from datetime import UTC, datetime

from pydantic import BaseModel, ConfigDict

from fincrime.agent.tools import GraphRepository, ReferentialIntegrityError, TraceEdge, TraceGraphResult, TraceNode
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService


class SnapshotConflict(Exception):
    pass


class InvalidExpansion(Exception):
    pass


class CanvasTrace(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    graph: TraceGraphResult
    hop_by_node_id: dict[str, int]
    time_min: datetime | None
    time_max: datetime | None
    unknown_time_edge_count: int


class CanvasService:
    def __init__(self, cases: CaseService, graph: GraphRepository) -> None:
        self._cases = cases
        self._graph = graph

    def _resolve_graph_facts(
        self, snapshot: CaseSnapshot
    ) -> tuple[dict[str, TraceNode], dict[str, TraceEdge], dict[str, list[TraceEdge]], dict[str, int]]:
        seed_entity = snapshot.seed_entity
        seed_node = self._graph.get_node(seed_entity)
        case_edges = self._graph.get_edges(snapshot.trace_edge_ids)

        node_map: dict[str, TraceNode] = {seed_entity: seed_node}
        edge_map: dict[str, TraceEdge] = {}

        for edge in case_edges:
            edge_map[edge.edge_id] = edge
            if edge.source not in node_map:
                node_map[edge.source] = self._graph.get_node(edge.source)
            if edge.target not in node_map:
                node_map[edge.target] = self._graph.get_node(edge.target)

        # Build undirected adjacency
        adj_raw: dict[str, dict[str, TraceEdge]] = {nid: {} for nid in node_map}
        for edge in case_edges:
            adj_raw[edge.source][edge.edge_id] = edge
            adj_raw[edge.target][edge.edge_id] = edge

        # Sort each adjacency list deterministically:
        # (timestamp is None, timestamp or UTC datetime.max, edge_id)
        max_dt = datetime.max.replace(tzinfo=UTC)
        adj: dict[str, list[TraceEdge]] = {}
        for nid, edges_dict in adj_raw.items():
            sorted_edges = sorted(
                edges_dict.values(),
                key=lambda e: (e.timestamp is None, e.timestamp or max_dt, e.edge_id),
            )
            adj[nid] = sorted_edges

        # BFS shortest undirected distance from seed up to distance 3
        dist: dict[str, int] = {seed_entity: 0}
        queue: deque[str] = deque([seed_entity])

        while queue:
            curr = queue.popleft()
            curr_dist = dist[curr]
            if curr_dist >= 3:
                continue
            for edge in adj.get(curr, []):
                nbr = edge.target if edge.source == curr else edge.source
                if nbr not in dist:
                    dist[nbr] = curr_dist + 1
                    queue.append(nbr)

        return node_map, edge_map, adj, dist

    def initial(self, case_id: str, *, case_snapshot: CaseSnapshot | None = None) -> CanvasTrace:
        snapshot = case_snapshot or self._cases.get(case_id)
        node_map, edge_map, adj, dist = self._resolve_graph_facts(snapshot)

        seed_entity = snapshot.seed_entity

        # Compute time bounds and unknown count across all <=3-hop scope edges
        scope_edges = [
            e for e in edge_map.values()
            if dist.get(e.source, 999) <= 3 and dist.get(e.target, 999) <= 3
        ]
        timestamped = [e.timestamp for e in scope_edges if e.timestamp is not None]
        time_min = min(timestamped) if timestamped else None
        time_max = max(timestamped) if timestamped else None
        unknown_time_edge_count = sum(1 for e in scope_edges if e.timestamp is None)

        # Initial edges: seed incident edges whose endpoints have distance <= 1
        initial_edge_candidates = [
            e for e in adj.get(seed_entity, [])
            if dist.get(e.source, 999) <= 1 and dist.get(e.target, 999) <= 1
        ]
        # Deduplicate while preserving sort order
        seen_edge_ids: set[str] = set()
        initial_edges: list[TraceEdge] = []
        for e in initial_edge_candidates:
            if e.edge_id not in seen_edge_ids:
                seen_edge_ids.add(e.edge_id)
                initial_edges.append(e)
                if len(initial_edges) >= 100:
                    break

        returned_node_ids: set[str] = {seed_entity}
        for e in initial_edges:
            returned_node_ids.add(e.source)
            returned_node_ids.add(e.target)

        result_nodes = [
            node_map[nid].model_copy(update={"is_seed": nid == seed_entity})
            for nid in returned_node_ids
        ]
        hop_by_node_id = {nid: dist[nid] for nid in returned_node_ids}
        total_hops = max(hop_by_node_id.values(), default=0)
        is_truncated = len(scope_edges) > len(initial_edges)

        graph_result = TraceGraphResult(
            nodes=tuple(sorted(result_nodes, key=lambda n: n.node_id)),
            edges=tuple(sorted(initial_edges, key=lambda e: e.edge_id)),
            is_truncated=is_truncated,
            total_hops=total_hops,
        )

        return CanvasTrace(
            graph=graph_result,
            hop_by_node_id=hop_by_node_id,
            time_min=time_min,
            time_max=time_max,
            unknown_time_edge_count=unknown_time_edge_count,
        )

    def expand(
        self,
        case_id: str,
        node_id: str,
        known_edge_ids: tuple[str, ...],
        snapshot_hash: str,
    ) -> CanvasTrace:
        snapshot = self._cases.get(case_id)
        if snapshot.snapshot_hash != snapshot_hash:
            raise SnapshotConflict(
                f"Snapshot hash conflict: expected {snapshot.snapshot_hash}, got {snapshot_hash}"
            )

        if len(set(known_edge_ids)) != len(known_edge_ids):
            raise InvalidExpansion("known_edge_ids must be unique")
        if len(known_edge_ids) > 100:
            raise InvalidExpansion(f"known_edge_ids length {len(known_edge_ids)} exceeds limit 100")

        case_edge_id_set = set(snapshot.trace_edge_ids)
        if not set(known_edge_ids).issubset(case_edge_id_set):
            raise InvalidExpansion("known_edge_ids contains edge not in case whitelist")

        node_map, edge_map, adj, dist = self._resolve_graph_facts(snapshot)
        seed_entity = snapshot.seed_entity

        # Check all known edge endpoints are within seed distance <= 3
        known_nodes: set[str] = {seed_entity}
        for eid in known_edge_ids:
            e = edge_map[eid]
            if dist.get(e.source, 999) > 3 or dist.get(e.target, 999) > 3:
                raise InvalidExpansion(f"Known edge {eid} has endpoint beyond 3 hops")
            known_nodes.add(e.source)
            known_nodes.add(e.target)

        # Selected node must be seed or an endpoint of a known edge
        if node_id not in known_nodes:
            raise InvalidExpansion(f"node_id {node_id} is not seed or endpoint of a known edge")

        # Candidate edges are selected node's incident edges with both endpoints <= 3
        candidate_edges = [
            e for e in adj.get(node_id, [])
            if dist.get(e.source, 999) <= 3 and dist.get(e.target, 999) <= 3
        ]

        # Scope edges across all <=3-hop scope
        scope_edges = [
            e for e in edge_map.values()
            if dist.get(e.source, 999) <= 3 and dist.get(e.target, 999) <= 3
        ]
        timestamped = [e.timestamp for e in scope_edges if e.timestamp is not None]
        time_min = min(timestamped) if timestamped else None
        time_max = max(timestamped) if timestamped else None
        unknown_time_edge_count = sum(1 for e in scope_edges if e.timestamp is None)

        # Preserve all known edges; append new sorted edges up to remaining 100-edge capacity
        known_edge_list = [edge_map[eid] for eid in known_edge_ids]
        remaining_capacity = 100 - len(known_edge_list)

        new_edges: list[TraceEdge] = []
        known_id_set = set(known_edge_ids)
        for e in candidate_edges:
            if e.edge_id not in known_id_set and e.edge_id not in {ne.edge_id for ne in new_edges}:
                new_edges.append(e)
                if len(new_edges) >= remaining_capacity:
                    break

        union_edges = known_edge_list + new_edges

        returned_node_ids: set[str] = {seed_entity}
        for e in union_edges:
            returned_node_ids.add(e.source)
            returned_node_ids.add(e.target)

        result_nodes = [
            node_map[nid].model_copy(update={"is_seed": nid == seed_entity})
            for nid in returned_node_ids
        ]
        hop_by_node_id = {nid: dist[nid] for nid in returned_node_ids}
        total_hops = max(hop_by_node_id.values(), default=0)
        is_truncated = len(scope_edges) > len(union_edges)

        graph_result = TraceGraphResult(
            nodes=tuple(sorted(result_nodes, key=lambda n: n.node_id)),
            edges=tuple(sorted(union_edges, key=lambda e: e.edge_id)),
            is_truncated=is_truncated,
            total_hops=total_hops,
        )

        return CanvasTrace(
            graph=graph_result,
            hop_by_node_id=hop_by_node_id,
            time_min=time_min,
            time_max=time_max,
            unknown_time_edge_count=unknown_time_edge_count,
        )
