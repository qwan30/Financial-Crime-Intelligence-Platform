import polars as pl

from fincrime.data.tracebench import LABEL_DERIVED_COLUMNS, public_transactions


def test_public_projection_removes_all_label_derived_columns() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
            **{name: ["derived"] for name in LABEL_DERIVED_COLUMNS},
        }
    )

    public = public_transactions(frame)

    assert not set(LABEL_DERIVED_COLUMNS).intersection(public.columns)
    assert public.columns == ["edge_id", "source_id", "target_id", "amount"]


def test_public_projection_drops_indirect_signal_metadata() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
            "derived_signal_metadata": [{"velocity": "high"}],
        }
    )

    public = public_transactions(frame)

    assert public.columns == ["edge_id", "source_id", "target_id", "amount"]


def test_public_projection_drops_renamed_label_and_signal_fields() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
            "label": [1],
            "is_suspicious": [True],
            "velocity_signal": [0.9],
        }
    )

    public = public_transactions(frame)

    assert public.columns == ["edge_id", "source_id", "target_id", "amount"]


def test_public_projection_drops_arbitrary_object_payloads() -> None:
    payload = pl.Series("raw_payload", [object()], dtype=pl.Object)
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
        }
    ).with_columns(payload)

    public = public_transactions(frame)

    assert public.columns == ["edge_id", "source_id", "target_id", "amount"]


def test_public_projection_allows_event_time_but_drops_unknown_fields() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
            "event_time": ["2026-01-01T00:00:00Z"],
            "currency": ["USD"],
        }
    )

    public = public_transactions(frame)

    assert public.columns == ["edge_id", "source_id", "target_id", "amount", "event_time"]
    assert public.to_dict(as_series=False) == {
        "edge_id": ["e1"],
        "source_id": ["a"],
        "target_id": ["b"],
        "amount": [100.0],
        "event_time": ["2026-01-01T00:00:00Z"],
    }


def test_public_projection_preserves_input_order_of_present_canonical_columns() -> None:
    frame = pl.DataFrame(
        {
            "amount": [100.0],
            "unknown": ["drop me"],
            "event_time": ["2026-01-01T00:00:00Z"],
            "edge_id": ["e1"],
        }
    )

    public = public_transactions(frame)

    assert public.columns == ["amount", "event_time", "edge_id"]
