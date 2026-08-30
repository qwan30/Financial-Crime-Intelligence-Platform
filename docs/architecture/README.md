# Financial Crime Intelligence Platform — Architecture Diagrams

These diagrams are derived from the current design specification and the three implementation plans dated 2026-08-30.

> **Status boundary:** these are **planned target architecture** artifacts. They are not evidence that `src/`, `apps/`, `infra/`, PostgreSQL persistence, streaming consumers, model training, DeepSeek integration, or the UI have been implemented or run.

## Diagram set

| Diagram | View | Canonical source | Purpose |
|---|---|---|---|
| 1. System architecture | [SVG](diagrams/01-system-architecture.svg) | [Mermaid](diagrams/01-system-architecture.mmd) | C4-style container view of research, investigation, optional AI, and later replay. |
| 2. Investigation sequence | [SVG](diagrams/02-sequence-flows.svg) | [Mermaid](diagrams/02-sequence-flows.mmd) | UML sequence for one analyst case, including LLM-off and DeepSeek paths. |
| 3. Logical ERD | [SVG](diagrams/03-logical-erd.svg) | [Mermaid](diagrams/03-logical-erd.mmd) | Domain contracts and identities without claiming a physical PostgreSQL schema. |
| 4. Module dependencies | [SVG](diagrams/04-module-dependencies.svg) | [Mermaid](diagrams/04-module-dependencies.mmd) | Focused package DAG; `A → B` means A provides artifacts consumed by B. |
| 5. State and business flow | [SVG](diagrams/05-state-business-flow.svg) | [Mermaid](diagrams/05-state-business-flow.mmd) | Training lifecycle and adjudicated analyst-feedback loop. |

The `.drawio` files in `diagrams/` are retained as the earlier editable whiteboard version. They are not the canonical display source because the offline Draw.io SVG router produced connector and label collisions on these dense diagrams.

## Shared notation

- Solid module boundaries represent capabilities explicitly covered by current implementation-plan tasks.
- Dashed module boundaries and nodes labeled `OPTIONAL`, `PLANNED`, or `TARGET` identify evidence-gated, later-phase, or incomplete responsibilities.
- Red branches are fail-closed outcomes such as invalid data, quarantine, or replay conflict.
- `UNKNOWN` trace truth is distinct from `CONFIRMED_BENIGN` and is never an automatic negative.
- DeepSeek output is `AI_HYPOTHESIS`. It cannot create labels, replace detector/ranker scores, decide model promotion, or perform analyst disposition.
- Detection and tracing are separate tasks. GraphSAGE is mandatory for the research release; HGT, TGN, and the hybrid are conditional experiments, not a sequential production pipeline.

## Important plan/spec differences reflected in the diagrams

1. The target ontology is temporal and heterogeneous, while the initial plan first builds an account-transfer `NetworkX MultiDiGraph` and a homogeneous GraphSAGE smoke baseline.
2. The target LangGraph design includes bounded tools and provider-off behavior, while the minimum plan initially exposes only `get_case_summary` in a one-node workflow.
3. The target case workflow includes disposition and feedback, while the current Case API task only specifies `GET /cases/{case_id}`. Target mutation endpoints are shown as dashed responsibilities.
4. The logical ERD is not a migration plan. Current case/evidence and replay stores begin in memory; PostgreSQL is only a later local infrastructure dependency.
5. The streaming plan proves an event envelope, in-memory replay state, parity scaffold, and local Compose contract. Durable receipts/source progress, strict gap detection, graph-state updates, and case sinks remain target responsibilities.

## Source documents

- [Graph AML + TraceBench design specification](../superpowers/specs/2026-08-30-graph-aml-tracebench-research-product-design.md)
- [Research foundation, training, and tracing plan](../superpowers/plans/2026-08-30-research-foundation-training-tracing.md)
- [Investigator workbench and DeepSeek plan](../superpowers/plans/2026-08-30-investigator-deepseek.md)
- [MLOps, streaming, and release evidence plan](../superpowers/plans/2026-08-30-mlops-streaming-release.md)

## Reproduction

Render the canonical Mermaid sources with the already-installed Mermaid CLI:

```powershell
mmdc -p .drawio-tmp/financial-crime-intelligence-platform/puppeteer-config.json `
  -c .drawio-tmp/financial-crime-intelligence-platform/mermaid-config.json `
  -b white -i <diagram.mmd> -o <diagram.svg>
```
