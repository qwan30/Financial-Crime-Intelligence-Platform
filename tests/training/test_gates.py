from __future__ import annotations

import pytest
from pydantic import ValidationError

from fincrime.training.gates import PromotionDecision, promotion_decision


def test_failed_candidate_returns_null_selection() -> None:
    decision = promotion_decision(
        baseline_values=(0.7,) * 5, candidate_values=(0.69,) * 5
    )
    assert decision.selected_model is None
    assert decision.mean_delta == pytest.approx(-0.01)
    assert decision.ci_lower < 0


def test_successful_candidate_promoted() -> None:
    baseline = (0.70, 0.71, 0.72, 0.69, 0.70)
    candidate = (0.78, 0.79, 0.80, 0.77, 0.79)
    decision = promotion_decision(baseline, candidate)
    assert decision.selected_model == "candidate"
    assert decision.mean_delta > 0
    assert decision.ci_lower > 0


def test_candidate_with_fewer_than_4_positive_deltas_is_rejected() -> None:
    # 3 seeds positive (+0.1), 2 seeds negative (-0.05), mean is positive (+0.04)
    baseline = (0.70, 0.70, 0.70, 0.70, 0.70)
    candidate = (0.80, 0.80, 0.80, 0.65, 0.65)
    decision = promotion_decision(baseline, candidate)
    assert decision.selected_model is None


@pytest.mark.parametrize(
    ("bad_baseline", "bad_candidate"),
    [
        ((0.7, 0.7, 0.7, 0.7), (0.8, 0.8, 0.8, 0.8)),  # 4 elements
        ((0.7,) * 6, (0.8,) * 6),  # 6 elements
        ((0.7,) * 5, (0.8,) * 4),  # mismatched lengths
    ],
)
def test_non_5_element_tuples_fail_validation(
    bad_baseline: tuple[float, ...], bad_candidate: tuple[float, ...]
) -> None:
    with pytest.raises(ValueError, match="5|length|elements"):
        promotion_decision(bad_baseline, bad_candidate)


@pytest.mark.parametrize(
    ("bad_baseline", "bad_candidate"),
    [
        ((0.7, 0.7, float("nan"), 0.7, 0.7), (0.8,) * 5),
        ((0.7,) * 5, (0.8, 0.8, float("inf"), 0.8, 0.8)),
    ],
)
def test_non_finite_values_fail_validation(
    bad_baseline: tuple[float, ...], bad_candidate: tuple[float, ...]
) -> None:
    with pytest.raises(ValueError, match="finite|nan|inf"):
        promotion_decision(bad_baseline, bad_candidate)


def test_promotion_decision_immutability() -> None:
    decision = PromotionDecision(
        selected_model="candidate", mean_delta=0.05, ci_lower=0.02
    )
    with pytest.raises(ValidationError):
        decision.selected_model = None  # type: ignore[misc]
