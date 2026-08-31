from __future__ import annotations

import math

import numpy as np
from pydantic import BaseModel, ConfigDict


class PromotionDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    selected_model: str | None
    mean_delta: float
    ci_lower: float


def promotion_decision(
    baseline_values: tuple[float, ...], candidate_values: tuple[float, ...]
) -> PromotionDecision:
    """Decide model promotion using fixed 5-seed bootstrap confidence bound."""
    if len(baseline_values) != 5 or len(candidate_values) != 5:
        raise ValueError("baseline_values and candidate_values must both contain exactly 5 elements")

    for name, vals in (("baseline_values", baseline_values), ("candidate_values", candidate_values)):
        for val in vals:
            if not isinstance(val, (int, float)) or not math.isfinite(val):
                raise ValueError(f"All values in {name} must be finite numeric values, got {val}")

    deltas = tuple(
        float(candidate - baseline)
        for baseline, candidate in zip(baseline_values, candidate_values, strict=True)
    )
    mean_delta = float(sum(deltas) / len(deltas))
    rng = np.random.default_rng(20260830)
    samples = np.array(deltas, dtype=np.float64)
    bootstrap_means = np.array(
        [rng.choice(samples, size=len(samples), replace=True).mean() for _ in range(10_000)],
        dtype=np.float64,
    )
    lower = float(np.quantile(bootstrap_means, 0.025))
    selected = (
        "candidate"
        if lower > 0 and sum(delta > 0 for delta in deltas) >= 4
        else None
    )
    return PromotionDecision(selected_model=selected, mean_delta=mean_delta, ci_lower=lower)
