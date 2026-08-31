from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from fincrime.contracts.manifests import NonBlankId


class TransactionEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: NonBlankId
    source_id: NonBlankId
    target_id: NonBlankId
    amount: float = Field(gt=0)
    event_time: datetime

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
