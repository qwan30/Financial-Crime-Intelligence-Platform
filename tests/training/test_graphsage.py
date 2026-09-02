from __future__ import annotations

import math

import pytest
import torch
from torch_geometric.data import Data

from fincrime.training.graphsage import (
    GraphSAGEDetector,
    build_neighbor_loader,
    train_graphsage_epoch,
)


def test_graphsage_smoke_training_returns_finite_loss() -> None:
    data = Data(
        x=torch.tensor([[0.0], [0.2], [0.8], [1.0]], dtype=torch.float32),
        edge_index=torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.int64),
        y=torch.tensor([0, 0, 1, 1], dtype=torch.int64),
        train_mask=torch.tensor([True, True, True, True], dtype=torch.bool),
    )
    model = GraphSAGEDetector(in_channels=1, hidden_channels=8)
    loss = train_graphsage_epoch(model, data, learning_rate=0.01)
    assert math.isfinite(loss)
    assert loss > 0.0


def test_neighbor_loader_keeps_seed_batch_bounded() -> None:
    data = Data(
        x=torch.rand((20, 2), dtype=torch.float32),
        edge_index=torch.tensor(
            [[i for i in range(19)], [i + 1 for i in range(19)]], dtype=torch.int64
        ),
        y=torch.zeros(20, dtype=torch.int64),
    )
    batch = next(
        iter(build_neighbor_loader(data, torch.tensor([0, 1], dtype=torch.int64), batch_size=2))
    )
    assert batch.batch_size == 2


def test_seed_deterministic_behavior() -> None:
    data = Data(
        x=torch.tensor([[0.0], [0.2], [0.8], [1.0]], dtype=torch.float32),
        edge_index=torch.tensor([[0, 1, 2], [1, 2, 3]], dtype=torch.int64),
        y=torch.tensor([0, 0, 1, 1], dtype=torch.int64),
        train_mask=torch.tensor([True, True, True, True], dtype=torch.bool),
    )
    torch.manual_seed(42)
    model1 = GraphSAGEDetector(in_channels=1, hidden_channels=8)
    loss1 = train_graphsage_epoch(model1, data, learning_rate=0.01)

    torch.manual_seed(42)
    model2 = GraphSAGEDetector(in_channels=1, hidden_channels=8)
    loss2 = train_graphsage_epoch(model2, data, learning_rate=0.01)

    assert loss1 == pytest.approx(loss2)


@pytest.mark.parametrize("invalid_channel", [0, -1, -8])
def test_invalid_channels_fail_validation(invalid_channel: int) -> None:
    with pytest.raises(ValueError, match="channel|positive"):
        GraphSAGEDetector(in_channels=invalid_channel, hidden_channels=8)
    with pytest.raises(ValueError, match="channel|positive"):
        GraphSAGEDetector(in_channels=1, hidden_channels=invalid_channel)


@pytest.mark.parametrize("invalid_lr", [0.0, -0.01, float("inf"), float("nan")])
def test_invalid_learning_rate_fails_validation(invalid_lr: float) -> None:
    data = Data(
        x=torch.tensor([[0.0], [1.0]], dtype=torch.float32),
        edge_index=torch.tensor([[0], [1]], dtype=torch.int64),
        y=torch.tensor([0, 1], dtype=torch.int64),
        train_mask=torch.tensor([True, True], dtype=torch.bool),
    )
    model = GraphSAGEDetector(in_channels=1, hidden_channels=4)
    with pytest.raises(ValueError, match="learning_rate|positive|finite"):
        train_graphsage_epoch(model, data, learning_rate=invalid_lr)


def test_empty_train_mask_fails_validation() -> None:
    data = Data(
        x=torch.tensor([[0.0], [1.0]], dtype=torch.float32),
        edge_index=torch.tensor([[0], [1]], dtype=torch.int64),
        y=torch.tensor([0, 1], dtype=torch.int64),
        train_mask=torch.tensor([False, False], dtype=torch.bool),
    )
    model = GraphSAGEDetector(in_channels=1, hidden_channels=4)
    with pytest.raises(ValueError, match="train_mask|empty|active"):
        train_graphsage_epoch(model, data, learning_rate=0.01)


def test_empty_input_nodes_in_loader_fails_validation() -> None:
    data = Data(
        x=torch.tensor([[0.0], [1.0]], dtype=torch.float32),
        edge_index=torch.tensor([[0], [1]], dtype=torch.int64),
        y=torch.tensor([0, 1], dtype=torch.int64),
    )
    with pytest.raises(ValueError, match="input_nodes|empty"):
        build_neighbor_loader(data, torch.tensor([], dtype=torch.int64), batch_size=2)


@pytest.mark.parametrize("invalid_batch_size", [0, -1, -5])
def test_invalid_batch_size_fails_validation(invalid_batch_size: int) -> None:
    data = Data(
        x=torch.tensor([[0.0], [1.0]], dtype=torch.float32),
        edge_index=torch.tensor([[0], [1]], dtype=torch.int64),
        y=torch.tensor([0, 1], dtype=torch.int64),
    )
    with pytest.raises(ValueError, match="batch_size|positive"):
        build_neighbor_loader(
            data, torch.tensor([0], dtype=torch.int64), batch_size=invalid_batch_size
        )
