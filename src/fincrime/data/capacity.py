from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class CapacityDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    status: Literal["READY", "SKIPPED_BY_RESOURCE"]
    required_bytes: int = Field(ge=0)
    available_bytes: int = Field(ge=0)


def capacity_decision(
    *,
    disk_free_bytes: int,
    archive_bytes: int,
    extraction_bytes: int,
    processed_bytes: int,
    temporary_bytes: int,
    safety_headroom_bytes: int,
) -> CapacityDecision:
    values = (
        disk_free_bytes,
        archive_bytes,
        extraction_bytes,
        processed_bytes,
        temporary_bytes,
        safety_headroom_bytes,
    )
    if any(value < 0 for value in values):
        raise ValueError("capacity values must be non-negative")
    required = (
        archive_bytes
        + extraction_bytes
        + processed_bytes
        + temporary_bytes
        + safety_headroom_bytes
    )
    return CapacityDecision(
        status="READY" if disk_free_bytes >= required else "SKIPPED_BY_RESOURCE",
        required_bytes=required,
        available_bytes=disk_free_bytes,
    )
