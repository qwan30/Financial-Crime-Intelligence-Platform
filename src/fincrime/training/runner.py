from __future__ import annotations

import json
from collections.abc import Mapping
from enum import StrEnum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ConfigDict


class TrainingStage(StrEnum):
    PREREGISTERED = "PREREGISTERED"
    DATA_VERIFIED = "DATA_VERIFIED"
    FITTED = "FITTED"
    VALIDATED = "VALIDATED"
    CALIBRATED = "CALIBRATED"
    FROZEN = "FROZEN"
    TESTED = "TESTED"
    TRACE_EVALUATED = "TRACE_EVALUATED"
    DECIDED = "DECIDED"


STAGE_ORDER = tuple(TrainingStage)


class TrainingRunState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    stage: TrainingStage

    def advance(self, next_stage: TrainingStage) -> TrainingRunState:
        if not isinstance(next_stage, TrainingStage):
            raise TypeError(f"next_stage must be a TrainingStage, got {type(next_stage).__name__}")
        current_index = STAGE_ORDER.index(self.stage)
        if current_index >= len(STAGE_ORDER) - 1:
            raise ValueError(f"cannot advance from terminal stage {self.stage.value}")
        expected = STAGE_ORDER[current_index + 1]
        if next_stage is not expected:
            raise ValueError(f"expected {expected.value}, got {next_stage.value}")
        return self.model_copy(update={"stage": next_stage})


def write_run_artifact(
    path: Path | str, payload: Mapping[str, Any] | BaseModel | dict[str, Any]
) -> None:
    """Write append-only atomic JSON artifact, refusing overwrite."""
    target_path = Path(path)
    target_path.parent.mkdir(parents=True, exist_ok=True)

    if isinstance(payload, BaseModel):
        data_to_write = payload.model_dump(mode="json")
    elif isinstance(payload, Mapping):
        try:
            data_to_write = json.loads(json.dumps(payload))
        except (TypeError, ValueError) as err:
            raise TypeError(f"Payload is not JSON serializable: {err}") from err
    else:
        raise TypeError(f"payload must be a dict or BaseModel, got {type(payload).__name__}")

    with target_path.open("x", encoding="utf-8") as target:
        json.dump(data_to_write, target, indent=2, sort_keys=True)
        target.write("\n")
