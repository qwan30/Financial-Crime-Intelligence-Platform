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

_PUBLIC_TRANSACTION_COLUMNS = frozenset(
    {"edge_id", "source_id", "target_id", "amount", "event_time"}
)


def public_transactions(frame: pl.DataFrame) -> pl.DataFrame:
    return frame.select([name for name in frame.columns if name in _PUBLIC_TRANSACTION_COLUMNS])
