# TASK-004: MLOps, Streaming Replay & Release Evidence Brief (Authoritative v15.0)

## 1. Overview & Scope
Implement Plan 4: Phases 10–12 of the Financial Crime Intelligence Platform under SLP Governance.
This authoritative specification incorporates all fixes across the 7 formal gates:
1. **True Incremental Scoring Parity:** `OnlineGraphAccumulator` maintains direct, neighbor-grouped cumulative edge sequences `incoming_neighbor_edges` and `outgoing_neighbor_edges` preserving neighbor-first insertion order, enforces canonical monotonic `(event_time, edge_id)` ordering and duplicate `edge_id` rejection matching `build_graph`, and computes `AccountFeatures` bitwise identical to `account_features(build_graph(events, cutoff=cutoff), account_id)`.
2. **Canonical Invariants:** Compact sorted JSON, strict UTC datetime with zero microseconds (`%Y-%m-%dT%H:%M:%SZ`), lowercase 64-hex SHA-256 payload hashing, and validated `ReplayState.apply` transitions via direct model construction.
3. **Deeply Immutable Replay State & True Duplicate No-Ops:** Contiguous partition offset tracking per `(topic, partition)` pair with coordinate-aware true duplicate no-ops (zero side-effect, no quarantine, no cursor advance), model-level tuple sortedness/uniqueness invariants, and `ReplayConflict` on payload or coordinate mismatch.
4. **Broker Replay with Durable Poison Quarantine:** Structured `BrokerRecord` inputs, `DurableFileQuarantineStore` JSONL persistence, and `committable_offsets` partition barrier halting at the expected cursor.
5. **Validated Fitted PSI Drift Contract:** Baseline quantile edges fitted into `FittedPSIBins` with verified `[-inf, ...finite..., +inf]` endpoints, clamp-and-sweep forward/backward `np.nextafter` repair across extreme float baselines, and `all(left < right)` machine-precision monotonicity, calculating deterministic `PSIDriftResult` with model-enforced `drift_detected == is_drift_detected(psi, threshold)`.
6. **Exact-Inventory Release Manifest with Production Git Default:** Dynamic filesystem SHA-256 hashing across mandatory status-specific artifact inventories (`RESEARCH_RELEASE` vs `FULL_PRODUCT_RELEASE`), model-enforced exact inventory set equality `artifact_names == set(get_mandatory_inventory(status))`, mandatory `sha_resolver: Callable[[], str]` defaulting strictly to `get_repo_git_sha()` in production (with test-only injection support), verified drift status, and fail-closed `OSError` handling via `build_release_manifest` and `verify_release_manifest`. No caller string overrides permitted.
7. **Local Infrastructure & RTK Discipline:** Pinned container services with dual Kafka listeners (`INTERNAL://kafka:9092,EXTERNAL://127.0.0.1:9092`) bound to `127.0.0.1` and global `rtk` command prefix enforcement across all runbook steps.

---

## 2. SLP Governance & Subagent Dispatch DAG

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

## 3. Interfaces & Contracts

### 3.1 Domain 1: MLflow Tracking & Streaming Events (Phase 10)
- `tracking_tags(git_sha: str, dataset_hash: str, split_hash: str) -> dict[str, str]`
- `log_frozen_run(tags: dict[str, str], metrics: dict[str, float], tracking_uri: str, experiment_name: str) -> str` (internally reads back and verifies `FINISHED` status, tags, and metrics before returning).
- `get_run_metadata(run_id: str, tracking_uri: str) -> dict[str, Any]`
- `TransactionEnvelope(schema_version: Literal["1"], event_id: str, source_partition: int, source_offset: int, source_id: str, target_id: str, amount: float, event_time: datetime)`
- `TransactionEnvelope.canonical_hash() -> str`
- `ReplayState.empty() -> ReplayState`
- `ReplayState.apply(topic: str, partition: int, offset: int, event_id: str, payload_hash: str) -> ReplayState`
- `ReplayConflict(RuntimeError)`

### 3.2 Domain 2: Scoring Parity, Replay & Monitoring (Phase 11)
- `compute_offline_features(events: Sequence[TransactionEvent], target_account: str, cutoff: datetime) -> AccountFeatures`
- `OnlineGraphAccumulator.empty() -> OnlineGraphAccumulator`
- `OnlineGraphAccumulator.ingest(event: TransactionEvent) -> OnlineGraphAccumulator`
- `OnlineGraphAccumulator.extract_features(target_account: str) -> AccountFeatures`
- Parity Guarantee: `acc.extract_features(target) == compute_offline_features(events, target, cutoff)` bitwise exact.
- `BrokerRecord(topic: str, partition: int, offset: int, payload: bytes, timestamp: datetime)`
- `QuarantinedRecord(topic: str, partition: int, offset: int, reason: str, payload_hash: str, quarantined_at: datetime)`
- `DurableFileQuarantineStore(storage_dir: Path)`
- `ReplayOutcome(state: ReplayState, accepted_event_ids: tuple[str, ...], quarantined_records: tuple[QuarantinedRecord, ...], committable_offsets: tuple[tuple[str, int, int], ...])`
- `replay_records(records: Sequence[BrokerRecord], initial_state: ReplayState, quarantine_store: QuarantineStore) -> ReplayOutcome`
- `fit_psi_bins(baseline: NDArray[np.float64], bins: int) -> FittedPSIBins`
- `calculate_psi(fitted: FittedPSIBins, current: NDArray[np.float64], threshold: float) -> PSIDriftResult`
- `is_drift_detected(psi: float, threshold: float) -> bool`
- Prometheus metrics: `EVENTS_PROCESSED`, `EVENTS_QUARANTINED`, `SCORING_LATENCY`.

### 3.3 Domain 3: Release Manifest & Local Gate (Phase 12)
- `ReleaseManifest(status: Literal["RESEARCH_RELEASE", "FULL_PRODUCT_RELEASE"], git_sha: str, artifact_hashes: tuple[tuple[str, str], ...], psi_drift_result: PSIDriftResult, actual_cash_cost_vnd: int, tests_passed: bool, known_limitations: tuple[str, ...])`
- `get_mandatory_inventory(status: str) -> tuple[str, ...]`
- `get_repo_git_sha() -> str`
- `build_release_manifest(status, artifacts, psi_drift_result, actual_cash_cost_vnd, tests_passed, known_limitations, sha_resolver=get_repo_git_sha) -> ReleaseManifest`
- `verify_release_manifest(manifest: ReleaseManifest, artifacts: Mapping[str, Path], sha_resolver=get_repo_git_sha) -> bool`
- `docs/runbooks/local-release.md` verified via `tests/release/test_runbook.py`.

---

## 4. Verification Gates
- Python Unit & Integration Tests: `rtk uv run pytest -q`
- Linting & Formatting: `rtk uv run ruff check .`
- Strict Typechecking: `rtk uv run mypy src`
