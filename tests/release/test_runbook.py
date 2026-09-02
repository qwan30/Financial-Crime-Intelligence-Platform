from pathlib import Path


def test_release_runbook_contains_required_verification_gates() -> None:
    runbook_path = Path("docs/runbooks/local-release.md")
    assert runbook_path.exists(), "docs/runbooks/local-release.md must exist"
    text = runbook_path.read_text(encoding="utf-8")
    for marker in (
        "rtk git rev-parse HEAD",
        "rtk uv run pytest -q",
        "rtk uv run ruff check .",
        "rtk uv run mypy src",
        "rtk npm test",
        "rtk docker compose -f infra/docker-compose.yml config",
        "ReleaseManifest",
    ):
        assert marker in text, f"Missing required gate marker '{marker}' in local release runbook"
