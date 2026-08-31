from __future__ import annotations

import pytest
from pydantic import ValidationError

from fincrime.training.advanced_gate import (
    AdvancedModelDecision,
    advanced_model_decision,
)


def test_no_graphsage_gain_records_justified_null() -> None:
    result = advanced_model_decision(False, -0.01, True, 0.0, 0.0)
    assert result.next_family == "JUSTIFIED_NULL"
    assert "GraphSAGE did not beat" in result.reason


def test_zero_graphsage_gain_records_justified_null() -> None:
    result = advanced_model_decision(True, 0.0, True, 0.0, 0.0)
    assert result.next_family == "JUSTIFIED_NULL"
    assert "GraphSAGE did not beat" in result.reason


def test_real_heterogeneity_opens_hgt_only_after_graphsage_gain() -> None:
    result = advanced_model_decision(True, 0.04, False, 0.0, 0.0)
    assert result.next_family == "hgt"
    assert "heterogeneous" in result.reason


def test_temporal_gap_opens_tgn_only_after_graphsage_gain() -> None:
    result = advanced_model_decision(False, 0.04, True, 0.0, 0.0)
    assert result.next_family == "tgn"
    assert "temporal" in result.reason


def test_both_passed_opens_hybrid() -> None:
    result = advanced_model_decision(False, 0.04, False, 0.02, 0.03)
    assert result.next_family == "hybrid"
    assert "both passed" in result.reason


def test_no_advanced_hypothesis_passed_records_justified_null() -> None:
    # GraphSAGE passed, but not heterogeneous, no temporal gap, and only one of HGT/TGN passed
    result = advanced_model_decision(False, 0.04, False, 0.02, -0.01)
    assert result.next_family == "JUSTIFIED_NULL"
    assert "no advanced hypothesis passed" in result.reason


def test_advanced_model_decision_immutability() -> None:
    decision = AdvancedModelDecision(
        next_family="hgt", reason="real heterogeneous ontology"
    )
    with pytest.raises(ValidationError):
        decision.next_family = "tgn"  # type: ignore[misc]


@pytest.mark.parametrize("bad_bool", [1, 0, "true", "false", None, [True]])
def test_invalid_bool_types_fail_validation(bad_bool: object) -> None:
    with pytest.raises(TypeError, match="bool|boolean"):
        advanced_model_decision(bad_bool, 0.04, False, 0.0, 0.0)  # type: ignore[arg-type]
    with pytest.raises(TypeError, match="bool|boolean"):
        advanced_model_decision(True, 0.04, bad_bool, 0.0, 0.0)  # type: ignore[arg-type]


@pytest.mark.parametrize("bad_delta", [float("nan"), float("inf"), float("-inf"), True, False, "0.04", None])
def test_invalid_delta_values_fail_validation(bad_delta: object) -> None:
    with pytest.raises((ValueError, TypeError), match="finite|numeric|float|delta"):
        advanced_model_decision(True, bad_delta, False, 0.0, 0.0)  # type: ignore[arg-type]
    with pytest.raises((ValueError, TypeError), match="finite|numeric|float|delta"):
        advanced_model_decision(True, 0.04, False, bad_delta, 0.0)  # type: ignore[arg-type]
    with pytest.raises((ValueError, TypeError), match="finite|numeric|float|delta"):
        advanced_model_decision(True, 0.04, False, 0.0, bad_delta)  # type: ignore[arg-type]
