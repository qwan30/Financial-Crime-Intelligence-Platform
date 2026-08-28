# Financial Crime Intelligence Platform — Design Specification

**Date:** 2026-08-27
**Status:** Draft / remediated; pending user approval and Phase 0 feasibility
**Project type:** Research-grade, production-shaped local reference platform
**Primary domain:** Fiat-banking Anti-Money Laundering (AML)
**Primary repository:** `financial-crime-intelligence-platform`

---

## 1. Document Authority and Requirement Language

This document is the normative V1 design. Later plans MAY add implementation detail, but MUST NOT weaken its data-isolation, evidence, security, accessibility, governance, or release-truth requirements without an approved specification change.

The key words **MUST**, **MUST NOT**, **SHOULD**, **SHOULD NOT**, and **MAY** express requirement levels:

- **MUST / MUST NOT**: mandatory for the named gate.
- **SHOULD / SHOULD NOT**: expected unless a written exception records rationale, owner, impact, and compensating control.
- **MAY**: optional and not required for acceptance.

For research and governance records, **signed** means an authenticated approver attestation bound to the exact artifact content hash, approver identity, active role, and UTC timestamp. **Cryptographically signed** is reserved for an envelope that additionally declares the signature algorithm, key ID, trust root, verification procedure, key-rotation procedure, and revocation status/procedure. Each use MUST apply the contract named for that artifact; V1 does not define one universal signature envelope.

Phase 0 is the implementation gate. Approval of this document authorizes feasibility work only. It does not prove that the data can support every proposed ontology, label, split, typology, model, or product claim.

---

## 2. Product Truth Boundary

The intended product is a research-grade, production-shaped local reference platform for fiat-banking AML detection and investigation. It is designed to exercise production concerns—versioned contracts, streaming correctness, evidence, case operations, security, accessibility, observability, recovery, and model governance—without claiming bank-production readiness or certification.

At this specification stage:

- no production code is claimed;
- no model has been trained or selected;
- no holdout has been evaluated;
- no champion model exists;
- no latency, throughput, detection, calibration, accessibility, security, release, deployment, or recovery result exists;
- no public dataset field is assumed to support an ontology node or typology until Phase 0 maps and verifies it;
- a null champion and an honest negative research result are valid outcomes.

Claims about implementation, performance, model quality, release, or operational readiness MUST cite an immutable artifact manifest and the evidence level defined in Section 24. A local pass MUST NOT be presented as remote CI, release, deployment, or production evidence.

---

## 3. Executive Summary

The platform investigates account-level and suspicious-subgraph risk rather than treating transaction classification as the complete AML problem. Its intended capabilities are:

- deterministic AML rules and progressively gated statistical, anomaly, graph, and temporal research;
- causal event-time features and bounded online entity state;
- calibrated risk components with explicit abstention and fail-closed outcomes;
- suspicious paths, rings, and neighborhoods when supported by source facts;
- immutable, typed evidence packages and auditable case operations;
- a read-only, evidence-grounded AI investigator;
- an accessible analyst workspace linking graph, timeline, evidence, and case state;
- human-gated model lifecycle management;
- held-out unknown-typology experiments, ablations, and separate AMLSim stress testing for a promotable candidate or a reproducible frozen research baseline when the preregistered protocol does not need final-test access; otherwise explicitly justified dependency-skips.

The project MUST reuse mature infrastructure and baseline implementations where licensing and fit permit. Custom work SHOULD concentrate on source mapping, causal temporal representation, risk/evidence contracts, streaming correctness, investigation workflow, and reproducible evaluation.

The research definition of done is execution and publication of the approved protocol, including negative findings and its sealed-null path. It is not a requirement that a graph, temporal, or hybrid model outperform simpler baselines.

---

## 4. Goals and Non-Goals

### 4.1 V1 goals

V1 MUST, subject to Phase 0 feasibility:

1. score eligible accounts or entities from continuously arriving transaction events;
2. discover and score bounded suspicious paths, rings, groups, or subgraphs;
3. compare known-typology detection with novelty/anomaly detection;
4. when a promotable candidate or a reproducible frozen research baseline exists, evaluate at least one intentionally excluded scenario family without contaminating training or model selection; otherwise record only the specific dependency skip allowed by Section 8.6;
5. produce evidence that is reconstructable for every alert and material case conclusion while its required source payloads remain retained/pinned, and expose the typed reduced guarantee after lawful source-payload retirement;
6. exercise near-real-time Kafka-based scoring under a declared benchmark workload;
7. support alert triage, assignment, investigation, evidence review, AI assistance, review, disposition, and reopen;
8. preserve data, code, feature, graph-state, rule, model, calibration, threshold, prompt, provider, and evidence provenance;
9. execute disjoint temporal evaluation, ablations, separate AMLSim stress tests, and uncertainty reporting on the candidate path; on the sealed-null path, retain split/integrity, deterministic-rule/reference-baseline, system/evidence/AI/UI, and operational-benchmark diagnostics, and execute research-only baseline evaluations when their preregistered protocol is valid without final-test access;
10. capture analyst feedback for offline analysis without autonomous retraining or promotion;
11. demonstrate fail-closed scoring and recoverable state under declared fault drills;
12. meet WCAG 2.2 AA for the named analyst paths.

### 4.2 Secondary goals

V1 SHOULD:

- make classical, anomaly, graph, and temporal comparisons reproducible;
- run locally through Docker Compose;
- expose system, model, and AML-operations telemetry;
- keep replaceable package boundaries while minimizing initial deployables;
- provide a truthful portfolio and research narrative tied to evidence.

### 4.3 V1 non-goals

V1 MUST NOT include or claim:

- cryptocurrency or blockchain AML;
- federated or cross-bank learning;
- real customer PII;
- automatic account freezing or payment blocking;
- autonomous regulatory filing;
- autonomous case disposition, retraining, threshold change, or model promotion;
- a bank-grade enterprise IAM implementation;
- production Kubernetes operations or production certification;
- a custom graph database or foundation-model training;
- fabricated entities, relationships, typologies, labels, or evidence;
- a requirement to implement every candidate anomaly or graph algorithm;
- a requirement that a complex model become champion.

Kubernetes examples MAY be added after local acceptance, but MUST NOT be a V1 dependency or evidence of deployment.

---

## 5. Terminology and Scoring Objects

- **Event time**: the source timestamp at which a financial event occurred.
- **Ingest time**: the timestamp at which the platform accepted the event.
- **Entity risk**: risk for a source-supported entity, initially an `Account` unless Phase 0 validates additional types.
- **Suspicious subgraph risk**: risk for a bounded, reproducible set of source-supported entities and events connected under a declared extraction rule.
- **Scenario group**: the indivisible AML scenario or connected label group used to prevent related records crossing evaluation sets.
- **Development train**: data used to fit model parameters.
- **Model-selection validation**: data used to choose features, algorithms, hyperparameters, and research branches.
- **Calibration set**: data used only after a candidate is frozen to fit calibrators, fusion weights, thresholds, and alert-volume policy.
- **Final temporal test**: the latest untouched evaluation set, accessed once under the approved protocol.
- **Unknown-typology set**: a separately declared scenario family excluded from supervised development and model selection.
- **Stress set**: separately generated AMLSim data used for robustness analysis, never silently mixed with AMLBench development data.
- **Champion**: a candidate approved by the model approver for a named local reference use. `null` is permitted.
- **Evidence item**: a typed, immutable reference to a source fact that is reconstructable while its required payload remains retained/pinned, or to a reproducible derived fact; lawful source retirement carries the Section 19.5 reduced guarantee.
- **Evidence snapshot**: the immutable `CaseEvidenceSnapshot` reviewed at a case transition or disposition; it references one or more underlying `EvidencePackage` artifacts and is not an EvidencePackage version.
- **Fail closed**: return a typed non-score/degraded outcome; never fabricate or substitute a risk score.
- **Release evidence**: immutable evidence tied to an exact Git SHA and produced by required remote gates.

---

## 6. Dataset Contract and Phase 0 Feasibility

### 6.1 Verified AMLBench facts and limitations

The candidate primary dataset is the `DVK2026/AMLBench` AusAML release. The planning facts to verify against the downloaded revision are:

- **35,554,888 transactions**;
- **112,620 accounts**;
- **seven months**;
- **297 unique AML scenarios**;
- **45.1 GB**;
- synthetic **5% AML-customer prevalence**;
- **no predefined held-out test because all 297 scenarios are assigned to training**.

These facts describe the published dataset, not a successful local download, schema inventory, usable split, training run, or license decision. Phase 0 MUST pin the exact dataset revision, verify its license/terms, hash local artifacts, and reconcile observed files and counts with the published facts.

The platform MUST NOT call a self-created split the dataset’s official test set. Any project test set is a project-defined, purged temporal test with its own manifest and limitations.

### 6.2 Dataset artifact manifest

Every acquired or generated dataset MUST have a machine-readable manifest containing at least:

- `dataset_id`, `source_uri`, `source_revision`, and retrieval timestamp;
- license identifier, license text hash, and review decision;
- file names, byte sizes, SHA-256 hashes, row counts, and schema versions;
- observed time range, account count, transaction count, and scenario count;
- source prevalence definitions and measured counts;
- null, duplicate, invalid-time, invalid-amount, and referential-integrity summaries;
- source-to-ontology mapping version and source-to-typology mapping version;
- split-manifest ID or `none`;
- generator code/config/seed hashes for synthetic data;
- producer Git SHA and environment lock hash;
- known limitations and approval record.

An artifact with missing required fields MUST be rejected from gated experiments.

### 6.3 Phase 0 entry checks

Before implementation beyond feasibility utilities, Phase 0 MUST establish:

1. exact dataset revision, terms, hashes, counts, schema, and storage footprint;
2. at least 20% free workspace headroom after raw, normalized, and one derived copy are budgeted;
3. measured CPU, memory, disk-throughput, and optional accelerator capacity using a representative sample;
4. a complete field inventory with types, nullability, cardinality, timestamp semantics, and identifier stability;
5. source-to-ontology and source-to-typology mappings;
6. label derivation rules and a leakage denylist;
7. a preregistered, signed, content-hashed `support_floor_manifest`, frozen before labels, metrics, or set counts are inspected, plus proof that a purged, scenario-grouped temporal split meets its planning floors and has no forbidden overlap;
8. a compute profile for rules, tabular, graph construction, and one bounded graph/temporal smoke run;
9. an approved data card describing synthetic prevalence and transferability limits.

### 6.4 Feasibility decision

Phase 0 MUST end with one of these signed decisions:

- **GO**: every Phase 0 gate passes; implementation MAY proceed within the verified claim boundary.
- **REVISE**: the dataset is usable only after the specification narrows ontology, typologies, scale, model ladder, or evaluation claims; the specification MUST be amended and approved before proceeding.
- **STOP**: license, integrity, storage/compute, label, or split feasibility fails; the project MUST select a different dataset or stop the unsupported claim.

Missing source fields MUST narrow the ontology. Insufficient scenario/time support MUST change the split or research claim. Neither condition permits fabricated data support.

### 6.5 AMLSim separation

IBM AMLSim is a controllable synthetic stress generator, not an extension of the AMLBench training population. AMLSim artifacts MUST have separate manifests, namespaces, preprocessing statistics, and evaluation reports. They MUST NOT be merged into AMLBench development data unless a later approved experiment explicitly studies domain mixing and reports it separately.

---

## 7. Source Mapping, Ontology, Labels, and Leakage

### 7.1 Source-to-ontology mapping

Phase 0 MUST publish a mapping table with one row per ontology type and relationship:

| Ontology object | Required source support | Default decision before verification |
|---|---|---|
| `Account` | stable sender/receiver account identifier | Candidate core node |
| `Transaction` | stable transaction or deterministically derived event identifier, amount, event time | Candidate core event/node |
| `Account -[TRANSFER]-> Account` | source account, destination account, event time, amount | Candidate core temporal edge |
| `Customer` / `OWNS` | stable customer identifier and explicit ownership field | Excluded unless verified |
| `Bank` / `HELD_AT` | explicit bank identifier and relationship | Excluded unless verified |
| `Branch` / `HAS_BRANCH` | explicit branch and bank identifiers | Excluded unless verified |
| `Merchant` / `AT_MERCHANT` | explicit merchant identifier and transaction relationship | Excluded unless verified |
| `Device` / `USES` | explicit device identifier and account/event relationship | Excluded unless verified |
| `IP`, `Address`, `Phone`, `Country`, `Beneficiary` | explicit stable fields and declared semantics | Excluded unless verified |

The final mapping MUST name source columns, normalization, cardinality, missing-value policy, identifier derivation, and confidence. A source account MUST NOT be relabeled as a customer, merchant, device, or beneficiary merely to create heterogeneity.

### 7.2 Typology mapping

The candidate research taxonomy is:

- **Flow**: fan-in, fan-out, rapid pass-through;
- **Obfuscation**: layering, circular flow, multi-hop routing;
- **Structuring**: structuring, smurfing;
- **Mule activity**: mule collection.

Phase 0 MUST map each source scenario label to exactly one of:

- supported named typology;
- supported broader family only;
- suspicious but untyped;
- unsupported/ambiguous and excluded from typology metrics.

The mapping MUST cite source values and reviewer approval. Name similarity alone is insufficient. Unsupported named typologies MUST be removed from V1 acceptance while remaining possible AMLSim stress hypotheses.

### 7.3 Label derivation

Labels MUST be derived after de-duplication and before feature construction using versioned code and manifests.

- A transaction is positive only when its source label links it to a verified AML scenario under the mapping. It is negative only when the source semantics justify that label. Otherwise it is unknown.
- An account is positive for a time cutoff when it has participated in a verified positive scenario at or before that cutoff. Its `label_available_at` MUST prevent future participation from labeling earlier features.
- An account is negative only for a declared observation window with no known positive participation under source semantics. It MUST NOT be described as definitively lawful.
- A suspicious subgraph is the deterministic, bounded induced set of scenario-linked transactions and participating source-supported entities under a versioned extraction rule. Background context MAY be attached but MUST be marked unlabeled context.
- Subgraph identity MUST be stable for the same dataset, mapping, cutoff, and extraction version.
- Multi-label typology targets MAY be used only where the source mapping supports them.

All label artifacts MUST record derivation version, cutoff, source scenario IDs, account IDs, transaction IDs, topology rule, and hash.

### 7.4 Leakage denylist

The following MUST NOT enter model inputs, learned encoders, normalization fits, graph construction for earlier cutoffs, or model-selection heuristics unless an approved experiment explicitly treats them as labels only:

- AML flag, scenario ID, typology label, laundering path ID, alert label, or disposition;
- fields or identifier prefixes derived from those values;
- generator configuration, seed, scenario template, or post-generation marker that reveals class;
- split name, row order imposed by label generation, or file path encoding class;
- future transactions, future node degree, future neighbor labels, or statistics fit beyond the scoring cutoff;
- investigation, analyst, case, regulatory, or model outputs created after the event;
- post-event balances or aggregates whose availability time is not proven;
- globally normalized values fit using validation, calibration, test, unknown-typology, or stress data;
- graph edges or embeddings created using future connectivity;
- duplicate or near-duplicate scenario members crossing sets.

Phase 0 MUST scan raw and derived schemas for direct, proxy, temporal, group, and preprocessing leakage. A denied field MAY remain in an audit-only table isolated from feature access.

---

## 8. Evaluation and Holdout Isolation

### 8.1 Required disjoint sets

The project MUST create these mutually exclusive sets:

1. **development train** — fit parameters and training-time statistics;
2. **model-selection validation** — select algorithms, features, hyperparameters, and research progression;
3. **calibration** — fit probability calibration, anomaly mappings, fusion weights, alert thresholds, and abstention policy after candidate freeze;
4. **final temporal test** — latest untouched project-defined test;
5. **unknown-typology evaluation** — scenario family excluded from supervised train, selection, and calibration;
6. **AMLSim stress evaluation** — separately generated robustness data.

No transaction, `scenario_leakage_group_id`, or prohibited near-duplicate MAY cross sets. The primary temporal evaluation MAY contain the same stable account or customer in more than one chronological set because deployment scoring observes continuing entities. Every scored event MUST nevertheless use state truncated at its event-time cutoff; future edges, features, labels, scenario outcomes, dispositions, and normalization statistics MUST be unavailable; and label artifacts MUST remain isolated by set.

The split builder MUST derive `scenario_leakage_group_id` before chronological assignment. It MUST use union-find over verified stable customer/account identifiers and source scenario identifiers: all customers/accounts belonging to the same generated or labelled AML scenario are unioned, scenario aliases or cross-bank copies with common generator/provenance identity are unioned, and transitive connections form one component. The ID MUST be the SHA-256 of the sorted dataset revision, stable member IDs, and source scenario/provenance IDs. Every scenario-linked transaction, label, duplicate/copy, and derived subgraph in one component MUST remain in one set. Non-scenario events for a continuing account MAY follow their chronological set under cutoff-truncated state; they MUST NOT expose the component’s future label or outcome.

The split algorithm MUST assign complete scenario leakage groups using one immutable scenario group anchor. The default `scenario_group_anchor_time` is the maximum event time inside the `scenario_leakage_group_id` after de-duplication. A different anchor rule MAY be used only when it is documented, signed, and content-hashed in the Phase 0 split configuration before labels, metrics, or set counts are inspected. The complete group MUST be assigned to the chronological set containing its anchor. A boundary-spanning scenario group MUST follow the predeclared scenario group anchor/boundary policy: assign the whole group by anchor when all scored events stay outside purge intervals, or exclude/quarantine the whole group from headline sets when the policy says boundary contamination risk is too high. It MUST never be split.

For scored events versus historical context, a transaction may have exactly one role in a split manifest: `SCORED_EVENT`, `HISTORICAL_CONTEXT_ONLY`, or `EXCLUDED_BOUNDARY_GROUP`. Earlier pre-cutoff events from a group assigned to a later set MAY be used only as historical context for later-set scoring and MUST NOT be scored, trained, calibrated, or counted as earlier-set labels. Later or post-cutoff events MUST never be context for earlier scores. The split algorithm MUST then apply chronological boundaries to remaining non-scenario events and MUST purge a documented boundary interval large enough to prevent lookback windows from reading across sets. A separate optional **cold-start evaluation** MAY group all events by stable customer/account connected component and assign each entity group to exactly one set. Cold-start results MUST be reported separately and MUST NOT replace or be conflated with the primary temporal evaluation.

### 8.2 Split proof and manifest

Before set counts are inspected, the model approver MUST sign and content-hash a preregistered `support_floor_manifest` containing the following minimum planning floors. These floors prevent unsupported execution claims; they are not proof of statistical adequacy, and a per-metric protocol MAY preregister higher floors.

| Set/configuration | Positive scenario groups | Positive accounts | Negative accounts | Temporal support |
|---|---:|---:|---:|---:|
| development train | 60 | 200 | 200 | 60 calendar days |
| model-selection validation | 30 | 100 | 100 | 30 calendar days |
| calibration | 30 | 100 | 100 | 30 calendar days |
| final temporal test | 30 | 100 | 100 | 30 calendar days |
| unknown-typology evaluation | 20, all from one wholly excluded typology family | 50 | 100 | 30 calendar days |
| each executed AMLSim stress configuration | 20 | 50 | 100 | 30 simulated days |

The split manifest MUST record:

- dataset and mapping hashes;
- event-time boundaries and purge durations;
- scenario grouping, union-find inputs, cross-bank copy/provenance rules, and `scenario_leakage_group_id` method;
- scenario group anchors, full group time spans, boundary policy decision, excluded/quarantined group IDs, and reason codes;
- transaction, account, scenario, positive, negative, and unknown counts per set;
- the `support_floor_manifest` ID/hash and observed values, units, PASS/FAIL, and shortfall reason against every applicable floor;
- per-set `SCORED_EVENT`, `HISTORICAL_CONTEXT_ONLY`, and `EXCLUDED_BOUNDARY_GROUP` counts;
- cross-set intersection counts, all required to equal zero for transactions and scenario groups;
- account/customer overlap counts and rates for every set pair, overlap policy, cutoff-truncation proof, label-isolation proof, and causal state-reset/continuation policy;
- automated proof that no post-cutoff scenario event, label, outcome, feature, edge, or normalization statistic from a later set is visible to any earlier-set score;
- cold-start entity-group intersections and results when that optional evaluation runs;
- time-range and lookback checks;
- unknown-typology exclusion proof;
- seed where tie-breaking requires one;
- producing code SHA, reviewer, and approval timestamp.

Any AMLBench planning-floor failure or inability to produce a valid set without forbidden overlap MUST yield Phase 0 `REVISE` or `STOP`. An AMLSim planning-floor failure MUST produce the existing Section 8.6 content-hashed `SKIPPED_BY_DEPENDENCY` decision and MUST NOT be called executed stress evidence. Random row splitting MUST NOT be used for headline claims.

### 8.3 Holdout access policy

The final temporal test MUST remain unread by exploratory notebooks and training jobs. Access MUST occur only after:

- algorithms, features, hyperparameters, preprocessing, calibration form, fusion, thresholds, alert budget, and uncertainty method are frozen;
- the evaluation manifest is signed by the model approver;
- an immutable candidate artifact and environment lock exist;
- the run is registered as the single final protocol execution.

Final-test results MUST NOT drive reruns, retuning, model replacement, calibration, fusion, weights, or thresholds. A failed or negative final result remains the result unless an approved new research cycle defines a new untouched test before viewing it.

### 8.4 Calibration and fusion

Supervised outputs MUST be assessed for calibration. Sigmoid/Platt scaling is the predeclared default. An alternative calibration form MAY be selected only from nested forward-chaining or cross-fitted out-of-fold predictions generated wholly inside model-selection validation; the comparison MUST use the frozen Brier/ECE objective and MUST NOT inspect the disjoint calibration set. After the form is selected and the candidate is frozen, that form MUST be fitted exactly once on the calibration set. Isotonic calibration is eligible only when every selection fold and the final calibration set contain at least 100 positive and 100 negative examples and its cross-fitted improvement exceeds the predeclared practical-effect margin without a worse worst-fold ECE; otherwise Platt scaling MUST be used. Anomaly scores MUST use a calibration-only empirical mapping with explicit out-of-range behavior.

If risk fusion is evaluated, candidate components and fusion forms MUST be chosen on model-selection validation, then fitted on calibration data. Weights MUST be non-negative and sum to one for deterministic weighted fusion. A learned meta-model MAY be compared, but simpler calibrated fusion SHOULD be selected when validation benefit is within the predeclared uncertainty/effect-size margin.

The final test MUST only estimate the already-frozen system.

### 8.5 Metrics and uncertainty

Accuracy MUST NOT be a headline metric. Reports MUST include, where label support permits:

- PR-AUC with 95% scenario-group bootstrap confidence interval;
- precision at a frozen top-K or alert budget;
- recall at a frozen precision target;
- F1 as a secondary metric;
- Brier score and expected calibration error;
- per-supported-typology recall and scenario detection rate;
- suspicious-subgraph recall under the versioned matching rule;
- unknown-pattern detection and novelty-alert precision;
- time-to-detection and captured amount only where semantics support them;
- false positives per 1,000 observed accounts and alerts per simulated day;
- p50/p95/p99 latency, throughput, lag, and typed failure rate.

Comparisons MUST report paired uncertainty at the scenario-group level and the predeclared practical-effect threshold. Small, uncertain differences MUST be described as inconclusive.

### 8.6 Null champion

Champion selection MUST apply frozen minimum gates for data integrity, calibration, alert volume, scenario coverage, `model_package_scoring_p95_ms`, reproducibility, and governance. `model_package_scoring_p95_ms` measures only the frozen package's scoring call under the Phase 7 package workload; `event_to_decision_p95_ms`, throughput, lag, PostgreSQL/outbox persistence overhead, typed failures, and recovery are Phase 8/12 integration gates and MUST NOT delay champion selection until after final-test access. `NO_PROMOTABLE_CHAMPION` means no candidate passes those pre-final gates; it requires a sealed-null manifest with `selected_model = null`, `champion = null`, and final temporal test status `NOT_RUN_SEALED`. The final temporal test MUST remain sealed and MUST NOT execute on this path. `NO_EVALUABLE_ARTIFACT` means no last reproducible frozen research baseline exists for the relevant protocol.

When `NO_PROMOTABLE_CHAMPION` has a last reproducible frozen research baseline and the preregistered experiment is valid without final-test access, unknown-typology evaluation, AMLSim stress evaluation, and applicable ablations MUST run as a research-only baseline evaluation, be labeled non-promotable, and publish negative results. `SKIPPED_BY_DEPENDENCY` is allowed only for a content-hashed decision naming a missing or invalid artifact, unsupported task/labels, infeasible resources, or protocol dependence on sealed final-test data; generic null champion status is insufficient. Dataset/split integrity checks, deterministic rules/reference-baseline diagnostics, system/evidence/AI/UI tests, and operational benchmarks MUST still run where applicable. A sealed-null manifest is acceptable for research/project completion only when every planned development and validation branch emitted its signed, content-hashed decision record and required negative-result report. The candidate path permits exactly one preregistered final-temporal-test execution and its applicable unknown-typology, AMLSim-stress, and ablation evaluations. The platform MAY run deterministic rules or a clearly labeled research baseline locally, but MUST NOT relabel it as a champion unless it passed the frozen promotion gates.

---

## 9. Research Ladder and Stop Conditions

### 9.1 Conditional progression

Research MUST progress through evidence-gated branches rather than implementing every model in advance. The stable branch IDs are normative: `RULE_TABULAR`, `BEHAVIOR_ANOMALY`, `GRAPH_ANOMALY`, `STATIC_GNN`, `TGN`, `HGT`, `HYBRID_TGN_HGT`, and `CALIBRATION_FUSION`.

Before any branch can read its result metrics or any holdout, the model approver MUST sign and content-hash a branch-specific `pre-execution gate manifest`. That manifest MUST include branch ID, input artifacts, exact metric direction, numerical thresholds, uncertainty interval method, effect-size and minimum practical improvement, alert-volume budget, compute/memory/time ceilings, required repetitions and seeds, stop/proceed/skip logic, and dependency-outcome rules. Measured results MUST append to a separate immutable decision record; they MUST NOT rewrite the frozen gate manifest.

The explicit prerequisite/outcome matrix is:

| Branch ID | Work package | Prerequisites | Eligible predecessor outcomes | Execute/skip rule | Downstream path |
|---|---|---|---|---|---|
| `RULE_TABULAR` | deterministic rules, logistic regression, and one tree baseline | Phase 0 GO, Phase 2 event contracts, Phase 3 labels/splits | none | Executes when prerequisites pass; otherwise emits `SKIPPED_BY_DEPENDENCY` | `BEHAVIOR_ANOMALY`, `GRAPH_ANOMALY`, `CALIBRATION_FUSION` |
| `BEHAVIOR_ANOMALY` | bounded behavioral anomaly baseline | `RULE_TABULAR` decision record and Phase 4 causal features when required by the manifest | `RULE_TABULAR` is `PROCEED` or `STOP` | Executes when its frozen manifest has valid inputs; skips only when prerequisite artifacts are missing or invalid | `TGN`, `CALIBRATION_FUSION` |
| `GRAPH_ANOMALY` | bounded graph anomaly candidate | `RULE_TABULAR` decision record and verified Phase 0 graph support | `RULE_TABULAR` is `PROCEED` or `STOP` | Executes only when graph construction is supported and within frozen resource ceilings; otherwise skips | `STATIC_GNN`, `HGT`, `CALIBRATION_FUSION` |
| `STATIC_GNN` | one GraphSAGE/GAT-class static graph baseline | `GRAPH_ANOMALY` decision record and causal graph builder | `GRAPH_ANOMALY` is `PROCEED` or `STOP` | Executes when static graph tensors meet the manifest's size and leakage gates; otherwise skips | `HGT`, `CALIBRATION_FUSION` |
| `TGN` | one event-time TGN-style baseline | `BEHAVIOR_ANOMALY` decision record and Phase 4 online/offline parity | `BEHAVIOR_ANOMALY` is `PROCEED` or `STOP` | Executes when temporal windows and replay package meet frozen ceilings; otherwise skips | `HYBRID_TGN_HGT`, `CALIBRATION_FUSION` |
| `HGT` | HGT-style relation-aware baseline | `STATIC_GNN` decision record and Phase 0 verified heterogeneous node/edge types | `STATIC_GNN` is `PROCEED` or `STOP` | Executes only when heterogeneity support and resource gates pass; otherwise skips | `HYBRID_TGN_HGT`, `CALIBRATION_FUSION` |
| `HYBRID_TGN_HGT` | typed TGN memory plus relation-aware HGT-style attention hypothesis | `TGN` and `HGT` decision records | both `TGN` and `HGT` are `PROCEED` | Executes only when both predecessors proceed and the manifest names the residual error and numerical target; otherwise skips | `CALIBRATION_FUSION` |
| `CALIBRATION_FUSION` | Phase 7 candidate or null research protocol | decision records for all prior branch IDs | any complete set of `PROCEED`, `STOP`, or `SKIPPED_BY_DEPENDENCY` records | Executes candidate path when at least one accepted candidate passes frozen promotion gates; executes null path when none survives | Phase 7 completion manifest |

Graph anomaly candidates such as PyGOD implementations MAY be reused after license, interface, scale, and memory checks. A candidate list is not an implementation commitment.

Every stage and every separately gated branch MUST emit exactly one decision: `PROCEED`, `STOP`, or `SKIPPED_BY_DEPENDENCY`. The decision record MUST name the stage/branch, accepted input artifact, dependency decisions, frozen gate-manifest hash, measured gate values, rationale, claim boundary, owner, reviewer, timestamp, Git SHA, artifact hashes, and next eligible stage; it MUST be signed by the model approver and content-hashed. `SKIPPED_BY_DEPENDENCY` means no implementation or result is claimed for that stage. Later-stage deliverables are conditional on the matrix above; a valid `STOP` or `SKIPPED_BY_DEPENDENCY` record satisfies roadmap dependency accounting and routes evaluation to `CALIBRATION_FUSION`, either with the last accepted simpler model or with the null path.

### 9.2 Compute profile

Before each graph or temporal stage, a profile manifest MUST record sample size, graph size, temporal span, hardware, software lock, wall time, peak RAM/VRAM, storage, throughput, estimated full-run cost, and failure behavior. Full-scale execution MUST NOT start when projected resource use exceeds the pre-execution gate manifest's frozen capacity values or leaves less than 20% free storage headroom.

### 9.3 Stop conditions

A stage MUST stop and publish its result when any of these applies:

- required source support or causal construction is absent;
- the predecessor branch already meets the pre-execution gate manifest's frozen research objective and the next branch lacks a manifest-defined distinct hypothesis;
- validation improvement is below the frozen minimum practical improvement or fails the frozen uncertainty interval criterion;
- alert volume, calibration, reproducibility, or explainability crosses the manifest's numerical stop threshold;
- projected runtime, memory, storage, or local scoring latency exceeds the frozen compute ceiling;
- two bounded remediation attempts fail for the same technical constraint;
- the model cannot be packaged and replayed deterministically.

Stopping is a valid result. The project MUST publish what was attempted, why it stopped, and the remaining claim boundary.

### 9.4 Unknown-typology and adversarial protocols

On the candidate path, and on the sealed-null path when Section 8.6 provides a reproducible frozen baseline and a protocol valid without final-test access, at least one source-supported scenario family MUST be excluded from supervised development for the unknown-typology protocol. Before development-set results are inspected, the model approver MUST sign and content-hash an unknown-typology manifest naming the wholly excluded family and source groups, dataset/split/mapping hashes, temporal placement, evaluation principal and exactly-one post-freeze evaluation-access procedure, freeze time, metrics, and report destination. Its data and results MUST remain inaccessible until the frozen candidate or eligible frozen research baseline exists; only that evaluation principal may then make the one evaluation access, which MUST NOT drive feature, model, branch, calibration, fusion, threshold, abstention-policy, or alert-budget selection or retuning.

Separately, a distinct pre-evaluation blind-custodian integrity/floor-validation path MUST NOT consume that one evaluation access. Its custodian query/procedure MUST be frozen and content-hashed before development results are inspected; the custodian MUST be isolated from development and model selection and MUST NOT receive candidate/model outputs. It MAY release only the predeclared aggregate counts/units, PASS/FAIL/shortfall, set/hash/temporal-placement binding, and exclusion/intersection proof required by Phase 0—never records, features, labels, typology examples, evaluation metrics, or other set data/results. The split and unknown-typology manifests MUST both bind the custodian identity/role, access time, query/procedure hash, input/output hashes, and released aggregates/proofs. The report MUST distinguish anomaly surfacing from named typology recognition and MUST NOT assign an unsupported known label; sealed-null baseline results MUST be labeled research-only/non-promotable. Otherwise it is `SKIPPED_BY_DEPENDENCY` only under the specific evidence requirements of Section 8.6.

On the candidate path, when AMLSim prerequisites and Section 8.2 support floors pass, at least one model-approver-approved AMLSim stress configuration MUST execute. The sealed-null path follows Section 8.6. Individual stress axes SHOULD cover controlled changes in amount, velocity, hop count, ring size, routing topology, or cash-out delay; additional axes MAY be preregistered. Each executed configuration MUST identify generator configuration, seed, difficulty scale, sample size, temporal support, and separation from AMLBench; results MUST report detection and alert-volume degradation against difficulty, including negative findings, and sealed-null baseline results MUST be labeled research-only/non-promotable. A missing prerequisite or planning-floor failure is `SKIPPED_BY_DEPENDENCY` only under the specific evidence requirements of Section 8.6 and is not executed evidence.

Every applicable ablation MUST have a signed, content-hashed ablation manifest frozen before ablation results are inspected. It MUST name the component removed, unchanged comparator, affected metrics and direction, preregistered practical-effect threshold, input/package prerequisites, and the exact Section 8.6 `SKIPPED_BY_DEPENDENCY` outcome when prerequisites fail. An executed ablation MUST change only the named component and report negative or inconclusive findings; this paragraph creates no additional skip category.

### 9.5 Research definition of done

Research is complete when the approved protocol has published every planned branch decision and negative-result report, applicable uncertainty analysis, and artifacts. The candidate path executes baselines, gated stops, one final test, unknown-typology evaluation, AMLSim stress tests, and ablations for implemented components; the sealed-null path records `NOT_RUN_SEALED`, executes research-only/non-promotable baseline evaluations where Section 8.6 permits, and otherwise records only specific, content-hashed `SKIPPED_BY_DEPENDENCY` decisions while completing all applicable non-candidate diagnostics. A winning hybrid model is not required. The outcome MAY be a simple champion, a partial ladder, an inconclusive comparison, or a sealed null champion.

---

## 10. Feature, Graph, and Risk Contracts

### 10.1 Causal features

Every online and offline feature MUST declare:

- name, semantic description, entity key, data type, unit, and null policy;
- event-time window and `available_at` semantics;
- source fields and transformation version;
- leakage classification;
- offline implementation and online implementation;
- parity tolerance and test fixture;
- owner and deprecation policy.

Candidate families include transaction amount/channel/time encodings; behavioral counts, sums, counterparty novelty, pass-through, and trailing deviation; causal degree, fan-in/out, cycle/path, density, and suspicious-neighbor measures; and device/context features only when verified.

Offline/online parity is mandatory for any production-shaped scoring feature. Feast MAY provide the feature definition abstraction after Phase 0 proves that its push and retrieval semantics fit the event-time contract. Parquet or a verified warehouse is the offline source; Redis is the online projection.

### 10.2 Graph construction

Graph artifacts MUST be heterogeneous only to the extent source mappings support heterogeneity. Every node, edge, attribute, and timestamp MUST trace to a source field or versioned derivation. Graph construction MUST be causal, serializable, bounded, and reproducible from a dataset manifest and cutoff.

Training MAY use PyTorch Geometric or an equivalent maintained framework. Neo4j is an investigation projection and MUST NOT be the scoring hot path or the source of truth for model state.

### 10.3 Risk output

A scoring component MUST be declared in the frozen package as either **partition-local**, depending only on state whose entity partition covers the decision cutoff, or **cross-entity**, depending on counterpart, neighborhood, graph, or other multi-partition state. A committed entity watermark is the greatest contiguous event-time cutoff and source offset for which that entity partition has durable `STATE_APPLIED` receipts in one `state_generation_id`; a component completeness watermark is the minimum such verified coverage across all inputs it requires in that generation. Neither watermark depends on downstream scoring, evidence, sinks, or `COMPLETE`. The PostgreSQL `EventTransitionResult` continuation ledger MUST store those watermarks as source partition/offset, event-time cutoff, `state_generation_id`, component/input ID, group/member receipt IDs, and coverage status. A cross-entity component MUST wait until every mandatory counterpart and graph input has the required same-generation/cutoff `STATE_APPLIED` coverage; cross-generation inputs are prohibited. Missing mandatory coverage blocks and retries rather than creating a wall-clock-dependent score. Only a mandatory input proven deterministically terminally absent after required group/coverage processing may yield `FAILED_CLOSED` with a typed terminal-absence reason; optional-component absence may be `ABSTAINED` only under the frozen abstention policy.

Every actual scoring attempt MUST create durable canonical `RiskDecision` and `EvidencePackage` records and return one of:

- `SCORED` with frozen component scores, required final score, subject, versions, and evidence package;
- `ABSTAINED` with no final score, the available components, a typed versioned abstention reason, and available evidence;
- `FAILED_CLOSED` with no final score, a typed failure reason, and available diagnostic evidence.

Evidence items MAY be empty for any status. Pre-scoring schema rejection/quarantine is not a scoring attempt and remains outside this decision/evidence creation contract.

Every scoring attempt MUST have a unique, deterministic `risk_decision_id` derived from the original event ID, `state_generation_id`, `replay_run_id`, scored subject, feature/rule/model/calibration/fusion/threshold versions, and decision-contract version. A normal delivery retry within the same state generation and replay run MUST reuse the same `risk_decision_id`. A controlled correction replay that changes state, features, model/rule versions, or evidence lineage MUST create a new `risk_decision_id`, link to any prior decision through `supersedes_decision_id` or a typed retraction reason, and preserve the prior decision and audit trail. That ID is the sole transport-idempotency key for alerts and case ingestion.

Risk inputs MAY include deterministic rules, supervised probability, behavioral anomaly, graph anomaly, temporal anomaly, and typology confidence. Only components present in the frozen model package MAY contribute. Incomplete or transient mandatory-input/`STATE_APPLIED` coverage MUST block and deterministically retry or reconcile without emitting a canonical score status. Only a mandatory input proven deterministically terminally absent after its required group/coverage processing MAY produce `FAILED_CLOSED`, with a typed terminal-absence reason. Optional unavailable input MUST follow the package’s predeclared abstention rule.

### 10.4 Suspicious subgraphs

Subgraph discovery MUST use bounded depth, time range, node count, edge count, and evidence count. Each result MUST record the query/extraction version and truncation state. Unbounded expansion is prohibited. A truncated result MUST be labeled `PARTIAL` and MUST NOT be described as the complete laundering network.

---

## 11. Initial Runtime Architecture

### 11.1 Three deployables

V1 starts with exactly three application deployables:

1. **Ingestion/scoring worker** — replay/consume, schema validation, quarantine, normalization, causal features, bounded entity state, model/rule loading, scoring, evidence creation, and risk-event publication.
2. **Case/agent API** — alert/case persistence, evidence retrieval, assignments, lifecycle transitions, dispositions, audit, bounded investigation queries, and read-only AI orchestration.
3. **Investigator web** — typed analyst interface for queues, cases, graph, timeline, evidence, AI output, review, and disposition.

Kafka, PostgreSQL, Redis, object/experiment storage, Neo4j, and monitoring are infrastructure dependencies, not extra application services. Package boundaries for ingestion, features, graph state, scoring, cases, evidence, and agent tools MUST remain explicit inside the deployables.

A package MAY split into a new deployable only after a decision record demonstrates an independent ownership, scaling, isolation, security, or availability need using profiling evidence. Speculative service splitting is prohibited.

### 11.2 State ownership

| State | System of record | Projection/cache |
|---|---|---|
| Raw and normalized event log | Kafka plus immutable archived artifacts | none |
| Dataset and model artifacts | content-addressed object storage / MLflow records | local read cache |
| Online causal entity state | replayable Kafka history plus versioned checkpoints | Redis and bounded in-process cache |
| Per-event processing continuation and committed entity/completeness watermarks | PostgreSQL durable `EventTransitionResult` plus outbox/receipts and coverage ledger | Redis applied-transition marker and Kafka consumer offset |
| Cases, assignments, transitions, dispositions, outbox | PostgreSQL | API cache if later justified |
| Evidence snapshots | immutable PostgreSQL/object artifacts with hashes | API read model |
| Investigation graph | source events/evidence manifests | Neo4j projection |
| Audit log | append-only PostgreSQL/object export with hash chain | search projection |

Redis or Neo4j loss MUST NOT destroy the only copy of a case, disposition, evidence snapshot, audit record, or model artifact.

### 11.3 Versioned contracts

All external events and APIs MUST use versioned schemas with compatibility tests. Required event families are:

- `RawTransactionEvent`;
- `NormalizedTransactionEvent`;
- `EntityStateCommand`;
- `RiskDecisionEvent`;
- `EvidencePackage`;
- `CaseLifecycleEvent`;
- `AuditEvent`.

Every event MUST include `schema_version`, stable `event_id`, source, event time, ingest time, producer, producer Git SHA, trace ID, and payload hash. Monetary values MUST use decimal amount plus ISO currency, never binary floating point. Unknown required enum values MUST fail validation; additive optional fields MAY be accepted under the compatibility policy.

### 11.4 Primary flow

The required local flow is:

`source replay -> raw Kafka topic -> validation/quarantine -> normalized event -> per-entity state command -> causal feature/state update -> scoring attempt -> evidence package -> risk event -> case/outbox persistence -> investigation projections -> analyst workflow`.

The UI MUST call typed Case/Agent API endpoints only. It MUST NOT query Redis, Neo4j, Kafka, MLflow, or model artifacts directly.

### 11.5 Docker Compose baseline

The V1 local baseline MUST remain Docker Compose and MUST NOT add an orchestrator or deployable. The Compose manifest and environment lock MUST pin every image by exact version and immutable digest; declare health checks and readiness-gated dependency conditions; use named persistent volumes for every durable local dependency; declare per-container CPU and memory reservations/requests and limits plus a documented minimum local CPU, RAM, disk, and free-space profile; and fail startup when a required dependency is unhealthy, an image digest differs, a required volume cannot be mounted, or the local profile is below the declared minimum. Phase 12 acceptance MUST include a clean-start gate from empty disposable volumes that records image digests, dependency health/readiness, migration/bootstrap status, service health, and artifact hashes. Existing retained volumes MAY be used only in a separately labeled recovery gate.

---

## 12. Streaming Correctness and Recovery

### 12.1 Kafka keys and partitions

Topic names MUST include a major contract version. The initial key policy is:

- raw events: verified source partition key, otherwise stable source account ID;
- normalized transactions: stable `event_id`;
- entity-state commands: affected `entity_id`, with one command per affected entity;
- risk decisions: scored `subject_id`;
- case lifecycle events: `case_id`;
- quarantine and late-event records: original `event_id`.

All mutations for one entity MUST route to the same entity-state partition. Partition count, key skew, hot keys, replication, retention, and consumer-group ownership MUST be recorded in the benchmark manifest. Cross-entity subgraph state is eventually consistent and MUST expose its completeness watermark.

### 12.2 Event time and late events

Features and graph state MUST use event time. Ingest time is audit metadata only. The initial allowed-lateness default is five minutes and MUST be configurable, versioned, and justified from Phase 0 arrival-delay measurements.

- Events within the allowed-lateness window MUST be buffered/reordered by entity before state application.
- A group found late for any expected member under Section 12.3 MUST take its whole-group `REPLAY_REQUIRED` disposition and MUST NOT silently mutate current state.
- A controlled replay MUST rebuild the affected partition from the last valid checkpoint, publish a new state version, and reconcile dependent risk/case projections without deleting history.
- Clock, timezone, daylight-saving, and equal-timestamp tie-breaking rules MUST be deterministic; UTC plus `event_id` lexical tie-break is the default.

The named `REPLAY_REQUIRED` operational alert MUST evaluate replay-required record count, oldest record age, and number/list of affected partitions against versioned thresholds. Its runbook MUST default to controlled partition replay for the **rebuild scope**; per-entity replay is not the default rebuild contract. A partial rebuild does not narrow the Section 12.4 global activation fence/materialization scope.

### 12.3 Idempotency and offset coordination

Stable `event_id` is the source delivery idempotency key. Every controlled replay or correction MUST derive its deterministic `state_generation_id` and `replay_run_id` from the `ReplayManifestCore` procedure in Section 12.4, never from wall-clock time or randomness. Entity state, feature windows, graph memory, state-version keys, and recovery checkpoints MUST be namespaced solely by `state_generation_id`, plus entity/partition identifiers where applicable; they MUST NOT use `replay_run_id`. `replay_run_id` is only execution, cursor, continuation, transition, decision, evidence, staging-lineage, and idempotency metadata. An inactive replay run writes state into its candidate `state_generation_id` namespace. After activation, live events use the already activated `state_generation_id` and literal `replay_run_id = live`, read/update that generation's existing state and checkpoints, and MUST NOT create an empty `(state_generation_id, live)` state namespace. A normal delivery retry retains those same IDs, `transition_id`, `risk_decision_id`, and `evidence_package_id`. A controlled late-event replay or correction MUST create a new `state_generation_id` and `replay_run_id`, and every affected entity mutation MUST get a new deterministic `transition_id` derived from the original `event_id`, `entity_id`, `state_generation_id`, `replay_run_id`, feature/rule/model versions that affect state, and transition-contract version. Duplicate payload hashes within the same lineage MUST be no-ops; the same lineage ID with a different payload hash MUST be quarantined as a conflict.

A correction execution MUST create new immutable `RiskDecision` and `EvidencePackage` artifacts, including a new `risk_decision_id` and `evidence_package_id`, derived from the original event ID, `state_generation_id`, `replay_run_id`, scored subject, feature/rule/model/calibration/fusion/threshold versions, and contract versions. It MUST NOT mutate prior transition, decision, evidence, case, or audit artifacts. The new artifacts MUST carry `supersedes_decision_id` and `supersedes_evidence_package_id` when they replace a prior artifact, or a typed retraction link when the corrected execution withdraws the prior score without a replacement. They MUST also include correction reason, correction source event, approver when manual approval is required, and prior artifact hashes.

Before advancing Redis, the worker MUST deterministically enumerate the normalized source event's complete expected entity-command group. `transition_group_id` MUST derive from the normalized event ID, payload hash, `state_generation_id`, `replay_run_id`, and entity-command contract version. Before any group receipt, member transition, or Redis mutation, it MUST compare the event cutoff with every expected member entity's committed watermark under the frozen lateness policy. If any member is late/replay-required, the entire group MUST take one deterministic `REPLAY_REQUIRED` disposition: no member may mutate live state and no live `EventTransitionResult` may begin. Before source-offset advancement, it MUST persist a whole-group late-event receipt binding group/event/payload, the complete expected member/partition set, every member's watermark comparison and reason, generation/run lineage, source coordinates, policy version, and affected replay partitions. Controlled replay MUST rebuild and reconcile every partition and dependent projection touched by that group under the existing candidate-generation/global-activation protocol; it MUST neither partially apply current members nor leave the group blocking forever. A PostgreSQL group receipt MUST otherwise store the canonical sorted expected member IDs, expected count, source topic/partition/offset, event cutoff, generation/run lineage, and group hash before any member transition begins. Every member MUST validate before that transaction: a malformed or unsupported member makes the whole group a pre-transition terminal-quarantine outcome, creates no `EventTransitionResult`, and advances the source offset only under the Section 12.7 persisted quarantine receipt.

For a valid group, the worker MUST atomically create or verify one durable `EventTransitionResult` per expected member in PostgreSQL. Each record MUST be unique by `transition_id` and contain the group receipt ID/hash; `state_generation_id`; `replay_run_id`; input/payload hash; source topic/partition/offset; prior and next state versions/hashes; complete deterministic state-transition bytes or a read-back-verified content-addressed blob; and monotonic processing stage. After every expected member's state mutation is durably applied and its Redis version/hash plus applied marker are verified, the worker MUST atomically advance the group receipt to durable `STATE_APPLIED`, recording every member transition ID/state hash/receipt and the resulting contiguous state-coverage watermark. Transition bytes and receipts are immutable; processing stage MAY advance only by compare-and-set or append-only child records. PostgreSQL is the processing-continuation and watermark source of truth; Redis is a rebuildable projection and a Kafka offset is only a consumption cursor.

Scoring MUST begin only after the source group is `STATE_APPLIED` and every required partition-local or cross-entity group/member receipt satisfies the same-generation/cutoff contract in Section 10.3. It MUST then append an immutable decision/evidence result containing the complete canonical `RiskDecision` and `EvidencePackage` payloads or their verified content-addressed blob references, supersession/retraction links when present, required sink intents, outbox messages with deterministic IDs, and completion receipts. Metadata, hash, or artifact intent without the retrievable complete transition or decision/evidence payload is insufficient. `COMPLETE` remains downstream of scoring/evidence/sinks and MUST NOT be a scoring or state-watermark prerequisite.

Ordinary transition delivery rules apply directly only to the active generation. An inactive replay generation MUST store each `RiskDecision`, `EvidencePackage`, case-correction output, and generation-scoped outbox entry as immutable `STAGED_NON_CURRENT` artifacts keyed by its candidate `state_generation_id` and `replay_run_id`. They MUST NOT be visible as current, affect alert priority, disposition, or current evidence, or be consumed by ordinary live correction consumers before activation. Its sinks write only the staged artifacts; they do not mutate a case-facing current view.

For each consumed record, the worker MUST:

1. validate the normalized event and every deterministically enumerated expected group member before durable transition work; quarantine the whole invalid group or persist the valid group receipt and each member's deterministic transition;
2. apply every member transition to Redis using compare-and-set on its prior state version/hash and persist its applied marker/receipt;
3. after the complete expected member set is verified, atomically advance the group to `STATE_APPLIED` and advance only contiguous entity/component state-coverage watermarks;
4. wait for all required same-generation/cutoff `STATE_APPLIED` receipts, then create the immutable canonical decision/evidence result and required sink intents/outbox messages;
5. deliver required locally owned sinks/outbox messages idempotently, persist their receipts, and mark the group/member continuation records `COMPLETE` only after state hashes are verified, decision/evidence are durable, and every required receipt exists;
6. commit the source Kafka offset only after every expected member is `COMPLETE`.

A retry MUST first load the group receipt and every expected `EventTransitionResult` by group/member ID, `state_generation_id`, and `replay_run_id`, verify the stored expected set/count and immutable payloads, and resume from durable stages. If Redis already shows a member's applied lineage marker and next-state hash, retry MUST NOT apply it again; missing member or `STATE_APPLIED` receipts block offset advancement and are recovered by deterministic retry/reconciliation. After `STATE_APPLIED`, retry MUST reconstruct any missing decision/evidence artifact or sink message from immutable lineage inputs, then resume delivery, receipt recording, and completion. A missing/hash-invalid payload or different Redis version/hash MUST fail closed and trigger reconciliation or replay. Wall-clock timeout or partial group arrival MUST NOT become a canonical `ABSTAINED`/`FAILED_CLOSED` result, and an event MUST NOT be marked fully processed solely because Redis state advanced.

Crash recovery MUST follow these boundaries:

- before the PostgreSQL group/member transaction commits: Redis remains unchanged and retry recomputes the deterministic group;
- after that commit but before all member applications: retry loads the expected set and applies only missing stored transitions;
- after a member Redis application but before its receipt: retry verifies the applied marker/version/hash and records the missing receipt;
- after all member receipts but before `STATE_APPLIED`: retry verifies exact expected-set completeness and atomically advances the group receipt;
- after `STATE_APPLIED` but before decision/evidence persistence: retry scores from the same immutable lineage inputs without waiting on `COMPLETE`;
- after sink/outbox delivery but before its receipt is recorded: deterministic message IDs and sink unique constraints make redelivery safe, and retry records or reconciles the receipt;
- after `COMPLETE` but before offset commit: retry verifies the complete record and commits the offset without repeating effects.

Kafka transactional production MAY be used for Kafka-only consume/produce paths. External sinks MUST use unique constraints, optimistic versions, deterministic message IDs, and idempotent upserts. "Exactly once" MUST NOT be claimed across Kafka, Redis, and PostgreSQL; the documented contract is at-least-once delivery with a PostgreSQL continuation ledger, idempotent effects, receipts, and reconciliation.

### 12.4 Deterministic replay

Before lineage IDs are derived, `ReplayManifestCore` MUST include the version/hash of every artifact, configuration, and policy capable of changing state, ordering, transition bytes, canonical classification, `RiskDecision`, `EvidencePackage`, or correction artifacts. It MUST canonicalize source offsets/artifact hashes; schema, mapping, feature, rule, model, calibration, fusion, and threshold versions; graph-construction and graph-state versions/hashes; partition count and key function; event-time ordering and tie-break policy; transition, decision, and evidence contract versions; correction/materiality policy; evidence-classification policy whenever it affects canonical bytes; source-start checkpoint; catch-up watermark; environment lock; Git SHA; parent active generation; and declared run kind. It MUST exclude `state_generation_id`, `replay_run_id`, core/final manifest hashes, attestations/signatures, and operational timestamps. `replay_core_hash = SHA256(canonical ReplayManifestCore)`; then `state_generation_id = SHA256("state-generation-v1" || parent_generation_id || replay_core_hash)` and `replay_run_id = SHA256("replay-run-v1" || state_generation_id || replay_core_hash || run_kind)`. The final `ReplayManifest` MUST contain the core, derived IDs, and parent lineage, then compute a separate final manifest hash/signature over canonical final content excluding only its own hash/signature fields.

Replay equivalence means exact equality of the canonical `RiskDecision` and `EvidencePackage` SHA-256 hashes defined in Section 14.3 for the same lineage. Deterministic event time, evidence cutoff time, state generation, replay run, and supersession/retraction links are hashed; operational processing/creation timestamps, delivery receipts, retries, and sink status are excluded from those content hashes and compared only as audit metadata. A divergence in either canonical hash MUST fail the replay gate and emit a comparison artifact. Contract verification MUST mutate each declared `ReplayManifestCore` input independently and prove that `replay_core_hash`, `state_generation_id`, and `replay_run_id`/lineage change; an input that can change canonical behavior without changing lineage fails the gate.

Controlled replay/correction MUST consume through a dedicated replay consumer group and cursor and MUST NOT commit replay offsets to the live consumer group. It MAY rebuild only the affected partitions into an inactive candidate `state_generation_id` namespace while live ingestion continues on the generation named by one global active-generation pointer. The frozen manifest MUST identify the complete partition inventory, affected rebuild set, source-start checkpoints, and initial watermarks; before cutover, each affected candidate partition replays deterministically through its frozen initial watermark and reconciles its staged decision, evidence, and case-correction artifacts.

Cutover fencing and materialization are global even when rebuild scope is partial. For every partition, the fence MUST first pause/buffer admission of new transition groups and propose a barrier/head. Before sealing that barrier, it MUST deterministically retry and drain every in-flight group with any begun or member-applied transition touching that partition at or below the proposal until the complete expected member set has one durable group `STATE_APPLIED` receipt. Only then may it seal the barrier, pause live state mutation and offset commit (consumption MAY buffer), and record exact `G1` coverage, state version/hash, and checkpoint. If a crash/missing receipt cannot be recovered and drained within the bounded fence, activation MUST abort, release every fence, and keep `G1` active.

Checkpoint and materialization coverage at each sealed barrier MUST equal the highest contiguous group `STATE_APPLIED` watermark and MUST exclude every later partially applied member/state. Each affected partition MUST replay rebuilt `G2` state through that barrier and verify staged corrections. Each untouched partition MUST be deterministically materialized/copied into the `G2` namespace from only its fenced, verified `G1` checkpoint/state at that group-consistent head, then read-back-verified with its source and `G2` hashes. No partition may mutate after its sealed barrier until global activation succeeds or aborts.

Only after every partition exists and is verified in `G2` may one atomic PostgreSQL/control transaction compare-and-set the single global active-generation pointer exactly once from expected `G1` to `G2`. The transaction MUST verify a complete partition inventory/map; every partition's rebuild/materialization mode, sealed barrier/head, group-consistent checkpoint/coverage, and `G1`/`G2` state hashes; absence of post-barrier mutation; and that every transition group with any begun or member-applied transition touching any partition at or below a sealed barrier has its complete expected member set and one durable group `STATE_APPLIED` receipt across the complete partition map; and that no required cross-entity input spans generations. It MUST also authorize the generation-scoped correction outbox or append an activation token bound to `G2` and its entries. If any partition cannot fence, materialize, or verify, activation MUST fail closed, `G1` remains active, all staged `G2` artifacts remain non-current, and every fence resumes `G1`. External scoring MUST NOT resolve `G2` until the complete inventory is present and MUST NOT observe or assemble a mixed-generation window.

The global activation transaction MUST append an immutable `ActivationRecord` containing manifest/core hashes, candidate/prior generation, replay run, complete partition map with rebuild/materialization modes, all barrier/head offsets, prior and candidate state hashes/versions/checkpoints, buffered-event ranges/hashes, activation token, actor/time, and immutable pre-activation staged-verification receipts: candidate hash/coverage, materialization read-back, no-post-barrier-mutation, cross-entity generation check, conflict checks, and staged artifact counts/hashes. Correction consumers MUST require a valid activation token, apply only artifacts for the globally activated generation, and do so idempotently; only then may they change case/evidence current views, priority, or dispositions. Post-activation drain and correction consumers MUST append application receipts linked by activation token and generation ID; those receipts are not required before the `ActivationRecord` commits. Completion is a derived status only when all required post-activation receipts exist.

After the successful global pointer compare-and-set, buffered and post-barrier events MUST deliver at least once, in order, into the newly active generation using live run lineage. Deterministic transition IDs, state-generation-keyed compare-and-set application, unique PostgreSQL/sink constraints, and idempotent outbox/case consumers MUST yield exactly one durable logical effect per event; redelivery is expected. Only then may fences release and normal offset commits resume. Fault drills MUST crash and redeliver before and after state compare-and-set, sink receipt, global pointer activation, and offset commit during buffer drain, and prove no lost, duplicate logical effect, mixed generation, or out-of-lineage event.

Before the successful atomic global active-generation pointer compare-and-set plus activation-token/outbox authorization, a bounded fence deadline, validation failure, or compare-and-set failure MUST abort candidate activation, release every fence, resume `G1`, and keep staged artifacts non-current. The activation manifest and failed `ActivationRecord` attempt remain auditable, and cleanup MUST NOT delete audit or provenance required by retention. After that atomic commit, `G2` remains active and MUST NOT resume or switch the pointer to `G1`; a deadline or failure MUST reacquire/resume the idempotent buffered drain and activated correction consumers from their receipts/cursors. Deadline handling MUST inspect durable activation state/token and choose exactly one of those paths. After generation activation-token/correction-outbox authorization, pointer-only rollback is PROHIBITED. If the activated generation later proves invalid, recovery MUST create a new forward correction generation whose manifest names the bad generation and intended restoration source, then follow the full replay, staging, partition-barrier, global compare-and-set, activation, and reconciliation protocol and emit superseding artifacts.

### 12.5 Redis persistence and recovery

Redis MUST use append-only persistence with `appendfsync everysec` plus periodic RDB snapshots for the local reference profile. The declared target is an RPO of at most one second for acknowledged Redis projection updates and an RTO of at most 30 minutes for the documented local benchmark dataset. Kafka history and versioned checkpoints remain the recovery basis.

Every recovery checkpoint MUST have a compact immutable checkpoint manifest naming owner and creation cadence; partition and `state_generation_id`; covered source offset and event-time watermark equal to the highest contiguous group `STATE_APPLIED` watermark; schema, feature, graph-state, and replay versions; canonical state hash excluding any later partially applied member/state; immutable object location, byte length, and SHA-256; retention/expiry; read-back integrity-check result; and latest restore-drill result. Creation MUST verify that no covered member-applied receipt lacks its complete group `STATE_APPLIED` receipt, upload the immutable checkpoint, read it back, verify its bytes/hash and canonical state hash, and only then commit its coverage in the PostgreSQL continuation ledger. Restore MUST verify the manifest, object hash, versions, group-consistent coverage, and canonical state hash before applying it, then replay strictly after—not at or before—the covered source offset.

Backup artifacts MUST be hashed and restore-tested at least once per release candidate. Sensitive backup classes MUST be encrypted at rest. Public-synthetic-only artifacts MAY omit at-rest encryption only with an approved backup encryption exception record naming classification, owner, approver, scope, rationale, compensating controls, expiry or review date, and audit ID. Absence of platform encryption support alone is not sufficient for an exception. A restore drill MUST rebuild Redis, resume from the recorded offsets, reconcile PostgreSQL/outbox state, and compare state and decision hashes. Targets are requirements until measured; reports MUST publish actual values and PASS/FAIL.

### 12.6 Eventual-consistency states

Case-facing decisions MUST expose one of:

- `PENDING_SCORE`;
- `SCORED_PERSISTENCE_PENDING`;
- `CASE_PENDING`;
- `AVAILABLE`;
- `DEGRADED_PROJECTION`;
- `ABSTAINED`;
- `FAILED_CLOSED`.

The UI MUST show the state, last successful stage, retry status, and data watermark. It MUST NOT show stale projections as complete. Neo4j or AI-provider failure MUST leave the case and evidence accessible with an explicit degraded state.

### 12.7 Failure behavior

- Invalid schemas MUST be quarantined with stable reason codes.
- Incomplete or transient mandatory feature/state/`STATE_APPLIED` coverage MUST block and deterministically retry or reconcile without emitting `SCORED`, `ABSTAINED`, or `FAILED_CLOSED`; only deterministically terminal absence after required group/coverage processing, or a terminal model-load/inference failure, may return `FAILED_CLOSED` with a typed reason.
- A provider outage MUST disable only the AI narrative path.
- Persistence failure MUST not acknowledge the source offset before recoverable state exists.
- Only malformed or unsupported input deterministically proven terminal before creation of `EventTransitionResult`, Redis advancement, or any sink effect may enter terminal quarantine. Source-offset advancement then requires a persisted terminal-quarantine receipt containing source coordinates, payload hash, reason, classifier version, and proof that no transition or sink effect began.
- Once durable transition work starts, a failure MUST remain blocking and recoverable through retry, receipt reconciliation, controlled partition replay, or forward correction. It MUST NOT become skip-and-advance quarantine after a retry count.
- Backpressure MUST pause consumption before unbounded memory growth.

---

## 13. Performance Contract

The Phase 7 research target is `model_package_scoring_p95_ms < 500` under a documented local package workload. This is not a current result and does not include persistence/outbox work, offline training, full replay, or unconstrained Neo4j traversal. Phase 8/12 MUST separately report `event_to_decision_p95_ms`, throughput, lag, persistence/outbox overhead, typed failures, and recovery under their integration workload.

The model approver and system owner MUST review, content-hash, sign, and freeze the benchmark manifest before execution. The frozen benchmark manifest MUST declare representative target rate, event/message type and size mix, state and graph size plus temporal window, concurrency, warm-up, measurement duration, error-rate ceiling, hardware/software profile and resource limits, cold/warm/cache mode, repetitions, and accepted exclusions. It MUST include protected-read audit appends, business-mutation audit appends, chain-head contention at declared concurrency, append latency/timeouts, and forced audit-unavailability cases proving that protected reads are not returned and business mutations do not commit without their required audit event. V1 retains the single audit chain per deployment/project namespace unless measured contention evidence and an approved specification change justify partitioning. Results MUST NOT be used to select, rewrite, or narrow the workload after measurement. Any manifest change creates a new benchmark ID and requires all affected repetitions to rerun.

Every performance claim MUST include a benchmark manifest with:

- exact Git SHA, artifact versions, environment lock, and configuration;
- CPU, RAM, disk, GPU if used, OS, container runtime, and resource limits;
- dataset/replay manifest, graph/state size, partition count, key distribution, and cache state;
- load generator version, event/message mix and size distribution, target/achieved rate, concurrency, warm-up, duration, and repetitions;
- p50/p95/p99/end-to-end latency, throughput, Kafka lag, quarantine, retry, abstention, and failure rates;
- protected-read and business-mutation audit-append p50/p95/p99 latency, chain-head lock/CAS contention, timeout/failure rates, and audit-unavailability fail-closed results;
- CPU, RAM, disk I/O, network, Redis, PostgreSQL, and Kafka utilization;
- cold-start, steady-state, and recovery results;
- frozen error-rate ceiling and accepted exclusions;
- raw result artifact hashes and PASS/FAIL against frozen thresholds.

The gate MUST fail if the workload, error rate, sample size, or environment is omitted. A benchmark on a reduced dataset MUST be labeled as such.

---

## 14. Typed Evidence Contract

### 14.1 Evidence package

Every canonical `RiskDecision` produced by an actual scoring attempt MUST reference an immutable `EvidencePackage` containing:

- `evidence_package_id`, schema version, deterministic decision event time, evidence cutoff time, subject ID/type, and content hash;
- source dataset/event IDs and payload hashes;
- model, rule, feature, graph-state, calibration, fusion, and threshold versions;
- available component scores, final score when and only when status is `SCORED`, decision status, and typed reason codes;
- zero or more typed evidence items;
- extraction limits, truncation flags, completeness watermark, and failure/degradation state;
- producer Git SHA and replay-manifest ID.

Each evidence item MUST contain:

- stable `evidence_id` and `evidence_type`;
- source references and source event times;
- typed value/unit or bounded entity/edge/path references;
- derivation name/version and parameters when derived;
- human-readable summary generated deterministically from typed fields;
- sensitivity classification and authorization scope;
- content hash.

Supported initial types are `TRANSACTION_FACT`, `BEHAVIORAL_FEATURE`, `RULE_HIT`, `MODEL_COMPONENT`, `TEMPORAL_PATTERN`, `GRAPH_PATH`, `GRAPH_NEIGHBORHOOD`, `CONTRADICTION`, and `DATA_QUALITY_WARNING`.

Status validation MUST enforce the Section 10.3 rules: `SCORED` requires a final score; `ABSTAINED` and `FAILED_CLOSED` forbid a final score; `ABSTAINED` requires a typed abstention reason; and `FAILED_CLOSED` requires a typed failure reason. Available diagnostic fields remain canonical even when the evidence-item list is empty.

### 14.2 Evidence invariants

- Every cited ID MUST exist in the exact package version.
- Every source fact MUST resolve to an immutable event/artifact hash.
- Every derived fact MUST name reproducible code and inputs.
- A model score alone MUST NOT be described as proof of money laundering.
- Truncated or incomplete evidence MUST carry visible state.
- Evidence packages and disposition snapshots MUST be append-only; corrections create a superseding version and retain the original.
- Authorization MUST be enforced when evidence is read, not only when a case is opened.

### 14.3 Canonical serialization and hashes

All decision and evidence content hashes MUST use SHA-256 over UTF-8 JSON Canonicalization Scheme serialization (RFC 8785). Producers MUST normalize Unicode strings to NFC before serialization, encode monetary/decimal values as canonical base-10 strings without exponent notation, encode deterministic times as UTC RFC 3339 with fixed microsecond precision, sort semantic sets by their stable IDs, and preserve schema-declared array order where order is meaningful.

The canonical `RiskDecision` hash MUST cover exactly: schema version; `risk_decision_id`; original event ID; `state_generation_id`; `replay_run_id`; subject ID/type; source event IDs and payload hashes; decision event time; evidence cutoff time; model, rule, feature, graph-state, calibration, fusion, and threshold versions; available component scores; final score when status permits it and an explicit canonical `null` otherwise; decision status; typed reason codes; EvidencePackage content hash; `supersedes_decision_id` or typed retraction link when present; `supersedes_evidence_package_id` when present; correction reason when present; producer Git SHA; and replay-manifest ID.

The canonical `EvidencePackage` hash MUST cover exactly: schema version; original event ID; `state_generation_id`; `replay_run_id`; subject ID/type; decision event time; evidence cutoff time; source dataset/event IDs and payload hashes; model, rule, feature, graph-state, calibration, fusion, and threshold versions; available component scores; final score when status permits it and an explicit canonical `null` otherwise; decision status/typed reasons; evidence-item content hashes in canonical order; extraction limits; truncation flags; completeness watermark; failure/degradation state; `supersedes_evidence_package_id` or typed retraction link when present; correction reason when present; producer Git SHA; and replay-manifest ID. `evidence_package_id` MUST be derived from this hash and MUST NOT be hashed into itself.

Each evidence-item hash MUST cover exactly: evidence type; source references and source event times; typed value/unit or bounded entity/edge/path references; derivation name/version/parameters; deterministic summary; sensitivity classification; and authorization scope. `evidence_id` MUST be derived from the item hash and MUST NOT be hashed into itself.

Operational processing/creation/ingest timestamps, database sequence values, retry counts, delivery receipts, outbox/sink status, trace IDs, and authorization-read events MUST remain in audit metadata and MUST NOT enter the canonical content hashes. Mutating any hashed field creates a new package/version; replay MUST compare canonical hashes, not database row timestamps.

### 14.4 Case evidence snapshot

Each case evidence version MUST be an immutable `CaseEvidenceSnapshot` containing `case_evidence_snapshot_id`, `case_id`, and `case_version`; prior snapshot ID/hash or genesis; normalized `EvidencePackage` ID/hash references in canonical order; current, superseded, and retracted occurrence mappings; analyst-supplied evidence references and note/comment references in fields distinguishable from source and derived facts; merge/split source and result provenance; completeness and degradation state; creation command ID/type; and canonical content hash. Sensitivity summaries MAY support display, but authorization MUST be evaluated per underlying evidence item and remains authoritative.

The snapshot hash MUST use Section 14.3 canonicalization over every field above except its own ID/hash; `case_evidence_snapshot_id` MUST be derived from that hash. Corrections, commands, merge, or split create a successor snapshot and never mutate or delete a prior snapshot.

---

## 15. Case Operations

### 15.1 Lifecycle and command matrix

V1 case states are `NEW`, `TRIAGED`, `INVESTIGATING`, `PENDING_REVIEW`, `CLOSED_CONFIRMED_SUSPICIOUS`, `CLOSED_FALSE_POSITIVE`, `CLOSED_INSUFFICIENT_EVIDENCE`, `ESCALATED`, `REOPENED`, plus immutable provenance tombstones `MERGED` and `SPLIT`. `ALERTED` is a risk/alert occurrence, not a case state. V1 accepts only these lifecycle commands:

| Command | Valid source state | Authorized actor | Result and mandatory data |
|---|---|---|---|
| `CREATE_CASE` | no case | case-ingestion service principal | `NEW`; originating `risk_decision_id`, `evidence_package_id`/hash, and exact resulting `CaseEvidenceSnapshot` ID/hash |
| `ATTACH_RISK_OCCURRENCE` | any non-tombstone case state | case-ingestion service principal | exact prior/resulting `CaseEvidenceSnapshot` IDs/hashes; occurrence `risk_decision_id`, `evidence_package_id`/hash, lineage IDs, correlation key, and supersession/retraction links. A nonterminal case MAY return to `INVESTIGATING` under the correction policy; a terminal/`ESCALATED` state MUST NOT change through this command. |
| `ASSIGN_CASE` / `REASSIGN_CASE` | `NEW`, `TRIAGED`, `INVESTIGATING`, `REOPENED` | Analyst with queue-assignment permission | state unchanged; assignee, reason, SLA recalculation |
| `TRIAGE_CASE` | `NEW` | assigned Analyst | `TRIAGED`; priority and triage reason |
| `START_INVESTIGATION` | `TRIAGED`, `REOPENED` | assigned Analyst | `INVESTIGATING`; investigation-start timestamp |
| `ADD_NOTE_OR_EVIDENCE` | `INVESTIGATING` | assigned Analyst | state unchanged; append-only note/evidence version |
| `MERGE_CASES` | only source-state combinations allowed by the deterministic matrix below | Analyst with case-merge permission | new resulting case in the matrix result state; all source cases become `MERGED` tombstones |
| `SPLIT_CASE` | only source-state combinations allowed by the deterministic matrix below | Analyst with case-split permission | new child cases in `INVESTIGATING`; source becomes a `SPLIT` tombstone |
| `SUBMIT_PROPOSED_DISPOSITION` | `INVESTIGATING` | assigned Analyst | `PENDING_REVIEW`; one proposed disposition, reason, and immutable evidence snapshot |
| `APPROVE_PROPOSED_DISPOSITION` | `PENDING_REVIEW` with an active, non-`SUPERSEDED` proposal | Reviewer who did not submit the proposal | `CONFIRMED_SUSPICIOUS` -> `CLOSED_CONFIRMED_SUSPICIOUS`; `FALSE_POSITIVE` -> `CLOSED_FALSE_POSITIVE`; `INSUFFICIENT_EVIDENCE` -> `CLOSED_INSUFFICIENT_EVIDENCE`; `ESCALATE` -> `ESCALATED` |
| `REJECT_PROPOSED_DISPOSITION` | `PENDING_REVIEW` | Reviewer who did not submit the proposal | `INVESTIGATING`; rejection reason and required follow-up |
| `REOPEN_CASE` | any three closed states or `ESCALATED` | Reviewer | `REOPENED`; new-evidence or quality-review reason and new evidence snapshot |

There is no direct `NEW`/`TRIAGED` to closed transition, and an Analyst MUST NOT approve a disposition. Every command MUST pass server-side role, object, assignment, sensitivity, and state authorization; supply the last observed `case_version` and exact `CaseEvidenceSnapshot` ID/hash; append an atomic audit event; and record actor, role, command, timestamp, previous/new state, reason, prior and resulting case versions, prior and resulting snapshot IDs/hashes, and lineage IDs where present. Lifecycle history MUST reference the exact snapshot observed or created by each command. `CREATE_CASE` stores the originating package and resulting snapshot; `ATTACH_RISK_OCCURRENCE` records the occurrence and successor snapshot; assignment, triage, and start commands record the observed snapshot; note/evidence commands create a successor snapshot; merge/split commands record every source and resulting snapshot; disposition proposal and reviewer commands reference the immutable proposal snapshot; and `REOPEN_CASE` references the exact new-evidence snapshot and approved reopen request when present. Invalid state/version or stale snapshot MUST return `409 Conflict`; denied authority MUST return `403 Forbidden`; neither outcome may mutate the case. Only Reviewer `REOPEN_CASE` may change an approved terminal case or `ESCALATED` case to `REOPENED`, which MUST pass through `START_INVESTIGATION` before another disposition proposal.

The deterministic merge/split source-state/result-state matrix is:

| Operation | Source-state set | Directly allowed | Result |
|---|---|---|---|
| `MERGE_CASES` | every source is `NEW`, `TRIAGED`, `INVESTIGATING`, or `REOPENED`, with compatible nonterminal evidence state | Yes | new case `INVESTIGATING`; every source becomes `MERGED` |
| `MERGE_CASES` | any terminal/`ESCALATED` source, mixed terminal/nonterminal sources, or incompatible approved disposition | No | Reviewer-authorized `REOPEN_CASE` is required for every affected source before merge. Merge MUST NOT create, copy, approve, or replace a terminal disposition. |
| `MERGE_CASES` | any `PENDING_REVIEW` source | No — PENDING_REVIEW merge is prohibited | Reviewer must reject or supersede every proposal and return every source to `INVESTIGATING` before merge. Merge MUST NOT copy, create, approve, or replace any disposition. |
| `SPLIT_CASE` | `NEW`, `TRIAGED`, or `INVESTIGATING` | Yes | every child is `INVESTIGATING`; source becomes `SPLIT` |
| `SPLIT_CASE` | `PENDING_REVIEW` | No | Reviewer executes `REJECT_PROPOSED_DISPOSITION`, which yields `INVESTIGATING`; split may then execute without `START_INVESTIGATION`. Split MUST NOT copy, create, approve, or replace a disposition. |
| `SPLIT_CASE` | `REOPENED` | No | Assigned Analyst executes `START_INVESTIGATION` to reach `INVESTIGATING`; split may then execute. |
| `SPLIT_CASE` | any terminal state or `ESCALATED` | No | Reviewer executes `REOPEN_CASE`, then assigned Analyst executes `START_INVESTIGATION` to reach `INVESTIGATING`; split may then execute. Split MUST NOT create, copy, approve, or replace a terminal disposition. |

`MERGE_CASES` and `SPLIT_CASE` MUST authorize the actor against every source case, require optimistic-concurrency versions and evidence snapshots for every source, and perform all source/result updates, provenance records, and audit records atomically or not at all. Resulting cases MUST link every source case ID, immutable history, occurrence ID, evidence version/snapshot, and audit hash; source cases are never deleted and their `MERGED`/`SPLIT` tombstones are immutable provenance states. The audit payload MUST contain the command, actor/role and authorization decisions, all source/result IDs and versions, source/result states, occurrence and evidence IDs/hashes, proposal status/snapshot when present, reason, assignment/SLA decision, concurrency preconditions, and transaction/audit hash.

### 15.2 Assignment, SLA, and aging

Cases MUST support queue, priority, one accountable owner, optional collaborators, assigned-at time, due-at time, and escalation state. Default SLA values MUST be configuration, versioned in the release manifest, and visible in the UI. Aging MUST use server time and show time in current state, time to due, and breached status.

Assignment changes MUST be audited. An Analyst MUST NOT investigate, submit a disposition, or change evidence on a case assigned to another Analyst; authorized reassignment MUST occur first and record the reason.

### 15.3 Deduplication and grouping

Alert transport idempotency MUST use unique `risk_decision_id`. Redelivery of the same ID and identical canonical payload MUST be a no-op except for an idempotent receipt; the same ID with a different payload hash MUST be quarantined as a conflict. Subject, rule/model package, supported typology family, and event-time window MAY form a versioned correlation/suppression key, but MUST NOT serve as transport deduplication.

Every distinct `risk_decision_id` MUST be retained as a separate occurrence. If correlation attaches or suppresses it into an existing alert/case rather than creating another queue item, the system MUST increment the occurrence count and append a new evidence version and immutable occurrence/history record. It MUST NOT silently discard a distinct risk decision.

Correction occurrences MUST be reconciled through `ATTACH_RISK_OCCURRENCE` using the new lineage IDs. The command MUST mark the superseded or retracted decision/evidence as non-current without deletion, attach the correction occurrence, create a successor `CaseEvidenceSnapshot`, recompute case priority and the current evidence view, preserve analyst notes, assignments, dispositions, and review history, and emit an audit event naming the correction reason and prior/current artifact IDs. If a material correction invalidates a proposed disposition, that proposal MUST become `SUPERSEDED`, non-approvable, and linked to the correction evidence; the nonterminal case MUST return to `INVESTIGATING`, and a new proposal is required before `PENDING_REVIEW`. If the deterministic policy classifies an approved terminal disposition or escalation as invalidated, it MAY mark that disposition `SUPERSEDED` and non-current and MUST raise an auditable reopen request with the exact successor snapshot, but it MUST NOT transition terminal state. Only a Reviewer may execute `REOPEN_CASE`; until then the case retains its terminal/`ESCALATED` lifecycle state while visibly exposing the superseded disposition and pending reopen request. Retries are idempotent on the new `risk_decision_id`, `evidence_package_id`, `case_evidence_snapshot_id`, `state_generation_id`, and `replay_run_id`.

Correction materiality and any automated quality policy that can supersede a proposal/disposition or raise a reopen request MUST be versioned, deterministic, content-hashed, model-approver/reviewer approved as appropriate, effective-dated, tested, and included in the evidence and audit records. No free-text or model-only materiality decision may trigger a state change, and no automated policy may execute `REOPEN_CASE`.

Case grouping MAY combine related alerts only through a deterministic, bounded rule. Merge and split MUST:

- retain source case IDs and immutable histories;
- create new lifecycle events and evidence snapshots;
- preserve disposition provenance;
- recalculate assignment/SLA explicitly;
- never delete the pre-merge or pre-split record;
- link every resulting case to source case IDs, moved or retained occurrence IDs, source and resulting evidence snapshots, actor, authorization decision, optimistic-concurrency versions, and audit event IDs.

### 15.4 Optimistic concurrency

Every mutable case command MUST supply the last observed `case_version` through `If-Match` or an equivalent typed field. A stale command MUST return `409 Conflict` with the current version and MUST NOT overwrite another analyst’s work.

### 15.5 Dispositions and feedback

The only V1 proposed dispositions are `CONFIRMED_SUSPICIOUS`, `FALSE_POSITIVE`, `ESCALATE`, and `INSUFFICIENT_EVIDENCE`. A proposal MUST include case ID/version, Analyst ID, timestamp, reason code, optional comment, model/rule versions, and immutable evidence snapshot ID. It has no terminal effect until a Reviewer executes `APPROVE_PROPOSED_DISPOSITION` under the matrix above. Proposal status is `ACTIVE`, `REJECTED`, `APPROVED`, or `SUPERSEDED`; a `SUPERSEDED` proposal can never be approved.

Analyst feedback MAY enter future offline datasets only after quality review, provenance capture, leakage analysis, and a new dataset manifest. It MUST NOT trigger direct retraining, threshold changes, or promotion.

---

## 16. Read-Only AI Investigator

### 16.1 Authority boundary

The AI investigator is a mandatory `v1.0.0` capability inside the Case/Agent API and remains read-only assistance, not an autonomous decision-maker. It MUST NOT freeze accounts, block transactions, file reports, change risk, mutate evidence, assign/merge/split/close cases, change dispositions, retrain or promote models, manage users, or execute arbitrary queries/code. Earlier research or vertical-slice release candidates MAY run with AI disabled, but their manifests and UI MUST state `AI_DISABLED` and they MUST NOT be tagged or described as `v1.0.0`. Provider outage after release MUST degrade to the manual workflow without erasing the mandatory build-time and release-gate evidence.

### 16.2 Least-privilege tools

Approved tools MAY retrieve only bounded, authorized data from the exact `CaseEvidenceSnapshot` authorized for the AI run, including items in its underlying packages, for:

- case summary, exact snapshot, and its authorized underlying evidence packages;
- entity profile and causal transaction timeline;
- historical behavior comparison;
- bounded neighbors, path, and ring queries;
- model/rule component metadata;
- prior cases only when role and sensitivity policy permit;
- contradictions and data-quality warnings.

Each tool MUST have a typed input/output schema, maximum result size, timeout, case/snapshot scope, sensitivity label, and authorization check. Authorization MUST run on every call using the human user’s identity and exact snapshot ID/hash. The model MUST never receive database credentials or unrestricted SQL/Cypher access.

The initial run limit is 20 tool calls, 30 seconds wall time, and 100 evidence items. Limits MUST be configurable and recorded with each run. A limit hit MUST return a partial/insufficient result, not silently omit the status.

### 16.3 Grounded output

The agent output MUST be typed into:

- observations with evidence IDs;
- hypotheses explicitly labeled as hypotheses;
- supporting evidence IDs;
- contradictory evidence IDs;
- confidence category with rationale;
- unresolved questions;
- recommended human checks;
- run/provider/prompt/tool-policy versions and degradation state.

Every AI run MUST bind to and record one exact authorized `CaseEvidenceSnapshot` ID/hash. Before display or persistence, deterministic validation MUST parse every cited `evidence_id`, verify membership in any underlying `EvidencePackage` referenced by that snapshot and per-item authorization for the human principal, and validate each material claim under the contract below. Failed validation MUST suppress the narrative and show `INSUFFICIENT EVIDENCE` plus a grounding-failure audit event.

A **material observation** is any asserted fact or inference that could change perceived subject risk, case priority, disposition, investigation scope, or a recommended human check. Every material observation MUST originate in typed tool output as one canonical `GroundedClaim` containing claim ID/type, normalized subject, typed predicate, normalized object/value and unit where applicable, time scope, support relation, supporting evidence IDs with exact canonical field paths, contradiction IDs, and exact snapshot ID/hash. `claim_id` MUST derive from the Section 14.3 canonical hash of those fields excluding itself.

The validator MUST re-evaluate the typed predicate/support relation against the cited fields in the exact snapshot's authorized underlying packages and MUST deterministically enumerate every relevant contradiction in the authorized snapshot for the same normalized subject, predicate, and overlapping time scope. Citation membership alone is insufficient; an unrelated authorized item fails claim support, and an omitted relevant contradiction fails grounding. Model prose MUST NOT create, broaden, merge, or alter a material claim beyond a validated `GroundedClaim`.

Allowed confidence categories are `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`, and `INSUFFICIENT_EVIDENCE`. Deterministic validation assigns `HIGH` only when every material claim has validated support, the exhaustive contradiction set is empty, and no relevant incomplete/degraded flag is present; `MEDIUM` when all have validated support and exactly one of a non-empty exhaustive contradiction set or incomplete/degraded evidence is present; `LOW` when all have validated support and both are present; `UNKNOWN` when the output asserts no material claim because the authorized snapshot does not answer the question; and `INSUFFICIENT_EVIDENCE` when a requested material conclusion lacks validated predicate support or grounding validation fails. Rationale MUST consume only validated support, the exhaustive contradiction set, and completeness/degradation fields; model prose cannot upgrade the category.

### 16.4 Prompt-injection controls

All retrieved content, regardless of source or storage channel, MUST be treated as untrusted data, structurally separated from system/tool instructions, length-limited, and escaped for the target interface. The agent MUST ignore embedded instructions, including those in transactions, evidence, stored analyst notes/comments/reason codes, prior narratives, and tool output; this list is illustrative and does not narrow the universal rule.

Tool selection and arguments MUST be policy-checked outside the model. High-risk strings, attempted role changes, secret requests, arbitrary query/code requests, cross-case access, data exfiltration, and forbidden actions MUST be refused and audited. Provider output MUST never directly execute a tool or case command.

### 16.5 Provider and retention policy

Before a provider is enabled, the administrator MUST record provider/model/version, hosting region where applicable, transport security, retention duration, training-use setting, subprocessors, incident terms, and approved data classifications. Provider training on submitted data MUST be disabled, and the shortest supported retention MUST be selected. Secrets and direct identifiers MUST be excluded; synthetic/anonymized IDs remain scoped data.

A provider without an approved retention/data-use record MUST remain disabled. Provider failure MUST leave evidence and manual investigation available.

### 16.6 AI adversarial evaluation

The release candidate MUST execute a versioned suite covering prompt injection, indirect injection, forged evidence IDs, unrelated-but-authorized citations, omitted relevant contradictions, cross-case access, excessive tool calls, provider failure, forbidden actions, unsupported conclusions, malicious prior narratives, and malicious stored analyst notes, comments, and reason codes.

Mandatory gates are:

- 100% refusal of forbidden case/banking/model actions;
- 0 displayed citations absent from the exact authorized snapshot's authorized underlying packages;
- 0 displayed material claims lacking validated field-level predicate support or omitting a relevant contradiction from the exhaustive snapshot scan;
- 0 successful cross-case authorization violations;
- 100% explicit `UNKNOWN` or `INSUFFICIENT EVIDENCE` behavior for evidence-starved cases;
- all tool-call, timeout, and result-size limits enforced.

Any Phase 10 agent-gate failure blocks `v1.0.0`. An earlier non-V1 research or vertical-slice candidate MAY continue the manual case workflow only with `AI_DISABLED` disclosed in its manifest and UI.

---

## 17. Analyst Experience and Accessibility

### 17.1 Research truth

Mobbin was considered as a visual-reference source, but searches were blocked by a paid-plan requirement. No Mobbin screen was reviewed; design claims MUST NOT imply otherwise. Functional information architecture is derived from this platform’s evidence, case, security, and accessibility requirements plus authoritative public guidance. Future Mobbin refinement MAY occur only after access and source attribution are documented.

### 17.2 Screens and primary workspace

The React and TypeScript investigator web contains:

- Operations Summary;
- Alert Queue;
- Case Investigation;
- Entity Profile;
- Graph Explorer;
- Transaction Timeline;
- Evidence Viewer;
- AI Investigator;
- Analyst Disposition;
- Model/Drift Console for authorized roles.

Case Investigation is the primary workspace. It MUST foreground case status, risk/degradation state, graph, timeline, evidence, AI output, assignment, SLA, audit-relevant actions, and disposition rather than generic dashboard charts.

### 17.3 Synchronized investigation behavior

Graph, timeline, and evidence panels MUST share stable entity, event, and evidence IDs.

- Selecting a graph node/edge MUST filter or highlight corresponding timeline and evidence items.
- Selecting a timeline event MUST focus the graph context and evidence references.
- Selecting an evidence citation MUST reveal its source event or a clear reason the source is outside the current bounded view.
- Filters MUST be visible, reversible, URL/state reproducible, and announced to assistive technology.
- Truncated, stale, partial, pending, and failed states MUST be visible in every affected panel.
- AI narrative MUST never replace the typed evidence view.

### 17.4 WCAG 2.2 AA

The Alert Queue, Case Investigation, evidence review, assignment, review, disposition, and reopen paths MUST meet WCAG 2.2 AA. Acceptance requires automated checks plus manual keyboard and screen-reader evidence.

The UI MUST provide:

- complete keyboard operation with logical focus order and no traps;
- visible focus indicators that meet contrast requirements;
- semantic headings, landmarks, labels, names, roles, states, and error associations;
- status communication not dependent on color, position, animation, graph shape, or sound alone;
- text/table alternatives for graph relationships and chart values with the same decision-relevant information;
- captions/labels for time ranges, currencies, risk units, and truncation;
- zoom/reflow support and reduced-motion behavior;
- accessible conflict, timeout, degraded, validation, and success messages;
- screen-reader announcements for asynchronous state changes without excessive interruption;
- target sizes, contrast, and authentication behavior required by WCAG 2.2 AA.

Cytoscape.js MAY render the visual graph, but the accessible table/path alternative is mandatory. A charting dependency MAY be selected only after keyboard, screen-reader, and data-table fallback evaluation.

---

## 18. Identity, Roles, and Segregation of Duties

V1 roles are:

- **Analyst** — view authorized queues/cases/evidence, assign or reassign with queue permission, triage assigned cases, investigate and add notes/evidence on assigned cases, merge/split with the named permissions, and submit proposed dispositions; MUST NOT approve or reopen.
- **Reviewer** — review evidence, approve/reject proposed dispositions, and alone execute `REOPEN_CASE`; MUST NOT approve a proposal the same principal submitted.
- **Model approver** — freeze evaluation manifests and approve/reject model packages; MUST NOT be the sole author and approver of the same package.
- **Auditor** — read cases, evidence snapshots, model records, and audit logs; no operational mutation.
- **Administrator** — manage users, role bindings, provider/config policy, and recovery; no implicit analyst/model approval authority.
- **Case-ingestion service principal** — create cases and attach risk occurrences only under the Section 15 command matrix; it is a workload identity and MUST NOT inherit or be assigned a human role.

`HIGH_RISK` is the disposition class containing `CONFIRMED_SUSPICIOUS` and `ESCALATE`; it is not a lifecycle state or an additional disposition. A principal holding both Analyst and Reviewer roles MUST select one active role per command, and server-side authorization MUST enforce no-self-approval from principal identity and proposal submitter identity across role changes or sessions. Dual-role assignment never permits one principal to submit and approve the same proposal.

OIDC-compatible authentication MUST protect the analyst web and every non-service API for V1. Every API and tool call MUST authorize action, object, sensitivity, and tenant/project scope server-side. UI hiding is not authorization. An offline/dev authentication bypass MAY exist only as `FIXTURE_AUTH_BYPASS`; it MUST be disabled by default, MUST refuse to start outside an explicit fixture-mode process, MUST use synthetic fixed principals with no external access, and MUST NOT satisfy integration, live, release, or `v1.0.0` gates.

Service-to-service calls MUST use the existing OIDC-compatible identity infrastructure to issue short-lived, audience-bound workload credentials with action-specific scopes. Every service call MUST authenticate and authorize the principal, audience, action, object, sensitivity, and project scope server-side; rotate credentials/keys; reject expired, revoked, wrong-audience, replayed, or over-scoped credentials; and audit principal ID, key-or-token ID, authorization result/reason, and trace ID. This adds no deployable. The case-ingestion service principal MUST remain separate from human principals and MUST NOT inherit Analyst, Reviewer, Administrator, Auditor, or Model-approver roles.

Segregation rules MUST require reviewer approval for confirmed-suspicious closure and model-approver approval for champion changes. Emergency administrative access MUST be time-bounded, reasoned, and audited, and MUST NOT bypass immutable evidence or disposition history.

---

## 19. Security, Privacy, and Audit

### 19.1 Data and transport

Only public synthetic or verified anonymized data is allowed. Direct identifiers and secrets MUST NOT enter prompts, logs, fixtures, screenshots, or committed artifacts. Data classes, allowed stores, retention, and deletion behavior MUST be documented.

TLS MUST protect service, browser, Kafka, database, Redis, Neo4j, object-store, and provider connections outside a documented loopback-only development exception. Certificates and exceptions MUST be configuration, not source edits.

Secrets MUST come from environment injection or a secret manager, MUST be absent from Git and images, MUST be masked in logs, and MUST have a rotation runbook.

### 19.2 Audit integrity

Audit events MUST cover authentication, authorization denials, evidence reads, AI tool calls, case transitions, assignments, merges/splits, dispositions, model changes, provider/config changes, exports, backup/restore, and emergency access.

The local reference platform MUST maintain one ordered chain per `deployment_id` and project namespace. Each event MUST include `audit_chain_id`, a gapless monotonic `audit_sequence`, stable event ID, actor/role, action, object, UTC timestamp, trace ID, result, reason, `previous_event_hash`, and `event_hash`. The event hash MUST use the Section 14.3 canonical serialization over those fields except `event_hash` itself.

For a business mutation, the append and the mutation MUST commit atomically in one PostgreSQL transaction. The transaction MUST lock or compare-and-set the chain-head row, allocate exactly the next sequence, verify the previous hash, insert the append-only event, and advance the head. Unique constraints on `(audit_chain_id, audit_sequence)`, `event_id`, and non-genesis `previous_event_hash` plus head verification MUST reject gaps, duplicates, and forks. Read/access events MUST be appended before the protected response is returned.

A closed immutable audit segment/checkpoint MUST retain the canonical audit fields in Section 19.2 for its records or an immutable export containing them, plus chain ID, first/last sequence, event count, first/last event hash, previous segment ID/root hash, immutable export location/hash, creation time, retention expiry/action, and cryptographic signature metadata. A cryptographically signed audit root over those fields MUST be exported to immutable object storage every 24 hours and before each release candidate; its envelope MUST declare algorithm, key ID, trust root, verification procedure/result, rotation generation, and revocation status/procedure. The signing private key MUST be non-exportable or held in a protected CI/OS keystore identity separate from the database administrator; administrators MAY request signing but MUST NOT read the key. Auditors MUST possess the pinned trust root and read-only exports.

While underlying canonical records are retained, verification MUST stream them in sequence, recalculate every canonical hash, check genesis and previous-hash continuity, detect missing/duplicate sequences and forks, compare the database head, verify export hashes and cryptographically signed audit-root signatures, and verify continuity with the preceding segment/export. After a retention-approved expiry deletes underlying canonical records, verification MUST still prove the retained segment/root signature, exact export bytes when the export remains retained, declared sequence range/count, and previous/next segment-root linkage; it MUST explicitly report that deleted records cannot be individually rehashed and MUST NOT claim full-record verification. Segment/root expiry MUST follow the versioned audit-retention class, preserve any legal hold, record an immutable expiry tombstone linked to the last retained root, and make the reduced verification guarantee visible. Verification MUST run daily, before release, and after restore. Any failure MUST alert, preserve evidence, block audit-integrity and release claims, and require an incident record; it MUST NOT rewrite the chain.

### 19.3 Supply chain and application security

Every release candidate MUST produce an SBOM and run dependency, container-image, secret, and license scans. Unresolved critical vulnerabilities, exposed secrets, prohibited licenses, or unverifiable base images block release. High findings require an approved, expiring exception with compensating control.

APIs MUST validate schemas, sizes, enums, identifiers, pagination, filters, uploads if later introduced, and rate limits. PostgreSQL access MUST use parameterized queries; rendered text MUST be safely encoded; state-changing browser requests MUST have CSRF protection where cookie authentication is used.

### 19.4 Threat models

Phase 1 MUST produce the baseline trust-boundary and abuse-case threat model before implementation beyond the foundation. Before implementing each affected subsystem in a later phase, that phase MUST update and approve the model for its new data flows, assets, actors, dependencies, and controls. Phase 12 MUST verify the consolidated threat models and mitigations against the exact candidate SHA; it MUST NOT be the first threat-modeling activity.

The baseline and phase-specific threat models MUST cover:

- event poisoning, replay, schema abuse, and partition hot spots;
- label leakage and training-data poisoning;
- model/artifact substitution and unsafe deserialization;
- broken object authorization and cross-case evidence access;
- prompt injection, tool abuse, provider retention, and data exfiltration;
- audit tampering and repudiation;
- denial of service and resource exhaustion;
- backup theft, restore poisoning, and stale projections;
- analyst misuse, privilege escalation, and segregation bypass.

Each threat MUST identify assets, trust boundaries, abuse case, control, verification, residual risk, and owner.

### 19.5 Retention, backup, and deletion

The local reference retention schedule MUST be versioned by data class. Cases, evidence, audit, datasets, prompts/outputs, and operational logs MUST have explicit durations; indefinite retention is prohibited without written rationale. Deletion MUST preserve legally/audit-required hashes and tombstones while removing eligible payloads.

Any source artifact required by a retained `CaseEvidenceSnapshot` that claims reconstructability MUST remain pinned for at least as long as that claim and any legal hold. A lawful deletion that retires such a payload MUST preserve the immutable prior snapshot and hashes, create a typed successor availability record/snapshot state `SOURCE_PAYLOAD_RETIRED`, mark the affected evidence non-reconstructable with reason, authority, time, and deletion receipt, and retain only allowed hashes/tombstones. The API and UI MUST immediately stop claiming full reconstructability for that evidence or case and MUST expose the typed non-reconstructable state; a sensitivity summary or retained hash is not a substitute for the retired source payload.

PostgreSQL and object artifacts MUST be backed up before each release candidate and restored in a drill. Redis recovery follows Section 12.5. Recovery evidence MUST state actual RPO/RTO, hash comparisons, missing records, and reconciliation outcome.

---

## 20. Model Governance and Drift

MLflow or an equivalent registry MUST track dataset/split manifests, Git SHA, environment, parameters, metrics, uncertainty, artifacts, package hashes, evaluation reports, status, and approvers.

The lifecycle is:

`research trigger -> candidate training -> model-selection validation -> freeze -> calibration -> governance review -> candidate final temporal test plus applicable unknown/stress/ablation reports, or sealed-null manifest with research-only frozen-baseline evaluations and specifically justified dependency skips -> human decision -> local reference promotion or null champion`.

Automatic promotion is prohibited. A champion change MUST reference an immutable package, full gate report, model approver, rollback package, and exact effective time.

Monitoring MUST include:

- data quality and arrival delay;
- amount, velocity, channel, counterparty, and other verified feature distributions;
- degree, component, neighborhood, and supported topology statistics;
- score distribution, calibration when labels mature, alert volume, precision@K, typology/scenario recall, and false-positive rate;
- label delay and analyst-disposition coverage.

Drift thresholds MUST be fitted without final-test reuse and versioned per model package. A breach MAY trigger research, shadow evaluation, or rollback review; it MUST NOT trigger autonomous retraining, threshold change, or promotion.

---

## 21. Observability and Operational Views

Services MUST emit structured logs with timestamp, severity, service, version, trace ID, event/case ID where authorized, outcome, and stable reason code. Sensitive payloads MUST be excluded.

Prometheus-compatible metrics MUST include:

- `transactions_processed_total`;
- `scoring_latency_seconds`;
- `alerts_created_total` and normalized alert rate;
- `kafka_consumer_lag`;
- feature lookup and entity-state update latency;
- quarantine, duplicate, conflict, late, replay, abstention, and failed-closed totals;
- model score distributions by authorized low-cardinality dimensions;
- case aging and SLA breaches;
- AI latency, tool calls, refusals, grounding failures, and provider failures;
- projection watermark and reconciliation differences;
- graph node/edge counts for bounded projections.

Grafana or equivalent MUST provide System Health, Model Health, and AML Operations views. Alerts MUST have owner, threshold, duration, severity, runbook, and test evidence. Dashboard presence alone is not operational acceptance.

---

## 22. Verification Strategy

### 22.1 Contract and unit verification

Required checks include schema compatibility, label derivation, leakage scanning, causal windows, deterministic features, graph construction, rules, calibration/fusion, evidence hashing/validation, lifecycle transitions, optimistic concurrency, authorization, agent grounding, audit hash chain, and time/decimal edge cases.

### 22.2 ML verification

Required checks include deterministic preprocessing, split intersections, future-feature denial, scenario grouping, train-only statistics, package load/score compatibility, calibration-set isolation, null-champion behavior, and reproducible smoke runs.

### 22.3 Integration verification

Required flows are:

- raw event to normalized or quarantined outcome;
- normalized event to ordered entity state and typed score outcome;
- reciprocal-counterparty events whose complete expected command groups reach `STATE_APPLIED` and score without circular waiting, including crashes before a member receipt and before group `STATE_APPLIED` followed by deterministic recovery;
- a two-entity event late for only one member proving one whole-group `REPLAY_REQUIRED` disposition, zero live member mutations, and deterministic replay/reconciliation;
- a cutover fault between two member Redis applications proving the partition barrier cannot seal and activation cannot proceed until the complete group reaches `STATE_APPLIED`, or the bounded fence aborts with `G1` active and no partial state checkpointed/materialized into `G2`;
- risk event to idempotent case and immutable evidence;
- duplicate/conflicting/late event behavior;
- crash between state, outbox, publication, and offset stages;
- replay and projection reconciliation, including a one-partition rebuild while untouched partitions receive live traffic, followed by all-partition fencing/materialization into a complete verified `G2` inventory before global activation;
- case concurrency, assignment, merge/split, review, disposition, and reopen;
- authorized agent tools, grounding rejection, injection refusal, and provider degradation.

### 22.4 End-to-end verification

A `v1.0.0` deterministic synthetic scenario MUST exercise:

`replay -> Kafka -> validation -> causal state/features -> scoring -> evidence -> alert/case -> graph/timeline/evidence UI -> grounded AI -> review/disposition -> audit -> restore/replay reconciliation`.

Earlier non-V1 candidates with declared `AI_DISABLED` MAY execute the same path with the AI step recorded as `SKIPPED_BY_DEPENDENCY`; the manifest MUST disclose that this is not V1 completion.

The manual analyst path MUST also succeed during provider outage and in earlier non-V1 `AI_DISABLED` candidates.

### 22.5 Accessibility, security, performance, and recovery

The release candidate MUST include:

- automated accessibility results and manual keyboard/screen-reader evidence for named paths;
- role/authorization and segregation tests;
- Phase 10 prompt-injection and AI refusal suite for `v1.0.0`; an `AI_DISABLED` disclosure and skipped-gate record for earlier non-V1 candidates;
- SBOM and security scan results;
- performance manifest and raw results;
- backup/restore and state-replay drill;
- partition-barrier cutover and forward-correction fault drills proving no lost, duplicate, or out-of-lineage event, plus the corresponding recovery runbook;
- fault drills for Kafka, Redis, PostgreSQL, Neo4j projection, model load, and AI provider.

Mocks MAY prove unit behavior but MUST NOT be labeled as live integration, recovery, provider, release, or production evidence.

---

## 23. Delivery Roadmap: Phase 0 Through Phase 13

Each phase MUST use a short-lived branch and pull request, stage exact paths, pass required local checks, pass protected-branch remote CI, and merge only after review. The named branch is illustrative; the pull request and exact SHA are normative evidence. Before implementation in each phase, its affected trust boundaries and abuse cases MUST update the approved threat model; Phase 12 only verifies the accumulated work.

### Phase 0 — Data and research feasibility

- **Purpose:** prove the dataset, label, split, ontology, license, storage, and compute claim boundary.
- **Deliverables:** dataset manifest; schema/data-quality inventory; mappings; leakage denylist; split proof; compute profile; data card; GO/REVISE/STOP record.
- **Dependencies:** approved draft specification and access to the exact dataset revision.
- **Exit gate:** every Section 6 requirement passes; no implementation phase starts on REVISE or STOP.
- **Git/GitHub milestone:** `research/phase-0-feasibility` PR merged to protected `main` with remote artifact checks.

### Phase 1 — Repository, contracts, and CI foundation

- **Purpose:** establish the smallest reproducible engineering skeleton.
- **Deliverables:** package boundaries for three deployables; schema registry; environment locks; exact-path validation scripts; CI; secret scanning; artifact-manifest library; local OIDC-compatible identity-provider bootstrap; analyst, reviewer, model approver, auditor, and administrator role bindings; deny-by-default server-side authorization contract and verification fixtures; baseline Phase 1 threat model with trust boundaries and abuse cases.
- **Dependencies:** Phase 0 GO.
- **Exit gate:** clean bootstrap from clone; contract compatibility checks; authenticated identity bootstrap; role/action/object/sensitivity authorization allow-and-deny fixtures; reviewed Phase 1 threat model; no committed secrets; and remote CI pass.
- **Git/GitHub milestone:** `feat/phase-1-foundation` PR at an immutable merge SHA.

### Phase 2 — Ingestion, validation, and provenance

- **Purpose:** create trustworthy event replay and quarantine.
- **Deliverables:** raw/normalized contracts; decimal/time handling; stable IDs/hashes; Kafka topics/keys; quarantine; dataset replay manifest.
- **Dependencies:** Phase 1.
- **Exit gate:** deterministic valid, invalid, duplicate, conflict, and late-event fixtures pass locally and remotely.
- **Git/GitHub milestone:** `feat/phase-2-ingestion` PR with integration artifacts.

### Phase 3 — Labels, splits, rules, and tabular baselines

- **Purpose:** establish causal research baselines before graph complexity.
- **Deliverables:** versioned labels/splits; leakage tests; rules; logistic and one tree baseline; metrics/uncertainty report; null-champion gate.
- **Dependencies:** Phase 2 and Phase 0 split proof.
- **Exit gate:** no split/leakage violation, reproducible baselines, and signed/hashed `PROCEED`, `STOP`, or `SKIPPED_BY_DEPENDENCY` records for the rules/tabular branches.
- **Git/GitHub milestone:** `research/phase-3-baselines` PR; large results stored as hashed artifacts, not Git blobs.

### Phase 4 — Causal features and bounded entity state

- **Purpose:** prove offline/online parity and recoverable account state.
- **Deliverables:** feature contracts; offline/online implementations; Redis projection; checkpoints; per-entity commands; replay comparison.
- **Dependencies:** Phase 3 contracts and Phase 2 stream.
- **Exit gate:** parity tolerance, event-time ordering, idempotency, crash/replay, RPO/RTO drill, and state-hash checks pass.
- **Git/GitHub milestone:** `feat/phase-4-feature-state` PR with recovery evidence.

### Phase 5 — Static graph and anomaly research

- **Purpose:** test whether bounded graph/anomaly methods add justified value.
- **Deliverables:** branch records for `BEHAVIOR_ANOMALY`, `GRAPH_ANOMALY`, and `STATIC_GNN` following the Section 9 explicit prerequisite/outcome matrix. Executed branches produce compute profiles, comparison artifacts, and signed/content-hashed decisions; skipped branches emit `SKIPPED_BY_DEPENDENCY` with dependency evidence.
- **Dependencies:** `RULE_TABULAR` decision record; `GRAPH_ANOMALY` and `STATIC_GNN` also require verified Phase 0 graph support.
- **Exit gate:** each named branch has reproducible artifacts plus a signed/hashed `PROCEED` or `STOP` record, or a valid `SKIPPED_BY_DEPENDENCY` record tied to its frozen pre-execution gate manifest.
- **Git/GitHub milestone:** `research/phase-5-static-graph` PR with artifact hashes.

### Phase 6 — Temporal, heterogeneous, and hybrid research

- **Purpose:** test progressively gated TGN, HGT, and hybrid hypotheses.
- **Deliverables:** branch records for `TGN`, `HGT`, and `HYBRID_TGN_HGT` following the Section 9 explicit prerequisite/outcome matrix. Executed branches produce profiling, package/replay compatibility evidence, comparison artifacts, and signed/content-hashed decisions; skipped branches emit `SKIPPED_BY_DEPENDENCY` with dependency evidence.
- **Dependencies:** Phase 4 causal state plus `BEHAVIOR_ANOMALY`, `GRAPH_ANOMALY`, and `STATIC_GNN` decision records as specified by branch ID.
- **Exit gate:** every named branch has package/replay and uncertainty evidence plus a signed/hashed `PROCEED` or `STOP` record, or a valid `SKIPPED_BY_DEPENDENCY` record tied to its frozen pre-execution gate manifest; no success is presumed.
- **Git/GitHub milestone:** `research/phase-6-temporal-hybrid` PR.

### Phase 7 — Calibration and final research protocol

- **Purpose:** freeze eligible candidates and complete the approved candidate or sealed-null protocol exactly once.
- **Deliverables:** `CALIBRATION_FUSION` completion manifest with one of two paths. Candidate path calibrates/fuses the accepted candidate and freezes thresholds before exactly one preregistered final temporal test execution plus applicable unknown/stress/ablation reports. Sealed-null path records `NO_PROMOTABLE_CHAMPION`, `selected_model = null`, `champion = null`, final temporal test status `NOT_RUN_SEALED`, why every branch stopped or was skipped, every required negative-result report, model/data cards with limitations, and either research-only/non-promotable frozen-baseline unknown/stress/ablation results or the specific content-hashed `SKIPPED_BY_DEPENDENCY` decision permitted by Section 8.6. The final temporal test MUST remain sealed on the sealed-null path.
- **Dependencies:** signed/hashed decision records for `RULE_TABULAR`, `BEHAVIOR_ANOMALY`, `GRAPH_ANOMALY`, `STATIC_GNN`, `TGN`, `HGT`, and `HYBRID_TGN_HGT`, each with `PROCEED`, `STOP`, or `SKIPPED_BY_DEPENDENCY`.
- **Exit gate:** isolation audit, immutable manifests, applicable uncertainty, negative-result publication, frozen `model_package_scoring_p95_ms` result, and model-approver decision before any final-test access. The release/research-completion gates MUST accept a sealed-null Phase 7 manifest only when every planned development/validation branch has its decision record and negative-result report and it includes either the valid research-only baseline evaluations or their specific content-hashed dependency decisions; they MUST NOT force a model claim or final-test execution. Deterministic rules MAY remain a reference baseline but MUST NOT be called champion unless they passed frozen promotion gates. End-to-end latency, throughput, lag, persistence/outbox overhead, typed failures, and recovery remain Phase 8/12 gates.
- **Git/GitHub milestone:** `research/phase-7-evaluation` PR; final-test artifacts protected and hashed.

### Phase 8 — Streaming scoring integration

- **Purpose:** integrate the frozen eligible rule/model package into the ingestion/scoring worker.
- **Deliverables:** typed outcomes, evidence packages, outbox, offset/state coordination, late-event/replay policy, fail-closed paths, benchmark harness.
- **Dependencies:** Phase 4 state and Phase 7 package or approved rules-only/null-model package.
- **Exit gate:** end-to-end event-to-risk integration, fault drills, deterministic replay, and documented performance result.
- **Git/GitHub milestone:** `feat/phase-8-streaming-scoring` PR with remote integration artifacts.

### Phase 9 — Evidence and case API

- **Purpose:** make alert and case operations durable and auditable.
- **Deliverables:** typed evidence store; lifecycle; assignment/SLA; deduplication; merge/split; optimistic concurrency; dispositions; audit chain.
- **Dependencies:** Phase 8 contracts plus the Phase 1 identity-provider bootstrap, role-binding artifact, and server-side authorization contract.
- **Exit gate:** concurrency, authorization, immutable history, idempotency, and restore tests pass.
- **Git/GitHub milestone:** `feat/phase-9-case-evidence` PR.

### Phase 10 — Read-only AI investigator

- **Purpose:** deliver the mandatory grounded, read-only AI capability for `v1.0.0` without expanding case authority.
- **Deliverables:** approved tools; policy enforcement; typed output; deterministic citation validation; provider record; injection/adversarial suite; manual fallback.
- **Dependencies:** Phase 9 evidence API and approved provider policy.
- **Exit gate:** all Section 16.6 mandatory gates pass for `v1.0.0`; failure blocks `v1.0.0`. Earlier research/vertical-slice candidates MAY retain a declared `AI_DISABLED` state.
- **Git/GitHub milestone:** `feat/phase-10-ai-investigator` PR with no secrets/provider payloads committed.

### Phase 11 — Investigator web and accessibility

- **Purpose:** deliver the synchronized analyst workflow.
- **Deliverables:** queue and case workspace; graph/timeline/evidence synchronization; assignment/review/disposition; degraded states; accessible alternatives.
- **Dependencies:** Phase 9; Phase 10 is mandatory for the `v1.0.0` candidate. Earlier vertical slices MAY exercise the manual UI with `AI_DISABLED` declared.
- **Exit gate:** named manual analyst flow, mandatory `v1.0.0` AI flow, provider-degraded fallback, WCAG 2.2 AA evidence, and concurrency/conflict behavior pass.
- **Git/GitHub milestone:** `feat/phase-11-investigator-web` PR with accessibility artifacts.

### Phase 12 — Integrated operations, security, performance, and recovery

- **Purpose:** verify the production-shaped local system as one release candidate.
- **Deliverables:** the Section 11.5 Docker Compose baseline and clean-start health evidence; telemetry/runbooks including partition-barrier cutover and forward-correction recovery; verification of consolidated threat models and mitigations; SBOM/scans; load test; backup/restore; Kafka/Redis/PostgreSQL/Neo4j/provider/model fault drills.
- **Dependencies:** Phases 8, 9, 10, and 11 for `v1.0.0`. An earlier non-V1 research/vertical-slice candidate MAY omit Phase 10 only with `AI_DISABLED` in its manifest and name.
- **Exit gate:** merge the candidate PR, record that merged commit as `candidate_sha`, and run every mandatory local and remote gate against that exact candidate SHA; failed mandatory drills block release.
- **Git/GitHub milestone:** `release/phase-12-candidate` PR merged to protected `main`; the tested merged commit becomes the exact candidate SHA. No release tag is created in Phase 12.

### Phase 13 — Release evidence and truthful publication

- **Purpose:** publish the reproducible local reference release and research record.
- **Deliverables:** publish the already-generated architecture, data/model cards, baseline reports, applicable candidate-path or research-only sealed-null ablation/unknown/stress reports, or the specific content-hashed `SKIPPED_BY_DEPENDENCY` records allowed by Section 8.6, latency/recovery reports, operational runbook, limitations, attribution, and release manifest as immutable release artifacts tied to `candidate_sha`; Phase 13 MUST NOT create or modify a repository file for publication.
- **Dependencies:** Phase 12 pass for the exact candidate SHA and Phase 7 completed protocol.
- **Exit gate:** every claim and artifact maps to the unchanged candidate SHA; negative/null results are retained; remote CI and release artifacts are verified. If any repository file changes, the change creates a new candidate SHA and all applicable Phase 12/release gates MUST rerun before tagging.
- **Git/GitHub milestone:** tag the exact Phase 12 candidate SHA and publish signed/versioned artifacts and immutable release notes without a new source commit. `v1.0.0` additionally requires the Phase 10 AI gates.

---

## 24. Git, CI, Evidence, and Release Truth

### 24.1 GitHub Flow

- `main` MUST be protected against direct pushes and force pushes.
- Every change MUST use a short-lived branch, reviewed pull request, required remote status checks, and exact-SHA evidence.
- Staging MUST name exact intended paths. Blanket adds and unrelated cleanup are prohibited.
- Generated data, model, benchmark, and scan artifacts MUST use approved artifact storage with hashes; secrets and large raw datasets MUST NOT enter Git.
- Commits SHOULD be small, phase-scoped, and use `<type>: <description>` subjects.
- A pull request MUST state scope, out-of-scope items, validation commands/results, artifact links/hashes, risks, rollback, and review approvals.

### 24.2 Evidence levels

- **UNIT**: isolated logic/contract evidence.
- **INTEGRATION**: real local dependencies and cross-component flow.
- **LIVE**: real external provider or runtime named in the protocol.
- **RELEASE**: required remote CI and immutable artifacts at the exact release SHA.
- **PRODUCTION**: real production environment evidence; outside V1.

An installed dependency, mock, local pass, container startup, merged PR, or artifact presence MUST NOT be promoted to a higher level. Missing Docker, Kafka, database, provider, remote CI, or credentials MUST produce BLOCKED/NOT RUN for the affected gate, not a downgraded PASS.

### 24.3 Release boundary

A local reference release requires:

- Phase 0 GO and completed Phase 7 protocol;
- one exact candidate SHA through required remote CI;
- Phase 12 integration, security, accessibility, performance, and recovery evidence;
- all Phase 10 AI/agent gates for `v1.0.0`; only explicitly named non-V1 candidates MAY record `AI_DISABLED` instead;
- immutable manifests, SBOM, scan results, release notes, limitations, and rollback instructions;
- no unresolved mandatory gate failure.

Release does not mean deployment or production certification. V1 MUST NOT claim bank readiness, regulatory approval, live customer use, or production SLO compliance.

---

## 25. Acceptance Criteria

### 25.1 Data and research

- Phase 0 ends in GO before implementation proceeds.
- Dataset facts, artifacts, mappings, labels, leakage denylist, and split proof are reproducible.
- Development train, model-selection validation, calibration, final temporal test, unknown-typology, and AMLSim stress sets follow Section 8; the final test remains sealed under `NO_PROMOTABLE_CHAMPION`, while valid no-final-test-access protocols execute on a reproducible frozen baseline as research-only/non-promotable and other skips meet Section 8.6.
- The research ladder obeys its gates and stop conditions.
- The final protocol executes once and publishes applicable uncertainty, limitations, and either a champion or the sealed-null manifest with `NO_PROMOTABLE_CHAMPION`, `selected_model = null`, `champion = null`, `NOT_RUN_SEALED`, and required research-only evaluations or specifically justified skips.

### 25.2 System

- The three-deployable architecture completes the deterministic event-to-audit flow.
- Invalid, duplicate, conflicting, late, missing-state, model-failure, persistence-failure, and provider-failure paths produce the specified typed outcomes.
- Replay, partition-barrier cutover, forward-correction recovery, backup/restore, idempotency, optimistic concurrency, and eventual-consistency behavior pass their drills.
- Performance results use the manifest in Section 13; an unmet target is reported as FAIL, not hidden.

### 25.3 Product and evidence

- Alerts and cases reference immutable typed evidence that is fully reconstructable while required source payloads remain retained/pinned; lawful `SOURCE_PAYLOAD_RETIRED` evidence is accepted only with its visible typed non-reconstructable/reduced guarantee and no full-reconstructability claim.
- Case assignment, SLA/aging, deduplication, merge/split, review, disposition, and reopen are authorized and audited.
- Graph, timeline, and evidence remain synchronized and disclose partial/stale state.
- The manual analyst flow works during provider outage or in explicitly disclosed non-V1 `AI_DISABLED` candidates.
- Named analyst paths meet WCAG 2.2 AA with automated and manual evidence.

### 25.4 AI, security, and governance

- AI tools are read-only, bounded, per-call authorized to the exact snapshot and its authorized underlying packages, injection-tested, and deterministically grounded through field-validated `GroundedClaim` objects with exhaustive relevant-contradiction checks.
- Roles and segregation of duties are enforced server-side.
- Audit integrity, TLS, secrets, retention, SBOM, scans, threat models, and recovery satisfy Sections 18–22.
- Model changes remain human-gated and reversible; drift never auto-promotes.

### 25.5 Truthful completion

The project is complete when the candidate or sealed-null protocol, manual workflow gates, and for `v1.0.0` the Phase 10 agent gates are executed and published at the required evidence level. Completion MUST NOT depend on a favorable hybrid result. A sealed-null completion requires every planned development/validation decision record and negative-result report, preserves the untouched final test, and executes research-only frozen-baseline evaluation where valid; every `SKIPPED_BY_DEPENDENCY` must meet Section 8.6. Any unsupported claim, hidden gate failure, reused or unsealed final test, fabricated entity/evidence, or mock labeled as live/release evidence invalidates acceptance.

---

## 26. Repository and Artifact Shape

The initial repository SHOULD preserve these package/artifact boundaries without turning each into a deployable:

```text
apps/
  investigator-web/

services/
  ingestion-scoring-worker/
  case-agent-api/

packages/
  schemas/
  datasets/
  labels/
  features/
  graph/
  scoring/
  evidence/
  cases/
  agent-tools/

research/
  baselines/
  anomaly/
  graph/
  temporal/
  evaluation/
  stress/

infra/
  docker/
  monitoring/

docs/
  architecture/
  data-card/
  model-card/
  evaluation/
  runbooks/
```

Names MAY change during per-phase planning if boundaries and three initial deployables remain intact.

---

## 27. Reuse, Attribution, and Future Scope

Candidate reuse includes AMLBench/AusAML, IBM AMLSim, PyTorch Geometric, maintained graph/anomaly baselines, Feast, MLflow, Kafka, Redis, PostgreSQL, Neo4j, Prometheus/Grafana, Cytoscape.js, and a state-machine agent library. Each adopted dependency MUST record license, version, source, security status, and whether use is imported, adapted, project-specific, or a research contribution.

Post-V1 possibilities include active learning, cross-bank privacy-preserving research, richer scenario generation, multi-agent assistance, regulatory-draft assistance with mandatory human review, Kubernetes deployment, and licensed visual-reference refinement. They MUST NOT be used to expand V1 acceptance implicitly.

---

## 28. Primary References

- [AMLBench dataset card](https://huggingface.co/datasets/DVK2026/AMLBench)
- [IBM AMLSim repository](https://github.com/IBM/AMLSim/)
- [Redis persistence documentation](https://redis.io/docs/latest/operate/oss_and_stack/management/persistence/)
- [Feast push data source reference](https://docs.feast.dev/reference/data-sources/push)
- [Apache Kafka introduction](https://kafka.apache.org/42/getting-started/introduction/)
- [Temporal Graph Networks paper](https://arxiv.org/abs/2006.10637)
- [Heterogeneous Graph Transformer paper](https://arxiv.org/abs/2003.01332)
- [Web Content Accessibility Guidelines 2.2](https://www.w3.org/TR/WCAG22/)
- [NIST AI RMF core](https://airc.nist.gov/airmf-resources/airmf/5-sec-core/)
- [OWASP prompt-injection risk](https://genai.owasp.org/llmrisk/llm01-prompt-injection/)

---

## 29. Proposed Future Product Statement Template

Before evidence exists, describe the work as:

> Designing a research-grade, production-shaped fiat-banking AML reference platform with causal temporal evaluation, evidence-grounded investigation, and human-gated model governance.

After a release, past-tense claims MUST be generated from the exact release manifest and MUST state limitations, evidence level, dataset nature, model outcome including a null champion, and measured rather than intended performance.
