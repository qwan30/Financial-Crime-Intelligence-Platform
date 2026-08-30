from __future__ import annotations

import polars as pl

LABEL_DERIVED_COLUMNS = (
    "_aml_designations",
    "_scenario_log",
    "scenario_id",
    "case_id",
    "signal_columns",
    "split_mask",
    "In_Scenario",
    "analyst_disposition",
)


def public_transactions(frame: pl.DataFrame) -> pl.DataFrame:
    forbidden = [name for name in LABEL_DERIVED_COLUMNS if name in frame.columns]
    return frame.drop(forbidden)
