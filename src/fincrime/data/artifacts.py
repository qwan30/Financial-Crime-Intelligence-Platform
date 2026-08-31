from __future__ import annotations

from pathlib import Path

import polars as pl

from fincrime.data.adapters import CANONICAL_COLUMNS
from fincrime.data.provenance import DerivedArtifactManifest, sha256_file
from fincrime.data.quality import QualityReport
from fincrime.data.tracebench import public_transactions


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
    report_hash = (
        quality_report.report_sha256()
        if isinstance(quality_report, QualityReport)
        else str(quality_report)
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
