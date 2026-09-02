from __future__ import annotations

from collections.abc import Mapping
from datetime import datetime, timedelta
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
    if (
        not isinstance(dt_dtype, pl.Datetime)
        or dt_dtype.time_zone is None
        or dt_dtype.time_zone == ""
    ):
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


class AMLSimSampleAdapter:
    mapping: ClassVar[Mapping[str, str]] = MappingProxyType(
        {
            "sourceNodeId": "source_id",
            "targetNodeId": "target_id",
            "value": "amount",
            "time": "event_time",
        }
    )

    def __init__(
        self,
        observation_start: datetime,
        tick_duration: timedelta,
        edge_id_prefix: str,
    ) -> None:
        if (
            not isinstance(observation_start, datetime)
            or observation_start.tzinfo is None
            or observation_start.tzinfo.utcoffset(observation_start) is None
        ):
            raise ValueError("observation_start must be timezone-aware datetime")
        if not isinstance(tick_duration, timedelta) or tick_duration.total_seconds() <= 0:
            raise ValueError("tick_duration must be strictly positive timedelta")
        if not isinstance(edge_id_prefix, str) or not edge_id_prefix.strip():
            raise ValueError("edge_id_prefix must be a non-blank string")

        self.observation_start = observation_start
        self.tick_duration = tick_duration
        self.edge_id_prefix = edge_id_prefix

    def transactions(self, frame: pl.DataFrame) -> pl.DataFrame:
        missing = tuple(sorted(set(self.mapping) - set(frame.columns)))
        if missing:
            raise ValueError(f"missing source columns: {missing}")

        for col_name in ("sourceNodeId", "targetNodeId"):
            if frame[col_name].null_count() > 0:
                raise ValueError("canonical frame contains null identifier")
            if (
                frame.schema[col_name].base_type() in (pl.String, pl.Utf8)
                and frame.height > 0
                and (frame[col_name].str.strip_chars() == "").any()
            ):
                raise ValueError("canonical frame contains blank identifier")

        if not frame.schema["value"].is_numeric():
            raise ValueError("canonical frame amount must be numeric")
        if frame["value"].null_count() > 0:
            raise ValueError("canonical frame contains null amount")
        if (
            frame.schema["value"].is_float()
            and frame.height > 0
            and not frame["value"].is_finite().all()
        ):
            raise ValueError("canonical frame contains non-finite amount")
        if frame.height > 0 and (frame["value"] <= 0).any():
            raise ValueError("canonical frame amount must be strictly positive")

        if not frame.schema["time"].is_integer():
            raise ValueError("relative ticks must be integer type")
        if frame["time"].null_count() > 0:
            raise ValueError("relative ticks contain null value")
        if frame.height > 0 and (frame["time"] < 0).any():
            raise ValueError("relative ticks must be non-negative")

        edge_ids = [f"{self.edge_id_prefix}{i}" for i in range(frame.height)]
        event_times = [self.observation_start + int(t) * self.tick_duration for t in frame["time"]]

        tz_name = (
            "UTC"
            if self.observation_start.tzinfo is not None
            and self.observation_start.tzinfo.tzname(self.observation_start)
            in ("UTC", "UTC+00:00", "+00:00", None)
            else str(self.observation_start.tzinfo)
        )

        canonical = pl.DataFrame(
            {
                "edge_id": pl.Series(edge_ids, dtype=pl.String),
                "source_id": frame["sourceNodeId"].cast(pl.String),
                "target_id": frame["targetNodeId"].cast(pl.String),
                "amount": frame["value"].cast(pl.Float64),
                "event_time": pl.Series(event_times, dtype=pl.Datetime("us", tz_name)),
            }
        )
        return _validate_canonical_frame(canonical)
