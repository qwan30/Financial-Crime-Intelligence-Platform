# SDLC Mario E2E Task Kanban

## Backlog / Plans Progress: 41/41 Merged or Implemented (100%)

### Plan 1: Research Foundation & Tracing (16/16 - 100% MERGED)
- [x] Phase 0-6 Research Tasks (PR #4 - #19)

### Plan 2: Detection Pilot Data Intake (7/7 - 100% MERGED)
- [x] Pilot Intake Tasks (PR #20 - #29)

### Plan 3: Investigator Workbench & DeepSeek (9/9 - 100% IMPLEMENTED & AUDITED)
- [x] Task 1: Define evidence and case contracts (`src/fincrime/evidence/models.py`, `src/fincrime/cases/models.py`)
- [x] Task 2: Implement append-only evidence and case services (`src/fincrime/evidence/store.py`, `src/fincrime/cases/service.py`)
- [x] Task 3: Expose bounded Case API (`apps/case_api/main.py`)
- [x] Task 4: Define bounded investigation tools (`src/fincrime/agent/tools.py`)
- [x] Task 5: Bound DeepSeek usage and local cost caps (`src/fincrime/agent/settings.py`)
- [x] Task 6: Add guarded DeepSeek provider adapter (`src/fincrime/agent/deepseek.py`)
- [x] Task 7: Orchestrate investigator workflow with LangGraph (`src/fincrime/agent/workflow.py`)
- [x] Task 8: Implement LLM boundary evaluation (`src/fincrime/agent/evaluation.py`, `data/manifests/eval_corpus_gold_cases.json`)
- [x] Task 9: Build minimal investigator React workbench (`apps/investigator-web/`)

### Plan 4: MLOps, Streaming & Release (9/9 - 100% IMPLEMENTED & AUDITED)
- [x] Task 1: Log frozen runs to local MLflow (`src/fincrime/mlops/tracking.py`)
- [x] Task 2: Define versioned streaming events (`src/fincrime/streaming/events.py`)
- [x] Task 3: Implement idempotent replay state (`src/fincrime/streaming/state.py`)
- [x] Task 4: Prove offline/online scoring parity (`src/fincrime/streaming/scoring.py`)
- [x] Task 5: Add local streaming infrastructure (`infra/docker-compose.yml`)
- [x] Task 6: Replay broker messages with validation & quarantine (`src/fincrime/streaming/replay.py`)
- [x] Task 7: Operational metrics & distribution drift monitoring (`src/fincrime/monitoring/`)
- [x] Task 8: Bind release evidence to exact hashes (`src/fincrime/release/manifest.py`)
- [x] Task 9: Define exact-SHA local release gate runbook (`docs/runbooks/local-release.md`)
