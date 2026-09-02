# Financial Crime Intelligence Platform

An intelligence platform and TraceBench evaluation harness for anti-money laundering (AML) research, forensic graph investigation, and streaming transaction triage.

The platform integrates temporal graph feature engineering, statistical and graph neural network baselines, a guarded investigator reasoning copilot, and an interactive analyst workbench with end-to-end evidence provenance.

---

## Core Trust Model

The platform enforces strict operational boundaries to ensure scientific reproducibility, audit compliance, and data integrity:

- **Leakage-Free Temporal Graph Construction**: Point-in-time account feature calculation and cutoff-aware `MultiDiGraph` construction prevent future-data contamination during training and feature extraction.
- **Cryptographic Lineage & Write-Once Storage**: Ingested datasets produce deterministic SHA-256 provenance hashes and write-once Parquet artifacts. Every model release is sealed with a cryptographic manifest.
- **Rigorous Model Promotion Gating**: An ordered training-run state machine enforces 5-seed bootstrap evaluation before any model can be promoted.
- **Guarded, Evidence-Bound AI Reasoning**: The DeepSeek reasoning provider is optional, budget-managed, and fail-closed (`INSUFFICIENT_EVIDENCE`, `AI_UNAVAILABLE`, `AI_INVALID_OUTPUT`). Every hypothesis claim must explicitly cite valid, non-empty case evidence IDs.
- **Idempotent Analyst Feedback**: Investigator decisions and feedback are tracked as immutable events (`AnalystFeedbackEvent`) with idempotency keys, preventing audit tampering and duplicate adjudication.
- **Offline/Online Scoring Parity**: Real-time graph state accumulation is verified against batch oracle scoring, backed by durable JSONL file quarantine for malformed or out-of-order records.

---

## System Architecture

The implemented architecture is organized into three decoupled operating lanes:

1. **Offline Research & Release Evidence**: Raw transaction extraction, quarantine, temporal graph feature calculation, tabular (Logistic Regression, LightGBM) and GraphSAGE training, bootstrap promotion gates, MLflow logging, and release manifest packaging.
2. **Investigator Workbench & Guarded Agent**: FastAPI case API, in-memory case/evidence stores, bounded graph traversal, React 19/Cytoscape investigator UI, and guarded DeepSeek hypothesis generation.
3. **Streaming Replay & Quarantine**: Strict envelope parsing, replay state machine, durable JSONL quarantine, and an online graph accumulator validated for offline/online scoring parity.

[![Implemented System Architecture](docs/architecture/archify/implemented-system.svg)](docs/architecture/archify/implemented-system.html)

> 🎬 **Interactive & Motion Previews:**
> - 🌐 [**Open Interactive HTML App**](docs/architecture/archify/implemented-system.html) — Live canvas with zoom/pan, chapter navigation, component spotlighting, and dark/light theme switching.
> - 🎥 [**Watch Trace Motion Video (WebM)**](docs/architecture/archify/implemented-system.webm) — 6-second recording illustrating continuous particle data flow across all three operating lanes.

---

## Investigation & Adjudication Workflow

The forensic workflow bridges automated graph intelligence and human analyst oversight:

1. **Case Hydration & Evidence Retrieval**: `GET /cases/{case_id}/workbench` fetches an immutable case snapshot, associated evidence items, and performs bounded multi-hop fund tracing on the transaction graph.
2. **Guarded Hypothesis Generation**: The case snapshot and verified evidence are submitted to DeepSeek Reasoner under strict token budgets. Output is validated against cited evidence IDs. If evidence is missing, budget is exhausted, or citations fail validation, the system fails closed gracefully.
3. **Analyst Review & Adjudication**: The human investigator examines the interactive graph topology, reviews supporting/mitigating evidence, evaluates the AI hypothesis, and submits disposition via `POST /cases/{case_id}/feedback`.

[![Investigation & Adjudication Workflow](docs/architecture/archify/investigation-workflow.svg)](docs/architecture/archify/investigation-workflow.html)

> 🎬 **Interactive & Motion Previews:**
> - 🌐 [**Open Interactive HTML App**](docs/architecture/archify/investigation-workflow.html) — Step through animated state transitions, trace prompt/evidence flows, and inspect fail-closed branches.
> - 🎥 [**Watch Workflow Animation Video (WebM)**](docs/architecture/archify/investigation-workflow.webm) — 6-second motion capture detailing the end-to-end hydration, guarded reasoning, and feedback cycle.

---

## Implemented Capabilities

| Subsystem | Components / Modules | Implemented Capability |
|---|---|---|
| **Data Ingestion & Quality** | `src/fincrime/data` | Safe archive extraction, source adapters, quarantine routing, write-once Parquet artifacts, provenance hashing, split leakage checks. |
| **Graph & Features** | `src/fincrime/graph`, `src/fincrime/features` | Cutoff-aware NetworkX `MultiDiGraph` construction, temporal edge filtering, point-in-time account feature engineering. |
| **Model Training & Gating** | `src/fincrime/training` | Logistic Regression, LightGBM, 2-layer GraphSAGE (PyG), 5-seed bootstrap statistical promotion gate, ordered training state machine. |
| **Evaluation & MLOps** | `src/fincrime/evaluation`, `mlops`, `monitoring`, `release` | Detection/tracing metrics, MLflow run logging and verification, PSI drift calculation, Prometheus metrics, SHA-256 release manifests. |
| **Case Management & API** | `apps/case_api`, `src/fincrime/cases`, `src/fincrime/evidence` | In-memory lock-protected case & evidence stores, FastAPI endpoints (`/healthz`, `/cases`, `/cases/{id}/workbench`, `/cases/{id}/feedback`). |
| **Investigator UI** | `apps/investigator-web` | React 19, Vite 6, Cytoscape graph visualization, case summary cards, evidence inspection, hypothesis display, feedback submission. |
| **Guarded AI Reasoning** | `src/fincrime/agent` | `GuardedDeepSeekProvider` with budget reservation/reconciliation, structured hypothesis parsing, mandatory evidence citation validation, fail-closed handling. |
| **Streaming & Parity** | `src/fincrime/streaming` | Strict transaction envelopes, replay state machine, durable JSONL quarantine store, online graph accumulator with offline/online scoring parity. |

---

## Honest Implementation Boundaries

| Area | Current Implemented Code | Planned Target Architecture |
|---|---|---|
| **Storage & Persistence** | In-memory, thread-safe / lock-protected stores (`CaseService`, `EvidenceStore`, `InMemoryGraphRepository`). | Persistent PostgreSQL 17 relational database and Redis 8.0 caching layer. |
| **Messaging & Ingestion** | In-memory streaming replay state machine and file-based durable JSONL quarantine. | Distributed Kafka 4.0 cluster with durable consumer group offsets. |
| **Advanced Graph Models** | Tabular baselines and 2-layer GraphSAGE. `advanced_gate.py` evaluates justification (`JUSTIFIED_NULL`). | Heterogeneous Graph Transformers (HGT) and Temporal Graph Networks (TGN). |
| **AI Role & Autonomy** | Advisory copilot only; fails closed to `AI_UNAVAILABLE` or `AI_INVALID_OUTPUT`; requires human adjudication. | Autonomous multi-agent coordination with automated SAR draft generation. |
| **Architecture Documentation** | `docs/architecture/archify/*` represents current codebase implementation. | `docs/architecture/diagrams/*` represents planned target specifications. |

---

## Getting Started

### Prerequisites

- **Python**: `>=3.12,<3.13` with [uv](https://docs.astral.sh/uv/) package manager
- **Node.js**: `>=20` with `npm` (for investigator UI)
- **Docker**: (Optional) for local infrastructure services

---

### Python Environment & Tests

1. **Install dependencies**:
   ```bash
   uv sync --all-groups
   ```

2. **Run test suite**:
   ```bash
   uv run --all-groups pytest -q --tb=short
   ```

---

### Running the Case API

Start the local FastAPI case management server:

```bash
uv run uvicorn apps.case_api.main:app --host 127.0.0.1 --port 8000
```

Key routes available:
- `GET /healthz`: Health check
- `POST /cases`: Create a case
- `GET /cases/{case_id}`: Retrieve case details
- `GET /cases/{case_id}/workbench`: Retrieve aggregated case snapshot, evidence, fund trace, and hypothesis
- `POST /cases/{case_id}/feedback`: Submit idempotent analyst feedback

---

### Running the Investigator Web UI

The investigator workbench is located under `apps/investigator-web`:

1. **Install dependencies**:
   ```bash
   cd apps/investigator-web
   npm ci
   ```

2. **Run development server**:
   ```bash
   npm run dev
   ```

3. **Run unit tests**:
   ```bash
   npm test -- --run
   ```

4. **Build production bundle**:
   ```bash
   npm run build
   ```

---

### Local Infrastructure (Optional)

Local supporting services (Kafka 4.0, Redis 8.0, PostgreSQL 17) are configured in `infra/docker-compose.yml` for testing environment contracts:

```bash
POSTGRES_PASSWORD=fincrime_local docker compose -f infra/docker-compose.yml up -d
```

> **Note**: Current application repositories operate in-memory and do not require Docker services to run unit tests or local development servers.

---

## Documentation & License

- **Target Architecture Documentation**: See [docs/architecture/README.md](docs/architecture/README.md) for target specifications, C4 diagrams, and domain entity relationships.
- **License**: Released under the [Apache-2.0 License](LICENSE).
