import polars as pl
import pytest

from fincrime.data.adapters import AMLBenchAdapter, AMLSimAdapter


def test_amlsim_adapter_maps_canonical_columns() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e1"],
            "orig_id": ["a"],
            "dest_id": ["b"],
            "amount": [10.0],
            "timestamp": ["2026-01-01T00:00:00Z"],
        }
    )

    assert AMLSimAdapter().transactions(raw).to_dict(as_series=False) == {
        "edge_id": ["e1"],
        "source_id": ["a"],
        "target_id": ["b"],
        "amount": [10.0],
        "event_time": ["2026-01-01T00:00:00Z"],
    }


def test_amlbench_adapter_maps_canonical_columns() -> None:
    raw = pl.DataFrame(
        {
            "transaction_id": ["e2"],
            "source_account_id": ["c"],
            "target_account_id": ["d"],
            "amount": [20.0],
            "transaction_time": ["2026-01-02T00:00:00Z"],
        }
    )

    assert AMLBenchAdapter().transactions(raw).to_dict(as_series=False) == {
        "edge_id": ["e2"],
        "source_id": ["c"],
        "target_id": ["d"],
        "amount": [20.0],
        "event_time": ["2026-01-02T00:00:00Z"],
    }


@pytest.mark.parametrize(
    ("adapter", "frame"),
    [
        (AMLSimAdapter(), pl.DataFrame({"orig_id": ["a"]})),
        (AMLBenchAdapter(), pl.DataFrame({"source_account_id": ["a"]})),
    ],
)
def test_adapter_fails_when_required_source_columns_are_missing(
    adapter: AMLSimAdapter | AMLBenchAdapter, frame: pl.DataFrame
) -> None:
    with pytest.raises(ValueError, match="missing source columns"):
        adapter.transactions(frame)
