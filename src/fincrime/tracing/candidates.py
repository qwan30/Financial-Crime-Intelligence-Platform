from __future__ import annotations

import heapq
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Literal

from fincrime.evidence.models import compute_sha256_hex
from fincrime.graph.events import TransactionEvent
from fincrime.tracing.models import (
    EXCLUSION_REASONS,
    REASON_CODE_ORDER,
    STOP_REASONS_ORDER,
    ExcludedTransition,
    ExclusionReason,
    ReasonCode,
    ResultStatus,
    RootBranch,
    StopReason,
    TerminalReason,
    TraceLabError,
    TracePath,
    TraceRequest,
    TraceResult,
    TraceStep,
    datetime_to_descending_usec,
    duration_microseconds,
)
from fincrime.tracing.snapshots import TraceSnapshot

MAX_EXAMINED_TRANSITIONS: int = 10000
MAX_PATH_STATES: int = 1000
MAX_EXCLUSION_EXAMPLES_LIMIT: int = 200


def _compute_steps(
    edges: tuple[TransactionEvent, ...],
    direction: Literal["forward", "backward"],
    seed_kind: Literal["account", "transaction"],
    anchor_id: str | None,
    max_gap_usec: int | None,
) -> tuple[TraceStep, ...]:
    """Compute trace steps for a sequence of edges in chronological money-transfer order."""
    steps: list[TraceStep] = []
    n = len(edges)

    for i, edge in enumerate(edges):
        if i == 0:
            prev_id = None
            delta_usec = None
            codes: list[ReasonCode] = []
            if seed_kind == "transaction" and edge.edge_id == anchor_id:
                codes.append("ANCHOR_TRANSACTION")
            elif seed_kind == "account" and (
                direction == "forward" or (direction == "backward" and n == 1)
            ):
                codes.append("SEED_INCIDENT")
        else:
            prev_edge = edges[i - 1]
            prev_id = prev_edge.edge_id
            td = edge.event_time.astimezone(UTC) - prev_edge.event_time.astimezone(UTC)
            delta_usec = duration_microseconds(td)
            codes = []
            if seed_kind == "transaction" and edge.edge_id == anchor_id:
                codes.append("ANCHOR_TRANSACTION")
            elif seed_kind == "account" and direction == "backward" and i == n - 1:
                codes.append("SEED_INCIDENT")
            codes.append("TEMPORAL_ORDER")
            if delta_usec == 0:
                codes.append("SAME_TIMESTAMP_ORDER_UNKNOWN")
            if max_gap_usec is not None and delta_usec <= max_gap_usec:
                codes.append("WITHIN_GAP")

        ordered_codes = tuple(c for c in REASON_CODE_ORDER if c in codes)
        steps.append(
            TraceStep(
                edge_id=edge.edge_id,
                previous_edge_id=prev_id,
                delta_microseconds=delta_usec,
                reason_codes=ordered_codes,
            )
        )

    return tuple(steps)


class _CandidateIterator:
    """Lazily merges adjacency edge streams for a parent endpoint in traversal order."""

    def __init__(
        self,
        snapshot: TraceSnapshot,
        endpoint: str,
        direction: Literal["forward", "backward"],
    ) -> None:
        self.snapshot = snapshot
        self.endpoint = endpoint
        self.direction = direction

        iterators: list[Iterator[TransactionEvent]] = []
        if direction == "forward":
            for cp in snapshot.get_forward_counterparties(endpoint):
                edge_ids = snapshot.get_forward_edges(endpoint, cp)
                events = [snapshot.get_event(eid) for eid in edge_ids]
                valid_events = [ev for ev in events if ev is not None]
                if valid_events:
                    iterators.append(iter(valid_events))

            def sort_key(ev: TransactionEvent) -> tuple[datetime, str]:
                return (ev.event_time.astimezone(UTC), ev.edge_id)

            self._merged: Iterator[TransactionEvent] = heapq.merge(*iterators, key=sort_key)
        else:
            for cp in snapshot.get_backward_counterparties(endpoint):
                edge_ids = snapshot.get_backward_edges(endpoint, cp)
                events = [snapshot.get_event(eid) for eid in edge_ids]
                valid_events = [ev for ev in events if ev is not None]
                if valid_events:
                    iterators.append(iter(valid_events))

            def sort_key_back(ev: TransactionEvent) -> tuple[int, str]:
                return (datetime_to_descending_usec(ev.event_time), ev.edge_id)

            self._merged = heapq.merge(*iterators, key=sort_key_back)

    def next_candidate(self) -> TransactionEvent | None:
        try:
            return next(self._merged)
        except StopIteration:
            return None


class _ActivePathState:
    def __init__(
        self,
        direction: Literal["forward", "backward"],
        edges: tuple[TransactionEvent, ...],
        endpoint: str,
        accounts: frozenset[str],
        root_branch: RootBranch | None,
        path_idx: int,
        iterator: _CandidateIterator,
    ) -> None:
        self.direction = direction
        self.edges = edges
        self.endpoint = endpoint
        self.accounts = accounts
        self.root_branch = root_branch
        self.path_idx = path_idx
        self.iterator = iterator
        self.has_admitted_child = False
        self.is_exhausted = False


def generate_candidates(snapshot: TraceSnapshot, request: TraceRequest) -> TraceResult:
    """Generate explainable temporal transaction-tracing candidates."""
    if not isinstance(snapshot, TraceSnapshot):
        raise TypeError(f"snapshot must be a TraceSnapshot, got {type(snapshot).__name__}")
    if not isinstance(request, TraceRequest):
        raise TypeError(f"request must be a TraceRequest, got {type(request).__name__}")

    cutoff_utc = snapshot.cutoff.astimezone(UTC)
    window_end_utc = request.window_end.astimezone(UTC)
    window_start_utc = request.window_start.astimezone(UTC)

    if window_end_utc > cutoff_utc:
        raise TraceLabError(
            "INVALID_REQUEST",
            f"window_end ({window_end_utc}) is later than snapshot cutoff ({cutoff_utc})",
        )

    # Empty result template
    empty_exclusion_counts: dict[str, int] = {r: 0 for r in EXCLUSION_REASONS}

    # Handle seeds
    seed_kind = request.seed.kind
    anchor_event: TransactionEvent | None = None
    anchor_id: str | None = None

    if seed_kind == "account":
        account_id = request.seed.account_id
        if not snapshot.has_account(account_id):
            return TraceResult(
                edge_ids=(),
                transactions=(),
                paths=(),
                excluded_transition_counts=empty_exclusion_counts,
                excluded_transition_examples=(),
                exclusion_examples_truncated=False,
                examined_transitions=0,
                admitted_path_states=0,
                returned_root_branches=(),
                status="SEED_NOT_FOUND",
                stop_reasons=(),
            )
    else:
        anchor_id = request.seed.edge_id
        if not snapshot.has_edge(anchor_id):
            return TraceResult(
                edge_ids=(),
                transactions=(),
                paths=(),
                excluded_transition_counts=empty_exclusion_counts,
                excluded_transition_examples=(),
                exclusion_examples_truncated=False,
                examined_transitions=0,
                admitted_path_states=0,
                returned_root_branches=(),
                status="SEED_NOT_FOUND",
                stop_reasons=(),
            )
        anchor_event = snapshot.get_event(anchor_id)
        if anchor_event is None:
            return TraceResult(
                edge_ids=(),
                transactions=(),
                paths=(),
                excluded_transition_counts=empty_exclusion_counts,
                excluded_transition_examples=(),
                exclusion_examples_truncated=False,
                examined_transitions=0,
                admitted_path_states=0,
                returned_root_branches=(),
                status="SEED_NOT_FOUND",
                stop_reasons=(),
            )
        anchor_time_utc = anchor_event.event_time.astimezone(UTC)
        if not (window_start_utc <= anchor_time_utc <= window_end_utc):
            raise TraceLabError(
                "INVALID_REQUEST",
                f"Anchor transaction {anchor_id} time ({anchor_time_utc}) is outside window [{window_start_utc}, {window_end_utc}]",
            )

    # State tracking
    admitted_edge_ids: set[str] = set()
    admitted_paths: list[TracePath] = []
    seen_path_signatures: set[tuple[str, tuple[str, ...]]] = set()
    covered_root_branches: set[RootBranch] = set()

    exclusion_counts: dict[str, int] = {r: 0 for r in EXCLUSION_REASONS}
    exclusion_examples: list[ExcludedTransition] = []
    exclusion_examples_truncated = False

    examined_transitions = 0
    stop_reasons_set: set[StopReason] = set()

    def record_exclusion(
        path_id: str | None,
        direction: Literal["forward", "backward"],
        edge_id: str,
        reason: ExclusionReason,
    ) -> None:
        nonlocal exclusion_examples_truncated
        exclusion_counts[reason] += 1
        if len(exclusion_examples) < MAX_EXCLUSION_EXAMPLES_LIMIT:
            exclusion_examples.append(
                ExcludedTransition(
                    path_id=path_id,
                    direction=direction,
                    edge_id=edge_id,
                    reason=reason,
                )
            )
        else:
            exclusion_examples_truncated = True

    # Initialize path states by layer
    # layer 0: initial states (length 0 for account, length 1 for anchor)
    current_layer_states: dict[
        Literal["backward", "forward"], dict[str, list[_ActivePathState]]
    ] = {
        "backward": {},
        "forward": {},
    }

    directions_to_run: list[Literal["backward", "forward"]] = []
    if request.direction in ("backward", "both"):
        directions_to_run.append("backward")
    if request.direction in ("forward", "both"):
        directions_to_run.append("forward")

    if seed_kind == "account":
        acc_id = request.seed.account_id
        # For account seed, create length-0 states per direction
        for d in directions_to_run:
            iterator = _CandidateIterator(snapshot, acc_id, d)
            st = _ActivePathState(
                direction=d,
                edges=(),
                endpoint=acc_id,
                accounts=frozenset([acc_id]),
                root_branch=None,
                path_idx=-1,  # no admitted path yet
                iterator=iterator,
            )
            # Root branch will be established on first hop
            current_layer_states[d]["_root"] = [st]
    else:
        assert anchor_event is not None
        admitted_edge_ids.add(anchor_event.edge_id)
        is_self_loop = anchor_event.source_id == anchor_event.target_id

        for d in directions_to_run:
            edges = (anchor_event,)
            steps = _compute_steps(
                edges=edges,
                direction=d,
                seed_kind="transaction",
                anchor_id=anchor_id,
                max_gap_usec=request.max_gap_microseconds,
            )
            term: TerminalReason | None = "CYCLE_CLOSED" if is_self_loop else None
            path_sig = (d, (anchor_event.edge_id,))
            seen_path_signatures.add(path_sig)

            path_id = compute_sha256_hex({"direction": d, "edge_ids": [anchor_event.edge_id]})
            tp = TracePath(
                path_id=path_id,
                direction=d,
                edge_ids=(anchor_event.edge_id,),
                steps=steps,
                terminal_reason=term,
            )
            admitted_paths.append(tp)
            path_idx = len(admitted_paths) - 1

            endpoint = anchor_event.target_id if d == "forward" else anchor_event.source_id
            accounts = frozenset([anchor_event.source_id, anchor_event.target_id])

            if term is None:
                # Check max_hops == 1
                if request.max_hops == 1:
                    incidents = snapshot.get_incident_edge_count(endpoint, d)
                    if incidents > 0:
                        admitted_paths[path_idx] = tp.model_copy(
                            update={"terminal_reason": "HOP_LIMIT"}
                        )
                        stop_reasons_set.add("HOP_LIMIT")
                    else:
                        admitted_paths[path_idx] = tp.model_copy(
                            update={"terminal_reason": "DEAD_END"}
                        )
                else:
                    iterator = _CandidateIterator(snapshot, endpoint, d)
                    st = _ActivePathState(
                        direction=d,
                        edges=edges,
                        endpoint=endpoint,
                        accounts=accounts,
                        root_branch=None,
                        path_idx=path_idx,
                        iterator=iterator,
                    )
                    current_layer_states[d]["_root"] = [st]

    # Helper to check if any states remain in layer
    def has_active_states(
        layer_states: dict[Literal["backward", "forward"], dict[str, list[_ActivePathState]]],
    ) -> bool:
        for d in ("backward", "forward"):
            for b_list in layer_states[d].values():
                if any(not s.is_exhausted for s in b_list):
                    return True
        return False

    current_hop = 0 if seed_kind == "account" else 1

    # Breadth-first layer traversal loop
    while current_hop < request.max_hops and has_active_states(current_layer_states):
        next_layer_states: dict[
            Literal["backward", "forward"], dict[str, list[_ActivePathState]]
        ] = {
            "backward": {},
            "forward": {},
        }

        # Check global stop conditions
        if stop_reasons_set.intersection({"EDGE_BUDGET", "WORK_BUDGET", "PATH_BUDGET"}):
            break

        # In this layer, alternate direction turns backward then forward
        # Within each direction, rotate branches round-robin, one transition attempt per turn
        active_dirs = [
            d
            for d in ("backward", "forward")
            if d in directions_to_run
            and any(
                any(not s.is_exhausted for s in b_list)
                for b_list in current_layer_states[d].values()
            )
        ]

        # Group branches in lexical counterparty order
        # For _root states, their counterparties are discovered when candidate is pulled
        branch_order: dict[Literal["backward", "forward"], list[str]] = {
            "backward": sorted(current_layer_states["backward"].keys()),
            "forward": sorted(current_layer_states["forward"].keys()),
        }

        # Indices for round-robin rotation
        parent_idx_in_branch: dict[tuple[str, str], int] = {}

        while active_dirs:
            if examined_transitions >= MAX_EXAMINED_TRANSITIONS:
                stop_reasons_set.add("WORK_BUDGET")
                break
            if stop_reasons_set.intersection({"EDGE_BUDGET", "PATH_BUDGET"}):
                break

            for d in list(active_dirs):
                branches = [
                    b
                    for b in branch_order[d]
                    if any(not s.is_exhausted for s in current_layer_states[d].get(b, []))
                ]
                if not branches:
                    active_dirs.remove(d)
                    continue

                for b in list(branches):
                    if examined_transitions >= MAX_EXAMINED_TRANSITIONS:
                        stop_reasons_set.add("WORK_BUDGET")
                        break
                    if stop_reasons_set.intersection({"EDGE_BUDGET", "PATH_BUDGET"}):
                        break

                    parent_list = [s for s in current_layer_states[d][b] if not s.is_exhausted]
                    if not parent_list:
                        continue

                    # Select parent state in admission order (round-robin)
                    idx_key = (d, b)
                    p_idx = parent_idx_in_branch.get(idx_key, 0) % len(parent_list)
                    parent_state = parent_list[p_idx]
                    parent_idx_in_branch[idx_key] = p_idx + 1

                    # Inspect one candidate transition
                    cand = parent_state.iterator.next_candidate()
                    if cand is None:
                        parent_state.is_exhausted = True
                        if not parent_state.has_admitted_child and parent_state.path_idx >= 0:
                            # If no children admitted, mark parent DEAD_END
                            cur_tp = admitted_paths[parent_state.path_idx]
                            if cur_tp.terminal_reason is None:
                                admitted_paths[parent_state.path_idx] = cur_tp.model_copy(
                                    update={"terminal_reason": "DEAD_END"}
                                )
                        continue

                    examined_transitions += 1

                    # Rejection precedence:
                    # 1. EDGE_ALREADY_IN_PATH
                    # 2. OUTSIDE_WINDOW
                    # 3. TEMPORAL_ORDER_VIOLATION
                    # 4. GAP_EXCEEDED
                    parent_path_id = (
                        admitted_paths[parent_state.path_idx].path_id
                        if parent_state.path_idx >= 0
                        else None
                    )

                    if any(cand.edge_id == e.edge_id for e in parent_state.edges):
                        record_exclusion(parent_path_id, d, cand.edge_id, "EDGE_ALREADY_IN_PATH")
                        continue

                    cand_time_utc = cand.event_time.astimezone(UTC)
                    if not (window_start_utc <= cand_time_utc <= window_end_utc):
                        record_exclusion(parent_path_id, d, cand.edge_id, "OUTSIDE_WINDOW")
                        continue

                    # Temporal order check
                    if parent_state.edges:
                        if d == "forward":
                            prev_time = parent_state.edges[-1].event_time.astimezone(UTC)
                            if cand_time_utc < prev_time:
                                record_exclusion(
                                    parent_path_id, d, cand.edge_id, "TEMPORAL_ORDER_VIOLATION"
                                )
                                continue
                            delta_usec = duration_microseconds(cand_time_utc - prev_time)
                        else:
                            prev_time = parent_state.edges[0].event_time.astimezone(UTC)
                            if cand_time_utc > prev_time:
                                record_exclusion(
                                    parent_path_id, d, cand.edge_id, "TEMPORAL_ORDER_VIOLATION"
                                )
                                continue
                            delta_usec = duration_microseconds(prev_time - cand_time_utc)

                        if (
                            request.max_gap_microseconds is not None
                            and delta_usec > request.max_gap_microseconds
                        ):
                            record_exclusion(parent_path_id, d, cand.edge_id, "GAP_EXCEEDED")
                            continue

                    # Form new path sequence
                    if d == "forward":
                        new_edges = parent_state.edges + (cand,)
                        next_endpoint = cand.target_id
                        counterparty_first_hop = cand.target_id
                    else:
                        new_edges = (cand,) + parent_state.edges
                        next_endpoint = cand.source_id
                        counterparty_first_hop = cand.source_id

                    new_edge_ids = tuple(e.edge_id for e in new_edges)
                    path_sig = (d, new_edge_ids)

                    # Deduplication: identical (direction, chronological edge_ids)
                    if path_sig in seen_path_signatures:
                        continue

                    # Check budget violations before admission
                    violates_edge = (cand.edge_id not in admitted_edge_ids) and (
                        len(admitted_edge_ids) + 1 > request.max_edges
                    )
                    violates_path = len(admitted_paths) + 1 > MAX_PATH_STATES

                    if violates_edge or violates_path:
                        if violates_edge:
                            stop_reasons_set.add("EDGE_BUDGET")
                        if violates_path:
                            stop_reasons_set.add("PATH_BUDGET")
                        # Do not admit
                        continue

                    # Successful admission!
                    parent_state.has_admitted_child = True
                    seen_path_signatures.add(path_sig)
                    admitted_edge_ids.add(cand.edge_id)

                    # Determine root branch
                    if parent_state.root_branch is not None:
                        branch = parent_state.root_branch
                    else:
                        branch = RootBranch(direction=d, counterparty_id=counterparty_first_hop)
                    covered_root_branches.add(branch)

                    # Cycle detection: returns to any account already in path
                    closes_cycle = next_endpoint in parent_state.accounts
                    new_accounts = parent_state.accounts | {next_endpoint}

                    new_steps = _compute_steps(
                        edges=new_edges,
                        direction=d,
                        seed_kind=seed_kind,
                        anchor_id=anchor_id,
                        max_gap_usec=request.max_gap_microseconds,
                    )

                    term_reason: TerminalReason | None = None
                    if closes_cycle:
                        term_reason = "CYCLE_CLOSED"
                    elif len(new_edges) == request.max_hops:
                        # At max_hops: check incident edges
                        incidents = snapshot.get_incident_edge_count(next_endpoint, d)
                        if incidents > 0:
                            term_reason = "HOP_LIMIT"
                            stop_reasons_set.add("HOP_LIMIT")
                        else:
                            term_reason = "DEAD_END"

                    path_id = compute_sha256_hex({"direction": d, "edge_ids": list(new_edge_ids)})
                    admitted_tp = TracePath(
                        path_id=path_id,
                        direction=d,
                        edge_ids=new_edge_ids,
                        steps=new_steps,
                        terminal_reason=term_reason,
                    )
                    admitted_paths.append(admitted_tp)
                    new_path_idx = len(admitted_paths) - 1

                    # If not terminal and not at max_hops, prepare for next layer
                    if term_reason is None and len(new_edges) < request.max_hops:
                        child_iterator = _CandidateIterator(snapshot, next_endpoint, d)
                        child_state = _ActivePathState(
                            direction=d,
                            edges=new_edges,
                            endpoint=next_endpoint,
                            accounts=new_accounts,
                            root_branch=branch,
                            path_idx=new_path_idx,
                            iterator=child_iterator,
                        )
                        b_key = branch.counterparty_id
                        if b_key not in next_layer_states[d]:
                            next_layer_states[d][b_key] = []
                        next_layer_states[d][b_key].append(child_state)

            active_dirs = [
                d
                for d in ("backward", "forward")
                if d in directions_to_run
                and any(
                    any(not s.is_exhausted for s in current_layer_states[d].get(b, []))
                    for b in branch_order[d]
                )
            ]

        current_layer_states = next_layer_states
        current_hop += 1

    # Check unexamined states for WORK_BUDGET
    if examined_transitions >= MAX_EXAMINED_TRANSITIONS:
        stop_reasons_set.add("WORK_BUDGET")

    # Determine final status and ordered stop reasons
    ordered_stop_reasons = tuple(r for r in STOP_REASONS_ORDER if r in stop_reasons_set)
    status: ResultStatus = "TRUNCATED" if ordered_stop_reasons else "EXHAUSTED_WITHIN_LIMITS"

    # Lexically sort edges and their corresponding transactions
    sorted_edge_ids = tuple(sorted(admitted_edge_ids))
    sorted_transactions = tuple(
        snapshot.get_event(eid) for eid in sorted_edge_ids if snapshot.get_event(eid) is not None
    )

    # Sort root branches: direction (backward then forward) then counterparty_id
    sorted_branches = tuple(
        sorted(
            covered_root_branches,
            key=lambda b: (0 if b.direction == "backward" else 1, b.counterparty_id),
        )
    )

    return TraceResult(
        edge_ids=sorted_edge_ids,
        transactions=sorted_transactions,
        paths=tuple(admitted_paths),
        excluded_transition_counts=exclusion_counts,
        excluded_transition_examples=tuple(exclusion_examples),
        exclusion_examples_truncated=exclusion_examples_truncated,
        examined_transitions=examined_transitions,
        admitted_path_states=len(admitted_paths),
        returned_root_branches=sorted_branches,
        status=status,
        stop_reasons=ordered_stop_reasons,
    )
