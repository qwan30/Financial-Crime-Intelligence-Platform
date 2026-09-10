from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

from fincrime.tracing.candidates import generate_candidates
from fincrime.tracing.models import (
    AccountSeed,
    TraceExport,
    TraceLabError,
    TraceRequest,
    TransactionSeed,
)
from fincrime.tracing.snapshots import import_amlsim_snapshot, load_trace_snapshot


def _parse_aware_datetime(val: str, field_name: str) -> datetime:
    try:
        dt = datetime.fromisoformat(val)
    except Exception as err:
        raise TraceLabError(
            "INVALID_REQUEST", f"Invalid ISO datetime for {field_name}: {val}"
        ) from err
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise TraceLabError("INVALID_REQUEST", f"{field_name} must include a timezone: {val}")
    return dt.astimezone(UTC)


def handle_trace_import_amlsim(args: argparse.Namespace) -> int:
    """Handler for trace-import-amlsim subcommand."""
    try:
        if args.tick_seconds <= 0:
            raise TraceLabError(
                "INVALID_REQUEST",
                f"--tick-seconds must be strictly positive, got {args.tick_seconds}",
            )

        obs_start = _parse_aware_datetime(args.observation_start, "--observation-start")
        tick_duration = timedelta(seconds=args.tick_seconds)

        lineage = import_amlsim_snapshot(
            archive_path=args.archive,
            manifest_path=args.manifest,
            output_path=args.output,
            observation_start=obs_start,
            tick_duration=tick_duration,
        )

        out_data = {
            "artifact_path": str(args.output),
            "lineage_path": str(args.output.with_suffix(".manifest.json")),
            "lineage": lineage.model_dump(mode="python"),
        }
        sys.stdout.write(json.dumps(out_data, indent=2) + "\n")
        return 0
    except TraceLabError as err:
        _print_error(err.code, err.message)
        return 2
    except FileExistsError as err:
        _print_error("OUTPUT_EXISTS", str(err))
        return 2
    except (FileNotFoundError, OSError) as err:
        _print_error("IO_ERROR", str(err))
        return 2


def handle_trace(args: argparse.Namespace) -> int:
    """Handler for trace query subcommand."""
    created_output_file: Path | None = None
    try:
        cutoff = _parse_aware_datetime(args.cutoff, "--cutoff")
        win_start = _parse_aware_datetime(args.window_start, "--window-start")
        win_end = _parse_aware_datetime(args.window_end, "--window-end")

        if win_start > win_end:
            raise TraceLabError(
                "INVALID_REQUEST", f"window_start ({win_start}) must be <= window_end ({win_end})"
            )

        max_gap_usec: int | None = None
        if args.max_gap_seconds is not None:
            if args.max_gap_seconds < 0:
                raise TraceLabError(
                    "INVALID_REQUEST",
                    f"--max-gap-seconds must be nonnegative, got {args.max_gap_seconds}",
                )
            max_gap_usec = args.max_gap_seconds * 1_000_000

        if args.max_hops < 1 or args.max_hops > 4:
            raise TraceLabError(
                "INVALID_REQUEST", f"--max-hops must be between 1 and 4, got {args.max_hops}"
            )
        if args.max_edges < 1 or args.max_edges > 100:
            raise TraceLabError(
                "INVALID_REQUEST", f"--max-edges must be between 1 and 100, got {args.max_edges}"
            )

        if args.account and args.transaction:
            raise TraceLabError(
                "INVALID_REQUEST", "Specify exactly one of --account or --transaction, not both"
            )
        if not args.account and not args.transaction:
            raise TraceLabError("INVALID_REQUEST", "Specify either --account or --transaction")

        seed = (
            AccountSeed(account_id=args.account)
            if args.account
            else TransactionSeed(edge_id=args.transaction)
        )

        request = TraceRequest(
            seed=seed,
            direction=args.direction,
            window_start=win_start,
            window_end=win_end,
            max_gap_microseconds=max_gap_usec,
            max_hops=args.max_hops,
            max_edges=args.max_edges,
        )

        # Preflight output if provided
        output_file: Path | None = args.output
        if output_file is not None and output_file.exists():
            raise TraceLabError("OUTPUT_EXISTS", f"Output file already exists: {output_file}")

        snapshot = load_trace_snapshot(
            artifact_path=args.artifact,
            lineage_path=args.lineage,
            cutoff=cutoff,
        )

        result = generate_candidates(snapshot, request)

        export = TraceExport.create(
            snapshot=snapshot.descriptor,
            request=request,
            result=result,
        )
        canonical_bytes = export.to_canonical_json_bytes() + b"\n"

        if output_file is not None:
            output_file.parent.mkdir(parents=True, exist_ok=True)
            try:
                with open(output_file, "xb") as f:
                    created_output_file = output_file
                    f.write(canonical_bytes)
            except FileExistsError as err:
                raise TraceLabError(
                    "OUTPUT_EXISTS", f"Output file already exists: {output_file}"
                ) from err
            except OSError as err:
                raise TraceLabError("IO_ERROR", f"Failed to write output file: {err}") from err

        sys.stdout.buffer.write(canonical_bytes)
        sys.stdout.buffer.flush()
        return 0
    except TraceLabError as err:
        if created_output_file and created_output_file.exists():
            try:
                created_output_file.unlink()
            except OSError:
                pass
        _print_error(err.code, err.message)
        return 2
    except ValueError as err:
        if created_output_file and created_output_file.exists():
            try:
                created_output_file.unlink()
            except OSError:
                pass
        _print_error("INVALID_REQUEST", str(err))
        return 2
    except (FileNotFoundError, OSError) as err:
        if created_output_file and created_output_file.exists():
            try:
                created_output_file.unlink()
            except OSError:
                pass
        _print_error("IO_ERROR", str(err))
        return 2


def _print_error(code: str, message: str) -> None:
    payload = {"error": {"code": code, "message": message}}
    sys.stderr.write(json.dumps(payload, indent=2) + "\n")
