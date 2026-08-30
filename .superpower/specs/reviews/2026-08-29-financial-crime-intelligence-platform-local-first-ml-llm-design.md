# Financial Crime Intelligence Platform — Local-First ML + Deep Trace + Evidence-Grounded LLM Investigation Design

**Date:** 2026-08-29
**Status:** Proposed design / pending user review
**Supersedes:** Selected ML, investigation, UI, evaluation, and acceptance assumptions from `2026-08-27-financial-crime-intelligence-platform-design(6).md`
**Project type:** Local-first AML engineering platform with optional scaled ML research and provider-based LLM investigation
**Primary domain:** Fiat banking Anti-Money Laundering (AML)
**Primary repository name:** `financial-crime-intelligence-platform`

---

## 1. Executive Decision

The project keeps an **ML-heavy target architecture**, but changes the **development and acceptance strategy** so expensive graph/temporal training is not a prerequisite for completing a useful product.

The core product must work end-to-end with:

1. deterministic AML rules and graph features,
2. a lightweight supervised risk model such as LightGBM/XGBoost,
3. a deterministic/bounded Deep Trace Engine,
4. an evidence model with reconstructable evidence IDs,
5. a provider-agnostic LLM Investigation Agent using API-based foundation models,
6. an analyst investigation UI centered on trace, time, evidence, uncertainty, and human disposition.

GraphSAGE, HGT, TGN, and a custom TGN+HGT hybrid remain **research upgrades**, not V1 completion blockers.

> **Algorithms compute. ML ranks. Databases prove. LLMs investigate. Humans decide.**

The project must remain valuable if the LLM provider is unavailable, and it must remain complete at a product level even if large-scale temporal heterogeneous GNN training is never performed.

---

## 2. Why This Revision Exists

The original specification is technically ambitious and research-oriented. It requires a progression from rules and tabular ML through graph anomaly detection, GraphSAGE/GAT, HGT, TGN, and finally a custom typed-TGN + HGT-style hybrid architecture.

That target is valid for a team or compute-rich research environment, but it creates three risks for a single-developer project:

1. **Compute risk** — repeated GNN/TGN experiments can exceed local VRAM/RAM and require rented GPUs.
2. **Schedule risk** — a large fraction of the project can be spent reproducing model baselines before any investigation product exists.
3. **Product risk** — even a strong detector does not automatically produce a good AML investigation experience.

This revision therefore separates:

- **target architecture**, which may include advanced graph ML;
- **minimum viable intelligence**, which must run locally;
- **research upgrades**, which are only implemented if previous stages show measurable benefit.

---

## 3. Hardware and Local-First Constraint

The initial development environment is assumed to be approximately:

- AMD Ryzen 5 7535HS,
- 16 GB RAM,
- NVIDIA RTX 4050 Laptop GPU with 6 GB VRAM,
- approximately 477 GB local storage.

The product must therefore be designed so core development is possible without an A100/H100-class GPU.

### 3.1 Recommended local upgrades

Recommended but not mandatory:

- upgrade system RAM to **32 GB** where possible;
- keep at least **100–150 GB free disk space** for datasets, Parquet artifacts, Docker images, graph stores, model checkpoints, MLflow artifacts, and generated evidence;
- use an additional SSD if available.

### 3.2 Hardware acceptance rule

A feature is not part of core V1 acceptance if it requires hardware substantially beyond the documented local development machine.

Advanced ML experiments may use rented compute later, but the product must not depend on them.

---

## 4. Revised Product Thesis

The platform is not primarily:

- a transaction classifier,
- a graph viewer,
- a chat interface over banking data,
- or a foundation-model wrapper.

It is an **evidence-grounded financial investigation system**.

Its purpose is:

> Starting from suspicious activity, reconstruct the most relevant money-flow paths through time, suppress irrelevant or benign graph expansion, explain why each entity or transaction is present in the investigation, expose uncertainty and data boundaries, and let an analyst interrogate the resulting evidence using a bounded LLM agent.

The major product differentiator is not “use a graph.” It is:

> **Turn a large temporal financial graph into a small, ranked, explainable, auditable investigation space.**

---

## 5. Core Architectural Layers

```text
Banking Events / Dataset Replay
            |
            v
+---------------------------+
| 1. Data & Feature Layer   |
| schema / Parquet / stats  |
+-------------+-------------+
              |
              v
+---------------------------+
| 2. Risk Detection Layer   |
| rules + LightGBM/XGBoost  |
| optional graph ML         |
+-------------+-------------+
              |
              v
      Suspicious Seeds
              |
              v
+---------------------------+
| 3. Deep Trace Engine      |
| temporal / amount / flow  |
| bounded graph search      |
| benign suppression        |
+-------------+-------------+
              |
              v
+---------------------------+
| 4. Evidence Engine        |
| facts / paths / versions  |
| supporting / mitigating   |
+-------------+-------------+
              |
              v
+---------------------------+
| 5. Investigation Tools    |
| typed, narrow, auditable  |
+-------------+-------------+
              |
              v
+---------------------------+
| 6. LLM Investigator       |
| provider API + workflow   |
| grounding + guardrails    |
+-------------+-------------+
              |
              v
+---------------------------+
| 7. Analyst UI             |
| trace / timeline / proof  |
| questions / disposition   |
+---------------------------+
```

Each layer must be independently testable and replaceable.

---

## 6. Layer 1 — Data and Feature System

### 6.1 Data strategy

The system supports:

- AusAML / AMLBench-style public data where available,
- IBM AML synthetic datasets for controlled testing,
- AMLSim for configurable laundering scenarios,
- smaller development subsets derived from larger datasets.

### 6.2 Development scale

Development should progress by scale rather than starting with the largest dataset:

- **Dev:** 100k–500k events
- **Local integration:** 500k–2M events
- **Local stress:** up to several million events when memory allows
- **Scaled benchmark:** optional external compute

The system must record which scale and dataset version produced every reported metric.

### 6.3 Chronological evaluation

Random splits must not be used as headline evaluation when they introduce temporal or graph leakage.

Required order:

```text
train -> calibration/model-selection -> untouched holdout
```

Features used to score an event at time `t` must only use information available at or before `t`.

### 6.4 Feature families

Core features:

**Transaction**
- amount,
- currency-normalized amount,
- transaction type,
- timestamp,
- channel.

**Behavioral**
- transaction counts over bounded windows,
- incoming/outgoing amounts,
- pass-through ratio,
- new-counterparty ratio,
- behavioral deviation from trailing history.

**Graph**
- in/out degree,
- unique counterparties,
- fan-in/fan-out,
- cycle indicators,
- local path statistics,
- motif counts where practical.

**Context**
- merchant category,
- device novelty,
- account age,
- known relationship duration,
- optional entity metadata only when source data actually supports it.

---

## 7. Layer 2 — Progressive ML Strategy

The target architecture may be ML-heavy, but development is **evidence-gated**. No advanced model is implemented merely because it appears in the architecture.

### 7.1 Stage M0 — deterministic baseline

Must include:

- AML rules/heuristics,
- typology-oriented graph rules,
- transparent feature calculations.

Purpose:
- validate data,
- provide interpretable baseline,
- create initial suspicious seeds,
- provide a fallback when models are unavailable.

### 7.2 Stage M1 — lightweight tabular ML

Primary local supervised model:

- LightGBM or XGBoost.

Optional:
- logistic regression,
- Isolation Forest,
- lightweight autoencoder only if useful.

This stage is mandatory.

### 7.3 Stage M2 — static graph ML

First graph-learning upgrade:

- GraphSAGE preferred,
- GAT optional.

Training must use bounded mini-batch or neighborhood sampling where possible.

**Promotion gate:** continue only if graph ML materially improves a predefined holdout metric such as PR-AUC, precision@K, recall at fixed alert budget, or downstream trace quality.

### 7.4 Stage M3 — heterogeneous graph ML

HGT is optional.

It is attempted only if:
- the heterogeneous ontology is supported by real source fields,
- GraphSAGE/static graph results justify the additional complexity,
- local hardware can run a meaningful subset experiment.

### 7.5 Stage M4 — temporal graph ML

TGN-style modeling is optional.

It is attempted only if:
- sequence/time effects cannot be captured adequately by engineered temporal features,
- a smaller experiment demonstrates plausible benefit,
- the expected benefit justifies training complexity.

### 7.6 Stage M5 — custom hybrid TGN + HGT

The original custom hybrid remains a **stretch research goal**.

It is not required for product completion.

It may only be implemented when:
1. HGT alone shows measurable benefit;
2. TGN alone shows measurable benefit;
3. the combined hypothesis is testable;
4. there is sufficient compute budget;
5. an ablation plan is defined before training.

### 7.7 Stop rule

If an advanced model does not materially improve holdout or investigation metrics, stop.

The project must prefer a simpler model when the gain is not significant enough to justify complexity, latency, cost, or explainability loss.

---

## 8. Detection Is Not Tracing

Risk detection and money-flow tracing are separate problems.

A detector answers:

> “Which accounts/events deserve investigation?”

A trace engine answers:

> “Given a seed, which temporally and financially coherent paths are relevant to this case?”

A model score must never be treated as proof that every neighbor of a high-risk node is suspicious.

---

## 9. Layer 3 — Deep Trace Engine

The Deep Trace Engine is a core custom subsystem.

It is not an LLM function and must not depend on a model provider.

### 9.1 Inputs

Example request:

```text
TraceRequest
- seed_account
- optional seed_transaction
- direction
- start_time
- end_time
- max_hops
- max_nodes
- max_edges
- amount_focus
- typology_hint
- include_external_boundaries
```

### 9.2 Outputs

```text
TraceResult
- trace_id
- ranked_paths[]
- included_nodes[]
- included_edges[]
- discarded_candidates[]
- amount_attribution
- temporal_summary
- uncertainty_summary
- evidence_ids[]
- trace_algorithm_version
- query_budget_used
```

### 9.3 Search strategy

The engine must not perform unrestricted BFS.

Candidate expansion may combine:

- temporal ordering,
- temporal proximity,
- amount retention,
- onward-transfer ratio,
- counterparty novelty,
- path/ring/cycle structure,
- known typology rules,
- risk-model priors,
- historical behavior deviation,
- known-benign relationship penalties,
- entity-resolution uncertainty.

### 9.4 Money fungibility rule

The system must not overclaim that an exact outgoing monetary unit is the same physical money as an incoming unit when the account balance is fungible.

The UI and API should use terms such as:

- **flow attribution**,
- **amount-consistent path**,
- **likely downstream flow**,

unless the source ledger semantics genuinely support exact lineage.

The attribution policy must be versioned. Candidate policies may include FIFO, proportional allocation, bounded temporal attribution, or a documented project-specific heuristic.

### 9.5 Bounded expansion

Every trace request must have explicit budgets:

- hop depth,
- time window,
- maximum candidate nodes,
- maximum candidate edges,
- maximum returned paths,
- timeout.

A trace that reaches its budget must report that it was truncated.

### 9.6 Benign suppression

The engine must model negative/mitigating signals, not only suspicious ones.

Examples:

- long-standing legitimate counterparty relationship,
- payroll behavior,
- known high-degree merchant/platform,
- historically normal transaction amount,
- no rapid onward movement,
- stable business seasonality,
- weak identity relation only.

A benign node may still appear in a path if required to reconstruct the flow, but it must not automatically inherit a “suspicious” label.

### 9.7 Why-included explanation

Every returned node/edge must be able to answer:

> “Why is this present in the trace?”

Example reasons:

- received 97% of upstream amount,
- forwarded 94% within six minutes,
- appears in three top-ranked candidate paths,
- forms part of a detected cycle,
- is a common downstream beneficiary,
- is connected through a weak/uncertain identity relation.

### 9.8 Why-not-suspicious explanation

The engine should also surface mitigating evidence.

Example:

```text
Entity is present in trace but not independently classified suspicious.

Mitigating signals:
- historical payroll behavior,
- 4.2-year counterparty relationship,
- transaction amount within expected range,
- no suspicious onward movement.
```

---

## 10. Trace Ranking

Initial implementation may use an interpretable score rather than a trained path model.

Conceptual form:

```text
TraceScore(P) =
  + temporal_consistency
  + amount_consistency
  + suspicious_structure
  + risk_prior
  + counterparty_novelty
  - benign_explanation
  - entity_uncertainty
  - excessive_path_complexity
```

The exact weighting method must be documented and versioned.

A later upgrade may replace hand-tuned ranking with:
- logistic regression,
- LightGBM ranker,
- another lightweight learning-to-rank method.

A path model must not become mandatory until labeled path-level evaluation data exists.

---

## 11. Third-Party and External-Bank Boundaries

The platform must never imply visibility beyond available data.

External nodes can have one of these states:

- known internal customer,
- resolved external party,
- external account reference,
- unknown counterparty,
- inferred entity candidate.

When trace visibility ends:

```text
TRACE BOUNDARY REACHED
No downstream transaction visibility is available after BANK-X.
```

The UI must visually distinguish internal observed graph from partial/external references.

---

## 12. Entity Resolution and Guilt-by-Association

Entity resolution is optional in the first local V1 unless the source dataset provides reliable identity features.

Rules:

1. uncertain identity links must carry confidence;
2. uncertain candidates must not be silently hard-merged;
3. false merge risk is treated as more dangerous than simple missing linkage;
4. a suspicious neighbor does not automatically make an entity suspicious;
5. relationship risk and entity risk are separate fields.

Example:

```text
Relationship to suspicious flow: HIGH
Entity fraud classification: UNKNOWN
Identity-link confidence: 0.73
```

---

## 13. Layer 4 — Evidence Engine

The Evidence Engine converts results from data, ML, graph computation, and tracing into immutable/reconstructable evidence references.

### 13.1 Evidence categories

- `OBSERVED` — source transaction/account facts,
- `DERIVED` — deterministic calculations,
- `MODEL` — model scores/predictions,
- `RULE` — triggered rule/typology logic,
- `TRACE` — path/flow reconstruction,
- `AI_HYPOTHESIS` — generated interpretation,
- `ANALYST` — human notes/disposition.

### 13.2 Evidence invariants

Every evidence item must include:

- `evidence_id`,
- source/version,
- case/trace relation,
- timestamp or relevant time range,
- reconstructable data reference,
- generation method/version,
- confidence where applicable.

An LLM may not invent evidence IDs.

### 13.3 Supporting vs mitigating evidence

Case conclusions should explicitly separate:

- supporting evidence,
- contradicting/mitigating evidence,
- missing evidence,
- unresolved uncertainty.

This is mandatory for AI-generated narratives.

---

## 14. Layer 5 — Bounded Investigation Tools

The LLM does not receive unrestricted database access.

The primary interface between the agent and the platform is a set of typed domain tools.

Initial tool set:

```text
get_case_summary()
get_entity_profile()
get_transaction_details()
get_transaction_timeline()

trace_funds()
find_paths_between()
find_cycles()
find_fan_in()
find_fan_out()
find_common_beneficiaries()

compare_behavior_windows()
get_counterparty_history()

explain_node_inclusion()
explain_edge_inclusion()

get_supporting_evidence()
get_mitigating_evidence()
get_missing_evidence()

retrieve_prior_cases()
retrieve_case_notes()
retrieve_kyc_documents()
retrieve_policy_guidance()
```

### 14.1 Explicitly prohibited primary tools

The agent must not rely on unrestricted:

```text
run_sql()
run_cypher()
execute_shell()
```

as normal investigation tools.

Internal service implementations may use SQL/Cypher behind typed bounded endpoints.

---

## 15. Layer 6 — Provider-Based LLM Investigator

The project will **not train a foundation model**.

It will use an external LLM provider API.

### 15.1 Provider abstraction

Business logic must not be tied to a single model provider.

Conceptual interface:

```text
InvestigationModel
  |- OpenAIProvider
  |- AnthropicProvider
  |- GeminiProvider
```

The project may start with only one provider implementation, but agent logic, tool schemas, evaluation cases, and evidence contracts must be provider-neutral.

### 15.2 LLM responsibilities

The LLM may:

- interpret analyst intent,
- choose approved tools,
- propose bounded investigation plans,
- synthesize retrieved evidence,
- compare supporting vs mitigating evidence,
- generate hypotheses,
- recommend next checks,
- produce structured narratives.

### 15.3 LLM non-responsibilities

The LLM must not be the source of truth for:

- transaction existence,
- transaction amount,
- path existence,
- account identity,
- model risk score,
- evidence existence,
- exact flow calculation,
- final regulated disposition.

### 15.4 Degraded mode

If the model provider is unavailable:

- alerts remain accessible,
- tracing still works,
- evidence still works,
- graph/timeline still works,
- analyst disposition still works.

Only natural-language reasoning and generated narrative are degraded.

This is a hard architectural acceptance requirement.

---

## 16. Agent Orchestration

A single explicit investigation agent is preferred initially.

Multi-agent architecture is deferred unless one agent becomes measurably inadequate.

Preferred workflow:

```text
Read case
  |
  v
Understand analyst question
  |
  v
Select bounded tool
  |
  v
Execute deterministic retrieval/computation
  |
  v
Validate returned evidence
  |
  +--> insufficient? --> call another tool / ask clarification
  |
  v
Search mitigating evidence
  |
  v
Construct hypothesis
  |
  v
Validate citations / structured output
  |
  v
Return answer + next checks
```

LangGraph, OpenAI Agents SDK, or another framework may implement the state machine.

Framework choice is not itself a product contribution.

---

## 17. Structured LLM Output Contract

Material responses should be structured before rendering.

Example:

```text
InvestigationAnswer
- answer_summary
- hypothesis
- confidence
- supporting_evidence_ids[]
- mitigating_evidence_ids[]
- missing_information[]
- tool_calls[]
- recommended_next_checks[]
- caveats[]
```

Unsupported claims must not be rendered as grounded facts.

---

## 18. RAG Policy

Transactions are structured financial events and must not be converted into arbitrary text chunks as the primary tracing mechanism.

RAG is appropriate for:

- KYC documents,
- policy guidance,
- analyst notes,
- prior case narratives,
- procedural documents,
- unstructured customer/merchant context.

Structured financial questions should use tools and graph/temporal computation first.

```text
Question
  |
  +--> Structured transaction question --> Trace/Graph/Case tools
  |
  +--> Document/policy question --------> RAG
  |
  +--> Mixed question ------------------> both -> Evidence Bundle -> LLM
```

---

## 19. Agent Safety and Security

The agent operates in a sensitive domain and must follow least-privilege principles.

Required controls:

- typed tool schemas,
- per-tool input validation,
- per-tool output validation,
- tool-call budgets,
- timeouts,
- model-call budgets,
- evidence ID validation,
- prompt-injection-resistant handling of retrieved documents,
- no automatic regulated action,
- no direct production-model promotion,
- no silent disposition update.

Retrieved documents are **untrusted evidence**, not instructions.

Potentially adversarial content in KYC/case notes must not override system/tool policy.

---

## 20. Layer 7 — Investigation UI

The primary UI is a **financial investigation workspace**, not a generic graph dashboard.

### 20.1 Core case layout

A case should emphasize:

1. what happened,
2. why the case exists,
3. where money likely moved,
4. which entities are involved,
5. what happened over time,
6. what evidence supports the hypothesis,
7. what evidence weakens the hypothesis,
8. what is unknown,
9. what the analyst should check next.

### 20.2 Graph policy

The UI must not render an entire high-degree neighborhood by default.

Instead it shows a **case graph projection**.

Required behavior:

- aggregate repeated transfers,
- cluster large benign/high-degree regions,
- semantic zoom,
- drill-down to raw transactions,
- bounded expansion,
- preserve trace reason per node/edge.

### 20.3 Multiple synchronized projections

Graph, timeline, transaction table, and evidence panel are projections of the same selected investigation state.

Selecting a node, path, time interval, or evidence item should update the other views.

### 20.4 Time as a first-class control

The case workspace should support:

- time-window filtering,
- before/during/after comparison,
- transaction playback where useful,
- suspicious-period highlighting.

### 20.5 AI panel

The AI panel is not a generic chat window.

It should expose:

- current hypothesis,
- strongest supporting evidence,
- strongest mitigating evidence,
- confidence,
- missing information,
- suggested investigation actions,
- conversation history.

Chat is one interaction mode, not the product center.

---

## 21. Evaluation Framework

The project measures four independent classes of quality.

### 21.1 Detection metrics

- PR-AUC,
- precision@K,
- recall at fixed alert budget,
- recall at fixed precision,
- calibration/Brier score where relevant,
- alerts per normalized transaction/account volume.

### 21.2 Tracing metrics

Core new metrics:

- node precision,
- node recall,
- edge precision,
- edge recall,
- path recall,
- hop coverage,
- illicit amount coverage where ground truth supports it,
- benign contamination rate,
- nodes/edges scanned,
- query latency,
- truncation rate.

### 21.3 Agent metrics

- tool selection accuracy,
- tool argument accuracy,
- valid evidence citation rate,
- grounded claim rate,
- unsupported claim rate,
- correct insufficient-evidence behavior,
- average tool calls,
- latency,
- provider cost per investigation.

### 21.4 Investigation/product metrics

When feasible:

- time to correct conclusion,
- interactions per investigation,
- number of irrelevant nodes viewed,
- evidence inspected before disposition,
- analyst override/correction rate.

---

## 22. Progressive Benchmark Ledger

Every meaningful architecture upgrade must be compared against the previous stage.

Example progression:

```text
V0  Rules
V1  + LightGBM
V2  + GraphSAGE
V3  + Deep Trace
V4  + Benign Suppression
V5  + Evidence Engine
V6  + LLM Investigator
V7  + optional HGT
V8  + optional TGN
V9  + optional HGT/TGN hybrid
```

Each version records:

```text
Before
After
Delta
Dataset version
Configuration
Runtime
Memory
Model/provider version
```

A version is not considered an improvement simply because it adds more components.

---

## 23. Adversarial and Controlled Scenarios

AMLSim or another controllable simulator should be used for scenarios such as:

- increasing hop count,
- longer transfer delay,
- lower amount retention,
- more benign neighbors,
- high-degree merchants,
- payroll-like fan-out,
- marketplace fan-in/out,
- larger mule rings,
- mixed legitimate and illicit activity,
- incomplete external-bank visibility.

The key degradation plots should include:

```text
Trace Recall vs Hop Count
Benign Contamination vs Graph Noise
Amount Coverage vs Transfer Delay
Trace Latency vs Graph Size
```

Advanced ML degradation plots are optional unless those models are implemented.

---

## 24. Infrastructure Strategy

Infrastructure is local-first and staged.

### 24.1 Core local services

Required:

- PostgreSQL,
- Neo4j or compatible graph investigation store,
- Case API,
- Trace service,
- Evidence service,
- Investigation agent,
- investigator web application.

### 24.2 Add when needed

- Kafka for replay/streaming,
- Redis for online state/cache,
- MLflow for experiment tracking,
- Prometheus/Grafana for operational benchmarking,
- MinIO for artifact storage.

The project must avoid starting every infrastructure component before its use case exists.

### 24.3 Docker

Docker Compose remains the preferred local integration mechanism.

Kubernetes is not a V1 requirement.

---

## 25. Revised Service Boundaries

```text
services/
  ingestion/
  feature-engine/
  risk-scoring/
  trace-engine/
  evidence-engine/
  case-api/
  investigation-agent/

apps/
  investigator-web/

ml/
  rules/
  tabular/
  graph/
  temporal/
  evaluation/

research/
  baselines/
  tracing/
  ablations/
  stress-tests/
  agent-evals/

schemas/
  events/
  cases/
  traces/
  evidence/
  tools/
  agent/

docs/
  architecture/
  evaluation/
  runbooks/
  research/
  superpowers/specs/
```

### 25.1 Trace Engine service

Responsibilities:

- bounded candidate expansion,
- temporal constraints,
- amount/flow attribution,
- path/cycle discovery,
- benign suppression,
- path ranking,
- third-party boundary representation,
- trace provenance.

### 25.2 Evidence Engine service

Responsibilities:

- evidence normalization,
- evidence IDs,
- supporting/mitigating classification,
- reconstruction references,
- evidence versioning,
- AI citation validation.

### 25.3 Investigation Agent

Responsibilities:

- interpret analyst intent,
- call approved tools,
- synthesize evidence,
- surface uncertainty,
- find contradictions,
- recommend next checks.

It does not own financial truth.

---

## 26. Testing Strategy

### 26.1 Unit tests

Must cover:

- temporal-window calculations,
- flow-attribution calculations,
- path ranking,
- benign suppression,
- graph expansion budgets,
- external boundary handling,
- evidence construction,
- evidence validation,
- agent tool schemas,
- structured agent output.

### 26.2 Integration tests

Required flows:

```text
dataset -> features -> risk score -> suspicious seed -> trace -> evidence -> case
```

and:

```text
analyst question -> agent -> bounded tool -> trace/evidence -> validated answer
```

### 26.3 Negative tests

Must include:

- missing evidence,
- nonexistent evidence ID,
- malformed tool arguments,
- excessive hop request,
- provider timeout,
- graph query timeout,
- trace truncation,
- prompt injection embedded in a retrieved document,
- entity relation with low confidence,
- external visibility boundary.

### 26.4 ML tests

If ML stage exists:

- chronological leakage checks,
- deterministic preprocessing,
- model load/score compatibility,
- baseline reproducibility,
- calibration behavior.

---

## 27. Failure Handling

### 27.1 LLM provider failure

Return a typed degraded state:

```text
AI_UNAVAILABLE
```

Do not block case investigation.

### 27.2 Trace budget exhausted

Return:

```text
TRACE_TRUNCATED
```

with budget used, last explored depth, and unexpanded candidate count if known.

### 27.3 Insufficient evidence

Return:

```text
INSUFFICIENT_EVIDENCE
```

The agent may not convert uncertainty into a confident accusation.

### 27.4 Model unavailable

Fall back to deterministic rules, previously materialized scores where explicitly valid, or a typed unavailable status.

No synthetic score may be invented.

---

## 28. Acceptance Criteria

### 28.1 Mandatory local product acceptance

The project is complete at V1 when this works locally:

```text
Dataset replay
 -> schema validation
 -> feature generation
 -> rules + LightGBM/XGBoost risk
 -> suspicious seed
 -> Deep Trace Engine
 -> Evidence Engine
 -> Case API
 -> LLM Investigation Agent via provider API
 -> Investigation UI
 -> Analyst disposition
 -> audit/provenance
```

### 28.2 Mandatory tracing acceptance

The system must demonstrate:

- bounded expansion,
- temporal filtering,
- amount-aware path reasoning,
- trace ranking,
- at least one benign-suppression mechanism,
- node/edge inclusion explanations,
- external visibility boundary behavior,
- trace provenance.

### 28.3 Mandatory AI acceptance

The agent must:

- use bounded tools,
- return structured outputs,
- cite valid evidence IDs,
- search for mitigating evidence,
- admit insufficient evidence,
- remain non-authoritative for regulated action,
- fail gracefully when the provider is unavailable.

### 28.4 Mandatory evaluation acceptance

The repository must contain:

- a rules baseline,
- a LightGBM/XGBoost baseline,
- detection metrics,
- trace metrics,
- agent evals,
- latency measurements,
- at least one controlled AMLSim stress experiment.

### 28.5 Optional advanced ML acceptance

The following are explicitly **not** required for V1 completion:

- GraphSAGE,
- GAT,
- HGT,
- TGN,
- custom HGT/TGN hybrid,
- large-scale GPU training.

When implemented, they must be reported as research upgrades with before/after measurements.

---

## 29. Development Phases

### Phase 0 — Local foundation

- free storage,
- prepare Parquet datasets,
- build chronological split,
- implement feature calculations,
- implement rules.

### Phase 1 — Lightweight risk engine

- LightGBM/XGBoost,
- calibration,
- baseline metrics.

### Phase 2 — Deep Trace Engine

- temporal bounded search,
- amount attribution,
- cycle/path analysis,
- ranking,
- provenance.

### Phase 3 — Benign and uncertainty handling

- high-degree benign entity logic,
- mitigating evidence,
- relation confidence,
- external boundaries.

### Phase 4 — Evidence Engine

- evidence schema,
- reconstructable IDs,
- supporting vs mitigating evidence,
- claim validation contract.

### Phase 5 — LLM Investigator

- provider adapter,
- typed tools,
- workflow orchestration,
- structured output,
- grounding validation,
- provider failure handling.

### Phase 6 — Intelligent case UI

- trace projection,
- timeline,
- transaction drill-down,
- evidence,
- AI investigation,
- disposition.

### Phase 7 — Evaluation harness

- detection benchmark,
- trace benchmark,
- agent benchmark,
- stress scenarios,
- latency/cost tracking.

### Phase 8 — Optional GraphSAGE experiment

Only after core product works.

### Phase 9 — Optional HGT/TGN experiments

Only after GraphSAGE/temporal-feature evidence supports further research.

### Phase 10 — Optional hybrid model

Stretch goal only.

---

## 30. Explicit Changes From the Original Specification

### 30.1 Changed

**Original:** static GNN, HGT, TGN, and custom hybrid are research acceptance requirements.
**Revised:** only rules + lightweight supervised ML are mandatory; advanced graph ML is optional and evidence-gated.

**Original:** suspicious-subgraph discovery is one subsystem after model scoring.
**Revised:** Deep Trace Engine becomes a first-class core service.

**Original:** graph visualization is a major investigation UI component.
**Revised:** graph is a bounded semantic projection of a trace, synchronized with time/evidence, never an unrestricted graph dump.

**Original:** AI investigation is full-featured but less explicit about provider architecture.
**Revised:** foundation models are API-based, provider-neutral, tool-bounded, and explicitly non-authoritative.

**Original:** evidence supports AI grounding.
**Revised:** evidence also supports trace inclusion, mitigating explanations, agent validation, and investigation replay.

### 30.2 Preserved

- fiat-banking AML domain,
- chronological holdout discipline,
- no foundation-model training,
- no autonomous account freeze or regulatory filing,
- human analyst disposition,
- immutable/reconstructable evidence,
- Docker Compose local integration,
- typed service contracts,
- agent evidence grounding,
- auditability and provenance.

---

## 31. Research Positioning

The project does not claim novelty merely for:

- using a graph for AML,
- using an LLM for AML,
- using RAG over financial data,
- using a GNN,
- visualizing suspicious accounts.

The research/engineering question is instead:

> How can a large financial graph be reduced into a bounded, temporally coherent, amount-aware, uncertainty-aware evidence trace that minimizes benign contamination and can be safely interrogated by a tool-using LLM?

Potential research artifacts:

- trace-quality evaluation protocol,
- benign contamination metric,
- amount-aware temporal tracing benchmark,
- UI/agent evaluation over grounded traces,
- comparison of deterministic vs ML-assisted path ranking.

A publishable paper is not a V1 completion requirement.

---

## 32. Risks and Mitigations

### Risk: trace search explodes

Mitigation:
- strict budgets,
- indexes,
- pre-filter by time,
- ranking before expansion where possible,
- high-degree-node policies.

### Risk: flow attribution overclaims exact money lineage

Mitigation:
- explicit attribution semantics,
- uncertainty labels,
- versioned policies,
- language such as “amount-consistent likely flow.”

### Risk: innocent entities are visually criminalized

Mitigation:
- relationship risk separate from entity risk,
- mitigating evidence,
- neutral graph styling for context-only nodes,
- no “fraudster” label from graph proximity alone.

### Risk: LLM becomes the real business logic

Mitigation:
- backend tools own computation,
- provider removal test,
- no arbitrary DB access,
- structured output validation.

### Risk: agent hallucination

Mitigation:
- evidence IDs,
- claim validation,
- missing-evidence state,
- supporting vs mitigating evidence,
- tool and output guardrails.

### Risk: local hardware blocks progress

Mitigation:
- lightweight mandatory model,
- data subsets,
- optional advanced ML,
- staged infrastructure,
- CPU-based tracing.

---

## 33. Reference Sources and Design Context

These references inform the revised design; they are not automatically claimed as original project contributions.

### AML graph and tracing

1. **FlowScope: Spotting Money Laundering Based on Graphs** — AAAI 2020
   https://ojs.aaai.org/index.php/AAAI/article/view/5906
   Relevance: complete source-to-destination money-flow detection and scalable graph formulation.

2. **Realistic Synthetic Financial Transactions for Anti-Money Laundering Models** — NeurIPS 2023 Datasets & Benchmarks
   https://proceedings.neurips.cc/paper_files/paper/2023/hash/5f38404edff6f3f642d6fa5892479c42-Abstract-Datasets_and_Benchmarks.html
   Relevance: public synthetic AML datasets, complete labels, scalable benchmarking context.

3. **IBM AMLSim**
   https://github.com/IBM/AMLSim
   Relevance: controllable synthetic laundering scenarios for graph/algorithm stress testing.

### LLM and AML

4. **Exploring the In-Context Learning Capabilities of LLMs for Money Laundering Detection in Financial Graphs** — 2025
   https://arxiv.org/abs/2507.14785
   Relevance: localized k-hop financial subgraphs serialized for LLM reasoning; useful baseline to go beyond with tool-based investigation.

5. **Explainable AML Triage with LLMs: Evidence Retrieval and Counterfactual Checks** — 2026 preprint
   https://arxiv.org/abs/2604.19755
   Relevance: evidence bundles, explicit citations, supporting/contradictory/missing evidence, counterfactual validation.

### Agent engineering

6. **OpenAI — A Practical Guide to Building Agents**
   https://openai.com/business/guides-and-resources/a-practical-guide-to-building-ai-agents/
   Relevance: agents as model + tools + instructions, standardized tools, layered guardrails, human escalation.

7. **OpenAI Agents SDK**
   https://openai.github.io/openai-agents-python/
   Relevance: function tools, structured schemas, guardrails, sessions, human-in-the-loop, tracing.

8. **LangGraph Persistence**
   https://docs.langchain.com/oss/python/langgraph/persistence
   Relevance: checkpoints, human-in-the-loop, replay/time-travel debugging, fault tolerance.

9. **Neo4j GraphRAG for Python**
   https://neo4j.com/docs/neo4j-graphrag-python/current/
   Relevance: graph/document retrieval and tool-based retrieval patterns; not used as the primary transaction tracing engine.

### Security

10. **OWASP Top 10 for LLM Applications / GenAI project resources**
    https://genai.owasp.org/llm-top-10/
    Relevance: prompt injection, sensitive information disclosure, improper output handling, excessive agency, vector/embedding risks, unbounded consumption.

---

## 34. Final Product Statement

**Financial Crime Intelligence Platform** is a local-first AML investigation platform that combines lightweight risk detection, bounded temporal financial tracing, evidence reconstruction, provider-based LLM investigation, and analyst decision support.

Its intended portfolio description is:

> Built an evidence-grounded financial crime investigation platform that used deterministic temporal fund tracing, graph analytics, lightweight ML risk scoring, and a provider-agnostic tool-using LLM agent to reconstruct suspicious money flows, separate suspicious signals from benign context, and support auditable analyst investigations without depending on foundation-model training or large-scale GPU infrastructure.

Its architecture must remain true to the following rule:

> **The LLM reasons about evidence; it does not manufacture the evidence.**
