# Financial Crime Intelligence Platform — Design Specification

**Date:** 2026-08-27
**Status:** Approved design / ready for implementation planning
**Project type:** Research-grade AML detection + production-grade AI investigation platform
**Primary domain:** Fiat banking Anti-Money Laundering (AML)
**Primary repository name:** `financial-crime-intelligence-platform`

---

## 1. Executive Summary

Financial Crime Intelligence Platform is an end-to-end AML research and investigation system for fiat banking. It is designed to detect suspicious accounts and suspicious transaction subgraphs rather than only classify individual transactions.

The system combines:

- temporal heterogeneous graph learning,
- supervised AML typology recognition,
- unsupervised graph and behavioral anomaly detection,
- calibrated multi-model risk fusion,
- real-time transaction scoring,
- suspicious-subgraph discovery,
- evidence-backed explanations,
- an AI investigation agent,
- analyst feedback and case disposition,
- drift monitoring and human-gated model lifecycle management,
- adversarial stress testing using synthetic AML simulations.

The project intentionally reuses mature open-source components and public datasets where they are already strong, while concentrating custom engineering on the system boundaries and research contributions that create differentiated value.

The guiding principle is:

> Reuse commodity infrastructure and baseline algorithms; build the banking-specific temporal graph representation, AML risk fusion, novelty detection, investigation workflow, evidence model, and evaluation framework.

---

## 2. Project Goals

### 2.1 Primary goals

The platform must:

1. Detect high-risk accounts/entities from continuously arriving banking events.
2. Detect suspicious groups, paths, rings, and transaction subgraphs.
3. Recognize known AML typologies.
4. Detect previously unseen or intentionally held-out AML behaviors as anomalies.
5. Produce evidence explaining why a case was created.
6. Support near-real-time transaction scoring from Kafka events.
7. Provide an analyst investigation interface centered on cases, entities, timelines, graph evidence, and AI-assisted investigation.
8. Preserve sufficient provenance to reconstruct why a model decision was made.
9. Support reproducible offline experiments, chronological holdout evaluation, ablation studies, adversarial AML stress tests, and latency benchmarks.
10. Use analyst feedback for evaluation and future training without directly auto-updating production models.

### 2.2 Secondary goals

The platform should:

- make it easy to compare classical, graph, and temporal models;
- demonstrate strong MLOps and model governance practices;
- expose clear system-health, model-health, and AML-operations telemetry;
- allow local end-to-end execution using Docker Compose;
- remain modular enough that individual ML components can be replaced without rewriting the product.

---

## 3. Non-Goals for V1

The following are explicitly outside V1 scope:

- cryptocurrency AML,
- federated learning,
- blockchain analysis,
- automatic account freezing,
- autonomous filing of regulatory reports,
- fully automated production model promotion,
- production Kubernetes operations,
- building a custom graph database,
- training foundation models,
- implementing dozens of anomaly algorithms from scratch,
- building an enterprise IAM platform,
- fabricating banking entities that the source data cannot support.

Kubernetes manifests may exist as optional deployment examples, but Docker Compose is the primary supported environment.

---

## 4. Core Problem Definition

The system is not primarily a transaction-level binary classifier.

### 4.1 Primary scoring targets

The two primary objects are:

1. **Entity risk** — a continuously updated risk score for accounts and other eligible banking entities.
2. **Suspicious subgraph risk** — a score for a connected group, path, ring, or network of entities and transactions that may correspond to coordinated financial-crime behavior.

A transaction is treated as a time-stamped event and evidence source that updates one or more entity states and may contribute to a suspicious subgraph.

### 4.2 Core AML typologies

V1 must support the following known typologies:

- rapid pass-through,
- fan-in,
- fan-out,
- circular transactions,
- structuring,
- smurfing,
- layering,
- multi-hop routing,
- mule collection.

For investigation and reporting, typologies are grouped hierarchically:

- **Flow**: fan-in, fan-out, rapid pass-through
- **Obfuscation**: layering, circular flow, multi-hop routing
- **Structuring**: structuring, smurfing
- **Mule activity**: mule collection

---

## 5. Dataset Strategy

### 5.1 Primary dataset: AusAML / AMLBench

AusAML is the primary training, validation, and evaluation dataset.

It is used for:

- model training,
- strict chronological validation,
- strict chronological holdout testing,
- graph and temporal representation experiments,
- known-typology evaluation,
- ablation studies,
- model comparison.

The dataset must not be merged naively with AMLSim outputs into a single training population because their generative distributions differ.

### 5.2 Synthetic stress dataset: IBM AMLSim

AMLSim is used as a controllable adversarial scenario generator rather than the main training corpus.

It must support stress scenarios such as:

- slower laundering,
- smaller transaction amounts,
- additional laundering hops,
- larger mule rings,
- changed graph topology,
- delayed cash-out,
- lower-velocity transaction patterns,
- topology-preserving amount perturbation,
- topology-changing routing perturbation,
- intentionally novel/held-out suspicious patterns.

AMLSim stress tests are used to measure model robustness and degradation under changing laundering behavior.

### 5.3 Data separation policy

Train, calibration, validation, stress, and holdout datasets must have explicit provenance and must not silently overlap.

All model-selection logic must avoid holdout leakage.

---

## 6. Temporal Evaluation Policy

Random train/test splits are not allowed for headline evaluation when they create temporal or graph leakage.

The default evaluation split is chronological:

- **Train**: earliest time interval
- **Calibration / model selection**: immediately following interval
- **Holdout**: latest untouched interval

Exact dates or steps depend on dataset availability, but the ordering is mandatory.

Where graph connectivity crosses split boundaries, preprocessing must preserve causal availability: future events may not affect features or embeddings used to score earlier events.

---

## 7. Banking Graph Ontology

### 7.1 Core node types

The core heterogeneous graph contains:

- `Customer`
- `Account`
- `Transaction`
- `Merchant`
- `Device`
- `Bank`
- `Branch`

Optional node types may be enabled only when supported by reliable source data:

- `IP`
- `Address`
- `Phone`
- `Country`
- `Beneficiary`

The system must not invent optional entities solely to increase graph complexity.

### 7.2 Core edge/relationship types

Examples include:

- `Customer -[OWNS]-> Account`
- `Account -[USES]-> Device`
- `Account -[HELD_AT]-> Bank`
- `Bank -[HAS_BRANCH]-> Branch`
- `Account -[SENDS]-> Transaction`
- `Transaction -[RECEIVED_BY]-> Account`
- `Transaction -[AT_MERCHANT]-> Merchant`

For temporal graph modeling, the core financial event may also be represented as a directed temporal interaction:

`Account_A -[TRANSFER(amount, time, channel, ...)] -> Account_B`

### 7.3 Graph representation requirements

The ML graph representation must be:

- heterogeneous,
- temporal,
- causally constructed,
- compatible with PyTorch Geometric or an equivalent reusable graph-learning framework,
- serializable/reproducible from source events and schema versions.

---

## 8. Feature System

### 8.1 Feature families

The system should compute features from four families:

#### Transaction features

- amount,
- currency-normalized amount when needed,
- channel,
- merchant/category context,
- transaction type,
- timestamp encodings.

#### Behavioral features

Examples:

- `txn_count_5m`
- `txn_count_1h`
- `txn_count_24h`
- `incoming_amount_30m`
- `outgoing_amount_30m`
- `new_counterparty_ratio`
- `pass_through_ratio`
- `time_since_last_txn`
- behavioral deviation from trailing history.

#### Graph features

Examples:

- temporal in-degree,
- temporal out-degree,
- unique counterparties,
- fan-in score,
- fan-out score,
- cycle score,
- path length statistics,
- suspicious-neighbor ratio,
- local density,
- motif counts where computationally practical.

#### Device/context features

When supported:

- device novelty,
- device switching rate,
- location change,
- merchant novelty,
- channel novelty.

### 8.2 Feature store

**Feast is the V1 feature-store abstraction.** Redis is the online store; offline historical feature materialization is backed by Parquet/warehouse data.

Expected design:

- offline store: Parquet/warehouse-backed historical features,
- online store: Redis or equivalent low-latency key-value store,
- common feature definitions shared across offline and online computation.

Offline/online feature parity is a hard requirement for features used in online scoring.

---

## 9. Model Strategy

### 9.1 Baseline ladder

The platform must benchmark a progression of increasingly expressive models:

1. deterministic AML rules/heuristics,
2. tabular statistical models,
3. Isolation Forest and/or tabular Autoencoder,
4. a strong supervised tabular baseline such as LightGBM/XGBoost,
5. PyGOD graph outlier detectors such as DOMINANT, CoLA, CONAD, GADNR, or other suitable candidates,
6. static graph models such as GraphSAGE and GAT,
7. heterogeneous graph models such as HGT,
8. Temporal Graph Network (TGN)-style model,
9. the project’s hybrid temporal heterogeneous AML model.

Not every baseline must be deployed online. Baselines primarily exist for research comparison.

### 9.2 Hybrid modeling objective

The V1 research contribution is not a new GNN primitive from first principles.

The custom contribution is the integration and extension of reusable graph/temporal backbones into a banking-specific architecture combining:

- temporal banking graph representation,
- heterogeneous entity encoding,
- supervised AML risk prediction,
- unsupervised novelty detection,
- typology prediction,
- suspicious-subgraph discovery,
- calibrated risk fusion.

### 9.3 Supervised and unsupervised heads

The model stack must include both:

- **supervised heads** for known AML labels/typologies,
- **unsupervised or self-supervised anomaly heads** for novelty detection.

The system must be able to produce high anomaly risk for a held-out suspicious pattern even when the supervised typology classifier has never seen that pattern during training.

---

## 10. Temporal Graph Model

### 10.1 Event-based modeling

The main temporal architecture is event-based, inspired by TGN-style continuous-time graph learning.

A transaction event triggers:

1. event encoding,
2. temporal message creation,
3. entity memory/state update,
4. temporal neighborhood aggregation,
5. updated entity embeddings,
6. one or more risk heads.

Snapshot-based temporal graphs may be used only as offline research baselines, not as the primary online architecture.

### 10.2 Heterogeneous integration

The V1 hybrid model uses one concrete architecture: **typed TGN memory + relation-aware HGT-style temporal neighborhood attention**.

For each supported node type, raw attributes are projected into a shared embedding space using a type-specific encoder. Each transaction creates a typed temporal message containing source/destination entity types, relation type, transaction attributes, and time encoding. Entity memories are updated using a TGN-style recurrent memory updater. At scoring time, the current entity memory is combined with a bounded set of causally valid temporal neighbors using relation-aware multi-head attention inspired by HGT.

The resulting entity representation feeds the supervised AML head, novelty/anomaly head, and typology head. This architecture is the project hybrid model; GraphSAGE, GAT, HGT-only, and TGN-only remain comparison baselines.

---

## 11. Risk Fusion

### 11.1 Risk inputs

Risk fusion may combine:

- behavioral anomaly score,
- graph anomaly score,
- temporal anomaly score,
- supervised AML probability,
- typology-specific confidence,
- deterministic rule evidence.

### 11.2 V1 fusion strategy

The primary V1 approach is calibrated weighted fusion. Each component score is calibrated on the calibration split using Platt scaling for probabilistic supervised outputs and isotonic calibration when monotonic non-parametric calibration is empirically better. Anomaly scores are transformed to calibrated risk percentiles/probabilities using calibration-only reference distributions.

Fusion weights are constrained to be non-negative and sum to one. They are selected only on the calibration split using a documented objective that prioritizes PR-AUC/precision-at-K while respecting an alert-volume guardrail. Holdout data must never be used to select calibration functions, weights, or thresholds.

This approach must be benchmarked against at least one learned meta-model, such as:

- logistic regression,
- gradient-boosted model,
- small MLP.

If learned fusion does not provide meaningful holdout gains, calibrated deterministic fusion remains the preferred production approach because it is easier to explain and govern.

---

## 12. Suspicious Subgraph Discovery

The platform must support discovery and scoring of suspicious neighborhoods, paths, rings, or connected transaction groups.

Subgraph discovery may use a combination of:

- thresholded high-risk entities,
- graph neighborhood expansion,
- typology-specific traversal patterns,
- temporal windows,
- cycle/path analysis,
- community/ring heuristics,
- learned node/edge scores.

The implementation must avoid unbounded graph expansion. Query depth, time windows, node limits, and evidence limits must be explicit.

---

## 13. Unknown-Typology Experiment

This is a flagship research experiment and is mandatory.

### 13.1 Protocol

At least one suspicious typology or scenario family is intentionally excluded from supervised training.

The model is evaluated on whether its anomaly/novelty components can still surface the unseen behavior.

### 13.2 Example

If circular laundering is held out from supervised training:

- supervised circular-flow head has no training signal for that class,
- temporal/graph novelty components must still raise anomaly risk for circular flow,
- the system should avoid falsely claiming a known typology label if not supported.

### 13.3 Metrics

Report:

- unseen-pattern detection rate,
- precision of novelty alerts,
- ranking position of unseen-pattern cases,
- alert-volume impact,
- comparison against supervised-only models.

---

## 14. Adversarial AMLSim Stress Testing

AMLSim must be used to generate controlled laundering mutations.

Stress dimensions include:

- transfer-size reduction,
- velocity reduction,
- increasing/decreasing hop count,
- increasing ring size,
- routing-topology mutation,
- delayed cash-out,
- splitting amounts across more accounts,
- merging flows into fewer collectors.

The system must measure performance degradation as a function of scenario difficulty.

A required research output is a plot or table equivalent to:

`Detection Rate vs. Adversary Difficulty`.

---

## 15. Online Streaming Architecture

### 15.1 Primary event flow

Kafka is the event backbone. V1 uses a dedicated Python consumer/service architecture rather than Spark/Flink on the scoring hot path; Spark may be used only for offline/batch experimentation if useful.

The online path is:

1. banking transaction/event source,
2. Kafka,
3. schema validation,
4. quarantine invalid events,
5. online feature computation/lookup,
6. temporal graph-state update,
7. model inference,
8. risk fusion,
9. evidence-package creation,
10. alert/case creation,
11. asynchronous persistence to investigation stores.

### 15.2 Hot-path constraints

The hot path must not depend on expensive Neo4j traversals.

Near-real-time scoring uses dedicated online feature/state components.

### 15.3 Latency target

Target:

- p95 incremental scoring latency < 500 ms under the project’s documented benchmark workload.

This target excludes offline training and full graph reconstruction.

---

## 16. Graph State and Neo4j Responsibilities

### 16.1 Training graph

PyTorch Geometric or equivalent is the primary representation for model training and offline graph ML.

### 16.2 Online temporal state

A dedicated graph-state service owns bounded incremental temporal state. Redis is the durable online state backend for entity feature/state records and replay checkpoints. The graph-state service may keep a bounded in-process cache for hot entity memories, but Redis is the recovery source for online state and checkpoint metadata. Model-specific large tensor checkpoints are versioned in MinIO/MLflow artifacts rather than stored as unbounded Redis values.

Kafka partition ordering and stable entity/event identifiers are used to make updates deterministic enough for replay. State updates must be idempotent with respect to event IDs.

### 16.3 Neo4j

Neo4j is an investigation/query store, not the mandatory scoring hot path.

It is used for:

- path queries,
- suspicious-neighbor discovery,
- ring visualization,
- analyst graph exploration,
- evidence retrieval,
- case investigation.

---

## 17. Evidence Model

Every case and material model conclusion must be grounded in explicit evidence.

### 17.1 Evidence package

A risk event/case should be able to include:

- final risk score,
- component scores,
- detected typologies,
- anomalous features,
- suspicious counterparties,
- suspicious transaction paths,
- relevant graph/subgraph identifiers,
- temporal patterns,
- model version,
- feature version,
- event IDs,
- evidence IDs.

### 17.2 Evidence invariants

Evidence IDs must map to reconstructable source facts.

An AI agent or explanation layer may not cite an evidence ID that does not exist in the evidence package.

---

## 18. AI Investigation Agent

### 18.1 Scope

V1 includes a full AI investigation agent, but it is not permitted to autonomously execute regulated or irreversible banking actions.

### 18.2 Recommended orchestration

LangGraph or a similar explicit state-machine framework is preferred because the investigation process is multi-step, stateful, tool-driven, and must remain auditable.

### 18.3 Agent tools

The agent may access bounded tools for:

- case summary retrieval,
- entity profile retrieval,
- transaction timeline retrieval,
- historical behavior comparison,
- graph-neighbor search,
- path/ring query,
- model score retrieval,
- typology evidence retrieval,
- prior-case lookup when allowed,
- evidence retrieval,
- contradiction checks.

### 18.4 Agent workflow

The agent should follow:

1. read case and risk components,
2. inspect timeline,
3. inspect graph neighborhood/path evidence,
4. inspect historical behavior,
5. construct one or more investigation hypotheses,
6. search for supporting evidence,
7. search for contradictory evidence,
8. classify confidence,
9. produce a case narrative,
10. recommend next analyst checks.

### 18.5 Agent safety boundaries

The agent must not:

- freeze an account,
- file a regulatory report,
- modify the model score,
- delete or rewrite evidence,
- promote models,
- silently update case disposition,
- fabricate evidence.

If evidence is insufficient, the output must explicitly state `UNKNOWN` or `INSUFFICIENT EVIDENCE` rather than infer unsupported facts.

### 18.6 Grounding requirement

Material statements in the case narrative must cite internal `evidence_id` values.

The application must validate those IDs against the evidence package before presenting the narrative as grounded.

---

## 19. Analyst Workflow

### 19.1 Allowed dispositions

At minimum:

- Confirmed suspicious
- False positive
- Escalate
- Insufficient evidence

### 19.2 Feedback capture

Disposition records must contain:

- analyst/user identifier,
- timestamp,
- case ID,
- selected disposition,
- optional reason/comment,
- model version,
- evidence snapshot or evidence-package version.

### 19.3 Feedback use

Analyst feedback may be used for:

- offline evaluation,
- error analysis,
- future retraining datasets,
- threshold analysis,
- active-learning extensions.

Feedback must not trigger direct autonomous production retraining or promotion in V1.

---

## 20. Investigation UI

### 20.1 Research constraint

Mobbin was selected as the preferred UI-reference source, but the available Mobbin connector currently requires a paid plan. Therefore, V1 specification fixes the functional information architecture without claiming Mobbin-derived visual references.

When Mobbin access is available, the UI may be visually refined using relevant case-management, fraud-operations, security-operations, graph-investigation, and analyst-workbench patterns without changing core product behavior.

### 20.2 Primary screens

The product contains:

- Operations Dashboard
- Alert Queue
- Case Investigation
- Entity Profile
- Graph Explorer
- Transaction Timeline
- Evidence Viewer
- AI Investigator
- Analyst Disposition
- Model/Drift Console

### 20.3 Frontend stack and main workspace

The investigator application uses **React + TypeScript**. Graph exploration uses **Cytoscape.js** (or a compatible graph visualization library only if Cytoscape proves inadequate during implementation), and quantitative timeline/metric visualizations use a lightweight React charting library. The UI communicates only through typed Case API endpoints and does not query Neo4j or model stores directly.

The Case Investigation screen is the primary UI and receives the majority of design effort.

Expected layout areas:

- case header and overall risk,
- network/graph visualization,
- transaction timeline,
- evidence/model explanation panel,
- AI investigator panel,
- analyst actions/disposition.

The product must avoid becoming a dashboard composed mainly of generic charts. Investigation context and evidence are primary.

---

## 21. Data Quality and Governance

### 21.1 Event validation

Incoming events must be validated against explicit schemas.

Invalid events are quarantined rather than silently coerced into valid data.

### 21.2 Provenance

Each scored decision must be able to record or resolve:

- event ID,
- source/dataset,
- event timestamp,
- feature-schema version,
- feature values or reproducible feature references,
- graph-state/snapshot version where applicable,
- model version,
- rule version,
- component risk scores,
- final score,
- evidence IDs.

### 21.3 Artifact integrity

Where practical, persist cryptographic hashes for:

- dataset artifacts,
- feature schema,
- model artifact,
- configuration,
- source Git commit.

The objective is decision reconstruction, not cryptography for its own sake.

---

## 22. Privacy and Security Simulation

The project uses synthetic or already anonymized/public datasets.

Requirements:

- no real PII,
- synthetic or anonymized entity IDs,
- basic analyst-role separation in the product model,
- audit logging for investigation actions and dispositions,
- secrets managed through environment/config tooling rather than committed source code.

The project does not attempt to implement a full banking IAM/security platform.

---

## 23. Drift Monitoring

### 23.1 Feature drift

Monitor distributions such as:

- transaction amount,
- transaction velocity,
- channel mix,
- new-counterparty ratio,
- behavioral feature distributions.

### 23.2 Graph drift

Monitor statistics such as:

- degree distributions,
- component sizes,
- neighborhood size,
- clustering/density metrics where practical,
- motif or typology-proxy frequencies.

### 23.3 Model drift

Monitor:

- PR-AUC when labels are available,
- precision@K,
- calibration,
- alert rate,
- typology recall,
- false-positive rate,
- risk-score distribution.

Drift signals may trigger candidate retraining workflows but not automatic promotion.

---

## 24. Model Lifecycle

MLflow or an equivalent experiment/registry system is required.

Track:

- dataset/version references,
- Git SHA,
- parameters,
- metrics,
- artifacts,
- model package,
- evaluation reports,
- candidate/champion status.

### 24.1 Retraining workflow

The required lifecycle is:

1. drift or scheduled research trigger,
2. candidate retraining,
3. chronological evaluation,
4. calibration,
5. unknown-typology evaluation,
6. adversarial AMLSim stress tests,
7. shadow/challenger evaluation where implemented,
8. human review,
9. explicit promotion.

Production auto-promotion is prohibited in V1.

---

## 25. Evaluation Framework

Accuracy alone is not an acceptable headline metric.

### 25.1 Core model metrics

- PR-AUC
- recall at fixed precision
- precision at top-K cases
- F1 as a secondary metric
- calibration error / Brier score where appropriate

### 25.2 AML metrics

- detection rate per AML typology
- suspicious subgraph/ring recall
- unseen-typology detection rate
- time-to-detection
- monetary exposure captured when amount data supports it

### 25.3 Operational metrics

- false positives per 1,000 accounts
- alerts per day or normalized simulated-day equivalent
- case volume
- p50/p95/p99 scoring latency
- throughput
- quarantine/error rates

### 25.4 Comparison requirements

The final benchmark must include:

- classical/tabular baseline,
- static graph baseline,
- graph anomaly baseline,
- temporal graph baseline,
- hybrid system.

---

## 26. Ablation Studies

At minimum, evaluate the effect of removing or replacing:

- temporal modeling,
- heterogeneous entity types,
- graph anomaly component,
- behavioral anomaly component,
- supervised typology head,
- risk fusion strategy,
- selected graph/context features.

The aim is to demonstrate which parts materially improve detection rather than merely increase system complexity.

---

## 27. Observability

### 27.1 Stack

Use:

- structured application logs,
- Prometheus,
- Grafana.

### 27.2 Operational telemetry

Expected metrics include:

- `transactions_processed_total`
- `scoring_latency_seconds`
- `alerts_created_total`
- `alert_rate`
- `kafka_consumer_lag`
- `feature_lookup_latency_seconds`
- `graph_state_update_latency_seconds`
- `model_score_distribution`
- `quarantine_events_total`
- `agent_latency_seconds`
- `agent_grounding_failures_total`
- `graph_nodes`
- `graph_edges`

### 27.3 Grafana views

Provide at least three logical dashboards:

- System Health
- Model Health
- AML Operations

---

## 28. Infrastructure

### 28.1 Primary environment

Docker Compose is the supported local integration environment.

Expected infrastructure/services include:

- Kafka
- PostgreSQL
- Redis
- Neo4j
- MinIO
- MLflow
- Prometheus
- Grafana
- ingestion service
- feature service/engine
- graph-state service
- scoring service
- case API
- investigation agent
- investigator web application

### 28.2 Kubernetes

Kubernetes manifests are optional examples only and must not become a dependency for local development or core acceptance tests.

---

## 29. Service Boundaries

### 29.1 Ingestion service

Responsibilities:

- consume/replay banking events,
- validate schemas,
- quarantine invalid data,
- publish normalized events.

### 29.2 Feature engine

Responsibilities:

- compute/update online features,
- enforce feature definitions,
- serve or materialize online features,
- preserve offline/online parity.

### 29.3 Graph-state service

Responsibilities:

- update bounded temporal state,
- expose model-required neighborhood/state information,
- avoid dependence on slow investigation queries.

### 29.4 Scoring service

Responsibilities:

- load production model package,
- obtain online features/state,
- score entities/events,
- perform risk fusion,
- create evidence packages,
- publish risk events.

### 29.5 Case API

Responsibilities:

- manage alerts/cases,
- expose case timelines/evidence,
- persist analyst dispositions,
- provide bounded endpoints to UI and investigation tools.

### 29.6 Investigation agent

Responsibilities:

- orchestrate evidence-grounded investigation,
- query approved tools,
- produce hypotheses, contradictions, narratives, and recommended next checks,
- never perform irreversible banking actions.

### 29.7 Investigator web

Responsibilities:

- analyst alert queue,
- case investigation workspace,
- graph/timeline exploration,
- evidence visualization,
- AI investigator interaction,
- disposition capture.

---

## 30. API and Event Design Principles

- Every externally meaningful event must have a stable event ID.
- Schemas must be versioned.
- Risk events must reference the exact model/feature/evidence versions used.
- APIs should return typed, bounded objects rather than raw database rows.
- Agent tools should expose narrow investigation capabilities, not unrestricted database access.
- Services should communicate using explicit contracts that allow independent testing.

---

## 31. Failure Handling

### 31.1 Invalid data

Invalid events are quarantined with a reason code and are not silently processed.

### 31.2 Feature/state failures

A scoring request/event that cannot obtain required features or temporal state must produce a typed failure outcome rather than an ungrounded score.

### 31.3 Model failures

Model-loading and inference errors must fail closed for scoring: no synthetic risk score may be fabricated.

### 31.4 Agent failures

If the AI provider fails or evidence retrieval is incomplete, the case remains accessible without AI narrative. The system must surface an explicit degraded/insufficient-evidence state.

### 31.5 Persistence failures

Risk events and cases should be idempotently creatable from stable IDs where practical so retrying does not duplicate investigation records.

---

## 32. Testing Strategy

### 32.1 Unit tests

Cover:

- feature calculations,
- graph transformations,
- typology rules,
- risk fusion,
- evidence validation,
- agent grounding checks,
- schema validation,
- time-window logic.

### 32.2 ML tests

Cover:

- deterministic seeds where possible,
- no train/holdout leakage,
- reproducible preprocessing,
- baseline smoke training,
- model-package load/score compatibility,
- calibration behavior.

### 32.3 Integration tests

Cover:

- Kafka event → normalized event,
- event → online features,
- event → graph state update,
- event → risk event,
- risk event → case,
- case → agent investigation,
- analyst disposition persistence.

### 32.4 End-to-end test

A deterministic synthetic scenario must exercise:

`AMLSim/AusAML replay -> Kafka -> validation -> features -> graph update -> inference -> risk fusion -> alert -> case -> evidence -> AI investigation -> analyst disposition -> audit trail`.

### 32.5 Performance tests

Measure:

- scoring throughput,
- p50/p95/p99 latency,
- feature-store latency,
- graph-state update latency,
- Kafka lag under load.

---

## 33. Research Artifacts

The repository must contain durable research documentation and outputs.

Expected structure:

```text
experiments/
  baselines/
  ablations/
  unseen-typology/
  adversarial/

docs/
  architecture/
  data-card/
  model-card/
  evaluation/
  runbooks/

notebooks/
  eda/
  baseline-comparison/
```

Required final artifacts include:

- architecture document,
- data card,
- model card,
- baseline comparison report,
- ablation report,
- unseen-typology report,
- adversarial stress-test report,
- latency benchmark,
- operational runbook.

---

## 34. Monorepo Layout

Target structure:

```text
financial-crime-intelligence-platform/

apps/
  investigator-web/

services/
  ingestion/
  feature-engine/
  graph-state/
  scoring/
  case-api/
  investigation-agent/

ml/
  datasets/
  features/
  graph/
  baselines/
  temporal/
  fusion/
  training/
  evaluation/
  explainability/

simulation/
  amlsim/

schemas/

infra/
  docker/
  kubernetes/
  monitoring/

experiments/
  baselines/
  ablations/
  unseen-typology/
  adversarial/

notebooks/
  eda/
  baseline-comparison/

docs/
  architecture/
  data-card/
  model-card/
  evaluation/
  runbooks/
  superpowers/
    specs/
```

The exact internal package names may evolve during implementation planning, but the service and research boundaries above must remain clear.

---

## 35. Reuse Strategy and Attribution

Reusable external systems and repositories are dependencies/reference implementations, not original project contributions.

Expected reuse candidates include:

- AusAML / AMLBench for primary data,
- IBM AMLSim for controlled synthetic AML stress scenarios,
- PyGOD for graph anomaly baselines,
- PyTorch Geometric for graph-learning infrastructure,
- TGN concepts/reference implementation for temporal graph learning,
- GraphSAGE/GAT/HGT implementations for baselines,
- Feast for feature-store abstractions,
- MLflow for experiment tracking and model registry,
- Kafka for event streaming,
- Neo4j for graph investigation,
- Prometheus/Grafana for observability,
- LangGraph or equivalent for bounded investigation-agent orchestration.

Any reused source code must preserve licensing and attribution requirements.

The project must clearly distinguish:

- imported dependency,
- adapted reference implementation,
- project-specific implementation,
- research contribution.

---

## 36. Primary Differentiators

The project’s differentiated value is the combination of:

1. fiat-banking heterogeneous graph ontology,
2. continuous-time temporal entity modeling,
3. supervised known-AML detection,
4. unsupervised novelty detection,
5. account-level and subgraph-level risk,
6. calibrated interpretable risk fusion,
7. held-out unknown-typology experiments,
8. adversarial AMLSim stress testing,
9. evidence-first investigation outputs,
10. bounded AI investigation agent,
11. near-real-time streaming inference,
12. analyst feedback and model-governance workflow.

---

## 37. Acceptance Criteria / Definition of Done

The project is not complete merely because model training succeeds.

### 37.1 End-to-end functional acceptance

The following flow must run end-to-end:

`AusAML/AMLSim replay -> Kafka -> schema validation -> online features -> temporal graph update -> model scoring -> risk fusion -> alert -> case -> graph/evidence UI -> AI investigation -> analyst disposition -> audit trail`.

### 37.2 ML/research acceptance

The repository must provide reproducible evidence for:

- at least one tabular baseline,
- at least one graph anomaly baseline,
- at least one static GNN baseline,
- a TGN-style temporal baseline,
- the hybrid model,
- strict chronological holdout evaluation,
- unknown-typology evaluation,
- AMLSim adversarial stress testing,
- ablation studies,
- calibration/risk-fusion comparison.

### 37.3 Product acceptance

The UI must support:

- prioritized alerts,
- case investigation,
- entity context,
- transaction timeline,
- suspicious graph/path visualization,
- model/evidence inspection,
- AI investigation narrative with evidence grounding,
- analyst disposition.

### 37.4 Systems acceptance

The system must expose:

- structured logs,
- Prometheus metrics,
- Grafana dashboards,
- reproducible Docker Compose startup,
- documented scoring latency benchmark,
- quarantine behavior for invalid input.

### 37.5 Governance acceptance

A stored case must be able to identify or reconstruct:

- source event(s),
- model version,
- feature version,
- scoring timestamp,
- risk components,
- final risk,
- evidence references,
- analyst disposition history.

---

## 38. Success Criteria

The project succeeds if it demonstrates all of the following:

- stronger AML detection than simple rules/tabular baselines on chronological holdout,
- measurable benefit from graph and/or temporal components supported by ablation,
- useful detection of at least one held-out/unseen suspicious pattern,
- graceful degradation analysis under adversarial AMLSim scenarios,
- near-real-time scoring with documented latency,
- evidence-backed analyst investigation flow,
- reproducible model and data provenance,
- a coherent end-to-end product story suitable for both technical interviews and research-oriented review.

---

## 39. Future Extensions

Potential post-V1 extensions include:

- active learning for analyst prioritization,
- federated multi-bank fraud learning,
- cross-bank privacy-preserving graph intelligence,
- multi-agent case investigation,
- richer rule-learning systems,
- scenario generation conditioned on detector weaknesses,
- graph foundation models,
- production Kubernetes deployment,
- regulatory-report drafting with mandatory human review,
- richer Mobbin-informed UI refinement when reference access is available.

These extensions must not be treated as V1 requirements.

---

## 40. Final Product Statement

**Financial Crime Intelligence Platform** is a fiat-banking AML platform that combines temporal heterogeneous graph learning, anomaly detection, known-typology modeling, streaming risk scoring, suspicious-network discovery, evidence-grounded AI investigation, analyst feedback, and adversarial stress testing.

The intended portfolio/research description is:

> Built a temporal heterogeneous graph intelligence platform for fiat-banking AML that combined supervised typology recognition with unsupervised graph novelty detection, real-time streaming risk scoring, evidence-grounded AI investigation, adversarial AML simulation, and analyst feedback.
