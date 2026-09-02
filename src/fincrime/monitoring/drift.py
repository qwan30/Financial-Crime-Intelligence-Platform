from __future__ import annotations

import math

import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator


def is_drift_detected(psi: float, threshold: float = 0.1) -> bool:
    """Return True if calculated population stability index meets or exceeds drift threshold."""
    return psi >= threshold


class FittedPSIBins(BaseModel):
    """Immutable model representing baseline bin boundaries and baseline frequencies for PSI."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    edges: tuple[float, ...]
    base_counts: tuple[float, ...]
    bins: int = Field(ge=2)

    @model_validator(mode="after")
    def validate_dimensions_and_monotonicity(self) -> FittedPSIBins:
        if len(self.edges) != self.bins + 1:
            raise ValueError(
                f"edges length must be bins + 1 ({self.bins + 1}), got {len(self.edges)}"
            )
        if len(self.base_counts) != self.bins:
            raise ValueError(
                f"base_counts length must be bins ({self.bins}), got {len(self.base_counts)}"
            )
        if self.edges[0] != -math.inf or self.edges[-1] != math.inf:
            raise ValueError("edges must start with -inf and end with +inf")
        if not all(math.isfinite(x) for x in self.edges[1:-1]):
            raise ValueError("interior edges must be finite real numbers")
        if not all(left < right for left, right in zip(self.edges[:-1], self.edges[1:])):
            raise ValueError("edges must be strictly monotonically increasing")
        for count in self.base_counts:
            if count < 0.0 or not math.isfinite(count):
                raise ValueError("base_counts must be finite non-negative numbers")
        if not math.isclose(sum(self.base_counts), 1.0, abs_tol=1e-5):
            raise ValueError(f"sum of base_counts must be approx 1.0, got {sum(self.base_counts)}")
        return self


class PSIDriftResult(BaseModel):
    """Validated population stability index evaluation result."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    psi: float = Field(ge=0.0)
    threshold: float = Field(gt=0.0)
    drift_detected: bool
    bins: int = Field(ge=2)

    @model_validator(mode="after")
    def validate_drift_consistency(self) -> PSIDriftResult:
        expected = is_drift_detected(self.psi, self.threshold)
        if self.drift_detected != expected:
            raise ValueError(
                f"drift_detected '{self.drift_detected}' inconsistent with "
                f"is_drift_detected({self.psi}, {self.threshold}) -> {expected}"
            )
        return self


def fit_psi_bins(baseline: NDArray[np.float64], bins: int = 10) -> FittedPSIBins:
    """Fit baseline distribution into quantile bins with robust clamp-and-sweep monotonicity."""
    if len(baseline) == 0:
        raise ValueError("Baseline distribution must not be empty")
    if baseline.ndim != 1:
        raise ValueError("Baseline must be a 1-D array")
    if not np.all(np.isfinite(baseline)):
        raise ValueError("Baseline must contain only finite numbers (no NaN or Inf)")
    if bins < 2:
        raise ValueError("bins must be >= 2")

    min_finite = -float(np.finfo(np.float64).max)
    max_finite = float(np.finfo(np.float64).max)

    quantiles = np.linspace(0, 1, bins + 1)
    raw_quantiles = np.quantile(baseline, quantiles)

    # Clamp all raw interior quantile values to finite float range
    interior: list[float] = []
    for x in raw_quantiles[1:-1]:
        val = float(x)
        if not math.isfinite(val) or val <= min_finite:
            val = min_finite
        elif val >= max_finite:
            val = max_finite
        interior.append(val)

    # Forward pass: ensure strictly increasing
    for i in range(1, len(interior)):
        if interior[i] <= interior[i - 1]:
            interior[i] = float(math.nextafter(interior[i - 1], math.inf))

    # Backward pass: if forward pass pushed rightmost interior to or past max_finite
    if interior and interior[-1] >= max_finite:
        interior[-1] = max_finite
        for i in range(len(interior) - 2, -1, -1):
            if interior[i] >= interior[i + 1]:
                interior[i] = float(math.nextafter(interior[i + 1], -math.inf))

    # Re-clamp first interior element if backward pass pushed past min_finite
    if interior and interior[0] <= min_finite:
        interior[0] = min_finite
        for i in range(1, len(interior)):
            if interior[i] <= interior[i - 1]:
                interior[i] = float(math.nextafter(interior[i - 1], math.inf))

    edges = (-math.inf,) + tuple(interior) + (math.inf,)
    base_counts = np.histogram(baseline, bins=edges)[0] / len(baseline)

    return FittedPSIBins(
        edges=edges,
        base_counts=tuple(float(x) for x in base_counts),
        bins=bins,
    )


def calculate_psi(
    fitted: FittedPSIBins,
    current: NDArray[np.float64],
    threshold: float = 0.1,
) -> PSIDriftResult:
    """Calculate Population Stability Index between fitted baseline and current distribution."""
    if len(current) == 0:
        raise ValueError("Current distribution must not be empty")
    if current.ndim != 1:
        raise ValueError("Current must be a 1-D array")
    if not np.all(np.isfinite(current)):
        raise ValueError("Current must contain only finite numbers (no NaN or Inf)")

    edges = np.array(fitted.edges)
    base_counts = np.array(fitted.base_counts)
    current_counts = np.histogram(current, bins=edges)[0] / len(current)

    base_safe = np.clip(base_counts, 1e-9, None)
    current_safe = np.clip(current_counts, 1e-9, None)

    psi_val = float(np.sum((current_safe - base_safe) * np.log(current_safe / base_safe)))
    psi_val = max(0.0, psi_val)

    return PSIDriftResult(
        psi=psi_val,
        threshold=threshold,
        drift_detected=is_drift_detected(psi_val, threshold),
        bins=fitted.bins,
    )
