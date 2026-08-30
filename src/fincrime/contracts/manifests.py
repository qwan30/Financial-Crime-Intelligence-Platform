from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from hashlib import sha256
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, HttpUrl


class FrozenModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")


class TraceLabel(StrEnum):
    RELEVANT = "RELEVANT"
    CONFIRMED_BENIGN = "CONFIRMED_BENIGN"
    UNKNOWN = "UNKNOWN"


class DatasetManifest(FrozenModel):
    dataset_id: str = Field(min_length=1)
    source_url: HttpUrl
    license: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    schema_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    created_at: datetime


class TraceEdge(FrozenModel):
    edge_id: str
    source_id: str
    target_id: str
    event_time: datetime
    label: TraceLabel


class TraceGoldManifest(FrozenModel):
    dataset_id: str
    generator_version: str
    generator_seed: int
    configuration_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    case_id: str
    typology: str
    edges: tuple[TraceEdge, ...]
    mandatory_anchors: tuple[str, ...]
    visibility_boundary_ids: tuple[str, ...] = ()


class SplitManifest(FrozenModel):
    train_case_ids: tuple[str, ...]
    validation_case_ids: tuple[str, ...]
    calibration_case_ids: tuple[str, ...]
    temporal_test_case_ids: tuple[str, ...]
    heldout_typology_case_ids: tuple[str, ...]
    unseen_generator_case_ids: tuple[str, ...]


def sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()
