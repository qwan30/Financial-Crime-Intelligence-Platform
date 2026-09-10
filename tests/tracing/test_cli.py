from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

import polars as pl

from fincrime.data.artifacts import write_public_artifact
from fincrime.data.provenance import sha256_file


def create_cli_test_artifact(tmp_path: Path) -> tuple[Path, Path]:
    out_dir = tmp_path / "cli_artifact"
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / "transactions.parquet"
    manifest_path = out_dir / "transactions.manifest.json"

    events = [
        {
            "edge_id": "tx_01",
            "source_id": "acc_A",
            "target_id": "acc_B",
            "amount": 100.0,
            "event_time": datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
        },
        {
            "edge_id": "tx_02",
            "source_id": "acc_B",
            "target_id": "acc_C",
            "amount": 80.0,
            "event_time": datetime(2026, 1, 1, 10, 10, tzinfo=UTC),
        },
        {
            "edge_id": "tx_03",
            "source_id": "acc_C",
            "target_id": "acc_D",
            "amount": 50.0,
            "event_time": datetime(2026, 1, 1, 10, 20, tzinfo=UTC),
        },
        # tx_external is outside any case boundary
        {
            "edge_id": "tx_external",
            "source_id": "acc_B",
            "target_id": "acc_E",
            "amount": 30.0,
            "event_time": datetime(2026, 1, 1, 10, 15, tzinfo=UTC),
        },
    ]
    df = pl.DataFrame(
        events,
        schema={
            "edge_id": pl.String,
            "source_id": pl.String,
            "target_id": pl.String,
            "amount": pl.Float64,
            "event_time": pl.Datetime(time_zone="UTC"),
        },
    )
    raw_hash = "0" * 64
    manifest = write_public_artifact(
        frame=df,
        output_path=parquet_path,
        source_id="cli-test-source",
        parent_raw_sha256=raw_hash,
        adapter_name="AMLSimSampleAdapter",
        adapter_version="1.0",
        conversion_parameters=(
            ("archive_member", "transactions.csv"),
            ("edge_id_prefix", "amlsim:"),
            ("observation_start", "2026-01-01T00:00:00.000000Z"),
            ("source_manifest_sha256", "1" * 64),
            ("tick_duration_microseconds", "1000000"),
            ("time_basis", "SYNTHETIC_TICKS"),
        ),
    )
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")
    return parquet_path, manifest_path


def test_cli_trace_successful_execution_and_determinism(tmp_path: Path) -> None:
    parquet_path, manifest_path = create_cli_test_artifact(tmp_path)
    out_json = tmp_path / "export1.json"

    cmd = [
        sys.executable,
        "-m",
        "fincrime.cli",
        "trace",
        "--artifact",
        str(parquet_path),
        "--lineage",
        str(manifest_path),
        "--cutoff",
        "2026-01-01T12:00:00Z",
        "--account",
        "acc_A",
        "--direction",
        "forward",
        "--window-start",
        "2026-01-01T09:00:00Z",
        "--window-end",
        "2026-01-01T11:00:00Z",
        "--max-hops",
        "3",
        "--max-edges",
        "10",
        "--output",
        str(out_json),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 0, f"CLI failed: {proc.stderr}"

    # File output exists and matches stdout
    assert out_json.exists()
    file_bytes = out_json.read_bytes()
    assert file_bytes == proc.stdout.encode("utf-8")

    data = json.loads(proc.stdout)
    assert data["format_version"] == "tracelab-1"
    assert data["algorithm_version"] == "breadth-temporal-1"
    assert data["interpretation"] == "TEMPORALLY_FEASIBLE_CANDIDATES_NOT_FUNDS_ATTRIBUTION"

    # Synthetic time provenance is recorded
    snapshot = data["snapshot"]
    assert snapshot["time_basis"] == "SYNTHETIC_TICKS"
    assert snapshot["tick_duration_microseconds"] == 1_000_000
    assert snapshot["observation_start"] == "2026-01-01T00:00:00.000000Z"

    # Edge discovery includes external transaction
    result = data["result"]
    assert "tx_01" in result["edge_ids"]
    assert "tx_external" in result["edge_ids"]
    assert result["status"] == "EXHAUSTED_WITHIN_LIMITS"

    # Re-running without --output yields exact byte-identical output to prior file
    cmd_no_out = [c for c in cmd if c not in ("--output", str(out_json))]
    proc2 = subprocess.run(cmd_no_out, capture_output=True, text=True, check=False)
    assert proc2.returncode == 0
    assert proc2.stdout.encode("utf-8") == file_bytes


def test_cli_trace_output_exists_fails(tmp_path: Path) -> None:
    parquet_path, manifest_path = create_cli_test_artifact(tmp_path)
    out_json = tmp_path / "export_exists.json"
    out_json.write_text("existing content", encoding="utf-8")

    cmd = [
        sys.executable,
        "-m",
        "fincrime.cli",
        "trace",
        "--artifact",
        str(parquet_path),
        "--lineage",
        str(manifest_path),
        "--cutoff",
        "2026-01-01T12:00:00Z",
        "--account",
        "acc_A",
        "--direction",
        "forward",
        "--window-start",
        "2026-01-01T09:00:00Z",
        "--window-end",
        "2026-01-01T11:00:00Z",
        "--output",
        str(out_json),
    ]

    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    err = json.loads(proc.stderr)
    assert err["error"]["code"] == "OUTPUT_EXISTS"


def test_cli_trace_invalid_arguments(tmp_path: Path) -> None:
    parquet_path, manifest_path = create_cli_test_artifact(tmp_path)

    # Missing timezone on cutoff -> INVALID_REQUEST
    cmd_naive = [
        sys.executable,
        "-m",
        "fincrime.cli",
        "trace",
        "--artifact",
        str(parquet_path),
        "--lineage",
        str(manifest_path),
        "--cutoff",
        "2026-01-01T12:00:00",  # naive
        "--account",
        "acc_A",
        "--direction",
        "forward",
        "--window-start",
        "2026-01-01T09:00:00Z",
        "--window-end",
        "2026-01-01T11:00:00Z",
    ]
    proc_naive = subprocess.run(cmd_naive, capture_output=True, text=True, check=False)
    assert proc_naive.returncode == 2
    err = json.loads(proc_naive.stderr)
    assert err["error"]["code"] == "INVALID_REQUEST"


def test_cli_trace_naive_timestamp_source_fails(tmp_path: Path) -> None:
    p = tmp_path / "naive_src.parquet"
    m = tmp_path / "naive_src.manifest.json"
    df = pl.DataFrame(
        {
            "edge_id": ["e1"],
            "source_id": ["A"],
            "target_id": ["B"],
            "amount": [10.0],
            "event_time": [datetime(2026, 1, 1, 10, 0)],  # noqa: DTZ001 - testing naive rejection
        }
    )
    df.write_parquet(p)
    m.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(p),
                "row_count": 1,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "fincrime.cli",
        "trace",
        "--artifact",
        str(p),
        "--lineage",
        str(m),
        "--cutoff",
        "2026-01-01T12:00:00Z",
        "--account",
        "A",
        "--direction",
        "forward",
        "--window-start",
        "2026-01-01T09:00:00Z",
        "--window-end",
        "2026-01-01T11:00:00Z",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    err = json.loads(proc.stderr)
    assert err["error"]["code"] == "INVALID_SOURCE"


def test_cli_trace_post_cutoff_malformed_row_fails(tmp_path: Path) -> None:
    p = tmp_path / "post_cutoff.parquet"
    m = tmp_path / "post_cutoff.manifest.json"
    df = pl.DataFrame(
        {
            "edge_id": ["e1", "e2"],
            "source_id": ["A", "B"],
            "target_id": ["B", "C"],
            "amount": [10.0, -50.0],  # Malformed post-cutoff amount
            "event_time": [
                datetime(2026, 1, 1, 10, 0, tzinfo=UTC),
                datetime(2026, 1, 1, 15, 0, tzinfo=UTC),  # After cutoff
            ],
        }
    )
    df.write_parquet(p)
    m.write_text(
        json.dumps(
            {
                "source_id": "test",
                "parent_raw_sha256": "0" * 64,
                "adapter_name": "Test",
                "adapter_version": "1.0",
                "conversion_parameters": [["time_basis", "EVENT_TIME"]],
                "output_sha256": sha256_file(p),
                "row_count": 2,
                "public_columns": ["edge_id", "source_id", "target_id", "amount", "event_time"],
            }
        ),
        encoding="utf-8",
    )

    cmd = [
        sys.executable,
        "-m",
        "fincrime.cli",
        "trace",
        "--artifact",
        str(p),
        "--lineage",
        str(m),
        "--cutoff",
        "2026-01-01T12:00:00Z",  # Cutoff is 12:00, e2 is at 15:00
        "--account",
        "A",
        "--direction",
        "forward",
        "--window-start",
        "2026-01-01T09:00:00Z",
        "--window-end",
        "2026-01-01T11:00:00Z",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    assert proc.returncode == 2
    err = json.loads(proc.stderr)
    assert err["error"]["code"] == "INVALID_SOURCE"
    assert "positive" in err["error"]["message"]
