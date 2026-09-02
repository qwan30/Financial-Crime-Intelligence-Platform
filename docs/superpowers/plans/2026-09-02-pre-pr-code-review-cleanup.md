# Pre-PR Code Review, Ponytail Audit & Worktree Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Safely clean up merged worktrees, execute a Ponytail Decision Ladder code review to eliminate dead/dirty code, verify full alignment with project rules and architecture invariants, and validate 100% test pass rate across the full stack before opening PR(s).

**Architecture:** A 5-phase progressive verification pipeline that isolates merged worktree pruning first, applies Ponytail simplification ladder (YAGNI, minimal diff, reuse) across Python and React workspaces, audits CLAUDE.md/AGENTS.md invariants, and gates readiness with full unit/integration/E2E test runs.

**Tech Stack:**
- Python 3.12 (`uv`, `pytest`, `ruff`, `mypy`, FastAPI, LangGraph, MLflow, Prometheus)
- TypeScript / React 19 (`vite`, `vitest`, `@playwright/test`, `cytoscape.js`)
- Git / Worktrees & RTK CLI toolchain

**Spec:** `.claude/rules/ponytail-review.md`, `GIT_WORKFLOW.md`, `CLAUDE.md`

## Global Constraints

- **Token Optimization:** All terminal commands for git, test, lint, and build MUST use the `rtk` prefix per `CLAUDE.md`.
- **Preservation First:** NEVER delete, prune, or reset any branch or worktree that contains unmerged commits or dirty state.
- **Ponytail Decision Ladder:** Strictly adhere to 7 principles: 1. YAGNI, 2. Codebase Reuse, 3. Standard Library First, 4. Native Platform, 5. Existing Dependencies, 6. Minimal Code, 7. Zero Negligence (maintain 80%+ coverage, typing, error handling).
- **Conventional Commits:** Commit messages must follow `<type>(<scope>): <imperative summary>` under 72 characters per `GIT_WORKFLOW.md`.
- **Zero Regression:** All 552 Python tests, 18 React/Vitest tests, and 2 Playwright E2E journeys must pass with 0 failures before PR readiness sign-off.

---

### Task 1: Safe Audit & Pruning of Merged Worktrees

**Files:**
- Modify: `.worktrees/*` (delete only directories of merged branches)
- Verify: Git worktree tracking database

**Interfaces:**
- Consumes: Git branch and worktree metadata against remote `origin/main`
- Produces: Clean local git worktree list with zero dangling pointers

- [ ] **Step 1: Inspect all worktrees and compare with origin/main**

```bash
rtk git worktree list
rtk git log origin/main --oneline -n 30
```

Verify that worktrees in `.worktrees/` corresponding to PRs #4 through #29 have their commits present on `origin/main` and contain no uncommitted changes.

- [ ] **Step 2: Prune clean merged worktrees**

Run:
```bash
rtk git worktree prune
```

For any merged worktree directories that remain registered, remove them explicitly:
```bash
# Example for verified merged worktree:
# rtk git worktree remove .worktrees/<merged-worktree-name>
```

- [ ] **Step 3: Verify no unmerged worktree was deleted and active branch is intact**

Run:
```bash
rtk git worktree list
rtk git status
rtk git branch --show-current
```
Expected: Only active working branch `feat/investigator-deepseek-workbench` (and any genuinely unmerged feature worktrees) remain; `git status` clean on active branch.

---

### Task 2: Ponytail Decision Ladder Review & Dead/Dirty Code Elimination

**Files:**
- Audit & Modify: `apps/case_api/**/*.py`, `src/fincrime/**/*.py`, `apps/investigator-web/src/**/*.{ts,tsx}`
- Audit & Modify: Unused imports, temporary debug logging, redundant helper wrappers

**Interfaces:**
- Consumes: `git diff origin/main...HEAD` across all 85 changed files
- Produces: Lean, minimal, bloat-free diff compliant with Ponytail Decision Ladder

- [ ] **Step 1: Run Ponytail Review inspection on staged and branch diff**

Execute Ponytail review inspection:
```bash
rtk git diff origin/main...HEAD --stat
```

Scan for:
1. YAGNI violations: Uncalled functions, dead abstractions, speculative parameters.
2. Codebase duplication: Custom helpers where `src/fincrime/common/` or stdlib suffices.
3. Dirty code: Leftover `print(...)`, `console.log(...)`, `# TODO: implement`, unnecessary commented-out blocks.

- [ ] **Step 2: Clean and simplify Python backend code**

Eliminate dead code, unused imports, and redundant scaffolding in `src/fincrime/` and `apps/case_api/`:
- Ensure `src/fincrime/cases/`, `src/fincrime/evidence/`, `src/fincrime/agent/`, `src/fincrime/streaming/`, `src/fincrime/mlops/`, `src/fincrime/monitoring/`, and `src/fincrime/release/` only expose needed symbols.
- Strip any extraneous debug prints or dead fallback branches.

- [ ] **Step 3: Clean and simplify React frontend code**

Review and clean `apps/investigator-web/`:
- Ensure components in `src/components/` and `src/services/` have no dead state variables, unused props, or dangling `console.log` statements.
- Verify Cytoscape graph configuration uses native options without redundant wrapper layers.

- [ ] **Step 4: Verify minimal diff and commit cleanup**

Run:
```bash
rtk git diff --check
rtk git status
```

Commit cleanups:
```bash
rtk git add src/ apps/
rtk git commit -m "chore(cleanup): eliminate dead code and debug logs via ponytail review"
```

---

### Task 3: Rules & Architectural Invariants Audit

**Files:**
- Verify: `CLAUDE.md`, `AGENTS.md`, `.claude/rules/ponytail-review.md`
- Verify: `apps/case_api/main.py`, `src/fincrime/release/manifest.py`, `src/fincrime/streaming/accumulator.py`, `src/fincrime/monitoring/drift.py`

**Interfaces:**
- Consumes: Invariant definitions from SDD & specs
- Produces: 100% type-checked, lint-clean codebase adhering to project rules

- [ ] **Step 1: Check Python static typing and linting**

Run Ruff linter and MyPy type checker:
```bash
rtk uv run ruff check .
rtk uv run mypy .
```
Expected: 0 errors, all types strictly resolved.

- [ ] **Step 2: Check React/TypeScript compilation and linting**

Run frontend build check:
```bash
cd apps/investigator-web && rtk npm run build
```
Expected: `tsc -b` and `vite build` complete with 0 errors and valid dist bundle.

- [ ] **Step 3: Audit architectural contracts**

Verify key invariants in code:
1. `apps/case_api/`: Responses adhere to standard Success/Error Envelopes.
2. `src/fincrime/evidence/`: Evidence store enforces immutability and checksum verification.
3. `src/fincrime/streaming/`: `OnlineGraphAccumulator` bitwise parity matches offline graph.
4. `src/fincrime/monitoring/`: Fitted PSI drift calculation uses clamp-and-sweep `nextafter`.
5. `src/fincrime/release/`: `ReleaseManifest` resolves exact inventory and dynamic Git SHA.

---

### Task 4: Full-Stack Regression Verification Gate

**Files:**
- Test: `tests/**/*.py`
- Test: `apps/investigator-web/src/**/*.test.{ts,tsx}`
- Test: `apps/investigator-web/e2e/**/*.spec.ts`

**Interfaces:**
- Consumes: Full test suites for Backend, Frontend Component/Unit, and E2E Browser
- Produces: Verified 100% green test execution report

- [ ] **Step 1: Run Python full test suite**

Run:
```bash
rtk uv run pytest -v
```
Expected: 552/552 tests PASS (100% pass rate).

- [ ] **Step 2: Run React component and API unit tests**

Run:
```bash
cd apps/investigator-web && rtk npm run test -- --run
```
Expected: 18/18 Vitest tests PASS (100% pass rate).

- [ ] **Step 3: Run Playwright E2E browser tests**

Run:
```bash
cd apps/investigator-web && rtk npx playwright test
```
Expected: 2/2 Playwright E2E browser journeys PASS.

- [ ] **Step 4: Check git status for unintended test side-effects**

Run:
```bash
rtk git status --short
```
Expected: No untracked junk files, test caches properly ignored by `.gitignore`.

---

### Task 5: Pre-PR Summary & Packaging Decision

**Files:**
- Create: `reports/2026-09-02-pre-pr-review-summary.md`

**Interfaces:**
- Consumes: Test results, diff statistics, and cleanup metrics
- Produces: Decision artifact for PR creation (Option 1: Monolithic vs Option 2: 2-Part PR)

- [ ] **Step 1: Generate pre-PR summary report**

Generate `reports/2026-09-02-pre-pr-review-summary.md` documenting:
- Final diff size and files changed count.
- Worktree cleanup outcomes (number of pruned worktrees, unmerged branches preserved).
- Ponytail Decision Ladder audit results.
- Test pass verification matrix (552 Python + 18 Vitest + 2 Playwright).
- Recommended PR packaging option.

- [ ] **Step 2: Commit summary report**

Run:
```bash
rtk git add reports/2026-09-02-pre-pr-review-summary.md
rtk git commit -m "docs(review): record pre-pr ponytail review and verification summary"
```

- [ ] **Step 3: Final branch verification and push readiness**

Run:
```bash
rtk git status
rtk git log -n 5 --oneline
```
Expected: Working tree clean, HEAD on `feat/investigator-deepseek-workbench`, ready for PR submission.

---

## Self-Review Checklist

- [x] **Spec coverage:** Covers safe worktree pruning, Ponytail 7-step review, rules verification (CLAUDE.md/AGENTS.md), and full-stack testing.
- [x] **No Placeholders:** Every task has explicit executable commands, expected outputs, and commit messages.
- [x] **Token Optimization:** Every terminal command prefixed with `rtk`.
- [x] **Safety Invariant:** Explicit preservation check for unmerged worktrees and branches.
