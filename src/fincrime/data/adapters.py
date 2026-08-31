from __future__ import annotations

from collections.abc import Mapping
from types import MappingProxyType
from typing import ClassVar

import polars as pl

CANONICAL_COLUMNS: tuple[str, ...] = (
    "edge_id",
    "source_id",
    "target_id",
    "amount",
    "event_time",
)
_ID_COLUMNS: tuple[str, ...] = ("edge_id", "source_id", "target_id")


def _validate_canonical_frame(frame: pl.DataFrame) -> pl.DataFrame:
    for col_name in _ID_COLUMNS:
        if frame.schema[col_name].base_type() not in (pl.String, pl.Utf8):
            raise ValueError("canonical frame identifier columns must be string type")
        if frame[col_name].null_count() > 0:
            raise ValueError("canonical frame contains null identifier")
        if frame.height > 0 and (frame[col_name].str.strip_chars() == "").any():
            raise ValueError("canonical frame contains blank identifier")

    if not frame.schema["amount"].is_numeric():
        raise ValueError("canonical frame amount must be numeric")
    if frame["amount"].null_count() > 0:
        raise ValueError("canonical frame contains null amount")
    if (
        frame.schema["amount"].is_float()
        and frame.height > 0
        and not frame["amount"].is_finite().all()
    ):
        raise ValueError("canonical frame contains non-finite amount")

    dt_dtype = frame.schema["event_time"]
    if dt_dtype.base_type() != pl.Datetime:
        raise ValueError("canonical frame event_time must be datetime type")
    if not isinstance(dt_dtype, pl.Datetime) or dt_dtype.time_zone is None or dt_dtype.time_zone == "":
        raise ValueError("canonical frame event_time must be timezone-aware")
    if frame["event_time"].null_count() > 0:
        raise ValueError("canonical frame contains null event_time")

    return frame



class AMLSimAdapter:
    mapping: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "transaction_id": "edge_id",
            "orig_id": "source_id",
            "dest_id": "target_id",
            "amount": "amount",
            "timestamp": "event_time",
        }
    )

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")
        canonical = frame.select(
            [pl.col(source).alias(target) for source, target in self.mapping.items()]
        )
        return _validate_canonical_frame(canonical)


class AMLBenchAdapter:
    mapping: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "transaction_id": "edge_id",
            "source_account_id": "source_id",
            "target_account_id": "target_id",
            "amount": "amount",
            "transaction_time": "event_time",
        }
    )

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")
        canonical = frame.select(
            [pl.col(source).alias(target) for source, target in self.mapping.items()]
        )
        return _validate_canonical_frame(canonical)
