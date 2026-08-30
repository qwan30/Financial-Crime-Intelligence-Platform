from __future__ import annotations

from enum import StrEnum
from hashlib import sha256
from pathlib import Path
from typing import Annotated

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    HttpUrl,
    StrictInt,
    StringConstraints,
)

NonBlankId = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TraceLabel(StrEnum):
    RELEVANT = "RELEVANT"
    CONFIRMED_BENIGN = "CONFIRMED_BENIGN"
    UNKNOWN = "UNKNOWN"


class DatasetManifest(FrozenModel):
    dataset_id: NonBlankId
    source_url: HttpUrl
    license: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: AwareDatetime


class TraceEdge(FrozenModel):
    edge_id: NonBlankId
    source_id: NonBlankId
    target_id: NonBlankId
    event_time: AwareDatetime
    label: TraceLabel


class TraceGoldManifest(FrozenModel):
    dataset_id: NonBlankId
    generator_version: str
    generator_seed: StrictInt
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_id: NonBlankId
    typology: str
    edges: tuple[TraceEdge, ...]
    mandatory_anchors: tuple[NonBlankId, ...]
    visibility_boundary_ids: tuple[NonBlankId, ...] = ()


class SplitManifest(FrozenModel):
    train_case_ids: tuple[NonBlankId, ...]
    validation_case_ids: tuple[NonBlankId, ...]
    calibration_case_ids: tuple[NonBlankId, ...]
    temporal_test_case_ids: tuple[NonBlankId, ...]
    heldout_typology_case_ids: tuple[NonBlankId, ...]
    unseen_generator_case_ids: tuple[NonBlankId, ...]


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
