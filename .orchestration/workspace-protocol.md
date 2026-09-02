# Workspace Protocol & Governance

## 1. Governance Architecture (SLP Model)
- **Human (Owner):** Ultimate authority on product intent, budget, non-reversible trade-offs, and final production merge/release approval.
- **Lead (Project Authority):** Problem framing, task decomposition, dependency orchestration, integration, and final Lead Project Acceptance.
- **Peer (Bounded Outcome):** Owns bounded technical units with explicit scope (`owned_scope`, `excluded_scope`, `verification_criteria`). Empowered to return `CONFIRM`, `PARTIAL`, `CHALLENGE`, `REOPEN_REQUEST`, `DEPENDENCY_REQUEST`, `BLOCKED`, `DONE`.
- **Supervisor (Governance & Quality):** Monitors process adherence, detects S1-S9 anti-patterns, guards against context drift, false-passes, and unverified claims.

## 2. Direct Control Mention (DCM) Boundaries
- **Boundary-control DCM (Strong):** Strict boundary definitions, read-only vs writable scopes, cost caps, budget thresholds, and frozen decisions.
- **Solution-control DCM (Weak):** Lead defines what acceptance looks like without dictating unresearched implementation minutiae.

## 3. Technology Stack & Verification Gates
- **Backend / Engine:** Python 3.12, Pydantic 2, Polars, PyArrow, NetworkX, PyTorch / PyG, FastAPI, LangGraph, LangChain Core.
- **Frontend / Workbench:** React 19, TypeScript, Vite, Cytoscape.js, Vitest, Playwright.
- **Verification Commands:**
  - Python: `uv run pytest -q && uv run ruff check . && uv run mypy src`
  - React/Web: `npm test -- --run && npm run build` in `apps/investigator-web`
  - Playwright E2E: Automated browser testing for visual and state flows.
- **Quality Invariants:** Ponytail Ladder (YAGNI, minimal complexity, reuse existing patterns, zero speculative abstractions).
