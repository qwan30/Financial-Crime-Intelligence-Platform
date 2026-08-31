from __future__ import annotations

import argparse
import shutil
from pathlib import Path

from fincrime.feasibility.resources import collect_resource_profile


def _existing_directory(value: str) -> Path:
    workspace = Path(value)
    if not workspace.is_dir():
        raise argparse.ArgumentTypeError("workspace must be an existing directory")
    return workspace


def main() -> int:
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="command", required=True)
    resource = subparsers.add_parser("resource-profile")
    resource.add_argument("--workspace", type=_existing_directory, default=Path.cwd())

    run = subparsers.add_parser("write-run-artifact")
    run.add_argument("--path", type=Path, required=True)
    run.add_argument("--run-id", required=True)

    pilot = subparsers.add_parser("pilot-admission")
    pilot.add_argument("--workspace", type=_existing_directory, default=Path.cwd())
    pilot.add_argument("--source-id", default="amlbench-slice")
    pilot.add_argument("--archive-bytes", type=int, required=True)
    pilot.add_argument("--extraction-bytes", type=int, required=True)
    pilot.add_argument("--processed-bytes", type=int, required=True)
    pilot.add_argument("--temporary-bytes", type=int, required=True)
    pilot.add_argument("--headroom-bytes", type=int, required=True)

    args = parser.parse_args()

    if args.command == "resource-profile":
        print(collect_resource_profile(args.workspace).model_dump_json(indent=2))
        return 0
    if args.command == "write-run-artifact":
        from fincrime.training.runner import write_run_artifact

        write_run_artifact(args.path, {"run_id": args.run_id})
        return 0
    if args.command == "pilot-admission":
        from fincrime.data.pilot import pilot_admission

        disk_free = shutil.disk_usage(args.workspace).free
        evidence = pilot_admission(
            source_id=args.source_id,
            disk_free_bytes=disk_free,
            archive_bytes=args.archive_bytes,
            extraction_bytes=args.extraction_bytes,
            processed_bytes=args.processed_bytes,
            temporary_bytes=args.temporary_bytes,
            safety_headroom_bytes=args.headroom_bytes,
        )
        print(evidence.model_dump_json(indent=2))
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
