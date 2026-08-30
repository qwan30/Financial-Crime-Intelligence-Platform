import polars as pl

from fincrime.data.tracebench import LABEL_DERIVED_COLUMNS, public_transactions


def test_public_projection_removes_all_label_derived_columns() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [100.0],
            "scenario_id": ["s1"],
            "_aml_designations": [1],
            "split_mask": ["train"],
        }
    )

    public = public_transactions(frame)

    assert not set(LABEL_DERIVED_COLUMNS).intersection(public.columns)
    assert public.columns == ["edge_id", "source_id", "target_id", "amount"]


def test_public_projection_drops_each_forbidden_column_and_preserves_public_data() -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "_aml_designations": [1],
            "source_id": ["a"],
            "_scenario_log": ["generated"],
            "target_id": ["b"],
            "scenario_id": ["s1"],
            "amount": [100.0],
            "case_id": ["c1"],
            "currency": ["USD"],
            "signal_columns": [["amount"]],
            "split_mask": ["train"],
            "In_Scenario": [True],
            "analyst_disposition": ["confirmed"],
        }
    )

    public = public_transactions(frame)

    assert public.columns == ["edge_id", "source_id", "target_id", "amount", "currency"]
    assert public.to_dict(as_series=False) == {
        "edge_id": ["e1"],
        "source_id": ["a"],
        "target_id": ["b"],
        "amount": [100.0],
        "currency": ["USD"],
    }
