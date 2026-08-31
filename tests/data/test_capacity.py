from __future__ import annotations

import pytest
from pydantic import ValidationError

from fincrime.data.capacity import CapacityDecision, capacity_decision


def test_capacity_decision_skips_oversized_archive_before_download() -> None:
    result = capacity_decision(
        disk_free_bytes=9_000,
        archive_bytes=7_000,
        extraction_bytes=7_000,
        processed_bytes=2_000,
        temporary_bytes=1_000,
        safety_headroom_bytes=1_000,
    )
    assert result.status == "SKIPPED_BY_RESOURCE"
    assert result.required_bytes == 18_000
    assert result.available_bytes == 9_000


def test_capacity_decision_ready_when_capacity_sufficient() -> None:
    result = capacity_decision(
        disk_free_bytes=20_000,
        archive_bytes=7_000,
        extraction_bytes=7_000,
        processed_bytes=2_000,
        temporary_bytes=1_000,
        safety_headroom_bytes=1_000,
    )
    assert result.status == "READY"
    assert result.required_bytes == 18_000
    assert result.available_bytes == 20_000


def test_capacity_decision_ready_at_exact_boundary() -> None:
    result = capacity_decision(
        disk_free_bytes=18_000,
        archive_bytes=7_000,
        extraction_bytes=7_000,
        processed_bytes=2_000,
        temporary_bytes=1_000,
        safety_headroom_bytes=1_000,
    )
    assert result.status == "READY"
    assert result.required_bytes == 18_000
    assert result.available_bytes == 18_000


@pytest.mark.parametrize(
    "param_name",
    [
        "disk_free_bytes",
        "archive_bytes",
        "extraction_bytes",
        "processed_bytes",
        "temporary_bytes",
        "safety_headroom_bytes",
    ],
)
def test_capacity_decision_rejects_negative_inputs(param_name: str) -> None:
    kwargs = {
        "disk_free_bytes": 10_000,
        "archive_bytes": 1_000,
        "extraction_bytes": 1_000,
        "processed_bytes": 1_000,
        "temporary_bytes": 1_000,
        "safety_headroom_bytes": 1_000,
    }
    kwargs[param_name] = -1
    with pytest.raises(ValueError, match="capacity values must be non-negative"):
        capacity_decision(**kwargs)


def test_capacity_decision_immutability() -> None:
    decision = CapacityDecision(
        status="READY",
        required_bytes=100,
        available_bytes=200,
    )
    with pytest.raises(ValidationError):
        decision.status = "SKIPPED_BY_RESOURCE"  # type: ignore[misc]
