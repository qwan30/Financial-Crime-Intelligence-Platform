from __future__ import annotations

from datetime import UTC, datetime
import json
import uuid

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import insert, select
from sqlalchemy.engine import Connection, Engine

from fincrime.agent.tools import ReferentialIntegrityError, TraceEdge, TypologyTag
from fincrime.cases.canvas import SnapshotConflict
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseNotFound
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    canonical_json_bytes,
    compute_sha256_hex,
)
from fincrime.storage.postgres import (
    case_evidence,
    case_snapshots,
    cases,
    evidence_items,
    graph_edges,
    graph_nodes,
    put_evidence,
)


class EdgeNotInCase(Exception):
    pass


class PersistenceUnavailable(Exception):
    pass


class PinCommand(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str = Field(min_length=1, max_length=128)
    analyst_id: str = Field(min_length=1, max_length=128)
    is_pinned: bool = Field(strict=True)
    typology_tag: TypologyTag | None = None


class PinnedTransaction(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str
    evidence_id: str
    analyst_id: str
    typology_tag: TypologyTag | None
    updated_at: datetime
    transaction: TraceEdge


class PinnedCase(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    case: CaseSnapshot
    evidence: tuple[EvidenceItem, ...]
    pins: tuple[PinnedTransaction, ...]


class PinningService:
    def __init__(self, engine: Engine) -> None:
        self._engine = engine

    def _load_pinned_case(self, conn: Connection, current_case: CaseSnapshot) -> PinnedCase:
        # Load all evidence in current_case.evidence_ids
        ev_stmt = select(evidence_items).where(evidence_items.c.evidence_id.in_(current_case.evidence_ids))
        ev_rows = conn.execute(ev_stmt).all()
        ev_map = {row.evidence_id: EvidenceItem.model_validate_json(json.dumps(row.payload)) for row in ev_rows}
        evidence_list = [ev_map[eid] for eid in current_case.evidence_ids if eid in ev_map]

        # Load active pins
        pin_stmt = select(case_evidence).where(
            case_evidence.c.case_id == current_case.case_id,
            case_evidence.c.is_pinned == True,  # noqa: E712
        )
        pin_rows = conn.execute(pin_stmt).all()

        pins: list[PinnedTransaction] = []
        if pin_rows:
            edge_ids = [r.edge_id for r in pin_rows]
            edge_stmt = select(graph_edges).where(graph_edges.c.edge_id.in_(edge_ids))
            edge_rows = conn.execute(edge_stmt).all()
            edge_map = {r.edge_id: TraceEdge.model_validate_json(json.dumps(r.payload)) for r in edge_rows}

            for r in pin_rows:
                if r.edge_id in edge_map:
                    pins.append(
                        PinnedTransaction(
                            edge_id=r.edge_id,
                            evidence_id=r.evidence_id,
                            analyst_id=r.analyst_id,
                            typology_tag=r.typology_tag,
                            updated_at=r.updated_at,
                            transaction=edge_map[r.edge_id],
                        )
                    )
        pins.sort(key=lambda p: p.edge_id)

        return PinnedCase(
            case=current_case,
            evidence=tuple(evidence_list),
            pins=tuple(pins),
        )

    def read(self, case_id: str) -> PinnedCase:
        with self._engine.connect() as conn:
            stmt = select(cases).where(cases.c.case_id == case_id).with_for_update(read=True)
            row = conn.execute(stmt).first()
            if row is None:
                raise CaseNotFound(f"Case '{case_id}' not found.")
            current_case = CaseSnapshot.model_validate_json(json.dumps(row.payload))
            return self._load_pinned_case(conn, current_case)

    def set_pin(self, case_id: str, command: PinCommand, expected_snapshot_hash: str) -> PinnedCase:
        with self._engine.begin() as conn:
            # 1. Lock case row
            stmt = select(cases).where(cases.c.case_id == case_id).with_for_update()
            case_row = conn.execute(stmt).first()
            if case_row is None:
                raise CaseNotFound(f"Case '{case_id}' not found.")

            current_case = CaseSnapshot.model_validate_json(json.dumps(case_row.payload))
            if current_case.snapshot_hash != expected_snapshot_hash:
                raise SnapshotConflict(
                    f"Snapshot conflict: expected {current_case.snapshot_hash}, got {expected_snapshot_hash}"
                )

            if command.edge_id not in current_case.trace_edge_ids:
                raise EdgeNotInCase(f"Edge '{command.edge_id}' not in case '{case_id}'")

            # Load source edge and endpoints
            edge_stmt = select(graph_edges).where(graph_edges.c.edge_id == command.edge_id)
            edge_row = conn.execute(edge_stmt).first()
            if edge_row is None:
                raise ReferentialIntegrityError(f"Edge '{command.edge_id}' not found in graph edges")
            edge = TraceEdge.model_validate_json(json.dumps(edge_row.payload))

            s_stmt = select(graph_nodes).where(graph_nodes.c.node_id == edge.source)
            t_stmt = select(graph_nodes).where(graph_nodes.c.node_id == edge.target)
            if conn.execute(s_stmt).first() is None or conn.execute(t_stmt).first() is None:
                raise ReferentialIntegrityError(f"Edge '{command.edge_id}' references missing endpoint node")

            # 2. Check current pin state
            pin_stmt = select(case_evidence).where(
                case_evidence.c.case_id == case_id,
                case_evidence.c.edge_id == command.edge_id,
            )
            existing_pin = conn.execute(pin_stmt).first()

            if existing_pin is not None and existing_pin.is_pinned == command.is_pinned and existing_pin.typology_tag == command.typology_tag:
                return self._load_pinned_case(conn, current_case)
            if existing_pin is None and not command.is_pinned:
                return self._load_pinned_case(conn, current_case)

            now_utc = datetime.now(UTC)

            # 3. Create or reuse observed transaction evidence on pin
            if command.is_pinned:
                raw_key = {"case_id": case_id, "edge_id": command.edge_id}
                obs_id = "ev:txn:" + compute_sha256_hex(raw_key)
                existing_obs = conn.execute(
                    select(evidence_items).where(evidence_items.c.evidence_id == obs_id)
                ).first()
                if existing_obs is None:
                    obs_snap_time = edge.timestamp if edge.timestamp is not None else now_utc
                    raw_obs = {
                        "evidence_id": obs_id,
                        "category": EvidenceCategory.OBSERVED,
                        "source_reference": f"edge:{command.edge_id}",
                        "polarity": EvidencePolarity.UNKNOWN,
                        "snapshot_time": obs_snap_time,
                        "generation_method_version": "forensic-canvas-transaction-v1",
                        "confidence": None,
                        "payload_summary": canonical_json_bytes(edge.model_dump(mode="json")).decode("utf-8"),
                    }
                    obs_hash = compute_sha256_hex(raw_obs)
                    obs_item = EvidenceItem(**raw_obs, integrity_hash=obs_hash)
                    put_evidence(conn, obs_item)
                pin_ev_id = obs_id
            else:
                pin_ev_id = existing_pin.evidence_id if existing_pin else ("ev:txn:" + compute_sha256_hex({"case_id": case_id, "edge_id": command.edge_id}))

            # 4. Create immutable action EvidenceItem
            act_id = "ev:pin:" + uuid.uuid4().hex
            action_payload = {
                "analyst_id": command.analyst_id,
                "edge_id": command.edge_id,
                "is_pinned": command.is_pinned,
                "previous_snapshot_hash": expected_snapshot_hash,
                "typology_tag": command.typology_tag,
            }
            raw_act = {
                "evidence_id": act_id,
                "category": EvidenceCategory.ANALYST,
                "source_reference": f"edge:{command.edge_id}",
                "polarity": EvidencePolarity.UNKNOWN,
                "snapshot_time": now_utc,
                "generation_method_version": "forensic-canvas-pin-v1",
                "confidence": None,
                "payload_summary": json.dumps(action_payload, sort_keys=True),
            }
            act_hash = compute_sha256_hex(raw_act)
            act_item = EvidenceItem(**raw_act, integrity_hash=act_hash)
            put_evidence(conn, act_item)

            # 5. Create new CaseSnapshot
            new_evidence_ids = set(current_case.evidence_ids)
            if command.is_pinned:
                new_evidence_ids.add(pin_ev_id)
            new_evidence_ids.add(act_id)

            new_case = CaseSnapshot.create_new(
                case_id=current_case.case_id,
                seed_entity=current_case.seed_entity,
                evidence_ids=tuple(sorted(new_evidence_ids)),
                trace_edge_ids=current_case.trace_edge_ids,
                created_at=current_case.created_at,
            )
            new_case_bytes = canonical_json_bytes(new_case.model_dump(mode="python", by_alias=False))

            conn.execute(
                insert(case_snapshots).values(
                    case_id=new_case.case_id,
                    snapshot_hash=new_case.snapshot_hash,
                    payload=new_case.model_dump(mode="json"),
                    canonical_bytes=new_case_bytes,
                )
            )
            conn.execute(
                cases.update().where(cases.c.case_id == new_case.case_id).values(
                    payload=new_case.model_dump(mode="json"),
                    canonical_bytes=new_case_bytes,
                )
            )

            # Upsert pin association
            if existing_pin is None:
                conn.execute(
                    insert(case_evidence).values(
                        case_id=case_id,
                        edge_id=command.edge_id,
                        evidence_id=pin_ev_id,
                        is_pinned=command.is_pinned,
                        typology_tag=command.typology_tag,
                        analyst_id=command.analyst_id,
                        updated_at=now_utc,
                    )
                )
            else:
                conn.execute(
                    case_evidence.update().where(
                        case_evidence.c.case_id == case_id,
                        case_evidence.c.edge_id == command.edge_id,
                    ).values(
                        is_pinned=command.is_pinned,
                        typology_tag=command.typology_tag,
                        analyst_id=command.analyst_id,
                        updated_at=now_utc,
                    )
                )

            return self._load_pinned_case(conn, new_case)
