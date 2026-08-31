from __future__ import annotations

import math
from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_validator

from fincrime.contracts.manifests import NonBlankId


class TransactionEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    edge_id: NonBlankId
    source_id: NonBlankId
    target_id: NonBlankId
    amount: float
    event_time: datetime

    @field_validator("amount", mode="after")
    @classmethod
    def _validate_amount(cls, v: float) -> float:
        if not math.isfinite(v) or v <= 0:
            raise ValueError(f"amount must be a finite positive number, got {v}")
        return v

    @field_validator("event_time", mode="after")
    @classmethod
    def _validate_event_time(cls, v: datetime) -> datetime:
        if not isinstance(v, datetime):
            raise TypeError(f"event_time must be a datetime object, got {type(v).__name__}")
        if v.tzinfo is None or v.tzinfo.utcoffset(v) is None:
            raise ValueError("event_time must be timezone-aware")
        return v

    def __init__(
        self,
        edge_id: str | None = None,
        source_id: str | None = None,
        target_id: str | None = None,
        amount: float | None = None,
        event_time: datetime | None = None,
        **data: object,
    ) -> None:
        if edge_id is not None:
            data["edge_id"] = edge_id
        if source_id is not None:
            data["source_id"] = source_id
        if target_id is not None:
            data["target_id"] = target_id
        if amount is not None:
            data["amount"] = amount
        if event_time is not None:
            data["event_time"] = event_time
        super().__init__(**data)
