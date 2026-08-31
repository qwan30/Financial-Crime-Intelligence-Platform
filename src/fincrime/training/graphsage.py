from __future__ import annotations

import math

import torch
from torch import Tensor
from torch.nn import functional
from torch_geometric.data import Data  # type: ignore[import-untyped]
from torch_geometric.loader import NeighborLoader  # type: ignore[import-untyped]
from torch_geometric.nn import SAGEConv  # type: ignore[import-untyped]


class GraphSAGEDetector(torch.nn.Module):
    """Two-layer GraphSAGE baseline detector."""

    def __init__(self, in_channels: int, hidden_channels: int) -> None:
        super().__init__()
        if in_channels <= 0:
            raise ValueError(f"in_channels must be positive, got {in_channels}")
        if hidden_channels <= 0:
            raise ValueError(f"hidden_channels must be positive, got {hidden_channels}")

        self.first = SAGEConv(in_channels, hidden_channels)
        self.second = SAGEConv(hidden_channels, 2)

    def forward(self, x: Tensor, edge_index: Tensor) -> Tensor:
        if x.ndim != 2:
            raise ValueError(f"x must be a 2D tensor, got {x.ndim}D tensor")
        if edge_index.ndim != 2 or edge_index.shape[0] != 2:
            raise ValueError(f"edge_index must have shape (2, E), got {tuple(edge_index.shape)}")

        hidden = self.first(x, edge_index).relu()
        return self.second(hidden, edge_index)  # type: ignore[no-any-return]


def build_neighbor_loader(
    data: Data, input_nodes: Tensor, batch_size: int
) -> NeighborLoader:
    """Build a bounded two-hop neighbor loader for batch training and inference."""
    if not isinstance(input_nodes, Tensor) or input_nodes.numel() == 0:
        raise ValueError("input_nodes must be a non-empty 1D Tensor of seed node indices")
    if batch_size <= 0:
        raise ValueError(f"batch_size must be positive, got {batch_size}")

    return NeighborLoader(
        data,
        input_nodes=input_nodes,
        num_neighbors=[15, 10],
        batch_size=batch_size,
        shuffle=False,
    )


def train_graphsage_epoch(
    model: GraphSAGEDetector, data: Data, learning_rate: float
) -> float:
    """Train GraphSAGE detector for one epoch and return scalar cross-entropy loss."""
    if not isinstance(learning_rate, (int, float)) or not math.isfinite(learning_rate) or learning_rate <= 0:
        raise ValueError(f"learning_rate must be a positive finite float, got {learning_rate}")

    if not hasattr(data, "x") or not hasattr(data, "edge_index") or not hasattr(data, "y") or not hasattr(data, "train_mask"):
        raise ValueError("data must contain x, edge_index, y, and train_mask attributes")

    train_mask: Tensor = data.train_mask
    if train_mask.dtype != torch.bool or train_mask.numel() == 0 or not bool(train_mask.any()):
        raise ValueError("data.train_mask must be a non-empty boolean tensor with at least one active sample")

    model.train()
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    optimizer.zero_grad()
    logits = model(data.x, data.edge_index)
    loss = functional.cross_entropy(logits[train_mask], data.y[train_mask])
    loss.backward()  # type: ignore[no-untyped-call]
    optimizer.step()

    loss_val = float(loss.detach().item())
    if not math.isfinite(loss_val):
        raise ValueError(f"Training produced non-finite loss: {loss_val}")
    return loss_val
