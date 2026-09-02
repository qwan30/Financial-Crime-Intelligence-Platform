from __future__ import annotations

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from fincrime.evidence.models import compute_sha256_hex


class Disposition(StrEnum):
    CONFIRMED_SUSPICIOUS = "CONFIRMED_SUSPICIOUS"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ESCALATE = "ESCALATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class AdjudicationStatus(StrEnum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"


class CaseSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    case_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-:]+$")
    seed_entity: str = Field(min_length=1)
    evidence_ids: tuple[str, ...] = Field(default=())
    trace_edge_ids: tuple[str, ...] = Field(default=())
    created_at: datetime
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("created_at must be a timezone-aware UTC datetime")
        return v

    @field_validator("evidence_ids", "trace_edge_ids")
    @classmethod
    def validate_sorted_unique_ids(cls, v: tuple[str, ...], info: Any) -> tuple[str, ...]:
        field = info.field_name
        if len(v) != len(set(v)):
            raise ValueError(f"{field} must be unique")
        if v != tuple(sorted(v)):
            raise ValueError(f"{field} must be sorted")
        return v

    @field_validator("snapshot_hash")
    @classmethod
    def validate_hash(cls, v: str, info: Any) -> str:
        data = info.data
        if "case_id" in data and "seed_entity" in data and "created_at" in data:
            raw_dict = {
                "case_id": data["case_id"],
                "seed_entity": data["seed_entity"],
                "evidence_ids": data.get("evidence_ids", ()),
                "trace_edge_ids": data.get("trace_edge_ids", ()),
                "created_at": data["created_at"],
            }
            computed = compute_sha256_hex(raw_dict)
            if v != computed:
                raise ValueError(f"Snapshot hash mismatch: expected {computed}, got {v}")
        return v

    @classmethod
    def create_new(
        cls,
        case_id: str,
        seed_entity: str,
        evidence_ids: tuple[str, ...] = (),
        trace_edge_ids: tuple[str, ...] = (),
        created_at: datetime | None = None,
    ) -> CaseSnapshot:
        dt = created_at or datetime.now(UTC)
        sorted_ev = tuple(sorted(set(evidence_ids)))
        sorted_edges = tuple(sorted(set(trace_edge_ids)))
        raw_dict = {
            "case_id": case_id,
            "seed_entity": seed_entity,
            "evidence_ids": sorted_ev,
            "trace_edge_ids": sorted_edges,
            "created_at": dt,
        }
        h = compute_sha256_hex(raw_dict)
        return cls(
            case_id=case_id,
            seed_entity=seed_entity,
            evidence_ids=sorted_ev,
            trace_edge_ids=sorted_edges,
            created_at=dt,
            snapshot_hash=h,
        )


class AnalystFeedbackEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    event_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-:]+$")
    analyst_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    disposition: Disposition
    reason: str = Field(min_length=1)
    created_at: datetime
    model_version: str | None = None
    snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    adjudication_status: AdjudicationStatus = AdjudicationStatus.PENDING

    @field_validator("created_at")
    @classmethod
    def validate_timezone(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("created_at must be a timezone-aware UTC datetime")
        return v

    @classmethod
    def create_new(
        cls,
        event_id: str,
        analyst_id: str,
        case_id: str,
        disposition: Disposition,
        reason: str,
        snapshot_hash: str,
        model_version: str | None = None,
        adjudication_status: AdjudicationStatus = AdjudicationStatus.PENDING,
        created_at: datetime | None = None,
    ) -> AnalystFeedbackEvent:
        dt = created_at or datetime.now(UTC)
        return cls(
            event_id=event_id,
            analyst_id=analyst_id,
            case_id=case_id,
            disposition=disposition,
            reason=reason,
            created_at=dt,
            model_version=model_version,
            snapshot_hash=snapshot_hash,
            adjudication_status=adjudication_status,
        )
