# Phase 0: Research, Exploration & Baseline Evidence

## 1. Repository Inventory & Baseline Audit
- **Branch:** `main` (commit `05f02c4 Merge pull request #29 from qwan30/feat/temporal-split-evidence`)
- **Language / Environment:** Python 3.12, Node.js (Vite/React planned)
- **Dependencies:** Polars 1.30, PyArrow 20, scikit-learn 1.6, LightGBM 4.6, NetworkX 3.4, PyTorch 2.12 (CPU), PyTorch Geometric 2.8.0
- **Test Suite Status:** 346 passing tests (pytest 8.3) in 46.2s
- **Static Analysis Status:** Ruff 0.11 clean, MyPy 1.15 strict clean across 31 source files.

## 2. Completed Milestones vs Next Objectives
- **Completed:**
  - Tasks 1-16 (Research Foundation, Canonical Adapters, Features, PIT Graph, Baselines, GraphSAGE, Tracing, Research Run) -> Merged via PR #4-#19.
  - Tasks 1-7 (Pilot Data Intake, AMLSim/AMLBench, Capacity, Quality, Labels, Provenance, Splits) -> Merged via PR #20-#29.
- **Immediate Next Focus (Plan 3: Investigator Workbench & DeepSeek):**
  - Phase 7: Immutable Evidence Store & Case API (Tasks 1-3)
  - Phase 8: Bounded LangGraph Investigator & DeepSeek Provider (Tasks 4-7)
  - Phase 9: Evaluation & React Workbench UI (Tasks 8-9)

## 3. Security & Quality Rules Applied
- Auto-loaded rules from `C:/Users/NITRO/.codex/rules/common/` (`coding-style.md`, `security.md`, `testing.md`), `python/`, `typescript/`, `react/`.
- Hard safety constraints: No hardcoded secrets, DeepSeek strictly non-decisional, append-only evidence hashing with SHA-256 integrity verification.
