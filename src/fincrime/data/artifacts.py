from __future__ import annotations

import re
from pathlib import Path

import polars as pl

from fincrime.data.adapters import CANONICAL_COLUMNS
from fincrime.data.provenance import DerivedArtifactManifest, sha256_file
from fincrime.data.quality import QualityReport
from fincrime.data.tracebench import public_transactions

_SHA256_HEX_PATTERN: re.Pattern[str] = re.compile(r"^[0-9a-f]{64}$")



def write_public_artifact(
    frame: pl.DataFrame,
    output_path: Path,
    source_id: str,
    parent_raw_sha256: str,
    adapter_name: str,
    adapter_version: str,
    conversion_parameters: tuple[tuple[str, str], ...],
) -> DerivedArtifactManifest:
    """Write public transactions to Parquet and return an immutable lineage manifest."""
    if output_path.exists():
        raise FileExistsError("output path already exists")

    public_frame = public_transactions(frame)
    missing = [col for col in CANONICAL_COLUMNS if col not in public_frame.columns]
    if missing:
        raise ValueError(f"frame missing canonical columns: {missing}")

    ordered_frame = public_frame.select(list(CANONICAL_COLUMNS))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ordered_frame.write_parquet(output_path)

    output_hash = sha256_file(output_path)
    return DerivedArtifactManifest(
        source_id=source_id,
        parent_raw_sha256=parent_raw_sha256,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        conversion_parameters=conversion_parameters,
        output_sha256=output_hash,
        row_count=ordered_frame.height,
        public_columns=CANONICAL_COLUMNS,
    )


def write_clean_artifact(
    frame: pl.DataFrame,
    output_path: Path,
    source_id: str,
    parent_raw_sha256: str,
    adapter_name: str,
    adapter_version: str,
    quality_report: QualityReport | str,
    conversion_parameters: tuple[tuple[str, str], ...] = (),
) -> DerivedArtifactManifest:
    """Write cleaned canonical transactions to Parquet and record quality report hash in lineage manifest."""
    if isinstance(quality_report, QualityReport):
        if quality_report.source_id != source_id:
            raise ValueError(
                f"quality_report source_id ({quality_report.source_id!r}) does not match artifact source_id ({source_id!r})"
            )
        if quality_report.raw_sha256 != parent_raw_sha256:
            raise ValueError(
                f"quality_report raw_sha256 ({quality_report.raw_sha256!r}) does not match parent_raw_sha256 ({parent_raw_sha256!r})"
            )
        if quality_report.accepted_rows != frame.height:
            raise ValueError(
                f"quality_report accepted_rows ({quality_report.accepted_rows}) does not match frame row count ({frame.height})"
            )
        report_hash = quality_report.report_sha256()
    elif isinstance(quality_report, str):
        if not _SHA256_HEX_PATTERN.fullmatch(quality_report):
            raise ValueError(
                f"quality_report string must be a valid 64-character hex SHA-256 digest, got {quality_report!r}"
            )
        report_hash = quality_report
    else:
        raise TypeError(
            f"quality_report must be a QualityReport instance or a SHA-256 hex string, got {type(quality_report).__name__}"
        )

    clean_params = conversion_parameters + (("quality_report_sha256", report_hash),)
    return write_public_artifact(
        frame=frame,
        output_path=output_path,
        source_id=source_id,
        parent_raw_sha256=parent_raw_sha256,
        adapter_name=adapter_name,
        adapter_version=adapter_version,
        conversion_parameters=clean_params,
    )
