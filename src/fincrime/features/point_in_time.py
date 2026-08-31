from __future__ import annotations

import math
from typing import Any

import networkx as nx  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict, Field

from fincrime.contracts.manifests import NonBlankId


class AccountFeatures(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    account_id: NonBlankId
    in_degree: int = Field(ge=0)
    out_degree: int = Field(ge=0)
    incoming_amount: float = Field(ge=0)
    outgoing_amount: float = Field(ge=0)
    pass_through_ratio: float = Field(ge=0, le=1.0)


def _extract_amount(data: dict[str, Any], edge_key: Any) -> float:
    if "amount" not in data:
        raise ValueError(f"Edge '{edge_key}' is missing required 'amount' attribute")
    amt = data["amount"]
    if not isinstance(amt, (int, float)):
        raise TypeError(f"Edge '{edge_key}' amount must be numeric, got {type(amt).__name__}")
    val = float(amt)
    if not math.isfinite(val):
        raise ValueError(f"Edge '{edge_key}' has non-finite amount: {val}")
    if val < 0:
        raise ValueError(f"Edge '{edge_key}' has negative amount: {val}")
    return val


def account_features(graph: nx.MultiDiGraph, account_id: str) -> AccountFeatures:
    """Derive transparent degree, amount, and pass-through features for an account."""
    if not isinstance(graph, nx.MultiDiGraph):
        raise TypeError(f"Expected nx.MultiDiGraph, got {type(graph).__name__}")

    if not isinstance(account_id, str) or not account_id.strip():
        raise ValueError("account_id must be a non-blank string")

    if account_id not in graph:
        return AccountFeatures(
            account_id=account_id,
            in_degree=0,
            out_degree=0,
            incoming_amount=0.0,
            outgoing_amount=0.0,
            pass_through_ratio=0.0,
        )

    incoming = sum(
        _extract_amount(data, key)
        for _, _, key, data in graph.in_edges(account_id, data=True, keys=True)
    )
    outgoing = sum(
        _extract_amount(data, key)
        for _, _, key, data in graph.out_edges(account_id, data=True, keys=True)
    )
    in_deg = int(graph.in_degree(account_id))
    out_deg = int(graph.out_degree(account_id))
    pass_through = 0.0 if incoming == 0.0 else min(outgoing / incoming, 1.0)

    return AccountFeatures(
        account_id=account_id,
        in_degree=in_deg,
        out_degree=out_deg,
        incoming_amount=incoming,
        outgoing_amount=outgoing,
        pass_through_ratio=pass_through,
    )
