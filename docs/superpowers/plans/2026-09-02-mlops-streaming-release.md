# MLOps, Streaming Replay & Release Evidence Implementation Plan (Authoritative v15.0)

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:dispatching-parallel-agents to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement Phase 10–12 of the Financial Crime Intelligence Platform: local MLflow tracking with internal read-back verification, canonical streaming event envelopes with exact second UTC precision, deeply immutable replay state with validated transitions, true offline/online feature scoring parity with neighbor-grouped cumulative accumulation matching NetworkX edge iteration, local container infrastructure with dual internal/external Kafka listeners, broker replay with coordinate-aware true duplicate no-ops, durable JSONL poison quarantine and partition commit barriers, validated fitted PSI drift bin contracts with finite interior machine-precision monotonicity across all baseline magnitudes, status-specific exact-inventory release manifest builder/verifier with repository-derived HEAD (and test-only resolver injection), and local release runbook verification under mandatory `rtk` command discipline.

**Architecture:** 
1. **MLflow Tracking:** Frozen runs are tracked to local MLflow with verified lowercase 40/64-hex artifact hashes and isolated client state, failing closed internally if read-back verification fails.
2. **Canonical Event Model:** Streaming events enforce canonical compact JSON formatting, strict UTC timestamps with zero microseconds (`%Y-%m-%dT%H:%M:%SZ`), and lowercase 64-hex SHA-256 payload integrity.
3. **True Incremental Scoring Parity:** `OnlineGraphAccumulator` maintains direct, neighbor-grouped cumulative edge sequences `incoming_neighbor_edges` and `outgoing_neighbor_edges` preserving neighbor-first insertion order. Ingestion strictly enforces canonical monotonic `(event_time, edge_id)` ordering and duplicate `edge_id` rejection matching `build_graph`. Feature extraction iterates neighbor groups in exact NetworkX `MultiDiGraph` iteration order (`_pred[u]` and `_succ[u]`), passing the exact sequence of float amounts to `sum()`, guaranteeing 100% bitwise exact parity against the production offline graph oracle (`build_graph(events, cutoff=cutoff)` + `account_features(graph, account_id)`).
4. **Broker Replay & True No-Op Commit Barrier:** Replay processes structured `BrokerRecord` inputs, checks coordinate-aware duplicate retry as an immediate no-op (no quarantine side-effect, no cursor change), enforces `ReplayConflict` on same-ID coordinate/payload divergence, persists malformed/gap records to durable `DurableFileQuarantineStore` with full coordinates, and freezes `committable_offsets` strictly at the expected contiguous offset before poison records to prevent broker cursor skips.
5. **Fitted PSI Drift Contract:** Baseline distribution is fitted into immutable `FittedPSIBins` with verified `[-inf, ...finite..., +inf]` endpoints and `all(left < right)` machine-precision monotonicity using a clamp-and-sweep forward/backward `np.nextafter` repair across extreme float baselines, calculating deterministic `PSIDriftResult` with model-enforced `drift_detected == is_drift_detected(psi, threshold)`.
6. **Exact-Inventory Release Manifest with Production Git Default:** `ReleaseManifest`, `build_release_manifest`, and `verify_release_manifest` enforce exact mathematical set equality `artifact_names == set(get_mandatory_inventory(status))` (rejecting both missing and extra unexpected files), default in production strictly to `get_repo_git_sha()` (with `sha_resolver` as a test-only injection hook), validate PSI drift status independently, and catch all IO/filesystem errors fail-closed.
7. **Hardened Local Infrastructure:** Local Compose defines dual KRaft listeners (`INTERNAL://kafka:9092,EXTERNAL://127.0.0.1:9092`) bound to `127.0.0.1` with explicit health checks and no fallback passwords.

**Tech Stack:** Python 3.12, Pydantic 2 (`frozen=True, extra="forbid", strict=True`), MLflow Skinny (`mlflow-skinny>=3.0`), Prometheus Client, NumPy, PyYAML, Docker Compose (Bitnami Kafka 4.0, Redis 8.0 Alpine, PostgreSQL 17 Alpine bound to 127.0.0.1), Pytest, Ruff, MyPy.

**Spec:** `.orchestration/tasks/TASK-004-mlops-streaming-release.md` and `.orchestration/decision-log.md` (Decisions 001, 009, 010, 011).

## Global Constraints

- **Python 3.12 & Strict Immutability:** 100% frozen immutable Pydantic models with `extra="forbid", strict=True`. Collections in state models must be immutable sorted tuples. Transitions must construct new validated models (no unvalidated `model_copy(update=...)`).
- **Canonical Serialization & UTC:** Datetime values must be timezone-aware UTC with zero microseconds (`%Y-%m-%dT%H:%M:%SZ`). Hashes must be lowercase 64-character hex strings computed via canonical JSON normalization.
- **True Cumulative Parity & Neighbor-Grouped Invariant:** `OnlineGraphAccumulator` aggregates amounts in canonical `(event_time, edge_id)` monotonic stream order, groups edges by neighbor matching NetworkX iteration order, and rejects duplicate `edge_id`s with `ValueError`. Feature extraction bitwise matches `AccountFeatures` derived by `account_features(build_graph(events, cutoff=cutoff), account_id)`.
- **Deterministic Replay & Broker Barrier:** Replay state must be contiguous per `(topic, partition)`. Exact duplicate events at the same coordinates are true no-ops with zero side-effects. Conflicting payloads or duplicate IDs at different coordinates must fail closed with `ReplayConflict`. Poison payloads must persist to `QuarantineStore` with full coordinates, freezing the committable offset at the expected contiguous cursor and halting further consumption on that partition.
- **Exact-Inventory Manifest:** `ReleaseManifest` models and verification functions strictly require exact set equality with `get_mandatory_inventory(status)`, rejecting missing or extra artifacts. In production, `build_release_manifest` and `verify_release_manifest` derive HEAD from `get_repo_git_sha()` (with `sha_resolver` as a test-only injection hook). Any IO/file error returns `False`.
- **Local-First Infrastructure:** All services bound strictly to `127.0.0.1` with dual internal/external listeners.
- **Command Prefix:** All shell commands must be prefixed with `rtk` (e.g., `rtk uv run pytest -q && rtk uv run ruff check . && rtk uv run mypy src`).

---

## Agent Team & SLP Subagent Dispatch DAG

```mermaid
graph TD
    subgraph Wave 0: Shared Dependency Scaffolding
        W0[Integrator: Install mlflow-skinny, prometheus-client, pyyaml<br/>Shared pyproject.toml & uv.lock lockfile via rtk]
    end

    subgraph Wave 1: Foundation & Contracts
        W1A[Worker 1A: MLflow Tracking & Provenance<br/>Task 1]
        W1B[Worker 1B: Streaming Envelopes & Replay State<br/>Tasks 2 & 3]
        W1C[Worker 1C: Local Compose Infrastructure<br/>Task 5]
    end

    subgraph Wave 2: Streaming Parity, Replay & Monitoring
        W2A[Worker 2A: True Offline/Online Scoring Parity<br/>Task 4]
        W2B[Worker 2B: Broker Replay, Durable Quarantine & Commit Barrier<br/>Task 6]
        W2C[Worker 2C: Prometheus & Fitted PSI Drift Metrics<br/>Task 7]
    end

    subgraph Wave 3: Release Manifest & Gate Runbook
        W3[Worker 3: Artifact Manifest & Release Runbook<br/>Tasks 8 & 9]
    end

    W0 --> W1A & W1B & W1C & W2A & W2B & W2C & W3
    W1B --> W2A
    W1B --> W2B
    W1A & W1C & W2A & W2B & W2C --> W3
```

---

## Detailed Task Breakdown

### Wave 0: Install Shared Dependencies (Prerequisite: `rtk` available on PATH)

- [ ] **Step 0.1: Add shared dependencies in one atomic step**

Run: `rtk uv add "mlflow-skinny>=3.0" "prometheus-client>=0.21,<1" "pyyaml>=6.0,<7"`

- [ ] **Step 0.2: Verify baseline test suite remains 100% green**

Run: `rtk uv run pytest -q && rtk uv run ruff check . && rtk uv run mypy src`
Expected: 454/454 passing, Ruff clean, MyPy clean.

- [ ] **Step 0.3: Commit baseline dependencies**

```bash
rtk git add pyproject.toml uv.lock && rtk git commit -m "chore(deps): add mlflow-skinny, prometheus-client, and pyyaml for Plan 4"
```

---

### Task 1: Log Frozen Runs to Local MLflow with Read-Back Verification

**Files:**
- Create: `src/fincrime/mlops/__init__.py`
- Create: `src/fincrime/mlops/tracking.py`
- Create: `tests/mlops/__init__.py`
- Create: `tests/mlops/test_tracking.py`

**Interfaces:**
- Consumes: validated lowercase 40-char git SHA, 64-char dataset/split hashes, finite metrics dictionary.
- Produces: `tracking_tags(...) -> dict[str, str]`, `log_frozen_run(...) -> str` with verified internal read-back via `MlflowClient`.

- [ ] **Step 1: Write the failing tracking test with read-back verification**

```python
# tests/mlops/test_tracking.py
from pathlib import Path
import pytest
from fincrime.mlops.tracking import tracking_tags, log_frozen_run, get_run_metadata


def test_tracking_tags_bind_and_validate_hashes() -> None:
    tags = tracking_tags("a" * 40, "b" * 64, "c" * 64)
    assert tags == {
        "git_sha": "a" * 40,
        "dataset_hash": "b" * 64,
        "split_hash": "c" * 64,
    }


def test_invalid_hash_format_rejected() -> None:
    with pytest.raises(ValueError):
        tracking_tags("short_sha", "b" * 64, "c" * 64)
    with pytest.raises(ValueError):
        tracking_tags("A" * 40, "b" * 64, "c" * 64)


def test_log_frozen_run_records_and_reads_back_cleanly(tmp_path: Path) -> None:
    tracking_uri = f"sqlite:///{tmp_path / 'mlflow.db'}"
    tags = tracking_tags("a" * 40, "b" * 64, "c" * 64)
    metrics = {"roc_auc": 0.885, "pr_auc": 0.652}
    
    run_id = log_frozen_run(tags, metrics, tracking_uri=tracking_uri, experiment_name="test_frozen")
    assert isinstance(run_id, str) and len(run_id) > 0
    
    meta = get_run_metadata(run_id, tracking_uri=tracking_uri)
    assert meta["tags"]["git_sha"] == "a" * 40
    assert meta["tags"]["dataset_hash"] == "b" * 64
    assert meta["metrics"]["roc_auc"] == pytest.approx(0.885)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/mlops/test_tracking.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.mlops'`

- [ ] **Step 3: Implement MLflow logger with internal read-back verification**

```python
# src/fincrime/mlops/__init__.py
"""MLOps tracking and lineage management."""

# src/fincrime/mlops/tracking.py
from __future__ import annotations
import math
import re
from typing import Any
from mlflow.tracking import MlflowClient

_GIT_SHA_REGEX = re.compile(r"^[0-9a-f]{40}$")
_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")


def tracking_tags(git_sha: str, dataset_hash: str, split_hash: str) -> dict[str, str]:
    if not _GIT_SHA_REGEX.match(git_sha):
        raise ValueError(
            f"Invalid git_sha: must be 40-character lowercase hex string, got '{git_sha}'"
        )
    if not _HEX64_REGEX.match(dataset_hash):
        raise ValueError(
            f"Invalid dataset_hash: must be 64-character lowercase hex string, got '{dataset_hash}'"
        )
    if not _HEX64_REGEX.match(split_hash):
        raise ValueError(
            f"Invalid split_hash: must be 64-character lowercase hex string, got '{split_hash}'"
        )
    return {
        "git_sha": git_sha,
        "dataset_hash": dataset_hash,
        "split_hash": split_hash,
    }


def log_frozen_run(
    tags: dict[str, str],
    metrics: dict[str, float],
    tracking_uri: str,
    experiment_name: str = "fincrime_research_frozen",
) -> str:
    for k, v in metrics.items():
        if not math.isfinite(v):
            raise ValueError(f"Metric '{k}' must be finite, got '{v}'")

    client = MlflowClient(tracking_uri=tracking_uri)
    experiment = client.get_experiment_by_name(experiment_name)
    if experiment is None:
        exp_id = client.create_experiment(experiment_name)
    else:
        exp_id = experiment.experiment_id

    run = client.create_run(experiment_id=exp_id, tags=tags)
    for k, v in metrics.items():
        client.log_metric(run.info.run_id, k, v)
    client.set_terminated(run.info.run_id, status="FINISHED")

    # Internal read-back verification (fail closed on mismatch)
    persisted = client.get_run(run.info.run_id)
    if persisted.info.status != "FINISHED":
        raise RuntimeError(
            f"MLflow run {run.info.run_id} status mismatch: expected FINISHED, got {persisted.info.status}"
        )
    for tk, tv in tags.items():
        if persisted.data.tags.get(tk) != tv:
            raise RuntimeError(
                f"MLflow tag mismatch on '{tk}': expected '{tv}', got '{persisted.data.tags.get(tk)}'"
            )
    for mk, mv in metrics.items():
        persisted_val = persisted.data.metrics.get(mk)
        if persisted_val is None or not math.isclose(persisted_val, mv, abs_tol=1e-6):
            raise RuntimeError(
                f"MLflow metric mismatch on '{mk}': expected {mv}, got {persisted_val}"
            )

    return str(run.info.run_id)


def get_run_metadata(run_id: str, tracking_uri: str) -> dict[str, Any]:
    client = MlflowClient(tracking_uri=tracking_uri)
    run = client.get_run(run_id)
    return {
        "run_id": run.info.run_id,
        "status": run.info.status,
        "tags": dict(run.data.tags),
        "metrics": dict(run.data.metrics),
    }
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/mlops/test_tracking.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/mlops tests/mlops && rtk git commit -m "feat(mlops): track frozen research runs in local MLflow with verified read-back"
```

---

### Task 2: Define Canonical Versioned Streaming Event Envelopes

**Files:**
- Create: `src/fincrime/streaming/__init__.py`
- Create: `src/fincrime/streaming/events.py`
- Create: `tests/streaming/__init__.py`
- Create: `tests/streaming/test_events.py`

**Interfaces:**
- Consumes: JSON / dictionary transaction payloads.
- Produces: `TransactionEnvelope` (strict frozen model, canonical UTC datetime with 0 microseconds, `canonical_hash() -> str`, `to_canonical_bytes() -> bytes`).

- [ ] **Step 1: Write failing event envelope, microsecond rejection, and golden bytes tests**

```python
# tests/streaming/test_events.py
from datetime import datetime, timezone
import pytest
from pydantic import ValidationError
from fincrime.streaming.events import TransactionEnvelope


def test_valid_transaction_envelope_canonical_hash_and_golden_bytes() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    env = TransactionEnvelope(
        schema_version="1",
        event_id="evt_tx_001",
        source_partition=0,
        source_offset=105,
        source_id="acc_source_1",
        target_id="acc_target_2",
        amount=1500000.0,
        event_time=now,
    )
    assert env.schema_version == "1"
    assert env.amount == 1500000.0
    
    expected_bytes = b'{"amount":1500000.0,"event_id":"evt_tx_001","event_time":"2026-09-02T12:00:00Z","schema_version":"1","source_id":"acc_source_1","source_offset":105,"source_partition":0,"target_id":"acc_target_2"}'
    assert env.to_canonical_bytes() == expected_bytes
    
    h1 = env.canonical_hash()
    assert len(h1) == 64
    assert h1 == h1.lower()


def test_microsecond_timestamp_rejected() -> None:
    dt_with_us = datetime(2026, 9, 2, 12, 0, 0, 123456, tzinfo=timezone.utc)
    with pytest.raises(ValidationError) as exc_info:
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=dt_with_us,
        )
    assert "microsecond must be 0" in str(exc_info.value)


def test_naive_datetime_and_non_utc_rejected() -> None:
    naive_dt = datetime(2026, 9, 2, 12, 0, 0)
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=1500000.0,
            event_time=naive_dt,
        )


def test_non_finite_or_negative_amount_rejected() -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    with pytest.raises(ValidationError):
        TransactionEnvelope(
            schema_version="1",
            event_id="evt_tx_001",
            source_partition=0,
            source_offset=105,
            source_id="acc_source_1",
            target_id="acc_target_2",
            amount=-50.0,
            event_time=now,
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/streaming/test_events.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.streaming'`

- [ ] **Step 3: Implement TransactionEnvelope with canonical hashing**

```python
# src/fincrime/streaming/__init__.py
"""Streaming ingestion, replay, and scoring state."""

# src/fincrime/streaming/events.py
from __future__ import annotations
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator


class TransactionEnvelope(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    schema_version: Literal["1"]
    event_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-:]+$")
    source_partition: int = Field(ge=0)
    source_offset: int = Field(ge=0)
    source_id: str = Field(min_length=1)
    target_id: str = Field(min_length=1)
    amount: float = Field(gt=0.0)
    event_time: datetime

    @field_validator("amount")
    @classmethod
    def validate_finite_amount(cls, v: float) -> float:
        if not math.isfinite(v) or v <= 0.0:
            raise ValueError(f"amount must be finite and positive, got {v}")
        return v

    @field_validator("event_time")
    @classmethod
    def validate_utc_datetime(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None:
            raise ValueError("event_time must be timezone-aware UTC")
        if v.utcoffset() != timezone.utc.utcoffset(v):
            raise ValueError("event_time must be in UTC (+00:00)")
        if v.microsecond != 0:
            raise ValueError(
                "event_time microsecond must be 0 for exact second canonical precision"
            )
        return v

    def to_canonical_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "event_id": self.event_id,
            "source_partition": self.source_partition,
            "source_offset": self.source_offset,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "amount": self.amount,
            "event_time": self.event_time.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

    def to_canonical_bytes(self) -> bytes:
        return json.dumps(
            self.to_canonical_dict(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
        ).encode("utf-8")

    def canonical_hash(self) -> str:
        return hashlib.sha256(self.to_canonical_bytes()).hexdigest().lower()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/streaming/test_events.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/streaming/events.py tests/streaming/test_events.py src/fincrime/streaming/__init__.py tests/streaming/__init__.py && rtk git commit -m "feat(streaming): define canonical versioned transaction events"
```

---

### Task 3: Implement Deeply Immutable Replay State with Fully Validated Transitions

**Files:**
- Create: `src/fincrime/streaming/state.py`
- Create: `tests/streaming/test_state.py`

**Interfaces:**
- Consumes: `topic: str`, `partition: int`, `offset: int`, `event_id: str`, `payload_hash: str`.
- Produces: `ReplayState` with strictly contiguous partition progression; raises `ReplayConflict` on payload hash mismatch, non-contiguous offset jumps, or duplicate event IDs at differing coordinates. Validates all transitions via model construction (no unvalidated `model_copy`).

- [ ] **Step 1: Write failing replay state, invariant validation, and continuity tests**

```python
# tests/streaming/test_state.py
import pytest
from pydantic import ValidationError
from fincrime.streaming.state import ReplayConflict, ReplayState


def test_empty_replay_state() -> None:
    state = ReplayState.empty()
    assert state.event_entries == ()
    assert state.partition_offsets == ()


def test_apply_contiguous_event_advances_state() -> None:
    state0 = ReplayState.empty()
    state1 = state0.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    assert state1.get_offset("tx", 0) == 1
    assert state1.get_hash("evt_1") == "a" * 64

    state2 = state1.apply("tx", partition=0, offset=1, event_id="evt_2", payload_hash="b" * 64)
    assert state2.get_offset("tx", 0) == 2


def test_identical_event_retry_at_same_coordinate_is_true_noop() -> None:
    state1 = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    state2 = state1.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    assert state1 == state2


def test_conflicting_event_payload_raises_conflict() -> None:
    state = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    with pytest.raises(ReplayConflict) as exc_info:
        state.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="c" * 64)
    assert "evt_1" in str(exc_info.value)


def test_duplicate_event_id_at_different_offset_raises_conflict() -> None:
    state = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64
    )
    with pytest.raises(ReplayConflict):
        state.apply("tx", partition=0, offset=1, event_id="evt_1", payload_hash="a" * 64)


def test_apply_path_validates_blank_and_negative_inputs() -> None:
    state = ReplayState.empty()
    with pytest.raises(ValueError):
        state.apply("tx", partition=-1, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("", partition=0, offset=0, event_id="evt_1", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=0, event_id="", payload_hash="a" * 64)
    with pytest.raises(ValueError):
        state.apply("tx", partition=0, offset=0, event_id="evt_1", payload_hash="A" * 64)


def test_direct_construction_invariants_enforced() -> None:
    with pytest.raises(ValidationError):
        ReplayState(
            event_entries=(("evt_1", "tx", 0, 0, "a" * 64), ("evt_1", "tx", 0, 1, "a" * 64)),
            partition_offsets=(("tx", 0, 1),),
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/streaming/test_state.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.streaming.state'`

- [ ] **Step 3: Implement deeply immutable ReplayState with fully validated transitions**

```python
# src/fincrime/streaming/state.py
from __future__ import annotations
import re
from pydantic import BaseModel, ConfigDict, Field, field_validator

_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")


class ReplayConflict(RuntimeError):
    """Raised when an event ID conflicts or offset sequence is non-contiguous."""


class ReplayState(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # Stored as immutable sorted tuples: ((event_id, topic, partition, offset, payload_hash), ...)
    event_entries: tuple[tuple[str, str, int, int, str], ...] = Field(default_factory=tuple)
    partition_offsets: tuple[tuple[str, int, int], ...] = Field(default_factory=tuple)

    @field_validator("event_entries")
    @classmethod
    def validate_entries(
        cls, v: tuple[tuple[str, str, int, int, str], ...]
    ) -> tuple[tuple[str, str, int, int, str], ...]:
        seen_events: set[str] = set()
        for event_id, topic, partition, offset, h in v:
            if not event_id.strip() or not topic.strip():
                raise ValueError("event_id and topic must not be blank")
            if partition < 0 or offset < 0:
                raise ValueError("partition and offset must be non-negative")
            if not _HEX64_REGEX.match(h):
                raise ValueError(f"Invalid lowercase SHA-256 hash '{h}' for event '{event_id}'")
            if event_id in seen_events:
                raise ValueError(f"Duplicate event_id '{event_id}' in ReplayState entries")
            seen_events.add(event_id)
        if v != tuple(sorted(v, key=lambda x: x[0])):
            raise ValueError("event_entries must be sorted by event_id")
        return v

    @field_validator("partition_offsets")
    @classmethod
    def validate_offsets(
        cls, v: tuple[tuple[str, int, int], ...]
    ) -> tuple[tuple[str, int, int], ...]:
        seen_keys: set[tuple[str, int]] = set()
        for topic, partition, off in v:
            if not topic.strip():
                raise ValueError("topic must not be blank")
            if partition < 0 or off < 0:
                raise ValueError("partition and offset must be non-negative")
            key = (topic, partition)
            if key in seen_keys:
                raise ValueError(f"Duplicate topic-partition key '{key}' in ReplayState offsets")
            seen_keys.add(key)
        if v != tuple(sorted(v, key=lambda x: (x[0], x[1]))):
            raise ValueError("partition_offsets must be sorted by (topic, partition)")
        return v

    @classmethod
    def empty(cls) -> "ReplayState":
        return cls(event_entries=(), partition_offsets=())

    def get_entry(self, event_id: str) -> tuple[str, str, int, int, str] | None:
        for entry in self.event_entries:
            if entry[0] == event_id:
                return entry
        return None

    def get_hash(self, event_id: str) -> str | None:
        entry = self.get_entry(event_id)
        return entry[4] if entry is not None else None

    def get_offset(self, topic: str, partition: int) -> int:
        for t, p, off in self.partition_offsets:
            if t == topic and p == partition:
                return off
        return 0

    def apply(
        self,
        topic: str,
        partition: int,
        offset: int,
        event_id: str,
        payload_hash: str,
    ) -> "ReplayState":
        if not topic.strip() or not event_id.strip():
            raise ValueError("topic and event_id must not be blank")
        if partition < 0 or offset < 0:
            raise ValueError("partition and offset must be non-negative")
        if not _HEX64_REGEX.match(payload_hash):
            raise ValueError(
                f"Invalid payload hash: must be lowercase 64-hex string, got '{payload_hash}'"
            )

        existing_entry = self.get_entry(event_id)
        current_offset = self.get_offset(topic, partition)

        if existing_entry is not None:
            _, ex_topic, ex_part, ex_off, ex_hash = existing_entry
            if (
                ex_topic == topic
                and ex_part == partition
                and ex_off == offset
                and ex_hash == payload_hash
            ):
                return self
            raise ReplayConflict(
                f"Conflicting retry for event '{event_id}': existing ({ex_topic}:{ex_part}@{ex_off}, {ex_hash}) != new ({topic}:{partition}@{offset}, {payload_hash})"
            )

        if offset != current_offset:
            raise ReplayConflict(
                f"Non-contiguous offset on {topic}:{partition}: expected {current_offset}, got {offset}"
            )

        new_entries = {e[0]: e for e in self.event_entries}
        new_entries[event_id] = (event_id, topic, partition, offset, payload_hash)

        new_offsets = {(t, p): off for t, p, off in self.partition_offsets}
        new_offsets[(topic, partition)] = offset + 1

        # Instantiate through normal model validation to enforce all invariants
        return ReplayState(
            event_entries=tuple(sorted(new_entries.values(), key=lambda x: x[0])),
            partition_offsets=tuple(sorted((t, p, off) for (t, p), off in new_offsets.items())),
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/streaming/test_state.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/streaming/state.py tests/streaming/test_state.py && rtk git commit -m "feat(streaming): make replay state deeply immutable, contiguous, and transition-validated"
```

---

### Task 4: Prove True Offline/Online Feature Scoring Parity with Neighbor-Grouped Cumulative Accumulator

**Files:**
- Create: `src/fincrime/streaming/scoring.py`
- Create: `tests/streaming/test_scoring_parity.py`

**Interfaces:**
- Consumes: Sequence of `TransactionEvent`.
- Produces: `OnlineGraphAccumulator` maintaining neighbor-grouped cumulative edge sequences in first-seen neighbor order, enforcing canonical monotonic `(event_time, edge_id)` ordering and duplicate edge rejection matching `build_graph`, and proving bitwise exact parity against `account_features(build_graph(events, cutoff=cutoff), account_id)`.

- [ ] **Step 1: Write failing parity and duplicate-edge tests against existing offline oracle**

```python
# tests/streaming/test_scoring_parity.py
from datetime import datetime, timezone
import pytest
from fincrime.graph.events import TransactionEvent
from fincrime.graph.build import build_graph
from fincrime.features.point_in_time import account_features
from fincrime.streaming.scoring import OnlineGraphAccumulator, compute_offline_features


def test_streaming_state_matches_offline_graph_and_features_exactly() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 9, 2, 10, 10, 0, tzinfo=timezone.utc)

    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=1000.0, event_time=t1
        ),
        TransactionEvent(
            edge_id="e2", source_id="acc_B", target_id="acc_C", amount=800.0, event_time=t2
        ),
        TransactionEvent(
            edge_id="e3", source_id="acc_D", target_id="acc_B", amount=500.0, event_time=t3
        ),
    ]

    cutoff = datetime(2026, 9, 2, 10, 15, 0, tzinfo=timezone.utc)

    # Offline path (actual production oracle using repository signature)
    offline_feats = compute_offline_features(events, target_account="acc_B", cutoff=cutoff)

    # Online accumulator (ingests stream in canonical order up to cutoff)
    acc = OnlineGraphAccumulator.empty()
    for ev in events:
        if ev.event_time <= cutoff:
            acc = acc.ingest(ev)
    online_feats = acc.extract_features(target_account="acc_B")

    # Bitwise exact parity checks across all fields
    assert online_feats.account_id == offline_feats.account_id
    assert online_feats.incoming_amount.hex() == offline_feats.incoming_amount.hex()
    assert online_feats.outgoing_amount.hex() == offline_feats.outgoing_amount.hex()
    assert online_feats.in_degree == offline_feats.in_degree
    assert online_feats.out_degree == offline_feats.out_degree
    assert online_feats.pass_through_ratio.hex() == offline_feats.pass_through_ratio.hex()


def test_duplicate_edge_id_raises_value_error_matching_build_graph() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=timezone.utc)

    ev1 = TransactionEvent(
        edge_id="dup_e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    ev2 = TransactionEvent(
        edge_id="dup_e1", source_id="acc_C", target_id="acc_D", amount=200.0, event_time=t2
    )

    acc = OnlineGraphAccumulator.empty().ingest(ev1)
    with pytest.raises(ValueError) as exc_info:
        acc.ingest(ev2)
    assert "Duplicate edge_id" in str(exc_info.value)


def test_non_monotonic_stream_order_rejected() -> None:
    t1 = datetime(2026, 9, 2, 10, 5, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)

    ev1 = TransactionEvent(
        edge_id="e1", source_id="acc_A", target_id="acc_B", amount=100.0, event_time=t1
    )
    ev2 = TransactionEvent(
        edge_id="e2", source_id="acc_A", target_id="acc_B", amount=200.0, event_time=t2
    )

    acc = OnlineGraphAccumulator.empty().ingest(ev1)
    with pytest.raises(ValueError) as exc_info:
        acc.ingest(ev2)
    assert "Non-monotonic stream order" in str(exc_info.value)


def test_parity_with_interleaved_multi_edges_and_extreme_magnitude_floats() -> None:
    t1 = datetime(2026, 9, 2, 10, 0, 0, tzinfo=timezone.utc)
    t2 = datetime(2026, 9, 2, 10, 1, 0, tzinfo=timezone.utc)
    t3 = datetime(2026, 9, 2, 10, 2, 0, tzinfo=timezone.utc)

    # Interleaved multi-edges between A->B and C->B with skewed float magnitudes (A: 1e16, C: 2.0, A: 1.0)
    events = [
        TransactionEvent(
            edge_id="e1", source_id="acc_A", target_id="acc_B", amount=1e16, event_time=t1
        ),
        TransactionEvent(
            edge_id="e2", source_id="acc_C", target_id="acc_B", amount=2.0, event_time=t2
        ),
        TransactionEvent(
            edge_id="e3", source_id="acc_A", target_id="acc_B", amount=1.0, event_time=t3
        ),
    ]
    cutoff = datetime(2026, 9, 2, 10, 5, 0, tzinfo=timezone.utc)

    offline_feats = compute_offline_features(events, target_account="acc_B", cutoff=cutoff)

    acc = OnlineGraphAccumulator.empty()
    for ev in events:
        acc = acc.ingest(ev)
    online_feats = acc.extract_features(target_account="acc_B")

    # Bitwise exact float match
    assert online_feats.incoming_amount.hex() == offline_feats.incoming_amount.hex()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/streaming/test_scoring_parity.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.streaming.scoring'`

- [ ] **Step 3: Implement OnlineGraphAccumulator with neighbor-grouped edge sequences**

```python
# src/fincrime/streaming/scoring.py
from __future__ import annotations
from datetime import UTC, datetime
from typing import Sequence
from pydantic import BaseModel, ConfigDict, Field

from fincrime.graph.events import TransactionEvent
from fincrime.graph.build import build_graph
from fincrime.features.point_in_time import account_features, AccountFeatures


def compute_offline_features(
    events: Sequence[TransactionEvent],
    target_account: str,
    cutoff: datetime,
) -> AccountFeatures:
    graph = build_graph(events, cutoff=cutoff)
    return account_features(graph, target_account)


class OnlineGraphAccumulator(BaseModel):
    """Cumulative online feature accumulator matching NetworkX neighbor-grouped edge iteration."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    # Map target -> tuple of (source_neighbor, tuple of amounts in edge insertion order)
    incoming_neighbor_edges: tuple[tuple[str, tuple[tuple[str, tuple[float, ...]], ...]], ...] = (
        Field(default_factory=tuple)
    )
    # Map source -> tuple of (target_neighbor, tuple of amounts in edge insertion order)
    outgoing_neighbor_edges: tuple[tuple[str, tuple[tuple[str, tuple[float, ...]], ...]], ...] = (
        Field(default_factory=tuple)
    )

    seen_edge_ids: tuple[str, ...] = Field(default_factory=tuple)
    last_event_key: tuple[str, str] | None = None

    @classmethod
    def empty(cls) -> "OnlineGraphAccumulator":
        return cls(
            incoming_neighbor_edges=(),
            outgoing_neighbor_edges=(),
            seen_edge_ids=(),
            last_event_key=None,
        )

    def ingest(self, event: TransactionEvent) -> "OnlineGraphAccumulator":
        if event.edge_id in self.seen_edge_ids:
            raise ValueError(f"Duplicate edge_id detected: {event.edge_id}")

        current_key = (event.event_time.astimezone(UTC).isoformat(), event.edge_id)
        if self.last_event_key is not None and current_key <= self.last_event_key:
            raise ValueError(
                f"Non-monotonic stream order: current {current_key} <= last {self.last_event_key}"
            )

        new_seen = self.seen_edge_ids + (event.edge_id,)

        # Update incoming neighbor groups: target -> source -> amounts
        inc_map = {tgt: list(sources) for tgt, sources in self.incoming_neighbor_edges}
        tgt_sources = inc_map.get(event.target_id, [])
        found_src = False
        new_tgt_sources: list[tuple[str, tuple[float, ...]]] = []
        for src, amts in tgt_sources:
            if src == event.source_id:
                new_tgt_sources.append((src, amts + (event.amount,)))
                found_src = True
            else:
                new_tgt_sources.append((src, amts))
        if not found_src:
            new_tgt_sources.append((event.source_id, (event.amount,)))
        inc_map[event.target_id] = new_tgt_sources

        # Update outgoing neighbor groups: source -> target -> amounts
        out_map = {src: list(targets) for src, targets in self.outgoing_neighbor_edges}
        src_targets = out_map.get(event.source_id, [])
        found_tgt = False
        new_src_targets: list[tuple[str, tuple[float, ...]]] = []
        for tgt, amts in src_targets:
            if tgt == event.target_id:
                new_src_targets.append((tgt, amts + (event.amount,)))
                found_tgt = True
            else:
                new_src_targets.append((tgt, amts))
        if not found_tgt:
            new_src_targets.append((event.target_id, (event.amount,)))
        out_map[event.source_id] = new_src_targets

        sorted_inc = tuple(sorted((tgt, tuple(srcs)) for tgt, srcs in inc_map.items()))
        sorted_out = tuple(sorted((src, tuple(tgts)) for src, tgts in out_map.items()))

        return OnlineGraphAccumulator(
            incoming_neighbor_edges=sorted_inc,
            outgoing_neighbor_edges=sorted_out,
            seen_edge_ids=new_seen,
            last_event_key=current_key,
        )

    def extract_features(self, target_account: str) -> AccountFeatures:
        inc_neighbors: tuple[tuple[str, tuple[float, ...]], ...] = ()
        for tgt, neighbors in self.incoming_neighbor_edges:
            if tgt == target_account:
                inc_neighbors = neighbors
                break

        out_neighbors: tuple[tuple[str, tuple[float, ...]], ...] = ()
        for src, neighbors in self.outgoing_neighbor_edges:
            if src == target_account:
                out_neighbors = neighbors
                break

        incoming_amounts = [amt for _, amts in inc_neighbors for amt in amts]
        outgoing_amounts = [amt for _, amts in out_neighbors for amt in amts]

        incoming_total = sum(incoming_amounts)
        outgoing_total = sum(outgoing_amounts)
        in_degree = len(incoming_amounts)
        out_degree = len(outgoing_amounts)

        if incoming_total <= 0.0:
            pass_through_ratio = 0.0
        else:
            pass_through_ratio = min(outgoing_total / incoming_total, 1.0)

        return AccountFeatures(
            account_id=target_account,
            incoming_amount=incoming_total,
            outgoing_amount=outgoing_total,
            in_degree=in_degree,
            out_degree=out_degree,
            pass_through_ratio=pass_through_ratio,
        )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/streaming/test_scoring_parity.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/streaming/scoring.py tests/streaming/test_scoring_parity.py && rtk git commit -m "feat(streaming): enforce true offline/online feature scoring parity with neighbor-grouped accumulator"
```

---

### Task 5: Add Local Streaming Infrastructure (Docker Compose Contract)

**Files:**
- Create: `infra/docker-compose.yml`
- Create: `infra/.env.example`
- Create: `tests/streaming/test_compose_contract.py`

**Interfaces:**
- Consumes: `infra/docker-compose.yml`.
- Produces: Verified container topology for Kafka (dual KRaft internal/external listeners), Redis, and PostgreSQL with valid healthchecks and local 127.0.0.1 bindings.

- [ ] **Step 1: Write failing Compose contract test**

```python
# tests/streaming/test_compose_contract.py
from pathlib import Path
import yaml


def test_compose_structure_and_local_binding() -> None:
    compose_path = Path("infra/docker-compose.yml")
    assert compose_path.exists(), "infra/docker-compose.yml must exist"
    data = yaml.safe_load(compose_path.read_text(encoding="utf-8"))

    services = data.get("services", {})
    assert "kafka" in services
    assert "redis" in services
    assert "postgres" in services

    for name, srv in services.items():
        assert "healthcheck" in srv, f"Service {name} missing healthcheck"
        ports = srv.get("ports", [])
        for p in ports:
            assert str(p).startswith("127.0.0.1:"), (
                f"Port mapping '{p}' in {name} must bind to 127.0.0.1"
            )

    kafka_env = services["kafka"]["environment"]
    assert "INTERNAL://kafka:9092" in kafka_env["KAFKA_CFG_ADVERTISED_LISTENERS"]
    assert "EXTERNAL://127.0.0.1:9092" in kafka_env["KAFKA_CFG_ADVERTISED_LISTENERS"]
    assert (
        "INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT"
        == kafka_env["KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP"]
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/streaming/test_compose_contract.py -v`
Expected: FAIL because `infra/docker-compose.yml` does not exist.

- [ ] **Step 3: Create infra/docker-compose.yml and .env.example**

```yaml
# infra/docker-compose.yml
services:
  kafka:
    image: bitnami/kafka:4.0
    environment:
      KAFKA_CFG_NODE_ID: "1"
      KAFKA_CFG_PROCESS_ROLES: broker,controller
      KAFKA_CFG_CONTROLLER_QUORUM_VOTERS: 1@kafka:9093
      KAFKA_CFG_LISTENERS: INTERNAL://0.0.0.0:9092,EXTERNAL://0.0.0.0:9094,CONTROLLER://0.0.0.0:9093
      KAFKA_CFG_ADVERTISED_LISTENERS: INTERNAL://kafka:9092,EXTERNAL://127.0.0.1:9092
      KAFKA_CFG_LISTENER_SECURITY_PROTOCOL_MAP: INTERNAL:PLAINTEXT,EXTERNAL:PLAINTEXT,CONTROLLER:PLAINTEXT
      KAFKA_CFG_CONTROLLER_LISTENER_NAMES: CONTROLLER
      KAFKA_CFG_INTER_BROKER_LISTENER_NAME: INTERNAL
    ports:
      - "127.0.0.1:9092:9094"
    healthcheck:
      test: ["CMD-SHELL", "/opt/bitnami/kafka/bin/kafka-topics.sh --bootstrap-server 127.0.0.1:9092 --list"]
      interval: 10s
      timeout: 5s
      retries: 12

  redis:
    image: redis:8.0-alpine
    command: ["redis-server", "--appendonly", "yes"]
    ports:
      - "127.0.0.1:6379:6379"
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
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD must be set in environment}
    ports:
      - "127.0.0.1:5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U fincrime -d fincrime"]
      interval: 5s
      timeout: 3s
      retries: 12
```

```dotenv
# infra/.env.example
POSTGRES_PASSWORD=replace_with_local_secure_password
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/streaming/test_compose_contract.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add infra/docker-compose.yml infra/.env.example tests/streaming/test_compose_contract.py && rtk git commit -m "chore(infra): add local streaming infrastructure with dual Kafka listeners and 127.0.0.1 isolation"
```

---

### Task 6: Replay Broker Records with Coordinate-Aware True No-Op, Durable Quarantine & Commit Barrier

**Files:**
- Create: `src/fincrime/streaming/replay.py`
- Create: `tests/streaming/test_replay.py`

**Interfaces:**
- Consumes: sequence of `BrokerRecord(topic, partition, offset, payload, timestamp)`, initial `ReplayState`, and `QuarantineStore`.
- Produces: `ReplayOutcome` with updated `ReplayState`, accepted IDs, `quarantined_records: tuple[QuarantinedRecord, ...]`, and `committable_offsets: tuple[tuple[str, int, int], ...]`.
- Invariants:
  - Exact coordinate retry is a true no-op (zero side-effect, no quarantine, no cursor advance).
  - Conflicting payload or same ID at different coordinates raises `ReplayConflict`.
  - Malformed payload or unexpected offset durably appends to `DurableFileQuarantineStore`, halts the partition, and freezes committable offset at the expected cursor.

- [ ] **Step 1: Write failing replay, coordinate-aware duplicate retry, durable quarantine, and commit barrier tests**

```python
# tests/streaming/test_replay.py
from datetime import datetime, timezone
import json
from pathlib import Path
import pytest
from fincrime.streaming.replay import (
    BrokerRecord,
    DurableFileQuarantineStore,
    replay_records,
)
from fincrime.streaming.state import ReplayConflict, ReplayState


def test_invalid_broker_record_is_quarantined_durably_with_coordinates(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    bad_payload = json.dumps({"schema_version": "99", "event_id": "bad_evt"}).encode("utf-8")
    record = BrokerRecord(
        topic="transactions",
        partition=0,
        offset=0,
        payload=bad_payload,
        timestamp=now,
    )
    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records([record], ReplayState.empty(), quarantine_store=store)

    assert outcome.accepted_event_ids == ()
    assert len(outcome.quarantined_records) == 1
    q = outcome.quarantined_records[0]
    assert q.topic == "transactions"
    assert q.partition == 0
    assert q.offset == 0
    assert q.reason == "INVALID_SCHEMA"
    assert outcome.committable_offsets == (("transactions", 0, 0),)

    persisted = store.get_records("transactions", 0)
    assert len(persisted) == 1
    assert persisted[0].payload_hash == q.payload_hash


def test_broker_exact_retry_at_already_advanced_state_is_true_noop(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    valid0 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")

    record = BrokerRecord(topic="tx", partition=0, offset=0, payload=valid0, timestamp=now)
    store = DurableFileQuarantineStore(storage_dir=tmp_path)

    from fincrime.streaming.events import TransactionEnvelope

    env = TransactionEnvelope.model_validate_json(valid0)
    state0 = ReplayState.empty().apply(
        "tx", partition=0, offset=0, event_id="evt_0", payload_hash=env.canonical_hash()
    )

    outcome = replay_records([record], state0, quarantine_store=store)

    # True no-op: no new accepted, no quarantine, state unchanged, committable offset unchanged at 1
    assert outcome.accepted_event_ids == ()
    assert outcome.quarantined_records == ()
    assert outcome.state == state0
    assert outcome.committable_offsets == (("tx", 0, 1),)
    assert len(store.get_records("tx", 0)) == 0


def test_poison_barrier_freezes_at_expected_offset_and_halts(tmp_path: Path) -> None:
    now = datetime(2026, 9, 2, 12, 0, 0, tzinfo=timezone.utc)
    valid1 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_0",
            "source_partition": 0,
            "source_offset": 0,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 100.0,
            "event_time": "2026-09-02T12:00:00Z",
        }
    ).encode("utf-8")
    poison = b'{"bad_json": true}'
    valid2 = json.dumps(
        {
            "schema_version": "1",
            "event_id": "evt_2",
            "source_partition": 0,
            "source_offset": 2,
            "source_id": "acc_1",
            "target_id": "acc_2",
            "amount": 200.0,
            "event_time": "2026-09-02T12:01:00Z",
        }
    ).encode("utf-8")

    records = [
        BrokerRecord(topic="tx", partition=0, offset=0, payload=valid1, timestamp=now),
        BrokerRecord(topic="tx", partition=0, offset=1, payload=poison, timestamp=now),
        BrokerRecord(topic="tx", partition=0, offset=2, payload=valid2, timestamp=now),
    ]

    store = DurableFileQuarantineStore(storage_dir=tmp_path)
    outcome = replay_records(records, ReplayState.empty(), quarantine_store=store)

    assert outcome.accepted_event_ids == ("evt_0",)
    assert len(outcome.quarantined_records) == 1
    assert outcome.state.get_offset("tx", 0) == 1
    assert outcome.committable_offsets == (("tx", 0, 1),)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/streaming/test_replay.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.streaming.replay'`

- [ ] **Step 3: Implement BrokerRecord, DurableFileQuarantineStore, and ReplayOutcome**

```python
# src/fincrime/streaming/replay.py
from __future__ import annotations
from datetime import datetime, timezone
from hashlib import sha256
from pathlib import Path
import re
from typing import Protocol, Sequence
from pydantic import BaseModel, ConfigDict, Field, field_validator

from fincrime.streaming.events import TransactionEnvelope
from fincrime.streaming.state import ReplayConflict, ReplayState

_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")


class BrokerRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    offset: int = Field(ge=0)
    payload: bytes
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None or v.utcoffset() != timezone.utc.utcoffset(v):
            raise ValueError("timestamp must be timezone-aware UTC")
        return v


class QuarantinedRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    topic: str = Field(min_length=1)
    partition: int = Field(ge=0)
    offset: int = Field(ge=0)
    reason: str = Field(min_length=1)
    payload_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    quarantined_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("quarantined_at")
    @classmethod
    def validate_utc(cls, v: datetime) -> datetime:
        if v.tzinfo is None or v.utcoffset() is None or v.utcoffset() != timezone.utc.utcoffset(v):
            raise ValueError("quarantined_at must be timezone-aware UTC")
        return v


class QuarantineStore(Protocol):
    def append(self, record: QuarantinedRecord) -> None: ...
    def get_records(self, topic: str, partition: int) -> list[QuarantinedRecord]: ...


class DurableFileQuarantineStore:
    def __init__(self, storage_dir: Path) -> None:
        self._dir = storage_dir
        self._dir.mkdir(parents=True, exist_ok=True)

    def _file_for(self, topic: str, partition: int) -> Path:
        return self._dir / f"quarantine_{topic}_{partition}.jsonl"

    def append(self, record: QuarantinedRecord) -> None:
        path = self._file_for(record.topic, record.partition)
        line = record.model_dump_json() + "\n"
        with path.open("a", encoding="utf-8") as f:
            f.write(line)

    def get_records(self, topic: str, partition: int) -> list[QuarantinedRecord]:
        path = self._file_for(topic, partition)
        if not path.exists():
            return []
        records: list[QuarantinedRecord] = []
        with path.open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(QuarantinedRecord.model_validate_json(line))
        return records


class ReplayOutcome(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    state: ReplayState
    accepted_event_ids: tuple[str, ...]
    quarantined_records: tuple[QuarantinedRecord, ...]
    committable_offsets: tuple[tuple[str, int, int], ...]


def replay_records(
    records: Sequence[BrokerRecord],
    initial_state: ReplayState,
    quarantine_store: QuarantineStore,
) -> ReplayOutcome:
    state = initial_state
    accepted: list[str] = []
    quarantined: list[QuarantinedRecord] = []

    committable: dict[tuple[str, int], int] = {
        (t, p): off for t, p, off in initial_state.partition_offsets
    }
    halted_partitions: set[tuple[str, int]] = set()

    for record in records:
        key = (record.topic, record.partition)
        if key not in committable:
            committable[key] = initial_state.get_offset(record.topic, record.partition)

        if key in halted_partitions:
            continue

        expected_offset = committable[key]
        payload_hash = sha256(record.payload).hexdigest().lower()

        # Step 1: Parse envelope
        try:
            event = TransactionEnvelope.model_validate_json(record.payload)
            if event.source_partition != record.partition or event.source_offset != record.offset:
                raise ValueError("Envelope coordinates do not match broker record coordinates")
        except Exception:
            q_rec = QuarantinedRecord(
                topic=record.topic,
                partition=record.partition,
                offset=record.offset,
                reason="INVALID_SCHEMA",
                payload_hash=payload_hash,
            )
            quarantined.append(q_rec)
            quarantine_store.append(q_rec)
            halted_partitions.add(key)
            continue

        # Step 2: Coordinate-aware duplicate check
        existing_entry = state.get_entry(event.event_id)
        if existing_entry is not None:
            _, ex_topic, ex_part, ex_off, ex_hash = existing_entry
            if (
                ex_topic == record.topic
                and ex_part == record.partition
                and ex_off == record.offset
                and ex_hash == event.canonical_hash()
            ):
                # True no-op: already applied at exact coordinate
                continue
            raise ReplayConflict(
                f"Conflicting retry for event '{event.event_id}': existing ({ex_topic}:{ex_part}@{ex_off}, {ex_hash}) != new ({record.topic}:{record.partition}@{record.offset}, {event.canonical_hash()})"
            )

        # Step 3: Check contiguous cursor for new event
        if record.offset != expected_offset:
            q_rec = QuarantinedRecord(
                topic=record.topic,
                partition=record.partition,
                offset=record.offset,
                reason="NON_CONTIGUOUS_OFFSET",
                payload_hash=payload_hash,
            )
            quarantined.append(q_rec)
            quarantine_store.append(q_rec)
            halted_partitions.add(key)
            continue

        # Step 4: Apply to state and advance committable cursor
        state = state.apply(
            topic=record.topic,
            partition=event.source_partition,
            offset=event.source_offset,
            event_id=event.event_id,
            payload_hash=event.canonical_hash(),
        )
        accepted.append(event.event_id)
        committable[key] = record.offset + 1

    formatted_committable = tuple(
        sorted((topic, part, off) for (topic, part), off in committable.items())
    )

    return ReplayOutcome(
        state=state,
        accepted_event_ids=tuple(accepted),
        quarantined_records=tuple(quarantined),
        committable_offsets=formatted_committable,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/streaming/test_replay.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/streaming/replay.py tests/streaming/test_replay.py && rtk git commit -m "feat(streaming): replay broker records with durable quarantine and partition commit barrier"
```

---

### Task 7: Operational Metrics & Validated Fitted PSI Drift Monitoring

**Files:**
- Create: `src/fincrime/monitoring/__init__.py`
- Create: `src/fincrime/monitoring/metrics.py`
- Create: `src/fincrime/monitoring/drift.py`
- Create: `tests/monitoring/__init__.py`
- Create: `tests/monitoring/test_drift.py`

**Interfaces:**
- Consumes: 1-D finite numpy arrays.
- Produces: `fit_psi_bins(baseline, bins=10) -> FittedPSIBins`, `calculate_psi(fitted_bins, current, threshold=0.1) -> PSIDriftResult`, `is_drift_detected(...) -> bool`, and Prometheus metrics (`EVENTS_PROCESSED`, `EVENTS_QUARANTINED`, `SCORING_LATENCY`).

- [ ] **Step 1: Write failing fitted PSI calculation, extreme magnitude, and model validation tests**

```python
# tests/monitoring/test_drift.py
import numpy as np
import pytest
from pydantic import ValidationError
from fincrime.monitoring.drift import (
    fit_psi_bins,
    calculate_psi,
    is_drift_detected,
    PSIDriftResult,
    FittedPSIBins,
)
from fincrime.monitoring.metrics import EVENTS_PROCESSED, EVENTS_QUARANTINED, SCORING_LATENCY


def test_identical_distributions_have_zero_psi() -> None:
    values = np.array([1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0], dtype=np.float64)
    fitted = fit_psi_bins(values, bins=4)
    result = calculate_psi(fitted, values, threshold=0.1)

    assert pytest.approx(result.psi, abs=1e-5) == 0.0
    assert result.drift_detected is False
    assert is_drift_detected(result.psi, threshold=0.1) is False


def test_shifted_distribution_triggers_drift() -> None:
    baseline = np.array([1.0, 2.0, 3.0, 4.0, 5.0], dtype=np.float64)
    current = np.array([10.0, 20.0, 30.0, 40.0, 50.0], dtype=np.float64)
    fitted = fit_psi_bins(baseline, bins=2)
    result = calculate_psi(fitted, current, threshold=0.1)

    assert result.psi > 0.1
    assert result.drift_detected is True


def test_psidriftresult_rejects_inconsistent_drift_boolean() -> None:
    with pytest.raises(ValidationError):
        PSIDriftResult(psi=0.5, threshold=0.1, drift_detected=False, bins=10)


def test_fitted_psi_bins_invariants_and_nan_rejection() -> None:
    # NaN edges rejected
    with pytest.raises(ValidationError):
        FittedPSIBins(edges=(-np.inf, np.nan, np.inf), base_counts=(0.5, 0.5), bins=2)
    # Non-monotonic edges rejected
    with pytest.raises(ValidationError):
        FittedPSIBins(edges=(-np.inf, 5.0, 3.0, np.inf), base_counts=(0.33, 0.33, 0.34), bins=3)


def test_extreme_mixed_extrema_baseline_fitting_and_calculation() -> None:
    # Skewed mixed extrema: [-finfo.max] + [finfo.max] * 9 with bins=10
    max_val = np.finfo(np.float64).max
    baseline = np.array([-max_val] + [max_val] * 9, dtype=np.float64)
    fitted = fit_psi_bins(baseline, bins=10)

    assert len(fitted.edges) == 11
    assert fitted.edges[0] == -np.inf
    assert fitted.edges[-1] == np.inf
    assert all(np.isfinite(x) for x in fitted.edges[1:-1])
    assert all(left < right for left, right in zip(fitted.edges[:-1], fitted.edges[1:]))

    # Mirrored skewed distribution
    mirrored = np.array([-max_val] * 9 + [max_val], dtype=np.float64)
    fitted_mirrored = fit_psi_bins(mirrored, bins=10)
    assert all(np.isfinite(x) for x in fitted_mirrored.edges[1:-1])
    assert all(
        left < right for left, right in zip(fitted_mirrored.edges[:-1], fitted_mirrored.edges[1:])
    )

    # Verify calculation executes cleanly without error
    res = calculate_psi(fitted, baseline)
    assert res.psi == pytest.approx(0.0, abs=1e-5)


def test_prometheus_metrics_initialized() -> None:
    assert EVENTS_PROCESSED._name == "fincrime_events_processed"
    assert EVENTS_QUARANTINED._name == "fincrime_events_quarantined"
    assert SCORING_LATENCY._name == "fincrime_scoring_latency_seconds"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/monitoring/test_drift.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.monitoring'`

- [ ] **Step 3: Implement FittedPSIBins, PSIDriftResult, and metrics**

```python
# src/fincrime/monitoring/__init__.py
"""Operational and statistical monitoring for streaming inference."""

# src/fincrime/monitoring/metrics.py
from prometheus_client import Counter, Histogram

EVENTS_PROCESSED = Counter(
    "fincrime_events_processed",
    "Total validated transaction events processed",
)

EVENTS_QUARANTINED = Counter(
    "fincrime_events_quarantined",
    "Total invalid transaction events quarantined",
)

SCORING_LATENCY = Histogram(
    "fincrime_scoring_latency_seconds",
    "Latency of incremental transaction scoring in seconds",
)

# src/fincrime/monitoring/drift.py
from __future__ import annotations
import math
import numpy as np
from numpy.typing import NDArray
from pydantic import BaseModel, ConfigDict, Field, model_validator


def is_drift_detected(psi: float, threshold: float = 0.1) -> bool:
    return psi >= threshold


class FittedPSIBins(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    edges: tuple[float, ...]
    base_counts: tuple[float, ...]
    bins: int = Field(ge=2)

    @model_validator(mode="after")
    def validate_dimensions_and_monotonicity(self) -> "FittedPSIBins":
        if len(self.edges) != self.bins + 1:
            raise ValueError(
                f"edges length must be bins + 1 ({self.bins + 1}), got {len(self.edges)}"
            )
        if len(self.base_counts) != self.bins:
            raise ValueError(
                f"base_counts length must be bins ({self.bins}), got {len(self.base_counts)}"
            )
        if self.edges[0] != -math.inf or self.edges[-1] != math.inf:
            raise ValueError("edges must start with -inf and end with +inf")
        if not all(math.isfinite(x) for x in self.edges[1:-1]):
            raise ValueError("interior edges must be finite real numbers")
        if not all(left < right for left, right in zip(self.edges[:-1], self.edges[1:])):
            raise ValueError("edges must be strictly monotonically increasing")
        for count in self.base_counts:
            if count < 0.0 or not math.isfinite(count):
                raise ValueError("base_counts must be finite non-negative numbers")
        if not math.isclose(sum(self.base_counts), 1.0, abs_tol=1e-5):
            raise ValueError(f"sum of base_counts must be approx 1.0, got {sum(self.base_counts)}")
        return self


class PSIDriftResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    psi: float = Field(ge=0.0)
    threshold: float = Field(gt=0.0)
    drift_detected: bool
    bins: int = Field(ge=2)

    @model_validator(mode="after")
    def validate_drift_consistency(self) -> "PSIDriftResult":
        expected = is_drift_detected(self.psi, self.threshold)
        if self.drift_detected != expected:
            raise ValueError(
                f"drift_detected '{self.drift_detected}' inconsistent with is_drift_detected({self.psi}, {self.threshold}) -> {expected}"
            )
        return self


def fit_psi_bins(baseline: NDArray[np.float64], bins: int = 10) -> FittedPSIBins:
    if len(baseline) == 0:
        raise ValueError("Baseline distribution must not be empty")
    if baseline.ndim != 1:
        raise ValueError("Baseline must be a 1-D array")
    if not np.all(np.isfinite(baseline)):
        raise ValueError("Baseline must contain only finite numbers (no NaN or Inf)")
    if bins < 2:
        raise ValueError("bins must be >= 2")

    min_finite = -float(np.finfo(np.float64).max)
    max_finite = float(np.finfo(np.float64).max)

    quantiles = np.linspace(0, 1, bins + 1)
    raw_quantiles = np.quantile(baseline, quantiles)

    # Clamp all raw interior quantile values to finite float range
    interior: list[float] = []
    for x in raw_quantiles[1:-1]:
        val = float(x)
        if not math.isfinite(val) or val <= min_finite:
            val = min_finite
        elif val >= max_finite:
            val = max_finite
        interior.append(val)

    # Forward pass: ensure strictly increasing
    for i in range(1, len(interior)):
        if interior[i] <= interior[i - 1]:
            interior[i] = float(np.nextafter(interior[i - 1], math.inf))

    # Backward pass: if forward pass pushed rightmost interior to or past max_finite
    if interior and interior[-1] >= max_finite:
        interior[-1] = max_finite
        for i in range(len(interior) - 2, -1, -1):
            if interior[i] >= interior[i + 1]:
                interior[i] = float(np.nextafter(interior[i + 1], -math.inf))

    # Re-clamp first interior element if backward pass pushed past min_finite
    if interior and interior[0] <= min_finite:
        interior[0] = min_finite
        for i in range(1, len(interior)):
            if interior[i] <= interior[i - 1]:
                interior[i] = float(np.nextafter(interior[i - 1], math.inf))

    edges = (-math.inf,) + tuple(interior) + (math.inf,)
    base_counts = np.histogram(baseline, bins=edges)[0] / len(baseline)

    return FittedPSIBins(
        edges=edges,
        base_counts=tuple(float(x) for x in base_counts),
        bins=bins,
    )


def calculate_psi(
    fitted: FittedPSIBins,
    current: NDArray[np.float64],
    threshold: float = 0.1,
) -> PSIDriftResult:
    if len(current) == 0:
        raise ValueError("Current distribution must not be empty")
    if current.ndim != 1:
        raise ValueError("Current must be a 1-D array")
    if not np.all(np.isfinite(current)):
        raise ValueError("Current must contain only finite numbers (no NaN or Inf)")

    edges = np.array(fitted.edges)
    base_counts = np.array(fitted.base_counts)
    current_counts = np.histogram(current, bins=edges)[0] / len(current)

    base_safe = np.clip(base_counts, 1e-9, None)
    current_safe = np.clip(current_counts, 1e-9, None)

    psi_val = float(np.sum((current_safe - base_safe) * np.log(current_safe / base_safe)))
    psi_val = max(0.0, psi_val)

    return PSIDriftResult(
        psi=psi_val,
        threshold=threshold,
        drift_detected=is_drift_detected(psi_val, threshold),
        bins=fitted.bins,
    )
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/monitoring/test_drift.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/monitoring tests/monitoring && rtk git commit -m "feat(monitoring): monitor operations and validated fitted PSI distribution drift"
```

---

### Task 8: Build and Verify Status-Specific Artifact Release Manifests with Test Resolver Injection

**Files:**
- Create: `src/fincrime/release/__init__.py`
- Create: `src/fincrime/release/manifest.py`
- Create: `tests/release/__init__.py`
- Create: `tests/release/test_manifest.py`

**Interfaces:**
- Consumes: directory of artifact files, status (`RESEARCH_RELEASE` vs `FULL_PRODUCT_RELEASE`), callable `sha_resolver: Callable[[], str]` (defaulting strictly to `get_repo_git_sha`), actual cost, and PSI drift result.
- Produces: `build_release_manifest(...) -> ReleaseManifest`, `verify_release_manifest(manifest, artifacts, sha_resolver) -> bool`. Fails closed if mandatory status-specific artifacts are missing, unexpected extra artifacts are present, unreadable, modified, or if derived git SHA does not match.

- [ ] **Step 1: Write failing release manifest builder, exact inventory, resolver injection, and tamper tests**

```python
# tests/release/test_manifest.py
from pathlib import Path
import pytest
from pydantic import ValidationError
from fincrime.monitoring.drift import PSIDriftResult
from fincrime.release.manifest import (
    ReleaseManifest,
    build_release_manifest,
    verify_release_manifest,
    get_mandatory_inventory,
)


def _create_dummy_files(tmp_path: Path, names: list[str]) -> dict[str, Path]:
    artifacts: dict[str, Path] = {}
    for name in names:
        p = tmp_path / f"{name}.json"
        p.write_text(f'{{"artifact": "{name}"}}', encoding="utf-8")
        artifacts[name] = p
    return artifacts


def test_build_and_verify_full_product_release_exact_inventory(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("FULL_PRODUCT_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    # Injected test-only resolver returning deterministic mock SHA
    test_resolver = lambda: "a" * 40

    manifest = build_release_manifest(
        status="FULL_PRODUCT_RELEASE",
        artifacts=artifacts,
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=150000,
        tests_passed=True,
        known_limitations=("Local Compose required for streaming",),
        sha_resolver=test_resolver,
    )
    assert manifest.status == "FULL_PRODUCT_RELEASE"
    assert manifest.actual_cash_cost_vnd == 150000

    # Verification passes with matching resolver
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is True

    # Tamper test: modified file fails
    artifacts[req_names[0]].write_text('{"tampered": true}', encoding="utf-8")
    assert verify_release_manifest(manifest, artifacts, sha_resolver=test_resolver) is False


def test_resolver_mismatch_fails_verification(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names)
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    manifest = build_release_manifest(
        status="RESEARCH_RELEASE",
        artifacts=artifacts,
        psi_drift_result=drift_res,
        actual_cash_cost_vnd=50000,
        tests_passed=True,
        known_limitations=(),
        sha_resolver=lambda: "c" * 40,
    )

    # Verifier with mismatched resolver fails closed
    assert verify_release_manifest(manifest, artifacts, sha_resolver=lambda: "d" * 40) is False


def test_extra_unexpected_inventory_rejected_on_build_and_verify(tmp_path: Path) -> None:
    req_names = list(get_mandatory_inventory("RESEARCH_RELEASE"))
    artifacts = _create_dummy_files(tmp_path, req_names + ["unexpected_extra"])
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    # Building with unexpected extra artifact must raise ValueError
    with pytest.raises(ValueError) as exc_info:
        build_release_manifest(
            status="RESEARCH_RELEASE",
            artifacts=artifacts,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=50000,
            tests_passed=True,
            known_limitations=(),
            sha_resolver=lambda: "c" * 40,
        )
    assert "Unexpected extra release artifacts" in str(exc_info.value)


def test_direct_construction_with_invalid_inventory_rejected() -> None:
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)
    with pytest.raises(ValidationError):
        ReleaseManifest(
            status="RESEARCH_RELEASE",
            git_sha="a" * 40,
            artifact_hashes=(("dataset", "a" * 64),),  # Missing other 4 research artifacts
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=0,
            tests_passed=True,
            known_limitations=(),
        )


def test_incomplete_evidence_rejected_for_full_product_release(tmp_path: Path) -> None:
    partial_artifacts = _create_dummy_files(tmp_path, ["dataset", "split"])
    drift_res = PSIDriftResult(psi=0.02, threshold=0.1, drift_detected=False, bins=10)

    with pytest.raises(ValueError) as exc_info:
        build_release_manifest(
            status="FULL_PRODUCT_RELEASE",
            artifacts=partial_artifacts,
            psi_drift_result=drift_res,
            actual_cash_cost_vnd=100,
            tests_passed=True,
            known_limitations=(),
            sha_resolver=lambda: "a" * 40,
        )
    assert "Missing mandatory release artifacts" in str(exc_info.value)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/release/test_manifest.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'fincrime.release'`

- [ ] **Step 3: Implement ReleaseManifest with exact inventory validation**

```python
# src/fincrime/release/__init__.py
"""Release manifest and audit gate bindings."""

# src/fincrime/release/manifest.py
from __future__ import annotations
from collections.abc import Callable
import hashlib
from pathlib import Path
import re
import subprocess
from typing import Literal, Mapping
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from fincrime.monitoring.drift import PSIDriftResult, is_drift_detected

_GIT_SHA_REGEX = re.compile(r"^[0-9a-f]{40}$")
_HEX64_REGEX = re.compile(r"^[0-9a-f]{64}$")

MANDATORY_INVENTORIES: dict[str, tuple[str, ...]] = {
    "RESEARCH_RELEASE": (
        "dataset",
        "split",
        "feature_config",
        "model_weights",
        "trace_report",
    ),
    "FULL_PRODUCT_RELEASE": (
        "dataset",
        "split",
        "feature_config",
        "model_weights",
        "trace_report",
        "agent_eval_report",
        "streaming_replay_log",
        "monitoring_drift_report",
    ),
}


def get_mandatory_inventory(status: str) -> tuple[str, ...]:
    if status not in MANDATORY_INVENTORIES:
        raise ValueError(f"Unknown release status: '{status}'")
    return MANDATORY_INVENTORIES[status]


def get_repo_git_sha() -> str:
    try:
        out = (
            subprocess.check_output(
                ["git", "rev-parse", "HEAD"],
                text=True,
                stderr=subprocess.PIPE,
            )
            .strip()
            .lower()
        )
    except Exception as exc:
        raise RuntimeError(f"Failed to derive git SHA from repository: {exc}") from exc
    if not _GIT_SHA_REGEX.match(out):
        raise ValueError(f"Derived invalid git SHA from HEAD: '{out}'")
    return out


class ReleaseManifest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    status: Literal["RESEARCH_RELEASE", "FULL_PRODUCT_RELEASE"]
    git_sha: str = Field(pattern=r"^[0-9a-f]{40}$")
    artifact_hashes: tuple[tuple[str, str], ...] = Field(min_length=1)
    psi_drift_result: PSIDriftResult
    actual_cash_cost_vnd: int = Field(ge=0)
    tests_passed: bool
    known_limitations: tuple[str, ...]

    @field_validator("artifact_hashes")
    @classmethod
    def validate_hashes(cls, v: tuple[tuple[str, str], ...]) -> tuple[tuple[str, str], ...]:
        names: set[str] = set()
        for name, h in v:
            if not name.strip():
                raise ValueError("Artifact name must not be blank")
            if name in names:
                raise ValueError(f"Duplicate artifact name '{name}' in manifest")
            names.add(name)
            if not _HEX64_REGEX.match(h):
                raise ValueError(f"Invalid lowercase SHA-256 '{h}' for artifact '{name}'")
        if v != tuple(sorted(v, key=lambda x: x[0])):
            raise ValueError("artifact_hashes must be sorted by name")
        return v

    @model_validator(mode="after")
    def validate_exact_status_inventory(self) -> "ReleaseManifest":
        expected_names = set(get_mandatory_inventory(self.status))
        actual_names = self.artifact_names
        if actual_names != expected_names:
            raise ValueError(
                f"ReleaseManifest artifact_names {actual_names} do not match exact mandatory inventory {expected_names} for status '{self.status}'"
            )
        return self

    def get_hash(self, name: str) -> str | None:
        for k, v in self.artifact_hashes:
            if k == name:
                return v
        return None

    @property
    def artifact_names(self) -> set[str]:
        return {k for k, _ in self.artifact_hashes}


def hash_file_sha256(path: Path) -> str:
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"Artifact file not found: {path}")
    h = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            h.update(chunk)
    return h.hexdigest().lower()


def build_release_manifest(
    status: Literal["RESEARCH_RELEASE", "FULL_PRODUCT_RELEASE"],
    artifacts: Mapping[str, Path],
    psi_drift_result: PSIDriftResult,
    actual_cash_cost_vnd: int,
    tests_passed: bool,
    known_limitations: tuple[str, ...],
    sha_resolver: Callable[[], str] = get_repo_git_sha,
) -> ReleaseManifest:
    final_sha = sha_resolver().lower()
    if not _GIT_SHA_REGEX.match(final_sha):
        raise ValueError(
            f"Invalid git_sha from resolver: must be 40-character lowercase hex, got '{final_sha}'"
        )

    mandatory = set(get_mandatory_inventory(status))
    supplied = set(artifacts.keys())

    missing = mandatory - supplied
    if missing:
        raise ValueError(
            f"Missing mandatory release artifacts: {sorted(missing)} for status '{status}'"
        )

    extra = supplied - mandatory
    if extra:
        raise ValueError(
            f"Unexpected extra release artifacts: {sorted(extra)} for status '{status}' (exact allowed: {sorted(mandatory)})"
        )

    hashes = {name: hash_file_sha256(path) for name, path in artifacts.items()}
    return ReleaseManifest(
        status=status,
        git_sha=final_sha,
        artifact_hashes=tuple(sorted(hashes.items(), key=lambda x: x[0])),
        psi_drift_result=psi_drift_result,
        actual_cash_cost_vnd=actual_cash_cost_vnd,
        tests_passed=tests_passed,
        known_limitations=known_limitations,
    )


def verify_release_manifest(
    manifest: ReleaseManifest,
    artifacts: Mapping[str, Path],
    sha_resolver: Callable[[], str] = get_repo_git_sha,
) -> bool:
    try:
        target_sha = sha_resolver().lower()
    except Exception:
        return False

    if not _GIT_SHA_REGEX.match(target_sha):
        return False
    if manifest.git_sha != target_sha:
        return False

    mandatory = set(get_mandatory_inventory(manifest.status))
    if set(artifacts.keys()) != mandatory or manifest.artifact_names != mandatory:
        return False
    if not manifest.tests_passed:
        return False
    if manifest.psi_drift_result.drift_detected:
        return False
    if is_drift_detected(manifest.psi_drift_result.psi, manifest.psi_drift_result.threshold):
        return False

    for name, path in artifacts.items():
        expected = manifest.get_hash(name)
        if expected is None:
            return False
        try:
            actual = hash_file_sha256(path)
        except OSError:
            return False
        if actual != expected:
            return False

    return True
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/release/test_manifest.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add src/fincrime/release tests/release && rtk git commit -m "feat(release): build and verify exact-inventory resolver-bound release manifests"
```

---

### Task 9: Define and Execute Exact-SHA Local Release Gate Runbook

**Files:**
- Create: `docs/runbooks/local-release.md`
- Create: `tests/release/test_runbook.py`

**Interfaces:**
- Consumes: repository documentation and release runbook.
- Produces: verified 10-step local release gate sequence verified by contract tests with 100% `rtk` prefix discipline.

- [ ] **Step 1: Write failing runbook marker tests**

```python
# tests/release/test_runbook.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `rtk uv run pytest tests/release/test_runbook.py -v`
Expected: FAIL because `docs/runbooks/local-release.md` does not exist.

- [ ] **Step 3: Write authoritative local release runbook**

```markdown
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
```

- [ ] **Step 4: Run test to verify it passes**

Run: `rtk uv run pytest tests/release/test_runbook.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
rtk git add docs/runbooks/local-release.md tests/release/test_runbook.py && rtk git commit -m "docs(release): define exact SHA release gate runbook under rtk discipline"
```

---

## Verification Checklist

- [ ] Python unit & integration tests pass: `rtk uv run pytest -q`
- [ ] Code formatting & linting clean: `rtk uv run ruff check .`
- [ ] Strict static type check clean: `rtk uv run mypy src`
- [ ] Full monorepo consistency maintained across all existing research, pilot, and investigator modules.
