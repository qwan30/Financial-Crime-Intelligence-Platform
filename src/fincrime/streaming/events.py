from __future__ import annotations

import hashlib
import json
import math
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["1"]
    event_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-:]+$")
    source_partition: int = Field(ge=0)
    source_offset: int = Field(ge=0)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    amount: float = Field(gt=0.0)
    event_time: datetime

    @field_validator("source_id", "target_id")
    @classmethod
    def validate_non_blank_ids(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("ID fields must not be blank or whitespace-only")
        return v

    @field_validator("amount")
    @classmethod
    def validate_finite_amount(cls, v: float) -> float:
        if not math.isfinite(v) or v <= 0.0:
            raise ValueError(f"amount must be finite and positive, got {v}")
        return v

    @field_validator("event_time")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("event_time must be timezone-aware UTC")
        if v.utcoffset() != UTC.utcoffset(v):
            raise ValueError("event_time must be in UTC (+00:00)")
        if v.microsecond != 0:
            raise ValueError(
                "event_time microsecond must be 0 for exact second canonical precision"
            )
        return v

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "amount": self.amount,
            "event_id": self.event_id,
            "event_time": self.event_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "schema_version": self.schema_version,
            "source_id": self.source_id,
            "source_offset": self.source_offset,
            "source_partition": self.source_partition,
            "target_id": self.target_id,
        }

    def to_canonical_bytes(self) -> bytes:
        return json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.to_canonical_bytes()).hexdigest().lower()
