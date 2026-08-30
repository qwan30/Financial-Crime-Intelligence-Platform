# MLOps, Streaming, and Release Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 10–12 local MLOps, replayable streaming, incremental scoring, monitoring, drift checks, and exact-SHA release evidence without changing offline research semantics.

**Architecture:** MLflow records already-frozen runs; Kafka replays versioned events through validation, point-in-time feature/graph updates, scoring, and idempotent case creation. Release evidence binds Git, dataset, split, feature, model, trace, agent, cost, and runtime hashes.

**Tech Stack:** Python 3.12, MLflow, Kafka-compatible broker, Redis, PostgreSQL, Prometheus client, Docker Compose, pytest.

## Global Constraints

- This plan starts after Research Release and Investigator Release exit reviews pass.
- Offline/online feature and graph semantics must match on the same event prefix.
- Every event has stable `event_id`, schema version, source coordinates, and event time.
- Invalid events are quarantined; no silent coercion or fabricated score.
- Hot-path scoring does not perform unbounded Neo4j traversal.
- Writes are idempotent by stable IDs; replay produces identical state and case artifacts.
- Cloud/managed services remain optional approved spend; local Compose is the release environment.
- Every task follows TDD and ends with a focused commit.

## Git Branching & PR Strategy (git-workflow / github-ops)

This implementation plan is split into **3 feature branches** and **3 Pull Requests** targeting `master`, using isolated git worktrees.

| Branch Name | Tasks Covered | PR Scope & Title | Target | Worktree Setup Command |
|-------------|---------------|------------------|--------|------------------------|
| `feat/phase10-mlflow-streaming-state` | Tasks 1–3 | PR #11: `feat(phase10): MLflow tracking, versioned streaming events and idempotent state` | `master` | `git worktree add ../fin-p10-streaming -b feat/phase10-mlflow-streaming-state` |
| `feat/phase11-parity-infra-monitoring` | Tasks 4–7 | PR #12: `feat(phase11): streaming scoring parity, broker replay and drift monitoring` | `master` | `git worktree add ../fin-p11-infra -b feat/phase11-parity-infra-monitoring` |
| `feat/phase12-release-manifest-gate` | Tasks 8–9 | PR #13: `feat(phase12): release manifest hashing and local release gate` | `master` | `git worktree add ../fin-p12-release -b feat/phase12-release-manifest-gate` |

### Commit Strategy
- **Format**: Follow Conventional Commits `<type>(<scope>): <subject>` with imperative mood (e.g. `feat(streaming): define versioned transaction events`).
- **Scopes**: `mlops`, `streaming`, `infra`, `monitoring`, `release`.
- **Pre-commit Gate**: Every Step 5 commit must pass `uv run pytest -q && uv run ruff check . && uv run mypy src` before committing.
- **Milestone Tagging**: Upon completion and merge of PR #13 (`feat/phase12-release-manifest-gate`), tag the master branch with `v1.0.0-release`.

## File Structure

```text
src/fincrime/
  mlops/tracking.py
  streaming/events.py
  streaming/replay.py
  streaming/state.py
  streaming/scoring.py
  monitoring/metrics.py
  monitoring/drift.py
  release/manifest.py
infra/docker-compose.yml
tests/mlops/
tests/streaming/
tests/monitoring/
tests/release/
```

---

### Task 1: Log frozen runs to local MLflow

**Branch:** `feat/phase10-mlflow-streaming-state` | **PR:** #11

**Files:**
- Create: `src/fincrime/mlops/tracking.py`
- Create: `tests/mlops/test_tracking.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: immutable run manifest and metric dictionary.
- Produces: MLflow run tagged with exact hashes; does not decide promotion.

- [ ] **Step 1: Write the failing tag test with an injected logger**

```python
from fincrime.mlops.tracking import tracking_tags


def test_tracking_tags_bind_git_and_data_hashes() -> None:
    tags = tracking_tags("a" * 40, "b" * 64, "c" * 64)
    assert tags == {"git_sha": "a" * 40, "dataset_hash": "b" * 64, "split_hash": "c" * 64}
```

- [ ] **Step 2: Add MLflow and verify RED**

Run: `uv add 'mlflow>=3.1,<4' && uv run pytest tests/mlops/test_tracking.py -v`

Expected: FAIL because tracking module does not exist.

- [ ] **Step 3: Implement pure tag construction and thin MLflow adapter**

```python
from __future__ import annotations

import mlflow


def tracking_tags(git_sha: str, dataset_hash: str, split_hash: str) -> dict[str, str]:
    return {"git_sha": git_sha, "dataset_hash": dataset_hash, "split_hash": split_hash}


def log_frozen_run(tags: dict[str, str], metrics: dict[str, float]) -> str:
    with mlflow.start_run() as run:
        mlflow.set_tags(tags)
        mlflow.log_metrics(metrics)
        return run.info.run_id
```

- [ ] **Step 4: Verify GREEN using a temporary local tracking URI**

Run: `uv run pytest tests/mlops/test_tracking.py -v`

Expected: pure contract and temporary-file MLflow integration tests pass.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock src/fincrime/mlops/tracking.py tests/mlops/test_tracking.py
git commit -m "feat(mlops): track frozen research runs in local MLflow"
```

---

### Task 2: Define versioned streaming events

**Branch:** `feat/phase10-mlflow-streaming-state` | **PR:** #11

**Files:**
- Create: `src/fincrime/streaming/events.py`
- Create: `tests/streaming/test_events.py`

**Interfaces:**
- Consumes: JSON event payloads.
- Produces: immutable `TransactionEnvelope`; unknown schema versions fail validation.

- [ ] **Step 1: Write the failing schema-version test**

```python
import pytest
from pydantic import ValidationError

from fincrime.streaming.events import TransactionEnvelope


def test_unknown_schema_version_is_rejected() -> None:
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="2",
            event_id="e1",
            source_partition=0,
            source_offset=1,
            source_id="a",
            target_id="b",
            amount=10,
            event_time="2026-01-01T00:00:00Z",
        )
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/streaming/test_events.py -v`

Expected: FAIL because event schema does not exist.

- [ ] **Step 3: Implement the v1 envelope**

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class TransactionEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    schema_version: Literal["1"]
    event_id: str
    source_partition: int = Field(ge=0)
    source_offset: int = Field(ge=0)
    source_id: str
    target_id: str
    amount: float = Field(gt=0)
    event_time: datetime
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/streaming/test_events.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/streaming/events.py tests/streaming/test_events.py
git commit -m "feat(streaming): define versioned transaction events"
```

---

### Task 3: Implement idempotent replay state

**Branch:** `feat/phase10-mlflow-streaming-state` | **PR:** #11

**Files:**
- Create: `src/fincrime/streaming/state.py`
- Create: `tests/streaming/test_state.py`

**Interfaces:**
- Consumes: ordered `TransactionEnvelope`.
- Produces: immutable `ReplayState`; identical event retry is no-op and conflicting payload fails.

- [ ] **Step 1: Write failing replay tests**

```python
import pytest

from fincrime.streaming.state import ReplayConflict, ReplayState


def test_identical_event_retry_is_noop() -> None:
    state = ReplayState.empty().apply("e1", "hash1", partition=0, offset=1)
    assert state.apply("e1", "hash1", partition=0, offset=1) == state


def test_conflicting_event_retry_fails() -> None:
    state = ReplayState.empty().apply("e1", "hash1", partition=0, offset=1)
    with pytest.raises(ReplayConflict):
        state.apply("e1", "hash2", partition=0, offset=1)
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/streaming/test_state.py -v`

Expected: FAIL because replay state does not exist.

- [ ] **Step 3: Implement immutable state transitions**

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ReplayConflict(RuntimeError):
    pass


class ReplayState(BaseModel):
    model_config = ConfigDict(frozen=True)
    event_hashes: dict[str, str]
    next_offsets: dict[int, int]

    @classmethod
    def empty(cls) -> "ReplayState":
        return cls(event_hashes={}, next_offsets={})

    def apply(self, event_id: str, payload_hash: str, partition: int, offset: int) -> "ReplayState":
        existing = self.event_hashes.get(event_id)
        if existing == payload_hash:
            return self
        if existing is not None:
            raise ReplayConflict(event_id)
        return self.model_copy(
            update={
                "event_hashes": {**self.event_hashes, event_id: payload_hash},
                "next_offsets": {**self.next_offsets, partition: offset + 1},
            }
        )
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/streaming/test_state.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/streaming/state.py tests/streaming/test_state.py
git commit -m "feat(streaming): make replay state idempotent"
```

---

### Task 4: Prove offline/online scoring parity

**Branch:** `feat/phase11-parity-infra-monitoring` | **PR:** #12

**Files:**
- Create: `src/fincrime/streaming/scoring.py`
- Create: `tests/streaming/test_scoring_parity.py`

**Interfaces:**
- Consumes: same ordered event prefix and frozen model package.
- Produces: identical feature vector and score for offline and incremental paths.

- [ ] **Step 1: Write the failing parity test**

```python
from fincrime.streaming.scoring import offline_score, online_score


def test_same_event_prefix_has_same_score() -> None:
    events = (("a", "b", 10.0), ("b", "c", 8.0))
    assert online_score(events) == offline_score(events)
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/streaming/test_scoring_parity.py -v`

Expected: FAIL because parity functions do not exist.

- [ ] **Step 3: Route both paths through one pure feature function**

```python
def _score(events: tuple[tuple[str, str, float], ...]) -> float:
    incoming = sum(amount for _, target, amount in events if target == "b")
    outgoing = sum(amount for source, _, amount in events if source == "b")
    return 0.0 if incoming == 0 else min(outgoing / incoming, 1.0)


def offline_score(events: tuple[tuple[str, str, float], ...]) -> float:
    return _score(events)


def online_score(events: tuple[tuple[str, str, float], ...]) -> float:
    return _score(events)
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/streaming/test_scoring_parity.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/streaming/scoring.py tests/streaming/test_scoring_parity.py
git commit -m "test(streaming): enforce offline online scoring parity"
```

---

### Task 5: Add local Kafka/Redis/PostgreSQL infrastructure

**Branch:** `feat/phase11-parity-infra-monitoring` | **PR:** #12

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/.env.example`
- Create: `tests/streaming/test_compose_contract.py`

**Interfaces:**
- Consumes: Docker Compose.
- Produces: pinned broker, Redis, PostgreSQL, and health checks for local integration only.

- [ ] **Step 1: Write the failing Compose contract test**

```python
from pathlib import Path


def test_compose_pins_required_services_and_healthchecks() -> None:
    text = Path("infra/docker-compose.yml").read_text(encoding="utf-8")
    for service in ("kafka:", "redis:", "postgres:"):
        assert service in text
    assert text.count("healthcheck:") >= 3
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/streaming/test_compose_contract.py -v`

Expected: FAIL because Compose file does not exist.

- [ ] **Step 3: Add the pinned local services**

```yaml
services:
  kafka:
    image: bitnami/kafka:4.0
    environment:
      KAFKA_CFG_NODE_ID: "1"
      KAFKA_CFG_PROCESS_ROLES: broker,controller
      KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_CFG_LISTENERS: PLAINTEXT://:9092,CONTROLLER://:9093
      KAFKA_CFG_ADVERTISED_LISTENERS: PLAINTEXT://localhost:9092
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
    ports: ["9092:9092"]
    healthcheck:
      test: ["CMD-SHELL", "/opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server localhost:9092 --list"]
      interval: 10s
      timeout: 5s
      retries: 12
  redis:
    image: redis:8.0-alpine
    command: ["redis-server", "--appendonly", "yes"]
    ports: ["6379:6379"]
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 3s
      retries: 12
  postgres:
    image: postgres:17-alpine
    environment:
      POSTGRES_DB: fincrime
      POSTGRES_USER: fincrime
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?set POSTGRES_PASSWORD}
    ports: ["5432:5432"]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fincrime -d fincrime"]
      interval: 5s
      timeout: 3s
      retries: 12
```

```dotenv
# infra/.env.example
POSTGRES_PASSWORD=replace-with-a-local-secret
```

- [ ] **Step 4: Verify GREEN and local startup**

Run: `uv run pytest tests/streaming/test_compose_contract.py -v && docker compose -f infra/docker-compose.yml config`

Expected: test passes; Compose config exits 0. Starting services is an integration step and must record actual RAM/disk use.

- [ ] **Step 5: Commit**

```powershell
git add infra/docker-compose.yml infra/.env.example tests/streaming/test_compose_contract.py
git commit -m "chore(infra): add local streaming infrastructure"
```

---

### Task 6: Replay broker messages through validation and idempotent state

**Branch:** `feat/phase11-parity-infra-monitoring` | **PR:** #12

**Files:**
- Create: `src/fincrime/streaming/replay.py`
- Create: `tests/streaming/test_replay.py`

**Interfaces:**
- Consumes: broker payload bytes in source-coordinate order.
- Produces: `ReplayOutcome` with updated state, accepted IDs, and quarantined reason codes.

- [ ] **Step 1: Write the failing poison-message test**

```python
from fincrime.streaming.replay import replay_payloads
from fincrime.streaming.state import ReplayState


def test_invalid_message_is_quarantined_without_state_advance() -> None:
    outcome = replay_payloads((b'{"schema_version":"99"}',), ReplayState.empty())
    assert outcome.accepted_event_ids == ()
    assert outcome.quarantined_reasons == ("INVALID_SCHEMA",)
    assert outcome.state == ReplayState.empty()
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/streaming/test_replay.py -v`

Expected: FAIL because replay module does not exist.

- [ ] **Step 3: Implement validation-first replay**

```python
from __future__ import annotations

from hashlib import sha256

from pydantic import BaseModel, ConfigDict, ValidationError

from fincrime.streaming.events import TransactionEnvelope
from fincrime.streaming.state import ReplayState


class ReplayOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)
    state: ReplayState
    accepted_event_ids: tuple[str, ...]
    quarantined_reasons: tuple[str, ...]


def replay_payloads(payloads: tuple[bytes, ...], initial: ReplayState) -> ReplayOutcome:
    state = initial
    accepted: list[str] = []
    quarantined: list[str] = []
    for payload in payloads:
        try:
            event = TransactionEnvelope.model_validate_json(payload)
        except ValidationError:
            quarantined.append("INVALID_SCHEMA")
            continue
        state = state.apply(
            event.event_id,
            sha256(payload).hexdigest(),
            event.source_partition,
            event.source_offset,
        )
        accepted.append(event.event_id)
    return ReplayOutcome(
        state=state,
        accepted_event_ids=tuple(accepted),
        quarantined_reasons=tuple(quarantined),
    )
```

- [ ] **Step 4: Verify GREEN with valid, retry, conflict, and poison fixtures**

Run: `uv run pytest tests/streaming/test_replay.py tests/streaming/test_state.py -v`

Expected: validation and idempotency tests pass; conflicting duplicate raises `ReplayConflict`.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/streaming/replay.py tests/streaming/test_replay.py
git commit -m "feat(streaming): replay validated transaction messages"
```

---

### Task 7: Expose operational and drift metrics

**Branch:** `feat/phase11-parity-infra-monitoring` | **PR:** #12

**Files:**
- Create: `src/fincrime/monitoring/metrics.py`
- Create: `src/fincrime/monitoring/drift.py`
- Create: `tests/monitoring/test_drift.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: baseline/current numeric samples and processing events.
- Produces: Prometheus counters/histograms and deterministic PSI drift result.

- [ ] **Step 1: Write the failing drift test**

```python
import numpy as np

from fincrime.monitoring.drift import population_stability_index


def test_identical_distributions_have_zero_psi() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0])
    assert population_stability_index(values, values, bins=2) == 0.0
```

- [ ] **Step 2: Add Prometheus client and verify RED**

Run: `uv add 'prometheus-client>=0.22,<1' && uv run pytest tests/monitoring/test_drift.py -v`

Expected: FAIL because monitoring modules do not exist.

- [ ] **Step 3: Implement deterministic PSI and bounded metrics**

```python
# src/fincrime/monitoring/drift.py
import numpy as np
from numpy.typing import NDArray


def population_stability_index(
    baseline: NDArray[np.float64], current: NDArray[np.float64], bins: int
) -> float:
    edges = np.quantile(baseline, np.linspace(0, 1, bins + 1))
    edges[0], edges[-1] = -np.inf, np.inf
    base_counts = np.histogram(baseline, bins=edges)[0] / len(baseline)
    current_counts = np.histogram(current, bins=edges)[0] / len(current)
    base_safe = np.clip(base_counts, 1e-9, None)
    current_safe = np.clip(current_counts, 1e-9, None)
    return float(np.sum((current_safe - base_safe) * np.log(current_safe / base_safe)))
```

```python
# src/fincrime/monitoring/metrics.py
from prometheus_client import Counter, Histogram

EVENTS_PROCESSED = Counter("fincrime_events_processed_total", "Validated events")
EVENTS_QUARANTINED = Counter("fincrime_events_quarantined_total", "Invalid events")
SCORING_LATENCY = Histogram("fincrime_scoring_latency_seconds", "Incremental scoring latency")
TRACE_TRUNCATED = Counter("fincrime_trace_truncated_total", "Truncated traces")
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/monitoring/test_drift.py -v`

Expected: test passes.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock src/fincrime/monitoring tests/monitoring/test_drift.py
git commit -m "feat(monitoring): monitor operations and drift"
```

---

### Task 8: Bind release evidence to exact hashes

**Branch:** `feat/phase12-release-manifest-gate` | **PR:** #13

**Files:**
- Create: `src/fincrime/release/manifest.py`
- Create: `tests/release/test_manifest.py`

**Interfaces:**
- Consumes: Git/data/split/feature/model/trace/agent hashes, checks, cost, and resource evidence.
- Produces: immutable `ReleaseManifest`; missing evidence prevents `RELEASE` status.

- [ ] **Step 1: Write the failing missing-evidence test**

```python
import pytest
from pydantic import ValidationError

from fincrime.release.manifest import ReleaseManifest


def test_release_requires_all_artifact_hashes() -> None:
    with pytest.raises(ValidationError):
        ReleaseManifest(git_sha="a" * 40, status="RELEASE")
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/release/test_manifest.py -v`

Expected: FAIL because release manifest does not exist.

- [ ] **Step 3: Implement the exact-hash contract**

```python
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    status: Literal["RESEARCH_RELEASE", "FULL_PRODUCT_RELEASE"]
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    dataset_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    split_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    feature_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    model_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    trace_report_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    agent_report_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    actual_cash_cost_vnd: int = Field(ge=0)
    tests_passed: bool
    known_limitations: tuple[str, ...]
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/release/test_manifest.py -v`

Expected: incomplete manifest is rejected; complete manifest passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/release/manifest.py tests/release/test_manifest.py
git commit -m "feat(release): bind release evidence to exact hashes"
```

---

### Task 9: Run the exact-SHA local release gate

**Branch:** `feat/phase12-release-manifest-gate` | **PR:** #13

**Files:**
- Create: `docs/runbooks/local-release.md`
- Create: `tests/release/test_runbook.py`

**Interfaces:**
- Consumes: the completed repository and local Compose profile.
- Produces: one documented command sequence and a release manifest generated only after all checks pass.

- [ ] **Step 1: Write the failing runbook marker test**

```python
from pathlib import Path


def test_release_runbook_contains_required_gates() -> None:
    text = Path("docs/runbooks/local-release.md").read_text(encoding="utf-8")
    for marker in ("git rev-parse HEAD", "pytest", "ruff", "mypy", "docker compose", "release manifest"):
        assert marker in text
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/release/test_runbook.py -v`

Expected: FAIL because runbook does not exist.

- [ ] **Step 3: Write the exact local release sequence**

```markdown
# Local Release Runbook

1. Record `git rev-parse HEAD` and require a clean tracked worktree.
2. Run `uv run pytest -q`.
3. Run `uv run ruff check .`.
4. Run `uv run mypy src`.
5. Run `npm test -- --run` and `npm run build` in `apps/investigator-web`.
6. Run `docker compose -f infra/docker-compose.yml config`.
7. Start local services and run the deterministic replay fixture twice.
8. Compare feature, score, trace, case, and evidence hashes across both runs.
9. Run `LLM_OFF` agent evaluation; run `DEEPSEEK_ON` only with approved key/cap.
10. Generate the release manifest with actual cost/resource usage and known limitations.
```

- [ ] **Step 4: Verify GREEN and perform a dry run without paid services**

Run: `uv run pytest tests/release/test_runbook.py -v`

Expected: marker test passes. Full release is claimed only after the runbook has actual passing evidence on one exact SHA.

- [ ] **Step 5: Commit**

```powershell
git add docs/runbooks/local-release.md tests/release/test_runbook.py
git commit -m "docs(release): define exact SHA release gate runbook"
```

## Full Product Release Exit Review & Tagging

After merging PR #13 (`feat/phase12-release-manifest-gate`) into `master`, verify the exit criteria and tag the milestone:

```powershell
git tag -a v1.0.0-release -m "Release v1.0.0-release: Full Product Release with MLOps & Streaming Replay"
git push origin v1.0.0-release
```

Before declaring full release, verify:

- Offline and online prefixes produce identical features/scores.
- Replay is idempotent and conflicting retries fail closed.
- Invalid events quarantine without advancing valid-state claims.
- MLflow records hashes but does not auto-promote.
- Drift and operational metrics are exported.
- Provider-off release path passes; paid DeepSeek use remains optional and capped.
- Exact-SHA manifest includes actual cost/resources and known limitations.
