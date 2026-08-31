from __future__ import annotations

from collections import Counter
from hashlib import sha256

import polars as pl
from pydantic import BaseModel, ConfigDict, Field

from fincrime.data.provenance import Hash, NonBlank, sha256_header

_REQUIRED_AMLSIM_COLUMNS: tuple[str, ...] = (
    "sourceNodeId",
    "targetNodeId",
    "value",
    "time",
)


class QualityReport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    source_id: NonBlank
    raw_sha256: Hash
    schema_sha256: Hash
    input_rows: int = Field(ge=0)
    accepted_rows: int = Field(ge=0)
    rejected_rows: int = Field(ge=0)
    duplicate_rows: int = Field(ge=0)
    reason_counts: tuple[tuple[NonBlank, int], ...]

    def report_sha256(self) -> str:
        return sha256(self.model_dump_json().encode("utf-8")).hexdigest()


def clean_amlsim_rows(
    frame: pl.DataFrame,
    raw_sha256: str,
    source_id: str = "amlsim-20k",
) -> tuple[pl.DataFrame, pl.DataFrame, QualityReport]:
    """Profile AMLSim rows, quarantine invalid rows with reason codes, and report exact duplicates."""
    missing = [col for col in _REQUIRED_AMLSIM_COLUMNS if col not in frame.columns]
    if missing:
        raise ValueError(f"missing required columns: {missing}")

    schema_fingerprint = sha256_header(",".join(frame.columns))

    if frame.height == 0:
        report = QualityReport(
            source_id=source_id,
            raw_sha256=raw_sha256,
            schema_sha256=schema_fingerprint,
            input_rows=0,
            accepted_rows=0,
            rejected_rows=0,
            duplicate_rows=0,
            reason_counts=(),
        )
        quarantine = frame.with_columns(
            pl.lit(None, dtype=pl.Int64).alias("row_ordinal"),
            pl.lit(None, dtype=pl.String).alias("reason_code"),
        )
        return frame, quarantine, report

    source_str = pl.col("sourceNodeId").cast(pl.String, strict=False)
    source_invalid = (
        pl.col("sourceNodeId").is_null()
        | source_str.is_null()
        | (source_str.str.strip_chars() == "")
    )

    target_str = pl.col("targetNodeId").cast(pl.String, strict=False)
    target_invalid = (
        pl.col("targetNodeId").is_null()
        | target_str.is_null()
        | (target_str.str.strip_chars() == "")
    )

    val_float = pl.col("value").cast(pl.Float64, strict=False)
    val_invalid = (
        pl.col("value").is_null()
        | val_float.is_null()
        | val_float.is_nan()
        | val_float.is_infinite()
        | (val_float <= 0.0)
    )

    time_int = pl.col("time").cast(pl.Int64, strict=False)
    time_float = pl.col("time").cast(pl.Float64, strict=False)
    time_invalid = (
        pl.col("time").is_null()
        | time_int.is_null()
        | time_float.is_null()
        | (time_float != time_int)
        | (time_int < 0)
    )

    is_id_invalid = source_invalid | target_invalid
    is_amount_invalid = ~is_id_invalid & val_invalid
    is_tick_invalid = ~is_id_invalid & ~val_invalid & time_invalid

    reason_expr = (
        pl.when(is_id_invalid)
        .then(pl.lit("missing_or_blank_identifier"))
        .when(is_amount_invalid)
        .then(pl.lit("non_positive_or_non_finite_amount"))
        .when(is_tick_invalid)
        .then(pl.lit("negative_or_invalid_tick"))
        .otherwise(pl.lit(None, dtype=pl.String))
        .alias("reason_code")
    )

    evaluated = (
        frame.with_row_index("row_ordinal")
        .with_columns(pl.col("row_ordinal").cast(pl.Int64), reason_expr)
    )

    accepted = (
        evaluated.filter(pl.col("reason_code").is_null())
        .drop(["row_ordinal", "reason_code"])
    )
    quarantine = evaluated.filter(pl.col("reason_code").is_not_null())

    duplicate_rows = frame.height - frame.unique().height

    reason_counts_counter = Counter(quarantine["reason_code"].to_list())
    sorted_reason_counts: tuple[tuple[NonBlank, int], ...] = tuple(
        (str(reason), count)
        for reason, count in sorted(reason_counts_counter.items(), key=lambda item: item[0])
    )

    report = QualityReport(
        source_id=source_id,
        raw_sha256=raw_sha256,
        schema_sha256=schema_fingerprint,
        input_rows=frame.height,
        accepted_rows=accepted.height,
        rejected_rows=quarantine.height,
        duplicate_rows=duplicate_rows,
        reason_counts=sorted_reason_counts,
    )

    return accepted, quarantine, report


def profile_amlsim_rows(
    frame: pl.DataFrame,
    raw_sha256: str,
    source_id: str = "amlsim-20k",
) -> QualityReport:
    """Profile AMLSim rows and return an immutable QualityReport."""
    _, _, report = clean_amlsim_rows(frame=frame, raw_sha256=raw_sha256, source_id=source_id)
    return report
