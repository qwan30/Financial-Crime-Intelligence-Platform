# Local Release Runbook

This runbook defines the authoritative 10-step verification sequence required to produce a valid `ReleaseManifest` and qualify for Production Certification under SLP Governance.

1. **Working Tree Cleanliness:** Record `rtk git rev-parse HEAD` and verify working tree has zero untracked or uncommitted changes.
2. **Python Test Suite:** Execute `rtk uv run pytest -q` and verify 100% pass rate.
3. **Python Lint Suite:** Execute `rtk uv run ruff check .` with zero violations.
4. **Python Type Safety:** Execute `rtk uv run mypy src` in strict mode with zero errors.
5. **Frontend Suite:** Run `rtk npm test -- --run && rtk npm run build` inside `apps/investigator-web/`.
6. **Infrastructure Config:** Ensure `infra/.env.example` is populated with `POSTGRES_PASSWORD` and execute `rtk docker compose -f infra/docker-compose.yml config`.
7. **Replay Determinism:** Execute deterministic streaming replay fixture twice and verify bitwise identical `ReplayState`.
8. **Parity Check:** Confirm offline and online scoring paths return identical values on the same event prefix.
9. **Budget & Drift Evaluation:** Verify LLM agent evaluation under `LLM_OFF` and check PSI drift metrics are strictly bounded below threshold.
10. **Manifest Generation:** Generate `ReleaseManifest` binding exact SHA-256 hashes of all mandatory status-specific artifacts and record final status in `.orchestration/decision-log.md`.
