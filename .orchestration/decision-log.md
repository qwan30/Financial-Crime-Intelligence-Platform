# Architectural Decision Log

## Decision 001: Separation of Research vs Investigator vs Streaming
- **Date:** 2026-08-30
- **Status:** APPROVED & FROZEN
- **Context:** AML platform needs clear boundaries between offline graph/ML research, agentic investigation workbench, and online streaming scoring.
- **Decision:**
  1. Phases 0-6 (Research Foundation, Training, Tracing) completed and merged (PR #4-#19).
  2. Pilot Intake Tasks 1-7 completed and merged (PR #20-#29).
  3. Phases 7-9 (Investigator + DeepSeek) implement bounded Case API, immutable evidence store, LangGraph workflow, and guarded DeepSeek adapter.
  4. Phases 10-12 (MLOps, Streaming, Release) build offline/online parity, Kafka replay, and release manifest gating.

## Decision 002: Guarded DeepSeek Provider & Local-First Boundaries
- **Date:** 2026-09-02
- **Status:** APPROVED & FROZEN
- **Context:** DeepSeek v4 integration for investigator agent.
- **Decision:**
  1. DeepSeek cannot create labels, risk scores, evidence IDs, or final dispositions.
  2. Local cost caps (monthly 200k VND, per-case 6 calls, 60k in/8k out tokens) enforced via hard pre-call budget checks.
  3. `LLM_OFF` fallback mode preserves full functionality without API keys.

## Decision 003: Design Review Action Items Incorporation (P0/P1 Gates)
- **Date:** 2026-09-02
- **Status:** APPROVED & FROZEN
- **Context:** Independent Design Review by `DesignReviewer` subagent yielded actionable boundary hardening items.

## Decision 004: Intermediate Hardened Specification
- **Date:** 2026-09-02
- **Status:** SUPERSEDED BY DECISION 009

## Decision 005: Intermediate v4.0 Specification
- **Date:** 2026-09-02
- **Status:** SUPERSEDED BY DECISION 009

## Decision 006: Intermediate v4.1 Specification
- **Date:** 2026-09-02
- **Status:** SUPERSEDED BY DECISION 009

## Decision 007: Intermediate v4.3 Specification
- **Date:** 2026-09-02
- **Status:** SUPERSEDED BY DECISION 009

## Decision 008: Intermediate v4.4 Specification
- **Date:** 2026-09-02
- **Status:** SUPERSEDED BY DECISION 009

## Decision 009: Final Authoritative Phase 1 Design Sign-off (v4.5) — 8 Gates & Ponytail Certified
- **Date:** 2026-09-02
- **Status:** APPROVED & FROZEN
- **Context:** Complete closure of all 8 Approval Gates and full certification against the Ponytail Decision Ladder in `TASK-003-investigator-deepseek.md`.

## Decision 010: Lead Project Acceptance & Production Certification (Plan 3: Investigator + DeepSeek)
- **Date:** 2026-09-02
- **Status:** APPROVED & CERTIFIED
- **Authority:** Lead Project Acceptance Authority (under SLP Governance)
- **Verification Evidence Summary:**
  1. **Phase 7 (Evidence & Case API):** 52 passing unit/integration tests (`tests/evidence`, `tests/cases`, `tests/api`). Canonical hashing, thread-safe stores with typed conflicts (`EvidenceConflict`, `CaseConflict`, `FeedbackConflict`), and FastAPI camelCase DTOs.
  2. **Phase 8 (Agent Tools, Budget, DeepSeek, Workflow):** 36 passing unit/integration tests (`tests/agent`). Fixed-point integer arithmetic `(7*in + 28*out + 1999)//2000`, strict `RESERVED -> DISPATCHED -> RECONCILED` lifecycle, monthly 200k VND hard cap, `InMemoryGraphRepository` with BFS traversal and referential integrity, and LangGraph 6-node state machine with closed 7-row failure transition matrix.
  3. **Phase 9 (Evaluation & UI Workbench):** 20 passing Python evaluation tests across 10-case gold corpus with 100% oracle match, 18 passing React/Vitest component tests, `tsc -b && vite build` clean bundle, and 2/2 passing Playwright Chromium browser journeys.
  4. **Full Monorepo Quality Gate:** 454 pytest tests passing (0 failures), Ruff lint clean, MyPy strict clean across 43 source files.
  5. **Production Audit & Security Report:** Clean report saved to `.orchestration/evidence/production-audit.md`.
  6. **Santa Method Verification:** Certified with `VERDICT: PASS` across all criteria.
- **Recommendation:** Hand over the completed candidate commit to the Human Owner for final merge and release decision.

## Decision 011: Plan 4 Architectural Blueprint & Subagent Dispatch Strategy (v15.0 — Multi-Round Audit Certified)
- **Date:** 2026-09-02
- **Status:** APPROVED & FROZEN
- **Authority:** Lead Project Acceptance Authority & Supervisor
- **Context:** Complete closure and sign-off across all 7 Acceptance Gates certified by Independent Subagent Closure Audit (`ClosureAuditV15`).
- **Decision:**
  1. **Canonical Streaming Contracts:** Strict UTC ISO-8601 timestamps with zero microseconds (`%Y-%m-%dT%H:%M:%SZ`), canonical compact JSON bytes hashing, deeply immutable coordinate-aware `ReplayState` with transition model validation.
  2. **True Parity & Neighbor Grouping:** `OnlineGraphAccumulator` derives `AccountFeatures` bitwise identical to `account_features(build_graph(events, cutoff=cutoff), account_id)` using neighbor-first iteration order, canonical monotonic stream order `(event_time, edge_id)`, and duplicate `edge_id` rejection.
  3. **Poison Quarantine & Barrier:** Structured `BrokerRecord` inputs, coordinate-aware true duplicate no-ops, `DurableFileQuarantineStore` JSONL writing, and `committable_offsets` partition barrier halting at expected cursor.
  4. **Fitted PSI Drift:** `FittedPSIBins` holding immutable baseline quantiles and base counts with clamp-and-sweep `nextafter` repair across extreme float baselines, calculating deterministic `PSIDriftResult` with model-enforced drift bounds.
  5. **Exact-Inventory Release Manifest:** Dynamic filesystem SHA-256 hashing with exact mathematical set equality `artifact_names == set(get_mandatory_inventory(status))`, production `get_repo_git_sha` derivation, verified drift bounds, and fail-closed error handling.
  6. **Hardened Local Infrastructure & RTK:** Docker Compose dual listeners (`INTERNAL://kafka:9092,EXTERNAL://127.0.0.1:9092`) bound to `127.0.0.1` and mandatory `rtk` prefix on all commands.
  7. **Subagent DAG with Wave 0:** Shared dependencies installed upfront in Wave 0 to prevent file lock contention, followed by Waves 1, 2, and 3.
## Decision 012: Lead Project Acceptance & Production Certification (Plan 4: MLOps, Streaming & Release)
- **Date:** 2026-09-02
- **Status:** APPROVED & CERTIFIED
- **Authority:** Lead Project Acceptance Authority (under SLP Governance)
- **Verification Evidence Summary:**
  1. **Phase 10 (MLOps Tracking & Event Models):** 27 passing unit/integration tests (`tests/mlops/`) and 19 streaming event/state tests (`tests/streaming/`). Validated 40-char git SHA, 64-char dataset/split hashes, MLflow client read-back status/tag/metric verification, canonical compact JSON serialization with exact UTC seconds, and deeply immutable `ReplayState` with model-validated transitions.
  2. **Phase 11 (Parity, Replay & Monitoring):** 11 scoring parity tests (`tests/streaming/test_scoring_parity.py`), 12 broker replay tests (`tests/streaming/test_replay.py`), and 12 monitoring tests (`tests/monitoring/test_drift.py`). Bitwise identical float hex matching between `OnlineGraphAccumulator` and `build_graph` + `account_features`, thread-safe `DurableFileQuarantineStore`, coordinate-aware duplicate retry no-ops, commit barrier partition halting, and `FittedPSIBins` with clamp-and-sweep `nextafter` monotonicity across extreme float baselines.
  3. **Phase 12 (Release Manifest & Gate Runbook):** 16 release tests (`tests/release/`). Exact inventory set equality enforcement (`RESEARCH_RELEASE` vs `FULL_PRODUCT_RELEASE`), production `get_repo_git_sha()` resolution, fail-closed tamper detection, and verified 10-step local release gate runbook under 100% `rtk` command prefix discipline.
  4. **Full Monorepo Quality Gate:** 552 pytest tests passing (0 failures), Ruff lint clean (0 violations), MyPy strict clean across 55 source files, 18 frontend Vitest tests passing, `tsc -b && vite build` clean, and 2/2 Playwright Chromium browser journeys passing.
  5. **Production Audit & Santa Method:** 100/100 score on Production Readiness Audit (`.orchestration/evidence/production-audit.md`) and dual Santa review convergence with `VERDICT: PASS`.
- **Recommendation:** Hand over the completed candidate commit to the Human Owner for final merge and deployment approval.
