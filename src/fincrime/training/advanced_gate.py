from __future__ import annotations

import math
from typing import Literal

from pydantic import BaseModel, ConfigDict


class AdvancedModelDecision(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    next_family: Literal["hgt", "tgn", "hybrid", "JUSTIFIED_NULL"]
    reason: str


def advanced_model_decision(
    heterogeneous_supported: bool,
    graphsage_delta: float,
    temporal_gap: bool,
    hgt_delta: float,
    tgn_delta: float,
) -> AdvancedModelDecision:
    """Gate advanced GNN research based on empirical baseline gains."""
    if type(heterogeneous_supported) is not bool:
        raise TypeError(
            f"heterogeneous_supported must be a bool, got {type(heterogeneous_supported).__name__}"
        )
    if type(temporal_gap) is not bool:
        raise TypeError(f"temporal_gap must be a bool, got {type(temporal_gap).__name__}")

    for name, val in (
        ("graphsage_delta", graphsage_delta),
        ("hgt_delta", hgt_delta),
        ("tgn_delta", tgn_delta),
    ):
        if type(val) is bool or not isinstance(val, (int, float)):
            raise TypeError(f"{name} must be a float, got {type(val).__name__}")
        if not math.isfinite(val):
            raise ValueError(f"{name} must be finite, got {val}")

    if graphsage_delta <= 0:
        return AdvancedModelDecision(
            next_family="JUSTIFIED_NULL", reason="GraphSAGE did not beat tabular baseline"
        )
    if heterogeneous_supported and hgt_delta <= 0:
        return AdvancedModelDecision(next_family="hgt", reason="real heterogeneous ontology")
    if temporal_gap and tgn_delta <= 0:
        return AdvancedModelDecision(next_family="tgn", reason="unresolved temporal feature gap")
    if hgt_delta > 0 and tgn_delta > 0:
        return AdvancedModelDecision(next_family="hybrid", reason="HGT and TGN both passed")
    return AdvancedModelDecision(next_family="JUSTIFIED_NULL", reason="no advanced hypothesis passed")
