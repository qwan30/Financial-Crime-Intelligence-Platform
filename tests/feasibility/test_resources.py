import json
import subprocess
import sys
from pathlib import Path

from fincrime.feasibility.resources import collect_resource_profile


def test_resource_profile_reports_positive_disk_capacity(tmp_path: Path) -> None:
    profile = collect_resource_profile(tmp_path)

    assert profile.cpu_count >= 1
    assert profile.ram_bytes > 1
    assert profile.disk_free_bytes > 0
    assert profile.actual_cash_cost_vnd == 0


def test_resource_profile_cli_emits_json(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "fincrime.cli",
            "resource-profile",
            "--workspace",
            str(tmp_path),
        ],
        check=True,
        capture_output=True,
        text=True,
    )

    profile = json.loads(result.stdout)
    assert profile["disk_free_bytes"] > 0
    assert profile["actual_cash_cost_vnd"] == 0
