from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.cli import main
from fincrime.training.runner import (
    STAGE_ORDER,
    TrainingRunState,
    TrainingStage,
    write_run_artifact,
)


def test_run_artifact_refuses_overwrite(tmp_path: Path) -> None:
    target = tmp_path / "run-manifest.json"
    write_run_artifact(target, {"run_id": "r1"})
    with pytest.raises(FileExistsError):
        write_run_artifact(target, {"run_id": "r2"})


def test_run_artifact_writes_valid_json(tmp_path: Path) -> None:
    target = tmp_path / "subdir" / "artifact.json"
    write_run_artifact(target, {"run_id": "r1", "seeds": [11, 23]})
    assert target.is_file()
    with target.open("r", encoding="utf-8") as f:
        data = json.load(f)
    assert data == {"run_id": "r1", "seeds": [11, 23]}


def test_training_stages_cannot_skip_stages() -> None:
    state = TrainingRunState(stage=TrainingStage.PREREGISTERED)
    with pytest.raises(ValueError, match="expected DATA_VERIFIED"):
        state.advance(TrainingStage.FROZEN)


def test_training_stages_advance_sequentially() -> None:
    state = TrainingRunState(stage=TrainingStage.PREREGISTERED)
    for next_stage in STAGE_ORDER[1:]:
        state = state.advance(next_stage)
    assert state.stage == TrainingStage.DECIDED


def test_terminal_stage_cannot_advance() -> None:
    state = TrainingRunState(stage=TrainingStage.DECIDED)
    with pytest.raises(ValueError, match="terminal"):
        state.advance(TrainingStage.PREREGISTERED)


def test_training_run_state_immutability() -> None:
    state = TrainingRunState(stage=TrainingStage.PREREGISTERED)
    with pytest.raises(ValidationError):
        state.stage = TrainingStage.FROZEN  # type: ignore[misc]


def test_write_run_artifact_rejects_non_serializable(tmp_path: Path) -> None:
    target = tmp_path / "invalid.json"
    with pytest.raises((TypeError, ValueError)):
        write_run_artifact(target, {"invalid": object()})
    assert not target.exists()


def test_cli_write_run_artifact(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "smoke" / "run-manifest.json"
    monkeypatch.setattr(
        "sys.argv",
        ["fincrime", "write-run-artifact", "--path", str(target), "--run-id", "smoke-test"],
    )
    exit_code = main()
    assert exit_code == 0
    assert target.is_file()
    with target.open("r", encoding="utf-8") as f:
        payload = json.load(f)
    assert payload == {"run_id": "smoke-test"}
