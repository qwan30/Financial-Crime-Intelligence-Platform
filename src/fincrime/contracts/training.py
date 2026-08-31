from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

RESEARCH_SEEDS: tuple[int, ...] = (11, 23, 37, 53, 71)


class TrainingRunSpec(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    hypothesis: str
    model_family: str
    dataset_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_manifest_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_schema_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    primary_metric: str
    alert_budget: int = Field(gt=0)
    search_trial_cap: int = Field(gt=0, le=50)
    random_seeds: tuple[int, ...] = RESEARCH_SEEDS


class ModelPackageManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str
    model_family: str
    artifact_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    selected: bool
    limitations: tuple[str, ...]
