from __future__ import annotations

import io
import json
import tarfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import polars as pl
import pytest

from fincrime.data.artifacts import write_public_artifact
from fincrime.data.provenance import sha256_file
from fincrime.tracing.models import TraceLabError
from fincrime.tracing.snapshots import (
    import_amlsim_snapshot,
    load_trace_snapshot,
)


def create_tar_archive(path: Path, members: dict[str, str | bytes]) -> None:
    """Create a tar archive with the specified members."""
    with tarfile.open(path, "w:gz") as tar:
        for name, content in members.items():
            data = content.encode("utf-8") if isinstance(content, str) else content
            ti = tarfile.TarInfo(name=name)
            ti.size = len(data)
            ti.mtime = 1767225600
            tar.addfile(ti, io.BytesIO(data))


def create_manifest(path: Path, archive_path: Path, count: int = 1) -> None:
    """Create a valid amlsim manifest matching the archive."""
    manifest_data = {
        "dataset_id": "amlsim-20k-fanin200",
        "sha256": sha256_file(archive_path),
        "schema_header": "sourceNodeId,targetNodeId,value,time",
        "transactions_count": count,
    }
    path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")


def test_import_source_hash_mismatch(tmp_path: Path) -> None:
    archive_path = tmp_path / "archive.tgz"
    create_tar_archive(
        archive_path, {"transactions.csv": "sourceNodeId,targetNodeId,value,time\n1,2,10.0,1\n"}
    )
    manifest_path = tmp_path / "manifest.json"
    manifest_data = {
        "dataset_id": "amlsim-20k-fanin200",
        "sha256": "0" * 64,  # wrong hash
        "schema_header": "sourceNodeId,targetNodeId,value,time",
        "transactions_count": 1,
    }
    manifest_path.write_text(json.dumps(manifest_data), encoding="utf-8")

    out_path = tmp_path / "out.parquet"
    with pytest.raises(TraceLabError) as exc_info:
        import_amlsim_snapshot(
            archive_path=archive_path,
            manifest_path=manifest_path,
            output_path=out_path,
            observation_start=datetime(2026, 1, 1, tzinfo=UTC),
            tick_duration=timedelta(seconds=1),
        )
    assert exc_info.value.code == "SOURCE_HASH_MISMATCH"


def test_import_ambiguous_or_missing_tar_member(tmp_path: Path) -> None:
    # Missing transactions.csv
    archive_empty = tmp_path / "empty.tgz"
    create_tar_archive(archive_empty, {"other.csv": "col1,col2\n1,2\n"})
    manifest_empty = tmp_path / "manifest_empty.json"
    create_manifest(manifest_empty, archive_empty, 0)

    out_path = tmp_path / "out1.parquet"
    with pytest.raises(TraceLabError) as exc_info:
        import_amlsim_snapshot(
            archive_path=archive_empty,
            manifest_path=manifest_empty,
            output_path=out_path,
            observation_start=datetime(2026, 1, 1, tzinfo=UTC),
            tick_duration=timedelta(seconds=1),
        )
    assert exc_info.value.code == "INVALID_SOURCE"

    # Ambiguous transactions.csv (2 members)
    archive_two = tmp_path / "two.tgz"
    create_tar_archive(
        archive_two,
        {
            "dir1/transactions.csv": "sourceNodeId,targetNodeId,value,time\n1,2,10.0,1\n",
            "dir2/transactions.csv": "sourceNodeId,targetNodeId,value,time\n1,2,10.0,1\n",
        },
    )
    manifest_two = tmp_path / "manifest_two.json"
    create_manifest(manifest_two, archive_two, 1)

    out_path2 = tmp_path / "out2.parquet"
    with pytest.raises(TraceLabError) as exc_info2:
        import_amlsim_snapshot(
            archive_path=archive_two,
            manifest_path=manifest_two,
            output_path=out_path2,
            observation_start=datetime(2026, 1, 1, tzinfo=UTC),
            tick_duration=timedelta(seconds=1),
        )
    assert exc_info2.value.code == "INVALID_SOURCE"


def test_import_no_overwrite(tmp_path: Path) -> None:
    archive_path = tmp_path / "archive.tgz"
    create_tar_archive(
        archive_path, {"transactions.csv": "sourceNodeId,targetNodeId,value,time\n1,2,10.0,1\n"}
    )
    manifest_path = tmp_path / "manifest.json"
    create_manifest(manifest_path, archive_path, 1)

    out_path = tmp_path / "out.parquet"
    out_path.write_bytes(b"existing content")

    with pytest.raises(TraceLabError) as exc_info:
        import_amlsim_snapshot(
            archive_path=archive_path,
            manifest_path=manifest_path,
            output_path=out_path,
            observation_start=datetime(2026, 1, 1, tzinfo=UTC),
            tick_duration=timedelta(seconds=1),
        )
    assert exc_info.value.code == "OUTPUT_EXISTS"


def test_load_stale_or_missing_lineage(tmp_path: Path) -> None:
    parquet_path = tmp_path / "data.parquet"
    manifest_path = tmp_path / "data.manifest.json"

    df = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": [10.0],
            "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
        }
    )
    lineage = write_public_artifact(
        frame=df,
        output_path=parquet_path,
        source_id="test",
        parent_raw_sha256="0" * 64,
        adapter_name="Test",
        adapter_version="1.0",
        conversion_parameters=(("time_basis", "EVENT_TIME"),),
    )
    manifest_path.write_text(lineage.model_dump_json(), encoding="utf-8")

    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    # Missing parquet
    with pytest.raises(TraceLabError) as exc_missing:
        load_trace_snapshot(tmp_path / "nonexistent.parquet", manifest_path, cutoff=cutoff)
    assert exc_missing.value.code == "IO_ERROR"

    # Missing manifest
    with pytest.raises(TraceLabError) as exc_manifest:
        load_trace_snapshot(parquet_path, tmp_path / "nonexistent.json", cutoff=cutoff)
    assert exc_manifest.value.code == "IO_ERROR"

    # Tampered parquet (hash mismatch)
    parquet_path.write_bytes(parquet_path.read_bytes() + b"corruption")
    with pytest.raises(TraceLabError) as exc_mismatch:
        load_trace_snapshot(parquet_path, manifest_path, cutoff=cutoff)
    assert exc_mismatch.value.code == "SOURCE_HASH_MISMATCH"


def test_changed_tick_mapping_identity(tmp_path: Path) -> None:
    archive_path = tmp_path / "archive.tgz"
    csv_data = "sourceNodeId,targetNodeId,value,time\n1,2,10.0,1\n"
    create_tar_archive(archive_path, {"transactions.csv": csv_data})
    manifest_path = tmp_path / "manifest.json"
    create_manifest(manifest_path, archive_path, 1)

    out1 = tmp_path / "out1.parquet"
    out2 = tmp_path / "out2.parquet"

    # Import 1: 1-second tick
    import_amlsim_snapshot(
        archive_path=archive_path,
        manifest_path=manifest_path,
        output_path=out1,
        observation_start=datetime(2026, 1, 1, tzinfo=UTC),
        tick_duration=timedelta(seconds=1),
    )
    # Import 2: 2-second tick
    import_amlsim_snapshot(
        archive_path=archive_path,
        manifest_path=manifest_path,
        output_path=out2,
        observation_start=datetime(2026, 1, 1, tzinfo=UTC),
        tick_duration=timedelta(seconds=2),
    )
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    snap1 = load_trace_snapshot(out1, out1.with_suffix(".manifest.json"), cutoff=cutoff)
    snap2 = load_trace_snapshot(out2, out2.with_suffix(".manifest.json"), cutoff=cutoff)

    assert snap1.descriptor.tick_duration_microseconds == 1_000_000
    assert snap2.descriptor.tick_duration_microseconds == 2_000_000
    assert snap1.descriptor.snapshot_id != snap2.descriptor.snapshot_id
    assert snap1.descriptor.time_basis == "SYNTHETIC_TICKS"


def test_load_naive_parquet_timestamp_rejected(tmp_path: Path) -> None:
    parquet_path = tmp_path / "naive.parquet"
    manifest_path = tmp_path / "naive.manifest.json"

    df = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": [10.0],
            "event_time": [datetime(2026, 1, 1, 10, 0)],  # noqa: DTZ001 - testing naive rejection
        }
    )
    df.write_parquet(parquet_path)
    lineage = write_public_artifact(
        frame=pl.DataFrame(
            {
                "edge_id": ["e1"],
                "source_id": ["A"],
                "target_id": ["B"],
                "amount": [10.0],
                "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
            }
        ),
        output_path=tmp_path / "dummy.parquet",
        source_id="test",
        parent_raw_sha256="0" * 64,
        adapter_name="Test",
        adapter_version="1.0",
        conversion_parameters=(("time_basis", "EVENT_TIME"),),
    )
    # Point lineage to naive parquet with its exact hash
    naive_hash = sha256_file(parquet_path)
    tampered_lineage = lineage.model_copy(update={"output_sha256": naive_hash})
    manifest_path.write_text(tampered_lineage.model_dump_json(), encoding="utf-8")

    with pytest.raises(TraceLabError) as exc_info:
        load_trace_snapshot(
            parquet_path, manifest_path, cutoff=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        )
    assert exc_info.value.code == "INVALID_SOURCE"
    assert "timezone-aware" in exc_info.value.message


def test_load_null_timestamp_rejected(tmp_path: Path) -> None:
    parquet_path = tmp_path / "null_time.parquet"
    manifest_path = tmp_path / "null_time.manifest.json"

    df = pl.DataFrame(
        [
            ("e1", "A", "B", 10.0, None),
        ],
        orient="row",
        schema={
            "edge_id": pl.String,
            "source_id": pl.String,
            "target_id": pl.String,
            "amount": pl.Float64,
            "event_time": pl.Datetime(time_zone="UTC"),
        },
    )
    df.write_parquet(parquet_path)
    lineage = write_public_artifact(
        frame=pl.DataFrame(
            {
                "edge_id": ["e1"],
                "source_id": ["A"],
                "target_id": ["B"],
                "amount": [10.0],
                "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
            }
        ),
        output_path=tmp_path / "dummy_null.parquet",
        source_id="test",
        parent_raw_sha256="0" * 64,
        adapter_name="Test",
        adapter_version="1.0",
        conversion_parameters=(("time_basis", "EVENT_TIME"),),
    )
    manifest_path.write_text(
        lineage.model_copy(
            update={"output_sha256": sha256_file(parquet_path), "row_count": 1}
        ).model_dump_json(),
        encoding="utf-8",
    )

    with pytest.raises(TraceLabError) as exc_info:
        load_trace_snapshot(
            parquet_path, manifest_path, cutoff=datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
        )
    assert exc_info.value.code == "INVALID_SOURCE"
    assert "null" in exc_info.value.message


def test_load_malformed_amount_schema_rejected(tmp_path: Path) -> None:
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)

    # 1. Non-positive amount
    p1 = tmp_path / "nonpos.parquet"
    df1 = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": [-5.0],
            "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
        }
    )
    df1.write_parquet(p1)
    m1 = tmp_path / "nonpos.manifest.json"
    m1.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(p1),
                "row_count": 1,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TraceLabError) as exc_info1:
        load_trace_snapshot(p1, m1, cutoff=cutoff)
    assert exc_info1.value.code == "INVALID_SOURCE"
    assert "positive" in exc_info1.value.message

    # 2. String amount
    p2 = tmp_path / "stramt.parquet"
    df2 = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": ["100.0"],
            "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
        }
    )
    df2.write_parquet(p2)
    m2 = tmp_path / "stramt.manifest.json"
    m2.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(p2),
                "row_count": 1,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TraceLabError) as exc_info2:
        load_trace_snapshot(p2, m2, cutoff=cutoff)
    assert exc_info2.value.code == "INVALID_SOURCE"
    assert "numeric" in exc_info2.value.message

    # 3. Non-finite amount (float nan)
    p3 = tmp_path / "nan.parquet"
    df3 = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": [float("nan")],
            "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
        }
    )
    df3.write_parquet(p3)
    m3 = tmp_path / "nan.manifest.json"
    m3.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(p3),
                "row_count": 1,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TraceLabError) as exc_info3:
        load_trace_snapshot(p3, m3, cutoff=cutoff)
    assert exc_info3.value.code == "INVALID_SOURCE"
    assert "finite" in exc_info3.value.message


def test_load_post_cutoff_malformed_row_rejected(tmp_path: Path) -> None:
    """Do not silently drop malformed rows, including rows later than cutoff."""
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    # Row 1 is before cutoff (valid), Row 2 is AFTER cutoff (non-positive amount)
    parquet_path = tmp_path / "post_cutoff_malformed.parquet"
    manifest_path = tmp_path / "post_cutoff_malformed.manifest.json"

    df = pl.DataFrame(
        {
            "edge_id": ["e1", "e2"],
            "source_id": ["A", "B"],
            "target_id": ["B", "C"],
            "amount": [10.0, -1.0],  # malformed post-cutoff amount
            "event_time": [
                datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2026, 1, 1, 15, 0, tzinfo=UTC),  # after cutoff!
            ],
        }
    )
    df.write_parquet(parquet_path)
    manifest_path.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(parquet_path),
                "row_count": 2,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TraceLabError) as exc_info:
        load_trace_snapshot(parquet_path, manifest_path, cutoff=cutoff)
    assert exc_info.value.code == "INVALID_SOURCE"
    assert "strictly positive" in exc_info.value.message


def test_load_lineage_public_columns_mismatch_rejected(tmp_path: Path) -> None:
    cutoff = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    parquet_path = tmp_path / "wrong_cols.parquet"
    manifest_path = tmp_path / "wrong_cols.manifest.json"

    df = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": [10.0],
            "extra_col": ["foo"],
            "event_time": [datetime(2026, 1, 1, 10, 0, tzinfo=UTC)],
        }
    )
    df.write_parquet(parquet_path)
    manifest_path.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(parquet_path),
                "row_count": 1,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(TraceLabError) as exc_info:
        load_trace_snapshot(parquet_path, manifest_path, cutoff=cutoff)
    assert exc_info.value.code == "INVALID_SOURCE"
    assert "public_columns" in exc_info.value.message
