from __future__ import annotations

from pathlib import Path

import polars as pl
import pytest

from fincrime.data.artifacts import write_clean_artifact, write_public_artifact
from fincrime.data.provenance import sha256_file
from fincrime.data.quality import QualityReport


def test_public_artifact_excludes_labels_and_records_output_hash(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
            "scenario_id": ["hidden"],
            "_aml_designations": ["sar"],
        }
    )
    target = tmp_path / "public.parquet"
    manifest = write_public_artifact(
        frame=frame,
        output_path=target,
        source_id="amlsim-20k-fanin200",
        parent_raw_sha256="a" * 64,
        adapter_name="AMLSimSampleAdapter",
        adapter_version="1.0",
        conversion_parameters=(("prefix", "sample_"),),
    )
    assert manifest.row_count == 1
    assert manifest.public_columns == ("edge_id", "source_id", "target_id", "amount", "event_time")
    assert manifest.output_sha256 == sha256_file(target)

    read_back = pl.read_parquet(target)
    assert read_back.columns == ["edge_id", "source_id", "target_id", "amount", "event_time"]
    assert "scenario_id" not in read_back.columns
    assert "_aml_designations" not in read_back.columns


def test_write_public_artifact_refuses_overwrite(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    target = tmp_path / "public.parquet"
    write_public_artifact(
        frame=frame,
        output_path=target,
        source_id="amlsim",
        parent_raw_sha256="a" * 64,
        adapter_name="adapter",
        adapter_version="1.0",
        conversion_parameters=(),
    )
    with pytest.raises(FileExistsError):
        write_public_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            conversion_parameters=(),
        )


def test_write_public_artifact_rejects_missing_canonical_columns(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
        }
    )
    target = tmp_path / "public.parquet"
    with pytest.raises(ValueError, match="canonical"):
        write_public_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            conversion_parameters=(),
        )


def test_write_public_artifact_preserves_canonical_order(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "event_time": ["2026-01-01T00:00:00Z"],
            "amount": [1.0],
            "target_id": ["b"],
            "source_id": ["a"],
            "edge_id": ["e1"],
        }
    )
    target = tmp_path / "public.parquet"
    manifest = write_public_artifact(
        frame=frame,
        output_path=target,
        source_id="amlsim",
        parent_raw_sha256="a" * 64,
        adapter_name="adapter",
        adapter_version="1.0",
        conversion_parameters=(),
    )
    read_back = pl.read_parquet(target)
    assert read_back.columns == ["edge_id", "source_id", "target_id", "amount", "event_time"]
    assert manifest.public_columns == ("edge_id", "source_id", "target_id", "amount", "event_time")


def test_write_clean_artifact_includes_quality_report_hash(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    report = QualityReport(
        source_id="amlsim-20k",
        raw_sha256="a" * 64,
        schema_sha256="b" * 64,
        input_rows=1,
        accepted_rows=1,
        rejected_rows=0,
        duplicate_rows=0,
        reason_counts=(),
    )
    target = tmp_path / "clean.parquet"
    manifest = write_clean_artifact(
        frame=frame,
        output_path=target,
        source_id="amlsim-20k",
        parent_raw_sha256="a" * 64,
        adapter_name="AMLSimSampleAdapter",
        adapter_version="1.0",
        quality_report=report,
        conversion_parameters=(("prefix", "sample_"),),
    )
    assert manifest.row_count == 1
    assert manifest.public_columns == ("edge_id", "source_id", "target_id", "amount", "event_time")
    assert manifest.output_sha256 == sha256_file(target)
    assert ("quality_report_sha256", report.report_sha256()) in manifest.conversion_parameters


def test_write_clean_artifact_refuses_overwrite(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    target = tmp_path / "clean.parquet"
    write_clean_artifact(
        frame=frame,
        output_path=target,
        source_id="amlsim",
        parent_raw_sha256="a" * 64,
        adapter_name="adapter",
        adapter_version="1.0",
        quality_report="c" * 64,
    )
    with pytest.raises(FileExistsError):
        write_clean_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            quality_report="c" * 64,
        )


def test_write_clean_artifact_rejects_invalid_quality_report_string(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    target = tmp_path / "clean.parquet"
    with pytest.raises(ValueError, match="quality_report"):
        write_clean_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            quality_report="invalid-hex-sha256",
        )


def test_write_clean_artifact_rejects_invalid_quality_report_type(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    target = tmp_path / "clean.parquet"
    with pytest.raises((TypeError, ValueError), match="quality_report"):
        write_clean_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            quality_report=12345,  # type: ignore[arg-type]
        )


def test_write_clean_artifact_rejects_mismatched_report_source_id(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    report = QualityReport(
        source_id="amlsim-different",
        raw_sha256="a" * 64,
        schema_sha256="b" * 64,
        input_rows=1,
        accepted_rows=1,
        rejected_rows=0,
        duplicate_rows=0,
        reason_counts=(),
    )
    target = tmp_path / "clean.parquet"
    with pytest.raises(ValueError, match="source_id"):
        write_clean_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim-20k",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            quality_report=report,
        )


def test_write_clean_artifact_rejects_mismatched_report_parent_raw_sha256(tmp_path: Path) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    report = QualityReport(
        source_id="amlsim-20k",
        raw_sha256="a" * 64,
        schema_sha256="b" * 64,
        input_rows=1,
        accepted_rows=1,
        rejected_rows=0,
        duplicate_rows=0,
        reason_counts=(),
    )
    target = tmp_path / "clean.parquet"
    with pytest.raises(ValueError, match="raw_sha256"):
        write_clean_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim-20k",
            parent_raw_sha256="b" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            quality_report=report,
        )


def test_write_clean_artifact_rejects_mismatched_accepted_rows_and_frame_height(
    tmp_path: Path,
) -> None:
    frame = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["a"],
            "target_id": ["b"],
            "amount": [1.0],
            "event_time": ["2026-01-01T00:00:00Z"],
        }
    )
    report = QualityReport(
        source_id="amlsim-20k",
        raw_sha256="a" * 64,
        schema_sha256="b" * 64,
        input_rows=2,
        accepted_rows=2,
        rejected_rows=0,
        duplicate_rows=0,
        reason_counts=(),
    )
    target = tmp_path / "clean.parquet"
    with pytest.raises(ValueError, match="accepted_rows"):
        write_clean_artifact(
            frame=frame,
            output_path=target,
            source_id="amlsim-20k",
            parent_raw_sha256="a" * 64,
            adapter_name="adapter",
            adapter_version="1.0",
            quality_report=report,
        )
