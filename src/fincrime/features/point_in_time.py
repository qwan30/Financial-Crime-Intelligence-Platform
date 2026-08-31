from __future__ import annotations

import networkx as nx  # type: ignore[import-untyped]
from pydantic import BaseModel, ConfigDict


class AccountFeatures(BaseModel):
    model_config = ConfigDict(frozen=True)

    account_id: str
    in_degree: int
    out_degree: int
    incoming_amount: float
    outgoing_amount: float
    pass_through_ratio: float


def account_features(graph: nx.MultiDiGraph, account_id: str) -> AccountFeatures:
    """Derive transparent degree, amount, and pass-through features for an account."""
    if account_id not in graph:
        return AccountFeatures(
            account_id=account_id,
            in_degree=0,
            out_degree=0,
            incoming_amount=0.0,
            outgoing_amount=0.0,
            pass_through_ratio=0.0,
        )

    incoming = sum(float(data["amount"]) for *_, data in graph.in_edges(account_id, data=True))
    outgoing = sum(float(data["amount"]) for *_, data in graph.out_edges(account_id, data=True))
    return AccountFeatures(
        account_id=account_id,
        in_degree=int(graph.in_degree(account_id)),
        out_degree=int(graph.out_degree(account_id)),
        incoming_amount=incoming,
        outgoing_amount=outgoing,
        pass_through_ratio=0.0 if incoming == 0.0 else min(outgoing / incoming, 1.0),
    )
