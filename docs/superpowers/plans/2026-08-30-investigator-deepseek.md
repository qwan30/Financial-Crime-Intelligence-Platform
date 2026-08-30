# Investigator Workbench and DeepSeek Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build Phase 7–9 evidence/case services, bounded investigator tools, LangGraph workflow, and an optional DeepSeek provider with hard safety and cost boundaries.

**Architecture:** Evidence and case truth live in deterministic local services. LangGraph orchestrates read-only tools, while DeepSeek only interprets validated evidence and returns structured hypotheses; provider-off mode preserves the full non-LLM workflow. A minimal React/Cytoscape workbench consumes typed Case API responses.

**Tech Stack:** Python 3.12, Pydantic 2, FastAPI, LangGraph, LangChain Core, OpenAI Python SDK configured for DeepSeek, React, TypeScript, Vite, Cytoscape.js, pytest, Vitest.

## Global Constraints

- This plan starts only after the Research Release Exit Review passes.
- `DEEPSEEK_API_KEY` comes from environment/secret storage and is never logged.
- DeepSeek cannot create labels, risk scores, evidence IDs, dispositions, or promotion decisions.
- Default model is `deepseek-v4-flash`; model availability is checked via `/models`.
- Per-case defaults: six calls, 60,000 input tokens, 8,000 output tokens, 60-second timeout.
- Monthly DeepSeek cap defaults to 200,000 VND and no automatic top-up exists.
- `LLM_OFF` and `DEEPSEEK_ON` evaluate the same frozen gold cases.
- The UI must distinguish entity risk, relationship-to-flow, and identity confidence.
- Every task follows TDD and ends with a focused commit.

## Git Branching & PR Strategy (git-workflow / github-ops)

This implementation plan is split into **3 feature branches** and **3 Pull Requests** targeting `master`, using isolated git worktrees.

| Branch Name | Tasks Covered | PR Scope & Title | Target | Worktree Setup Command |
|-------------|---------------|------------------|--------|------------------------|
| `feat/phase7-evidence-case-api` | Tasks 1–3 | PR #8: `feat(phase7): immutable evidence store and Case API` | `master` | `git worktree add ../fin-p7-cases -b feat/phase7-evidence-case-api` |
| `feat/phase8-deepseek-investigator-workflow` | Tasks 4–7 | PR #9: `feat(phase8): bounded LangGraph investigator and DeepSeek adapter` | `master` | `git worktree add ../fin-p8-agent -b feat/phase8-deepseek-investigator-workflow` |
| `feat/phase9-eval-workbench-ui` | Tasks 8–9 | PR #10: `feat(phase9): investigator workbench UI and LLM boundary evaluation` | `master` | `git worktree add ../fin-p9-ui -b feat/phase9-eval-workbench-ui` |

### Commit Strategy
- **Format**: Follow Conventional Commits `<type>(<scope>): <subject>` with imperative mood (e.g. `feat(contracts): define evidence and case contracts`).
- **Scopes**: `contracts`, `evidence`, `cases`, `api`, `agent`, `ui`.
- **Pre-commit Gate**: Every Step 5 commit must pass `uv run pytest -q && uv run ruff check . && uv run mypy src` before committing.
- **Milestone Tagging**: Upon completion and merge of PR #10 (`feat/phase9-eval-workbench-ui`), tag the master branch with `v0.2.0-beta.investigator`.

## File Structure

```text
src/fincrime/
  evidence/models.py
  evidence/store.py
  cases/models.py
  cases/service.py
  agent/settings.py
  agent/tools.py
  agent/deepseek.py
  agent/workflow.py
  agent/evaluation.py
apps/case_api/main.py
apps/investigator-web/
  package.json
  src/api.ts
  src/App.tsx
  src/CaseWorkspace.tsx
tests/evidence/
tests/cases/
tests/agent/
tests/api/
apps/investigator-web/src/*.test.tsx
```

---

### Task 1: Define evidence and case contracts

**Branch:** `feat/phase7-evidence-case-api` | **PR:** #8

**Files:**
- Create: `src/fincrime/evidence/models.py`
- Create: `src/fincrime/cases/models.py`
- Create: `tests/evidence/test_models.py`
- Create: `tests/cases/test_models.py`

**Interfaces:**
- Consumes: source facts, model/trace references, and analyst actions.
- Produces: immutable `EvidenceItem`, `CaseSnapshot`, `Disposition`, and `AnalystFeedbackEvent`.

- [ ] **Step 1: Write failing contract tests**

```python
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from fincrime.evidence.models import EvidenceCategory, EvidenceItem


def test_evidence_requires_integrity_hash() -> None:
    with pytest.raises(ValidationError):
        EvidenceItem(
            evidence_id="ev-1",
            category=EvidenceCategory.OBSERVED,
            source_reference="edge:e1",
            snapshot_time=datetime.now(timezone.utc),
            generation_method_version="source-v1",
            integrity_hash="bad",
        )
```

```python
from fincrime.cases.models import Disposition


def test_case_dispositions_are_bounded() -> None:
    assert {item.value for item in Disposition} == {
        "CONFIRMED_SUSPICIOUS",
        "FALSE_POSITIVE",
        "ESCALATE",
        "INSUFFICIENT_EVIDENCE",
    }
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/evidence/test_models.py tests/cases/test_models.py -v`

Expected: FAIL because evidence/case modules do not exist.

- [ ] **Step 3: Implement immutable domain models**

```python
# src/fincrime/evidence/models.py
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class EvidenceCategory(StrEnum):
    OBSERVED = "OBSERVED"
    DERIVED = "DERIVED"
    RULE = "RULE"
    MODEL = "MODEL"
    TRACE = "TRACE"
    AI_HYPOTHESIS = "AI_HYPOTHESIS"
    ANALYST = "ANALYST"


class EvidencePolarity(StrEnum):
    SUPPORTING = "SUPPORTING"
    MITIGATING = "MITIGATING"
    MISSING = "MISSING"
    UNKNOWN = "UNKNOWN"


class EvidenceItem(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    evidence_id: str
    category: EvidenceCategory
    source_reference: str
    polarity: EvidencePolarity
    snapshot_time: datetime
    generation_method_version: str
    integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    confidence: float | None = Field(default=None, ge=0, le=1)
```

```python
# src/fincrime/cases/models.py
from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class Disposition(StrEnum):
    CONFIRMED_SUSPICIOUS = "CONFIRMED_SUSPICIOUS"
    FALSE_POSITIVE = "FALSE_POSITIVE"
    ESCALATE = "ESCALATE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class CaseSnapshot(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    case_id: str
    seed_entity: str
    evidence_ids: tuple[str, ...]
    trace_edge_ids: tuple[str, ...]
    snapshot_hash: str


class AnalystFeedbackEvent(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    event_id: str
    analyst_id: str
    case_id: str
    action: str
    reason: str
    created_at: datetime
    adjudicated: bool = False
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/evidence/test_models.py tests/cases/test_models.py -v`

Expected: tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/evidence/models.py src/fincrime/cases/models.py tests/evidence/test_models.py tests/cases/test_models.py
git commit -m "feat(contracts): define evidence and case contracts"
```

---

### Task 2: Implement append-only evidence and case services

**Branch:** `feat/phase7-evidence-case-api` | **PR:** #8

**Files:**
- Create: `src/fincrime/evidence/store.py`
- Create: `src/fincrime/cases/service.py`
- Create: `tests/evidence/test_store.py`
- Create: `tests/cases/test_service.py`

**Interfaces:**
- Consumes: immutable evidence/case objects.
- Produces: `EvidenceStore.put/get`, `CaseService.create/get/append_feedback`; conflicting IDs fail closed.

- [ ] **Step 1: Write failing idempotency tests**

```python
import pytest

from fincrime.evidence.store import EvidenceConflict, EvidenceStore


def test_same_id_with_different_payload_conflicts() -> None:
    store = EvidenceStore()
    store.put_json("ev-1", '{"value":1}')
    with pytest.raises(EvidenceConflict):
        store.put_json("ev-1", '{"value":2}')
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/evidence/test_store.py -v`

Expected: FAIL because the store does not exist.

- [ ] **Step 3: Implement the smallest append-only stores**

```python
# src/fincrime/evidence/store.py
class EvidenceConflict(RuntimeError):
    pass


class EvidenceStore:
    def __init__(self) -> None:
        self._items: dict[str, str] = {}

    def put_json(self, evidence_id: str, payload: str) -> None:
        existing = self._items.get(evidence_id)
        if existing is not None and existing != payload:
            raise EvidenceConflict(evidence_id)
        self._items = {**self._items, evidence_id: payload}

    def get_json(self, evidence_id: str) -> str:
        return self._items[evidence_id]
```

```python
# src/fincrime/cases/service.py
from fincrime.cases.models import AnalystFeedbackEvent, CaseSnapshot


class CaseService:
    def __init__(self) -> None:
        self._cases: dict[str, CaseSnapshot] = {}
        self._feedback: tuple[AnalystFeedbackEvent, ...] = ()

    def create(self, case: CaseSnapshot) -> CaseSnapshot:
        existing = self._cases.get(case.case_id)
        if existing is not None and existing != case:
            raise ValueError(f"conflicting case: {case.case_id}")
        self._cases = {**self._cases, case.case_id: case}
        return case

    def get(self, case_id: str) -> CaseSnapshot:
        return self._cases[case_id]

    def append_feedback(self, event: AnalystFeedbackEvent) -> None:
        self._feedback = (*self._feedback, event)
```

- [ ] **Step 4: Add the CaseService idempotency test and verify GREEN**

```python
# tests/cases/test_service.py
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService


def test_identical_case_create_is_idempotent() -> None:
    service = CaseService()
    case = CaseSnapshot(
        case_id="c1",
        seed_entity="a",
        evidence_ids=("ev-1",),
        trace_edge_ids=("e1",),
        snapshot_hash="a" * 64,
    )
    assert service.create(case) == case
    assert service.create(case) == case
```

Run: `uv run pytest tests/evidence/test_store.py tests/cases/test_service.py -v`

Expected: idempotent create passes; conflict and append-only feedback tests pass.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/evidence/store.py src/fincrime/cases/service.py tests/evidence/test_store.py tests/cases/test_service.py
git commit -m "feat(evidence): store immutable evidence and cases"
```

---

### Task 3: Expose a bounded Case API

**Branch:** `feat/phase7-evidence-case-api` | **PR:** #8

**Files:**
- Create: `apps/case_api/main.py`
- Create: `tests/api/test_case_api.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `CaseService` and validated case IDs.
- Produces: `GET /cases/{case_id}` response envelope; no raw database endpoint.

- [ ] **Step 1: Write the failing API test**

```python
from fastapi.testclient import TestClient

from apps.case_api.main import app


def test_missing_case_returns_typed_404() -> None:
    response = TestClient(app).get("/cases/missing")
    assert response.status_code == 404
    assert response.json() == {"success": False, "data": None, "error": "case_not_found"}
```

- [ ] **Step 2: Add FastAPI and verify RED**

Run: `uv add 'fastapi>=0.116,<1' 'uvicorn>=0.35,<1' && uv run pytest tests/api/test_case_api.py -v`

Expected: FAIL because the API app does not exist.

- [ ] **Step 3: Implement the typed endpoint**

```python
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse

from fincrime.cases.service import CaseService

app = FastAPI(title="Financial Crime Case API")
service = CaseService()


@app.exception_handler(HTTPException)
async def http_exception_handler(_: object, error: HTTPException) -> JSONResponse:
    return JSONResponse(status_code=error.status_code, content=error.detail)


@app.get("/cases/{case_id}")
def get_case(case_id: str) -> dict[str, object | None]:
    try:
        case = service.get(case_id)
    except KeyError as error:
        raise HTTPException(
            status_code=404,
            detail={"success": False, "data": None, "error": "case_not_found"},
        ) from error
    return {"success": True, "data": case.model_dump(mode="json"), "error": None}
```

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/api/test_case_api.py -v`

Expected: typed 404 test passes.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock apps/case_api/main.py tests/api/test_case_api.py
git commit -m "feat(api): expose bounded case API"
```

---

### Task 4: Define bounded investigation tools

**Branch:** `feat/phase8-deepseek-investigator-workflow` | **PR:** #9

**Files:**
- Create: `src/fincrime/agent/tools.py`
- Create: `tests/agent/test_tools.py`

**Interfaces:**
- Consumes: case/evidence services and bounded request schemas.
- Produces: read-only `get_case_summary`, `get_supporting_evidence`, `get_mitigating_evidence`, and `trace_funds` tools.

- [ ] **Step 1: Write the failing tool-budget test**

```python
import pytest

from fincrime.agent.tools import EvidenceToolInput, TraceToolInput, get_case_summary
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService


def test_trace_tool_rejects_more_than_four_hops() -> None:
    with pytest.raises(ValueError):
        TraceToolInput(case_id="c1", max_hops=5, max_edges=100)


def test_case_summary_is_read_only_and_bounded() -> None:
    service = CaseService()
    service.create(CaseSnapshot(case_id="c1", seed_entity="a", evidence_ids=("ev-1",), trace_edge_ids=("e1",), snapshot_hash="a" * 64))
    summary = get_case_summary(service, EvidenceToolInput(case_id="c1"))
    assert summary == {"case_id": "c1", "seed_entity": "a", "evidence_ids": ("ev-1",), "trace_edge_ids": ("e1",)}
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/agent/test_tools.py -v`

Expected: FAIL because agent tools do not exist.

- [ ] **Step 3: Implement schemas before decorators**

```python
from pydantic import BaseModel, ConfigDict, Field

from fincrime.cases.service import CaseService


class TraceToolInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    case_id: str
    max_hops: int = Field(ge=1, le=4)
    max_edges: int = Field(ge=1, le=100)


class EvidenceToolInput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    case_id: str


def get_case_summary(service: CaseService, request: EvidenceToolInput) -> dict[str, object]:
    case = service.get(request.case_id)
    return {
        "case_id": case.case_id,
        "seed_entity": case.seed_entity,
        "evidence_ids": case.evidence_ids,
        "trace_edge_ids": case.trace_edge_ids,
    }
```

Keep these service functions as normal typed functions. Task 7 wraps only this allowlist with LangChain `@tool(args_schema=...)`; no generic SQL, Cypher, shell, or network wrapper is exposed.

- [ ] **Step 4: Verify GREEN**

Run: `uv run pytest tests/agent/test_tools.py -v`

Expected: budget validation passes.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/agent/tools.py tests/agent/test_tools.py
git commit -m "feat(agent): define bounded investigation tools"
```

---

### Task 5: Enforce DeepSeek settings and local cost caps

**Branch:** `feat/phase8-deepseek-investigator-workflow` | **PR:** #9

**Files:**
- Create: `src/fincrime/agent/settings.py`
- Create: `tests/agent/test_settings.py`

**Interfaces:**
- Consumes: environment variables and usage events.
- Produces: `DeepSeekSettings`, `UsageLedger`, and `AI_BUDGET_EXHAUSTED` before a request exceeds cap.

- [ ] **Step 1: Write failing default/cap tests**

```python
import pytest

from fincrime.agent.settings import BudgetExhausted, DeepSeekSettings, UsageLedger


def test_deepseek_defaults_are_bounded() -> None:
    settings = DeepSeekSettings(api_key="secret")
    assert settings.model == "deepseek-v4-flash"
    assert settings.max_calls_per_case == 6
    assert settings.estimated_cost_vnd_per_call == 5_000
    assert settings.monthly_cap_vnd == 200_000


def test_usage_ledger_blocks_request_over_monthly_cap() -> None:
    ledger = UsageLedger(monthly_cap_vnd=200_000, spent_vnd=199_999)
    with pytest.raises(BudgetExhausted):
        ledger.reserve(estimated_cost_vnd=2)
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/agent/test_settings.py -v`

Expected: FAIL because settings do not exist.

- [ ] **Step 3: Implement frozen settings and immutable ledger updates**

```python
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class BudgetExhausted(RuntimeError):
    code = "AI_BUDGET_EXHAUSTED"


class DeepSeekSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    api_key: SecretStr
    base_url: str = "https://api.deepseek.com"
    model: str = "deepseek-v4-flash"
    reasoning_effort: str = "low"
    request_timeout_seconds: int = 60
    max_calls_per_case: int = 6
    max_input_tokens_per_case: int = 60_000
    max_output_tokens_per_case: int = 8_000
    estimated_cost_vnd_per_call: int = 5_000
    monthly_cap_vnd: int = 200_000


class UsageLedger(BaseModel):
    model_config = ConfigDict(frozen=True)
    monthly_cap_vnd: int = Field(ge=0)
    spent_vnd: int = Field(ge=0)

    def reserve(self, estimated_cost_vnd: int) -> "UsageLedger":
        updated = self.spent_vnd + estimated_cost_vnd
        if updated > self.monthly_cap_vnd:
            raise BudgetExhausted()
        return self.model_copy(update={"spent_vnd": updated})
```

- [ ] **Step 4: Verify GREEN and secret redaction**

Run: `uv run pytest tests/agent/test_settings.py -v`

Expected: tests pass; `str(SecretStr("secret"))` never exposes the key.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/agent/settings.py tests/agent/test_settings.py
git commit -m "feat(agent): bound DeepSeek usage and local cost caps"
```

---

### Task 6: Implement the DeepSeek provider adapter

**Branch:** `feat/phase8-deepseek-investigator-workflow` | **PR:** #9

**Files:**
- Create: `src/fincrime/agent/deepseek.py`
- Create: `tests/agent/test_deepseek.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: `DeepSeekSettings`, validated messages/tools, and injected OpenAI-compatible client.
- Produces: validated provider message or typed `AI_AUTH_FAILED`, `AI_BUDGET_EXHAUSTED`, `AI_UNAVAILABLE`.

- [ ] **Step 1: Write failing auth and retry tests with a fake client**

```python
import pytest

from fincrime.agent.deepseek import AIProviderError, DeepSeekProvider, assert_model_available
from fincrime.agent.settings import DeepSeekSettings, UsageLedger


class UnauthorizedClient:
    def create(self, **_: object) -> object:
        error = RuntimeError("unauthorized")
        error.status_code = 401  # type: ignore[attr-defined]
        raise error


class OverloadedClient:
    def __init__(self) -> None:
        self.calls = 0

    def create(self, **_: object) -> object:
        self.calls += 1
        if self.calls < 3:
            error = RuntimeError("overloaded")
            error.status_code = 503  # type: ignore[attr-defined]
            raise error
        return {"content": "ok"}


def test_401_fails_without_retrying() -> None:
    provider = DeepSeekProvider(
        settings=DeepSeekSettings(api_key="secret"),
        ledger=UsageLedger(monthly_cap_vnd=200_000, spent_vnd=0),
        create_completion=UnauthorizedClient().create,
    )
    with pytest.raises(AIProviderError, match="AI_AUTH_FAILED"):
        provider.complete(messages=[])


def test_503_retries_twice_then_succeeds() -> None:
    client = OverloadedClient()
    provider = DeepSeekProvider(
        settings=DeepSeekSettings(api_key="secret"),
        ledger=UsageLedger(monthly_cap_vnd=200_000, spent_vnd=0),
        create_completion=client.create,
        sleep=lambda _: None,
    )
    assert provider.complete(messages=[]) == {"content": "ok"}
    assert client.calls == 3


def test_seventh_logical_call_is_blocked_locally() -> None:
    provider = DeepSeekProvider(
        settings=DeepSeekSettings(api_key="secret"),
        ledger=UsageLedger(monthly_cap_vnd=200_000, spent_vnd=0),
        create_completion=lambda **_: {"content": "ok"},
    )
    for _ in range(6):
        provider.complete(messages=[])


def test_unavailable_runtime_model_fails_before_investigation() -> None:
    with pytest.raises(AIProviderError, match="AI_MODEL_UNAVAILABLE"):
        assert_model_available("deepseek-v4-flash", {"deepseek-v4-pro"})
    with pytest.raises(AIProviderError, match="AI_CALL_LIMIT_REACHED"):
        provider.complete(messages=[])
```

- [ ] **Step 2: Add the SDK and verify RED**

Run: `uv add 'openai>=1.99,<2' && uv run pytest tests/agent/test_deepseek.py -v`

Expected: FAIL because provider adapter does not exist.

- [ ] **Step 3: Implement injected transport and typed errors**

```python
from __future__ import annotations

from collections.abc import Callable
from time import sleep as system_sleep
from typing import Any

from fincrime.agent.settings import DeepSeekSettings, UsageLedger


class AIProviderError(RuntimeError):
    pass


def assert_model_available(model: str, available_models: set[str]) -> None:
    if model not in available_models:
        raise AIProviderError("AI_MODEL_UNAVAILABLE")


class DeepSeekProvider:
    def __init__(
        self,
        settings: DeepSeekSettings,
        ledger: UsageLedger,
        create_completion: Callable[..., Any],
        sleep: Callable[[float], None] = system_sleep,
    ) -> None:
        self.settings = settings
        self.ledger = ledger
        self.create_completion = create_completion
        self.sleep = sleep
        self.calls_made = 0

    def complete(self, messages: list[dict[str, str]]) -> Any:
        if self.calls_made >= self.settings.max_calls_per_case:
            raise AIProviderError("AI_CALL_LIMIT_REACHED")
        self.calls_made += 1
        self.ledger = self.ledger.reserve(
            estimated_cost_vnd=self.settings.estimated_cost_vnd_per_call
        )
        for attempt in range(3):
            try:
                return self.create_completion(
                    model=self.settings.model,
                    messages=messages,
                    reasoning_effort=self.settings.reasoning_effort,
                    timeout=self.settings.request_timeout_seconds,
                )
            except Exception as error:
                status = getattr(error, "status_code", None)
                if status == 401:
                    raise AIProviderError("AI_AUTH_FAILED") from error
                if status == 402:
                    raise AIProviderError("AI_BUDGET_EXHAUSTED") from error
                if status in {429, 500, 503} and attempt < 2:
                    self.sleep(float(2**attempt))
                    continue
                raise AIProviderError("AI_UNAVAILABLE") from error
        raise AIProviderError("AI_UNAVAILABLE")
```

- [ ] **Step 4: Verify GREEN without a real API key**

Run: `uv run pytest tests/agent/test_deepseek.py -v`

Expected: auth, balance, retry, timeout, malformed JSON, and cap tests pass with fake clients; no network request occurs.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock src/fincrime/agent/deepseek.py tests/agent/test_deepseek.py
git commit -m "feat(agent): add guarded DeepSeek provider adapter"
```

---

### Task 7: Build the LangGraph investigation workflow

**Branch:** `feat/phase8-deepseek-investigator-workflow` | **PR:** #9

**Files:**
- Create: `src/fincrime/agent/workflow.py`
- Create: `tests/agent/test_workflow.py`
- Modify: `pyproject.toml`

**Interfaces:**
- Consumes: case ID, bounded tools, optional provider.
- Produces: `InvestigationState` and structured `InvestigationAnswer`; provider-off returns `AI_UNAVAILABLE` without blocking case data.

- [ ] **Step 1: Write the failing provider-off test**

```python
import pytest

from fincrime.agent.workflow import build_langchain_tools, build_workflow, validate_citations
from fincrime.cases.service import CaseService


def test_provider_off_preserves_case_and_returns_ai_unavailable() -> None:
    workflow = build_workflow(provider=None)
    result = workflow.invoke({"case_id": "c1", "evidence_ids": ["ev-1"]})
    assert result["case_id"] == "c1"
    assert result["ai_status"] == "AI_UNAVAILABLE"
    assert result["evidence_ids"] == ["ev-1"]


def test_unknown_evidence_citation_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown evidence IDs"):
        validate_citations(("ev-1", "fabricated"), frozenset({"ev-1"}))


def test_structured_answer_accepts_only_known_evidence() -> None:
    provider = lambda _: {
        "summary": "Review required",
        "status": "REVIEW_REQUIRED",
        "supporting_evidence_ids": ["ev-1"],
        "mitigating_evidence_ids": [],
        "missing_information": ["beneficiary identity"],
        "recommended_next_checks": ["verify beneficiary"],
    }
    result = build_workflow(provider).invoke({"case_id": "c1", "evidence_ids": ["ev-1"]})
    assert result["answer"]["status"] == "REVIEW_REQUIRED"


def test_agent_exposes_only_allowlisted_tools() -> None:
    assert [tool.name for tool in build_langchain_tools(CaseService())] == ["get_case_summary"]
```

- [ ] **Step 2: Add LangGraph/LangChain and verify RED**

Run: `uv add 'langgraph>=0.6,<1' 'langchain-core>=0.3,<1' && uv run pytest tests/agent/test_workflow.py -v`

Expected: FAIL because workflow does not exist.

- [ ] **Step 3: Implement the minimal StateGraph**

```python
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langchain_core.tools import StructuredTool
from pydantic import BaseModel, ConfigDict

from fincrime.agent.tools import EvidenceToolInput, get_case_summary
from fincrime.cases.service import CaseService


class InvestigationAnswer(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    summary: str
    status: str
    supporting_evidence_ids: tuple[str, ...]
    mitigating_evidence_ids: tuple[str, ...]
    missing_information: tuple[str, ...]
    recommended_next_checks: tuple[str, ...]


class InvestigationState(TypedDict):
    case_id: str
    evidence_ids: list[str]
    ai_status: str
    answer: dict[str, Any] | None


def validate_citations(citations: tuple[str, ...], valid_ids: frozenset[str]) -> None:
    unknown = tuple(sorted(set(citations) - valid_ids))
    if unknown:
        raise ValueError(f"unknown evidence IDs: {unknown}")


def build_langchain_tools(service: CaseService) -> tuple[StructuredTool, ...]:
    def case_summary(case_id: str) -> dict[str, object]:
        return get_case_summary(service, EvidenceToolInput(case_id=case_id))

    return (
        StructuredTool.from_function(
            func=case_summary,
            name="get_case_summary",
            description="Return a bounded case summary by case ID.",
            args_schema=EvidenceToolInput,
        ),
    )


def build_workflow(provider: Callable[[list[dict[str, str]]], Any] | None) -> Any:
    builder = StateGraph(InvestigationState)

    def investigate(state: InvestigationState) -> InvestigationState:
        if provider is None:
            return {**state, "ai_status": "AI_UNAVAILABLE", "answer": None}
        raw = provider([{"role": "user", "content": state["case_id"]}])
        answer = InvestigationAnswer.model_validate(raw)
        validate_citations(
            answer.supporting_evidence_ids + answer.mitigating_evidence_ids,
            frozenset(state["evidence_ids"]),
        )
        return {
            **state,
            "ai_status": "COMPLETE",
            "answer": answer.model_dump(mode="json"),
        }

    builder.add_node("investigate", investigate)
    builder.add_edge(START, "investigate")
    builder.add_edge("investigate", END)
    return builder.compile()
```

- [ ] **Step 4: Verify GREEN including citation rejection**

Run: `uv run pytest tests/agent/test_workflow.py -v`

Expected: provider-off and nonexistent-evidence citation tests pass.

- [ ] **Step 5: Commit**

```powershell
git add pyproject.toml uv.lock src/fincrime/agent/workflow.py tests/agent/test_workflow.py
git commit -m "feat(agent): orchestrate bounded investigation workflow"
```

---

### Task 8: Evaluate DeepSeek against the no-LLM workflow

**Branch:** `feat/phase9-eval-workbench-ui` | **PR:** #10

**Files:**
- Create: `src/fincrime/agent/evaluation.py`
- Create: `src/fincrime/agent/smoke.py`
- Create: `tests/agent/test_evaluation.py`
- Create: `research/agent-evals/cases.json`

**Interfaces:**
- Consumes: same frozen cases for `LLM_OFF` and `DEEPSEEK_ON`.
- Produces: citation-validity, unsupported-claim, insufficient-evidence, tool-call, latency, token, and VND-cost report.

- [ ] **Step 1: Write the failing citation metric test**

```python
from fincrime.agent.evaluation import citation_validity


def test_citation_validity_rejects_unknown_ids() -> None:
    assert citation_validity(("ev-1", "fake"), frozenset({"ev-1"})) == 0.5
```

- [ ] **Step 2: Verify RED**

Run: `uv run pytest tests/agent/test_evaluation.py -v`

Expected: FAIL because agent evaluation does not exist.

- [ ] **Step 3: Implement deterministic metrics and fixed cases**

```python
def citation_validity(citations: tuple[str, ...], valid_ids: frozenset[str]) -> float:
    if not citations:
        return 1.0
    return sum(item in valid_ids for item in citations) / len(citations)
```

```json
[
  {
    "case_id": "gold-insufficient-1",
    "evidence_ids": ["ev-observed-1"],
    "expected_status": "INSUFFICIENT_EVIDENCE"
  },
  {
    "case_id": "gold-mitigating-1",
    "evidence_ids": ["ev-support-1", "ev-mitigating-1"],
    "expected_status": "REVIEW_REQUIRED"
  }
]
```

```python
# src/fincrime/agent/smoke.py
from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from openai import OpenAI

from fincrime.agent.deepseek import DeepSeekProvider
from fincrime.agent.settings import DeepSeekSettings, UsageLedger


def main() -> int:
    api_key = os.environ.get("DEEPSEEK_API_KEY")
    if not api_key:
        print("DEEPSEEK_API_KEY is required for the approved smoke run")
        return 2
    settings = DeepSeekSettings(api_key=api_key)
    client = OpenAI(api_key=api_key, base_url=settings.base_url)
    provider = DeepSeekProvider(
        settings=settings,
        ledger=UsageLedger(monthly_cap_vnd=settings.monthly_cap_vnd, spent_vnd=0),
        create_completion=client.chat.completions.create,
    )
    response = provider.complete(
        messages=[{"role": "user", "content": "Return INSUFFICIENT_EVIDENCE."}]
    )
    print(
        json.dumps(
            {
                "model": settings.model,
                "pricing_url": "https://api-docs.deepseek.com/quick_start/pricing/",
                "retrieved_at": datetime.now(timezone.utc).isoformat(),
                "usage": response.usage.model_dump() if response.usage else None,
                "content": response.choices[0].message.content,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 4: Run provider-off evaluation, then optional approved DeepSeek smoke**

Run without key: `uv run pytest tests/agent/test_evaluation.py -v`

Expected: deterministic metrics pass; no paid request occurs. After explicit key/cap approval, run `uv run python -m fincrime.agent.smoke` once and save its JSON output as a run artifact; never make this network call part of pytest.

- [ ] **Step 5: Commit**

```powershell
git add src/fincrime/agent/evaluation.py src/fincrime/agent/smoke.py tests/agent/test_evaluation.py research/agent-evals/cases.json
git commit -m "test(agent): evaluate DeepSeek investigation boundary"
```

---

### Task 9: Build the minimal synchronized investigator workbench

**Branch:** `feat/phase9-eval-workbench-ui` | **PR:** #10

**Files:**
- Create: `apps/investigator-web/package.json`
- Create: `apps/investigator-web/tsconfig.json`
- Create: `apps/investigator-web/vite.config.ts`
- Create: `apps/investigator-web/index.html`
- Create: `apps/investigator-web/src/api.ts`
- Create: `apps/investigator-web/src/main.tsx`
- Create: `apps/investigator-web/src/App.tsx`
- Create: `apps/investigator-web/src/TraceGraph.tsx`
- Create: `apps/investigator-web/src/setup.ts`
- Create: `apps/investigator-web/src/CaseWorkspace.tsx`
- Create: `apps/investigator-web/src/CaseWorkspace.test.tsx`

**Interfaces:**
- Consumes: typed Case API envelope.
- Produces: graph/timeline/evidence summary with AI status visible and no accusation styling for context-only nodes.

- [ ] **Step 1: Write the failing UI test**

```tsx
import { render, screen } from "@testing-library/react";
import { vi } from "vitest";
import { CaseWorkspace } from "./CaseWorkspace";

vi.mock("cytoscape", () => ({ default: () => ({ destroy: () => undefined }) }));

test("shows evidence and provider-off state", () => {
  render(
    <CaseWorkspace
      caseData={{ caseId: "c1", evidenceIds: ["ev-1"], traceEdgeIds: ["e1"] }}
      aiStatus="AI_UNAVAILABLE"
    />,
  );
  expect(screen.getByText("Case c1")).toBeInTheDocument();
  expect(screen.getByText("AI unavailable — investigation tools remain active")).toBeInTheDocument();
});
```

- [ ] **Step 2: Install frontend dependencies and verify RED**

```json
{
  "name": "investigator-web",
  "private": true,
  "type": "module",
  "scripts": {
    "test": "vitest",
    "build": "tsc -b && vite build"
  },
  "dependencies": {
    "cytoscape": "3.33.1",
    "react": "19.1.1",
    "react-dom": "19.1.1"
  },
  "devDependencies": {
    "@testing-library/jest-dom": "6.8.0",
    "@testing-library/react": "16.3.0",
    "@types/cytoscape": "3.21.9",
    "@types/react": "19.1.10",
    "@types/react-dom": "19.1.7",
    "@vitejs/plugin-react": "5.0.1",
    "jsdom": "26.1.0",
    "typescript": "5.9.2",
    "vite": "7.1.3",
    "vitest": "3.2.4"
  }
}
```

```json
{
  "compilerOptions": {
    "target": "ES2022",
    "module": "ESNext",
    "moduleResolution": "Bundler",
    "jsx": "react-jsx",
    "strict": true,
    "noEmit": true
  },
  "include": ["src", "vite.config.ts"]
}
```

```ts
// vite.config.ts
import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  test: { environment: "jsdom", setupFiles: ["./src/setup.ts"] },
});
```

```ts
// src/setup.ts
import "@testing-library/jest-dom/vitest";
```

```html
<!-- index.html -->
<div id="root"></div>
<script type="module" src="/src/main.tsx"></script>
```

Run from `apps/investigator-web`: `npm install && npm test -- --run`

Expected: FAIL because `CaseWorkspace` does not exist.

- [ ] **Step 3: Implement the smallest useful workspace**

```ts
// src/api.ts
export type CaseEnvelope = {
  success: boolean;
  data: { caseId: string; evidenceIds: string[]; traceEdgeIds: string[] } | null;
  error: string | null;
};

export async function fetchCase(caseId: string): Promise<CaseEnvelope> {
  const response = await fetch(`/cases/${encodeURIComponent(caseId)}`);
  return (await response.json()) as CaseEnvelope;
}
```

```tsx
// src/App.tsx
import { CaseWorkspace } from "./CaseWorkspace";

export function App() {
  return (
    <CaseWorkspace
      caseData={{ caseId: "demo", evidenceIds: [], traceEdgeIds: [] }}
      aiStatus="AI_UNAVAILABLE"
    />
  );
}
```

```tsx
// src/TraceGraph.tsx
import cytoscape from "cytoscape";
import { useEffect, useRef } from "react";

export function TraceGraph({ edgeIds }: { edgeIds: string[] }) {
  const container = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!container.current) return;
    const graph = cytoscape({
      container: container.current,
      elements: edgeIds.flatMap((id, index) => [
        { data: { id: `n${index}` } },
        { data: { id: `n${index + 1}` } },
        { data: { id, source: `n${index}`, target: `n${index + 1}` } },
      ]),
      style: [{ selector: "node", style: { "background-color": "#64748b" } }],
      layout: { name: "breadthfirst", directed: true },
    });
    return () => graph.destroy();
  }, [edgeIds]);
  return <div aria-label="Bounded transaction trace" ref={container} style={{ height: 320 }} />;
}
```

```tsx
// src/main.tsx
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { App } from "./App";

createRoot(document.getElementById("root")!).render(
  <StrictMode><App /></StrictMode>,
);
```

```tsx
import { TraceGraph } from "./TraceGraph";

type CaseData = {
  caseId: string;
  evidenceIds: string[];
  traceEdgeIds: string[];
};

export function CaseWorkspace({
  caseData,
  aiStatus,
}: {
  caseData: CaseData;
  aiStatus: string;
}) {
  return (
    <main>
      <h1>Case {caseData.caseId}</h1>
      <section aria-labelledby="trace-heading">
        <h2 id="trace-heading">Trace</h2>
        <p>{caseData.traceEdgeIds.length} bounded edges</p>
        <TraceGraph edgeIds={caseData.traceEdgeIds} />
      </section>
      <section aria-labelledby="evidence-heading">
        <h2 id="evidence-heading">Evidence</h2>
        <ul>{caseData.evidenceIds.map((id) => <li key={id}>{id}</li>)}</ul>
      </section>
      {aiStatus === "AI_UNAVAILABLE" && (
        <p>AI unavailable — investigation tools remain active</p>
      )}
    </main>
  );
}
```

- [ ] **Step 4: Verify GREEN and accessibility basics**

Run: `npm test -- --run && npm run build`

Expected: UI test and production build pass.

- [ ] **Step 5: Commit**

```powershell
git add apps/investigator-web
git commit -m "feat(ui): add investigator case workspace"
```

## Investigator Release Exit Review & Tagging

After merging PR #10 (`feat/phase9-eval-workbench-ui`) into `master`, verify the exit criteria and tag the milestone:

```powershell
git tag -a v0.2.0-beta.investigator -m "Release v0.2.0-beta.investigator: Phase 7–9 Investigator Workbench & DeepSeek"
git push origin v0.2.0-beta.investigator
```

Before moving to the next plan, verify:

- Case/evidence stores are append-only and reject conflicting IDs.
- Tools enforce four-hop/100-edge budgets.
- Provider-off workflow passes end-to-end.
- DeepSeek key is environment-only and cost cap is enforced locally.
- DeepSeek cannot modify labels, scores, evidence, or dispositions.
- Same cases are evaluated with `LLM_OFF` and `DEEPSEEK_ON`.
- UI makes AI unavailable/insufficient evidence explicit.
