from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from fincrime.cli import main
from fincrime.data.pilot import PilotEvidence, pilot_admission


def test_insufficient_capacity_returns_detection_only_skipped_evidence() -> None:
    evidence = pilot_admission("amlbench-slice", 1, 9, 9, 1, 1)
    assert isinstance(evidence, PilotEvidence)
    assert evidence.capacity.status == "SKIPPED_BY_RESOURCE"
    assert evidence.verdict == "detection_only"
    assert evidence.source_id == "amlbench-slice"


def test_sufficient_capacity_returns_ready_evidence() -> None:
    evidence = pilot_admission("amlsim-sample", 100_000, 1_000, 1_000, 1_000, 1_000, 1_000)
    assert evidence.capacity.status == "READY"
    assert evidence.verdict == "detection_only"
    assert evidence.source_id == "amlsim-sample"


def test_pilot_evidence_immutability() -> None:
    evidence = pilot_admission("amlbench-slice", 1, 9, 9, 1, 1)
    with pytest.raises(ValidationError):
        evidence.verdict = "tracing_approved"  # type: ignore[misc]


def test_cli_pilot_admission_emits_valid_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        "sys.argv",
        [
            "fincrime",
            "pilot-admission",
            "--workspace",
            str(tmp_path),
            "--archive-bytes",
            "7560000000",
            "--extraction-bytes",
            "7560000000",
            "--processed-bytes",
            "2000000000",
            "--temporary-bytes",
            "1000000000",
            "--headroom-bytes",
            "1000000000",
        ],
    )
    exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["verdict"] == "detection_only"
    assert "capacity" in payload
    assert payload["capacity"]["required_bytes"] == 19120000000
