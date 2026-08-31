from __future__ import annotations

import polars as pl

_REQUIRED_NODES_COLUMNS: tuple[str, ...] = ("nodeid", "isFraud", "fraudStep")


def account_labels(nodes: pl.DataFrame) -> pl.DataFrame:
    """Extract restricted account-level labels from nodes.csv."""
    missing = [col for col in _REQUIRED_NODES_COLUMNS if col not in nodes.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    if nodes.height > 0:
        if nodes["nodeid"].null_count() > 0:
            raise ValueError("null or blank identifier in nodes frame")

        node_str = nodes["nodeid"].cast(pl.String, strict=False)
        if node_str.null_count() > 0 or (node_str.str.strip_chars() == "").any():
            raise ValueError("null or blank identifier in nodes frame")

        if nodes["isFraud"].null_count() > 0:
            raise ValueError("isFraud must contain non-null 0 or 1 values")

        fraud_float = nodes["isFraud"].cast(pl.Float64, strict=False)
        fraud_int = nodes["isFraud"].cast(pl.Int64, strict=False)
        if (
            fraud_int.null_count() > 0
            or fraud_float.null_count() > 0
            or fraud_float.is_nan().any()
            or fraud_float.is_infinite().any()
            or (fraud_float != fraud_int.cast(pl.Float64)).any()
            or (~fraud_int.is_in([0, 1])).any()
        ):
            raise ValueError("isFraud must contain only 0 or 1")

    return nodes.select(
        [
            pl.col("nodeid").cast(pl.String).alias("account_id"),
            pl.col("isFraud").cast(pl.Int64).alias("is_fraud"),
            pl.col("fraudStep").cast(pl.String).alias("label_provenance"),
        ]
    )
