from __future__ import annotations

import argparse
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

    args = parser.parse_args()

    if args.command == "resource-profile":
        print(collect_resource_profile(args.workspace).model_dump_json(indent=2))
        return 0
    if args.command == "write-run-artifact":
        from fincrime.training.runner import write_run_artifact

        write_run_artifact(args.path, {"run_id": args.run_id})
        return 0
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
