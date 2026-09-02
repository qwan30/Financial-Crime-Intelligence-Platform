from __future__ import annotations

import math

import numpy as np
import pytest
from pydantic import ValidationError

from fincrime.monitoring.drift import (
    FittedPSIBins,
    PSIDriftResult,
    calculate_psi,
    fit_psi_bins,
    is_drift_detected,
)
from fincrime.monitoring.metrics import (
    EVENTS_PROCESSED,
    EVENTS_QUARANTINED,
    SCORING_LATENCY,
)


def test_is_drift_detected_logic() -> None:
    assert is_drift_detected(0.15, threshold=0.1) is True
    assert is_drift_detected(0.10, threshold=0.1) is True
    assert is_drift_detected(0.0999, threshold=0.1) is False
    assert is_drift_detected(0.0, threshold=0.1) is False
    assert is_drift_detected(0.25, threshold=0.25) is True
    assert is_drift_detected(0.24, threshold=0.25) is False


def test_identical_distributions_have_zero_psi() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float64)
    fitted = fit_psi_bins(values, bins=4)
    result = calculate_psi(fitted, values, threshold=0.1)

    assert pytest.approx(result.psi, abs=1e-5) == 0.0
    assert result.drift_detected is False
    assert is_drift_detected(result.psi, threshold=0.1) is False


def test_shifted_distribution_triggers_drift() -> None:
    baseline = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    current = np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64)
    fitted = fit_psi_bins(baseline, bins=2)
    result = calculate_psi(fitted, current, threshold=0.1)

    assert result.psi > 0.1
    assert result.drift_detected is True


def test_psidriftresult_rejects_inconsistent_drift_boolean() -> None:
    # Drift detected should be True when psi >= threshold
    with pytest.raises(ValidationError, match="inconsistent"):
        PSIDriftResult(psi=0.5, threshold=0.1, drift_detected=False, bins=10)

    # Drift detected should be False when psi < threshold
    with pytest.raises(ValidationError, match="inconsistent"):
        PSIDriftResult(psi=0.05, threshold=0.1, drift_detected=True, bins=10)

    # Valid instances should succeed
    res_drift = PSIDriftResult(psi=0.5, threshold=0.1, drift_detected=True, bins=10)
    assert res_drift.drift_detected is True

    res_no_drift = PSIDriftResult(psi=0.05, threshold=0.1, drift_detected=False, bins=10)
    assert res_no_drift.drift_detected is False


def test_psidriftresult_validation_constraints() -> None:
    with pytest.raises(ValidationError):
        PSIDriftResult(psi=-0.01, threshold=0.1, drift_detected=False, bins=10)

    with pytest.raises(ValidationError):
        PSIDriftResult(psi=0.0, threshold=0.0, drift_detected=False, bins=10)

    with pytest.raises(ValidationError):
        PSIDriftResult(psi=0.0, threshold=-0.1, drift_detected=False, bins=10)

    with pytest.raises(ValidationError):
        PSIDriftResult(psi=0.0, threshold=0.1, drift_detected=False, bins=1)


def test_fitted_psi_bins_invariants_and_nan_rejection() -> None:
    # NaN edges rejected
    with pytest.raises(ValidationError):
        FittedPSIBins(edges=(-np.inf, np.nan, np.inf), base_counts=(0.5, 0.5), bins=2)

    # Non-monotonic edges rejected
    with pytest.raises(ValidationError, match="strictly monotonically"):
        FittedPSIBins(edges=(-np.inf, 5.0, 3.0, np.inf), base_counts=(0.33, 0.33, 0.34), bins=3)

    # Equal adjacent edges rejected
    with pytest.raises(ValidationError, match="strictly monotonically"):
        FittedPSIBins(edges=(-np.inf, 5.0, 5.0, np.inf), base_counts=(0.33, 0.33, 0.34), bins=3)

    # Edge missing -inf start
    with pytest.raises(ValidationError, match="-inf"):
        FittedPSIBins(edges=(0.0, 5.0, np.inf), base_counts=(0.5, 0.5), bins=2)

    # Edge missing +inf end
    with pytest.raises(ValidationError, match=r"\+inf"):
        FittedPSIBins(edges=(-np.inf, 5.0, 100.0), base_counts=(0.5, 0.5), bins=2)

    # Length mismatch for edges vs bins
    with pytest.raises(ValidationError, match="edges length"):
        FittedPSIBins(edges=(-np.inf, 5.0, np.inf), base_counts=(0.33, 0.33, 0.34), bins=3)

    # Length mismatch for base_counts vs bins
    with pytest.raises(ValidationError, match="base_counts length"):
        FittedPSIBins(edges=(-np.inf, 2.0, 5.0, np.inf), base_counts=(0.5, 0.5), bins=3)

    # Negative base_counts rejected
    with pytest.raises(ValidationError, match="non-negative"):
        FittedPSIBins(edges=(-np.inf, 5.0, np.inf), base_counts=(-0.1, 1.1), bins=2)

    # Sum of base_counts != 1.0 rejected
    with pytest.raises(ValidationError, match="approx 1.0"):
        FittedPSIBins(edges=(-np.inf, 5.0, np.inf), base_counts=(0.4, 0.4), bins=2)

    # Valid model succeeds
    valid = FittedPSIBins(edges=(-np.inf, 0.0, np.inf), base_counts=(0.5, 0.5), bins=2)
    assert valid.bins == 2
    assert valid.edges == (-math.inf, 0.0, math.inf)


def test_fit_psi_bins_input_validation() -> None:
    # Empty array
    with pytest.raises(ValueError, match="must not be empty"):
        fit_psi_bins(np.array([], dtype=np.float64), bins=5)

    # 2-D array
    with pytest.raises(ValueError, match="1-D array"):
        fit_psi_bins(np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64), bins=2)

    # NaN in baseline
    with pytest.raises(ValueError, match="finite numbers"):
        fit_psi_bins(np.array([1.0, np.nan, 3.0], dtype=np.float64), bins=2)

    # Inf in baseline
    with pytest.raises(ValueError, match="finite numbers"):
        fit_psi_bins(np.array([1.0, np.inf, 3.0], dtype=np.float64), bins=2)

    # Bins < 2
    with pytest.raises(ValueError, match="bins must be >= 2"):
        fit_psi_bins(np.array([1.0, 2.0, 3.0], dtype=np.float64), bins=1)


def test_calculate_psi_input_validation() -> None:
    fitted = fit_psi_bins(np.array([1.0, 2.0, 3.0, 4.0], dtype=np.float64), bins=2)

    # Empty current
    with pytest.raises(ValueError, match="must not be empty"):
        calculate_psi(fitted, np.array([], dtype=np.float64))

    # 2-D current
    with pytest.raises(ValueError, match="1-D array"):
        calculate_psi(fitted, np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float64))

    # NaN in current
    with pytest.raises(ValueError, match="finite numbers"):
        calculate_psi(fitted, np.array([1.0, np.nan, 3.0], dtype=np.float64))

    # Inf in current
    with pytest.raises(ValueError, match="finite numbers"):
        calculate_psi(fitted, np.array([1.0, np.inf, 3.0], dtype=np.float64))


def test_extreme_mixed_extrema_baseline_fitting_and_calculation() -> None:
    # Skewed mixed extrema: [-finfo.max] + [finfo.max] * 9 with bins=10
    max_val = np.finfo(np.float64).max
    baseline = np.array([-max_val] + [max_val] * 9, dtype=np.float64)
    fitted = fit_psi_bins(baseline, bins=10)

    assert len(fitted.edges) == 11
    assert fitted.edges[0] == -np.inf
    assert fitted.edges[-1] == np.inf
    assert all(np.isfinite(x) for x in fitted.edges[1:-1])
    assert all(left < right for left, right in zip(fitted.edges[:-1], fitted.edges[1:]))

    # Mirrored skewed distribution
    mirrored = np.array([-max_val] * 9 + [max_val], dtype=np.float64)
    fitted_mirrored = fit_psi_bins(mirrored, bins=10)
    assert all(np.isfinite(x) for x in fitted_mirrored.edges[1:-1])
    assert all(
        left < right for left, right in zip(fitted_mirrored.edges[:-1], fitted_mirrored.edges[1:])
    )

    # Verify calculation executes cleanly without error
    res = calculate_psi(fitted, baseline)
    assert res.psi == pytest.approx(0.0, abs=1e-5)


def test_constant_baseline_distribution() -> None:
    # Constant baseline: quantiles are all the same value 42.0
    baseline = np.array([42.0] * 100, dtype=np.float64)
    fitted = fit_psi_bins(baseline, bins=5)

    assert len(fitted.edges) == 6
    assert fitted.edges[0] == -np.inf
    assert fitted.edges[-1] == np.inf
    assert all(np.isfinite(x) for x in fitted.edges[1:-1])
    assert all(left < right for left, right in zip(fitted.edges[:-1], fitted.edges[1:]))

    # Calculate PSI on same constant distribution
    res = calculate_psi(fitted, baseline)
    assert res.psi == pytest.approx(0.0, abs=1e-5)
    assert res.drift_detected is False


def test_split_extrema_and_subnormal_distributions() -> None:
    max_val = np.finfo(np.float64).max
    split_extrema = np.array([-max_val] * 5 + [max_val] * 5, dtype=np.float64)
    fitted_split = fit_psi_bins(split_extrema, bins=4)
    assert len(fitted_split.edges) == 5
    assert all(left < right for left, right in zip(fitted_split.edges[:-1], fitted_split.edges[1:]))

    res_split = calculate_psi(fitted_split, split_extrema)
    assert res_split.psi == pytest.approx(0.0, abs=1e-5)

    subnormal = np.array([0.0, 1e-300, 1e-300, 1e-300, 1.0], dtype=np.float64)
    fitted_sub = fit_psi_bins(subnormal, bins=4)
    assert len(fitted_sub.edges) == 5
    assert all(left < right for left, right in zip(fitted_sub.edges[:-1], fitted_sub.edges[1:]))

    res_sub = calculate_psi(fitted_sub, subnormal)
    assert res_sub.psi == pytest.approx(0.0, abs=1e-5)


def test_prometheus_metrics_initialized() -> None:
    assert EVENTS_PROCESSED._name == "fincrime_events_processed"
    assert EVENTS_QUARANTINED._name == "fincrime_events_quarantined"
    assert SCORING_LATENCY._name == "fincrime_scoring_latency_seconds"
