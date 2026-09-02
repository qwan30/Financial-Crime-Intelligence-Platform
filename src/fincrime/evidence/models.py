from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from enum import Enum, StrEnum
from typing import Any, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


def normalize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        if val.tzinfo is None or val.utcoffset() is None:
            raise ValueError("Naive datetime is prohibited; timezone required")
        utc_dt = val.astimezone(UTC)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, (list, tuple)):
        return [normalize_value(x) for x in val]
    if isinstance(val, dict):
        return {k: normalize_value(v) for k, v in val.items()}
    return val


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    normalized = normalize_value(data)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_sha256_hex(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()


class EvidenceCategory(StrEnum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    RULE = "RULE"
    MODEL = "MODEL"
    TRACE = "TRACE"
    ANALYST = "ANALYST"


class EvidencePolarity(StrEnum):
    SUPPORTING = "SUPPORTING"
    MITIGATING = "MITIGATING"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    evidence_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-:]+$")
    category: EvidenceCategory
    source_reference: str = Field(min_length=1)
    polarity: EvidencePolarity
    snapshot_time: datetime
    generation_method_version: str = Field(min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    payload_summary: str = Field(min_length=1)
    integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def validate_integrity_hash_and_timezone(self) -> Self:
        if self.snapshot_time.tzinfo is None or self.snapshot_time.utcoffset() is None:
            raise ValueError("Naive datetime is prohibited; timezone required")
        dumped = self.model_dump(mode="python", by_alias=False, exclude={"integrity_hash"})
        expected = compute_sha256_hex(dumped)
        if self.integrity_hash != expected:
            raise ValueError(
                f"Integrity hash mismatch: expected {expected}, got {self.integrity_hash}"
            )
        return self
