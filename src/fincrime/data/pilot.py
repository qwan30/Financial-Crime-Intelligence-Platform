from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict

from fincrime.data.capacity import CapacityDecision, capacity_decision
from fincrime.data.provenance import DerivedArtifactManifest, NonBlank, SourceManifest


class PilotEvidence(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonBlank
    capacity: CapacityDecision
    verdict: Literal["detection_only"] = "detection_only"
    source_manifest: SourceManifest | None = None
    derived_manifest: DerivedArtifactManifest | None = None


def pilot_admission(
    source_id: str,
    disk_free_bytes: int,
    archive_bytes: int,
    extraction_bytes: int,
    processed_bytes: int,
    temporary_bytes: int,
    safety_headroom_bytes: int = 0,
    *,
    source_manifest: SourceManifest | None = None,
    derived_manifest: DerivedArtifactManifest | None = None,
) -> PilotEvidence:
    cap = capacity_decision(
        disk_free_bytes=disk_free_bytes,
        archive_bytes=archive_bytes,
        extraction_bytes=extraction_bytes,
        processed_bytes=processed_bytes,
        temporary_bytes=temporary_bytes,
        safety_headroom_bytes=safety_headroom_bytes,
    )
    return PilotEvidence(
        source_id=source_id,
        capacity=cap,
        verdict="detection_only",
        source_manifest=source_manifest,
        derived_manifest=derived_manifest,
    )
