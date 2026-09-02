# TASK-003: Investigator Workbench & DeepSeek Implementation Brief (Authoritative v4.5)

## 1. Overview & Scope
Implement Plan 3: Phases 7–9 of the Financial Crime Intelligence Platform. This specification defines all canonical byte algorithms, atomic budget ledger semantics, non-decisional LLM failure transitions, graph repository ports, wire DTOs, and the 8-family evaluation harness across eight formal approval gates, fully certified against the Ponytail Decision Ladder.

---

## 2. Gate 1 & Gate 2: Canonical Serialization, Hash Invariants & Typed Stores (Phase 7)

### Canonical Normalization Pipeline (Gate 1)
All integrity hashes and replay comparisons follow this deterministic 5-stage normalization pipeline:
1. **Timezone Validation & Normalization:** Datetime values MUST be timezone-aware (`tzinfo is not None and val.utcoffset() is not None`). Naive datetimes raise `ValueError("Naive datetime is prohibited; timezone required")`. Valid datetimes are converted to UTC and formatted as ISO-8601 string `%Y-%m-%dT%H:%M:%SZ`.
2. **Enum Unboxing:** Any `Enum` instance is replaced with its underlying `.value`.
3. **Model Dump:** Pydantic models dumped via `model_dump(mode="python", by_alias=False, exclude={hash_field})`.
4. **Deterministic Collections:** Lists and tuples recursively normalized; dictionary keys sorted.
5. **Canonical JSON Bytes:** Encoded via `json.dumps(normalized, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')`.

```python
import hashlib
import json
from datetime import datetime, timezone
from enum import Enum
from typing import Any


def normalize_value(val: Any) -> Any:
    if isinstance(val, datetime):
        if val.tzinfo is None or val.utcoffset() is None:
            raise ValueError("Naive datetime is prohibited; timezone required")
        utc_dt = val.astimezone(timezone.utc)
        return utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(val, Enum):
        return val.value
    if isinstance(val, (list, tuple)):
        return [normalize_value(x) for x in val]
    if isinstance(val, dict):
        return {k: normalize_value(v) for k, v in val.items()}
    return val


def canonical_json_bytes(data: dict[str, Any]) -> bytes:
    normalized = normalize_value(data)
    return json.dumps(
        normalized,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8")


def compute_sha256_hex(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json_bytes(data)).hexdigest()
```

### Models (`src/fincrime/evidence/models.py`, `src/fincrime/cases/models.py`)
- **`EvidenceCategory` (StrEnum):** `OBSERVED`, `DERIVED`, `RULE`, `MODEL`, `TRACE`, `ANALYST`.
- **`EvidencePolarity` (StrEnum):** `SUPPORTING`, `MITIGATING`, `MISSING`, `UNKNOWN`.
- **`EvidenceItem` (frozen, extra='forbid', strict=True):**
  - `evidence_id: str = Field(min_length=1, pattern=r"^[a-zA-Z0-9_\-:]+$")`
  - `category: EvidenceCategory`
  - `source_reference: str = Field(min_length=1)`
  - `polarity: EvidencePolarity`
  - `snapshot_time: datetime` (must be timezone-aware UTC)
  - `generation_method_version: str = Field(min_length=1)`
  - `confidence: float | None = Field(default=None, ge=0.0, le=1.0)`
  - `payload_summary: str = Field(min_length=1)`
  - `integrity_hash: str = Field(pattern=r"^[0-9a-f]{64}$")`
  - Validator: `integrity_hash` must match `compute_sha256_hex(self.model_dump(mode="python", by_alias=False, exclude={"integrity_hash"}))`.
- **`Disposition` (StrEnum):** `CONFIRMED_SUSPICIOUS`, `FALSE_POSITIVE`, `ESCALATE`, `INSUFFICIENT_EVIDENCE`.
- **`AdjudicationStatus` (StrEnum):** `PENDING`, `ACCEPTED`, `REJECTED`.
- **`CaseSnapshot` (frozen, extra='forbid', strict=True):**
  - `case_id: str = Field(min_length=1)`
  - `seed_entity: str = Field(min_length=1)`
  - `evidence_ids: tuple[str, ...] = Field(default=())` (unique, sorted; empty tuple `()` allowed for initial cases)
  - `trace_edge_ids: tuple[str, ...] = Field(default=())` (sorted)
  - `created_at: datetime` (must be timezone-aware UTC)
  - `snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")`
  - Validator: `snapshot_hash` must match `compute_sha256_hex(self.model_dump(mode="python", by_alias=False, exclude={"snapshot_hash"}))`.
- **`AnalystFeedbackEvent` (frozen, extra='forbid', strict=True):**
  - `event_id: str = Field(min_length=1)`
  - `analyst_id: str = Field(min_length=1)`
  - `case_id: str = Field(min_length=1)`
  - `disposition: Disposition`
  - `reason: str = Field(min_length=1)`
  - `created_at: datetime` (must be timezone-aware UTC)
  - `model_version: str | None = None`
  - `snapshot_hash: str = Field(pattern=r"^[0-9a-f]{64}$")`
  - `adjudication_status: AdjudicationStatus = AdjudicationStatus.PENDING`

### Typed Exceptions & Stores (Gate 2)
- Exceptions:
  - `EvidenceConflict(Exception)`: same `evidence_id` with differing canonical bytes.
  - `CaseConflict(Exception)`: same `case_id` with differing canonical bytes.
  - `FeedbackConflict(Exception)`: same `event_id` with differing canonical bytes.
  - `CaseNotFound(Exception)`: referencing non-existent `case_id`.
  - `EvidenceNotFound(Exception)`: referencing non-existent `evidence_id`.
- **`EvidenceStore`:**
  - Thread-safe store under `threading.Lock`.
  - `put(item: EvidenceItem) -> EvidenceItem`: Computes canonical bytes. If `evidence_id` exists: if canonical bytes match, returns stored item (idempotent); else raises `EvidenceConflict`.
  - `get(evidence_id: str) -> EvidenceItem`: Returns item or raises `EvidenceNotFound`.
  - `get_many(evidence_ids: tuple[str, ...] | list[str]) -> list[EvidenceItem]`: Resolves list of items or raises `EvidenceNotFound`.
- **`CaseService`:**
  - Thread-safe store under `threading.Lock`.
  - `create(case: CaseSnapshot) -> CaseSnapshot`: Verifies `snapshot_hash`. Revalidates that every ID in `case.evidence_ids` exists in `EvidenceStore`. If `case_id` exists: if canonical bytes match, returns stored snapshot (idempotent); else raises `CaseConflict`.
  - `get(case_id: str) -> CaseSnapshot`: Returns snapshot or raises `CaseNotFound`.
  - `append_feedback(event: AnalystFeedbackEvent) -> AnalystFeedbackEvent`: Verifies `event.case_id` exists. If `event_id` exists: if canonical bytes match, returns stored event; else raises `FeedbackConflict`.

---

## 3. Gate 3: Concurrency-Safe Budget Controller & Provider (Phase 8)

### Settings (`src/fincrime/agent/settings.py`)
- `DeepSeekSettings` (frozen, extra='forbid', strict=True):
  - `api_key: SecretStr | None = None`
  - `model_name: str = "deepseek-v4-flash"`
  - `api_base_url: str = "https://api.deepseek.com/v1"`
  - `monthly_cap_vnd: int = Field(default=200000, gt=0, le=5000000)`
  - `max_calls_per_case: int = Field(default=6, gt=0, le=20)`
  - `max_input_tokens_per_case: int = Field(default=60000, gt=0, le=200000)`
  - `max_output_tokens_per_case: int = Field(default=8000, gt=0, le=32000)`
  - `timeout_seconds: float = Field(default=60.0, gt=0.0, le=300.0)`

### Fixed-Point Integer Cost Arithmetic
- Cost formulas (returning exact `int` VND):
  $$\text{calc\_reserved\_cost}(in, out) = \left\lceil \frac{7 \cdot in + 28 \cdot out}{2000} \right\rceil$$
  $$\text{calc\_actual\_cost}(in, out) = \left\lceil \frac{7 \cdot in + 28 \cdot out}{2000} \right\rceil$$

### Budget Controller State Machine
- `ReservationToken(attempt_id: str, case_id: str, reserved_input: int, reserved_output: int, reserved_vnd: int)`
- **Atomic Reservation (`reserve(case_id: str, prompt: str) -> ReservationToken`):**
  Executed inside a single `threading.Lock` critical section:
  1. Calculate mathematical input upper bound: $\text{input\_allowance} = \text{len}(\text{prompt.encode('utf-8')})$.
  2. Query settled attempts for `case_id`: $\text{settled\_calls}, \text{settled\_in}, \text{settled\_out}$.
  3. Query pending attempts for `case_id`: $\text{pending\_calls} = |\text{pending}|, \text{pending\_in} = \sum \text{reserved\_input}, \text{pending\_out} = \sum \text{reserved\_output}$.
  4. Check Case Call Cap: if $\text{settled\_calls} + \text{pending\_calls} + 1 > \text{max\_calls\_per\_case} \implies \text{raise BudgetExceededError}$.
  5. Check Case Input Token Cap: if $\text{settled\_in} + \text{pending\_in} + \text{input\_allowance} > \text{max\_input\_tokens\_per\_case} \implies \text{raise BudgetExceededError}$.
  6. Calculate Available Output: $\text{avail\_out} = \text{max\_output\_tokens\_per\_case} - \text{settled\_out} - \text{pending\_out}$.
     If $\text{avail\_out} \le 0 \implies \text{raise BudgetExceededError}$.
     $\text{reserved\_output} = \min(\text{avail\_out}, \text{settings.max\_output\_tokens\_per\_case})$.
  7. Check Monthly VND Cap:
     $$\text{Total Active Commitment} = \sum_{\text{settled in month}} \text{actual\_vnd} + \sum_{\text{pending in month}} \text{reserved\_vnd}$$
     $$\text{reserved\_vnd} = \text{calc\_reserved\_cost}(\text{input\_allowance}, \text{reserved\_output})$$
     If $\text{Total Active Commitment} + \text{reserved\_vnd} > \text{monthly\_cap\_vnd} \implies \text{raise BudgetExceededError}$.
  8. Insert `AttemptRecord(status="RESERVED", ...)` and return `ReservationToken(attempt_id, case_id, input_allowance, reserved_output, reserved_vnd)`.

- **Reconciliation Under Lock:**
  - `reconcile(token, actual_in, actual_out)`: under the controller lock, updates attempt to `RECONCILED` with $\text{actual\_vnd} = \text{calc\_actual\_cost}(\text{actual\_in}, \text{actual\_out})$. If provider returns 0 or missing tokens, retains full `reserved_vnd`.
  - Dispatched attempt failure (network/timeout/retry fail): reconciled at full conservative `reserved_vnd`.
  - `release(token)`: allowed ONLY if attempt was never dispatched over the network.

### Guarded DeepSeek Provider (`src/fincrime/agent/deepseek.py`)
- Custom Exceptions:
  - `BudgetExceededError(Exception)`: raised when budget/token cap exceeded.
  - `AIProviderError(Exception)`: raised on network/timeout/transport failure.
  - `AIInvalidOutputError(Exception)`: raised on JSON or schema parse error.
- `GuardedDeepSeekProvider`:
  - `generate_hypothesis(case_id: str, prompt: str) -> RawHypothesisOutput`:
    - Atomically calls `token = budget_controller.reserve(case_id, prompt)`.
    - Marks attempt `DISPATCHED`.
    - Calls client with `timeout=settings.timeout_seconds, max_tokens=token.reserved_output`.
    - If `BudgetExceededError` -> propagates `BudgetExceededError`.
    - If transport/timeout error -> reconciles conservative cost and raises `AIProviderError`.
    - If JSON/schema invalid -> reconciles actual tokens and raises `AIInvalidOutputError`.

---

## 4. Gate 4 & Gate 5: Non-Decisional LLM Contract & Citation Allowlisting (Phase 8)

### Output Models (`src/fincrime/agent/workflow.py`)
```python
class RawMaterialClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    claim_text: str = Field(min_length=1, max_length=500)
    cited_evidence_ids: tuple[str, ...] = Field(min_length=1)


class RawHypothesisOutput(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    summary: str = Field(min_length=1, max_length=2000)
    claims: tuple[RawMaterialClaim, ...]


class HypothesisStatus(StrEnum):
    HYPOTHESIS_GENERATED = "HYPOTHESIS_GENERATED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    AI_UNAVAILABLE = "AI_UNAVAILABLE"
    AI_INVALID_OUTPUT = "AI_INVALID_OUTPUT"


class MaterialClaim(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    claim_text: str = Field(min_length=1, max_length=500)
    cited_evidence_ids: tuple[str, ...] = Field(min_length=1)


class InvestigationHypothesis(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    hypothesis_id: str = Field(min_length=1)
    case_id: str = Field(min_length=1)
    status: HypothesisStatus
    summary: str = Field(min_length=1)
    claims: tuple[MaterialClaim, ...]
    generated_at: datetime
    model_version: str | None = None
```

### Complete Failure-to-Status Transition Matrix
| Trigger Condition | Caught Exception | Final `HypothesisStatus` | `summary` message | `claims` |
|---|---|---|---|---|
| Zero evidence in case (`len(case.evidence_ids) == 0`) | None (Route directly) | `INSUFFICIENT_EVIDENCE` | `"Case snapshot contains no evidence items"` | `()` |
| `LLM_OFF` / `api_key is None` | None (Route directly) | `AI_UNAVAILABLE` | `"AI provider disabled (LLM_OFF mode)"` | `()` |
| Budget cap exceeded | `BudgetExceededError` | `AI_UNAVAILABLE` | `"AI investigation budget limit reached"` | `()` |
| Provider transport/timeout failure | `AIProviderError` | `AI_UNAVAILABLE` | `"AI provider request failed or timed out"` | `()` |
| Malformed JSON or schema parse error | `AIInvalidOutputError` | `AI_INVALID_OUTPUT` | `"AI provider returned invalid structured output"` | `()` |
| Uncited claim or citation not in `case.evidence_ids` | None (Citation check) | `AI_INVALID_OUTPUT` | `"AI hypothesis cited unauthorized or empty evidence"` | `()` |
| All claims have valid citations in `case.evidence_ids` | None | `HYPOTHESIS_GENERATED` | Clean narrative summary | `claims` |

**Gate 5 Citation Rule:** Citations are valid iff for every claim $c$, `set(c.cited_evidence_ids).issubset(set(loaded_case.evidence_ids))` and `len(c.cited_evidence_ids) > 0`.

**PERSISTENCE INVARIANT:** AI hypotheses are strictly read-only and are NEVER stored into `EvidenceStore`, `CaseSnapshot.disposition`, risk tables, or labels.

---

## 5. Gate 5 & Gate 7: Graph Repository & Read Tools (Phase 8)

### Graph Models & `InMemoryGraphRepository` Adapter (Gate 7)
```python
class TraceNode(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    node_id: str = Field(min_length=1)
    entity_type: str = Field(min_length=1)
    risk_score: float | None = Field(default=None, ge=0.0, le=1.0)
    is_seed: bool = False
    is_context: bool = False


class TraceEdge(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    edge_id: str = Field(min_length=1)
    source: str = Field(min_length=1)
    target: str = Field(min_length=1)
    flow_amount: float = Field(ge=0.0)
    relationship_type: str = Field(min_length=1)
    identity_confidence: float = Field(ge=0.0, le=1.0)


class TraceGraphResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)
    nodes: tuple[TraceNode, ...]
    edges: tuple[TraceEdge, ...]
    is_truncated: bool
    total_hops: int


class ReferentialIntegrityError(Exception):
    pass


class InMemoryGraphRepository:
    def __init__(
        self,
        nodes: dict[str, TraceNode] | None = None,
        edges: dict[str, TraceEdge] | None = None,
    ) -> None:
        self._nodes: dict[str, TraceNode] = dict(nodes or {})
        self._edges: dict[str, TraceEdge] = dict(edges or {})
        self._lock = threading.Lock()

    def add_node(self, node: TraceNode) -> None:
        with self._lock:
            self._nodes[node.node_id] = node

    def add_edge(self, edge: TraceEdge) -> None:
        with self._lock:
            self._edges[edge.edge_id] = edge

    def get_subgraph_by_edge_ids(
        self,
        edge_ids: tuple[str, ...],
        seed_entity: str,
        max_hops: int = 4,
        max_edges: int = 100,
    ) -> TraceGraphResult:
        if not (1 <= max_hops <= 4):
            raise ValueError(f"max_hops must be in 1..4, got {max_hops}")
        if not (1 <= max_edges <= 100):
            raise ValueError(f"max_edges must be in 1..100, got {max_edges}")

        with self._lock:
            # 1. Referential integrity: check all requested edge IDs and their endpoints exist
            if seed_entity not in self._nodes:
                raise ReferentialIntegrityError(
                    f"Seed entity not found in graph nodes: {seed_entity}"
                )

            all_requested_edges: list[TraceEdge] = []
            for eid in edge_ids:
                if eid not in self._edges:
                    raise ReferentialIntegrityError(f"Requested edge not found: {eid}")
                edge = self._edges[eid]
                if edge.source not in self._nodes or edge.target not in self._nodes:
                    raise ReferentialIntegrityError(f"Edge {eid} references missing endpoint node")
                all_requested_edges.append(edge)

            # 2. Strict BFS traversal rooted at seed_entity
            traversed_edges: list[TraceEdge] = []
            visited_nodes: set[str] = {seed_entity}
            current_frontier: set[str] = {seed_entity}
            actual_hops = 0

            edge_pool = list(all_requested_edges)
            for hop in range(1, max_hops + 1):
                next_frontier: set[str] = set()
                new_edges_in_hop: list[TraceEdge] = []
                for e in list(edge_pool):
                    if e.source in current_frontier or e.target in current_frontier:
                        new_edges_in_hop.append(e)
                        next_frontier.add(e.source)
                        next_frontier.add(e.target)
                        edge_pool.remove(e)
                if not new_edges_in_hop:
                    break
                traversed_edges.extend(new_edges_in_hop)
                current_frontier = next_frontier
                visited_nodes.update(next_frontier)
                actual_hops = hop
                if len(traversed_edges) >= max_edges:
                    break

            result_edges = traversed_edges[:max_edges]
            is_truncated = len(all_requested_edges) > len(result_edges)

            needed_node_ids = {seed_entity}
            for edge in result_edges:
                needed_node_ids.add(edge.source)
                needed_node_ids.add(edge.target)

            result_nodes = [self._nodes[nid] for nid in needed_node_ids]

            return TraceGraphResult(
                nodes=tuple(sorted(result_nodes, key=lambda n: n.node_id)),
                edges=tuple(sorted(result_edges, key=lambda e: e.edge_id)),
                is_truncated=is_truncated,
                total_hops=actual_hops,
            )
```

### Bounded Read Tools (`src/fincrime/agent/tools.py`)
1. `get_case_summary(case_id: str, case_service: CaseService) -> CaseSummary`
2. `get_supporting_evidence(case_id: str, case_service: CaseService, evidence_store: EvidenceStore, limit: int = 50) -> list[EvidenceItem]`: bounds `1 <= limit <= 50`, deterministically sorted by `evidence_id`.
3. `get_mitigating_evidence(case_id: str, case_service: CaseService, evidence_store: EvidenceStore, limit: int = 50) -> list[EvidenceItem]`: bounds `1 <= limit <= 50`, deterministically sorted by `evidence_id`.
4. `get_fund_trace(case_id: str, case_service: CaseService, graph_repo: InMemoryGraphRepository, max_hops: int = 4, max_edges: int = 100) -> TraceGraphResult`

---

## 6. Gate 6: Wire DTOs, Envelopes & Workbench Endpoint (Phase 9)

### Wire DTOs (`apps/case_api/main.py`)
Wire fields use camelCase aliases with `populate_by_name=True`:
```python
def to_camel(snake: str) -> str:
    components = snake.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class BaseDTO(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )


class ErrorDetail(BaseDTO):
    code: str
    message: str


class CaseResponse(BaseDTO):
    case_id: str
    seed_entity: str
    evidence_ids: list[str]
    trace_edge_ids: list[str]
    created_at: str
    snapshot_hash: str


class EvidenceResponse(BaseDTO):
    evidence_id: str
    category: str
    source_reference: str
    polarity: str
    snapshot_time: str
    generation_method_version: str
    payload_summary: str
    integrity_hash: str
    confidence: float | None = None


class TraceNodeResponse(BaseDTO):
    node_id: str
    entity_type: str
    risk_score: float | None = None
    is_seed: bool
    is_context: bool


class TraceEdgeResponse(BaseDTO):
    edge_id: str
    source: str
    target: str
    flow_amount: float
    relationship_type: str
    identity_confidence: float


class TraceGraphResponse(BaseDTO):
    nodes: list[TraceNodeResponse]
    edges: list[TraceEdgeResponse]
    is_truncated: bool
    total_hops: int


class MaterialClaimResponse(BaseDTO):
    claim_text: str
    cited_evidence_ids: list[str]


class HypothesisResponse(BaseDTO):
    hypothesis_id: str
    case_id: str
    status: str
    summary: str
    claims: list[MaterialClaimResponse]
    generated_at: str
    model_version: str | None = None


class WorkbenchData(BaseDTO):
    case: CaseResponse
    evidence: list[EvidenceResponse]
    trace: TraceGraphResponse
    hypothesis: HypothesisResponse


class SuccessEnvelope(BaseDTO, Generic[T]):
    success: Literal[True] = True
    data: T
    error: None = None


class ErrorEnvelope(BaseDTO):
    success: Literal[False] = False
    data: None = None
    error: ErrorDetail


CaseEnvelope = Annotated[
    SuccessEnvelope[CaseResponse] | ErrorEnvelope, Field(discriminator="success")
]
WorkbenchEnvelope = Annotated[
    SuccessEnvelope[WorkbenchData] | ErrorEnvelope, Field(discriminator="success")
]
FeedbackEnvelope = Annotated[
    SuccessEnvelope[dict[str, str]] | ErrorEnvelope, Field(discriminator="success")
]
```

### API Routes in `apps/case_api/main.py`
- `GET /healthz` -> `{"status": "ok"}`
- `GET /cases/{case_id}` -> `CaseEnvelope`
- `POST /cases` -> `CaseEnvelope`
- `POST /cases/{case_id}/feedback` -> `FeedbackEnvelope`
- `GET /cases/{case_id}/workbench` -> `WorkbenchEnvelope`

---

## 7. Gate 7 & Gate 8: Exact 8-Family Metric Formulas & Frozen Gold Manifest (Phase 9)

### 8 Metric Family Formulas (Gate 8)
Let $K$ be the set of evaluated cases ($N = |K|$). For each case $k \in K$, let $C_k$ be the claims produced.
1. **Citation Precision ($P$):**
   $$P = \begin{cases} \frac{\sum_{k \in K} \sum_{c \in C_k} |\text{Valid}(c)|}{\sum_{k \in K} \sum_{c \in C_k} |\text{Cited}(c)|} & \text{if } \sum |\text{Cited}| > 0 \\ 1.0 & \text{if } \sum |\text{Cited}| = 0 \end{cases}$$
2. **Claim Coverage ($Cov$):**
   $$Cov = \begin{cases} \frac{\sum_{k \in K} |\{c \in C_k : |\text{Valid}(c)| \ge 1\}|}{\sum_{k \in K} |C_k|} & \text{if } \sum |C_k| > 0 \\ 1.0 & \text{if } \sum |C_k| = 0 \end{cases}$$
3. **Unsupported Claims Count ($U$):**
   $$U = \sum_{k \in K} \sum_{c \in C_k} \mathbf{1}\Big(|\text{Valid}(c)| = 0 \lor |\text{Cited}(c) \setminus \text{Valid}(c)| > 0\Big)$$
4. **Abstention Rate ($A$):**
   $$A = \begin{cases} \frac{|\{k \in K : \text{status}(k) \in \{\text{INSUFFICIENT\_EVIDENCE}, \text{AI\_UNAVAILABLE}\}\}|}{N} & \text{if } N > 0 \\ 0.0 & \text{if } N = 0 \end{cases}$$
5. **Tool Calls Total ($T$):**
   $$T[\text{tool}] = \sum_{k \in K} \text{executions}(\text{tool}, k)$$
6. **Latency Percentiles ($P50, P95$):**
   For sorted latencies $L = [l_1, \dots, l_N]$ (in ms):
   $$P_p = \begin{cases} l_{\lceil p \cdot N \rceil} & \text{if } N > 0 \\ 0.0 & \text{if } N = 0 \end{cases}$$
7. **Token Totals ($Tok$):**
   $$Tok_{\text{in}} = \sum_{k \in K} \text{input\_tokens}(k), \quad Tok_{\text{out}} = \sum_{k \in K} \text{output\_tokens}(k)$$
8. **Cost Totals ($Cost$ in VND):**
   $$\text{Cost}_{\text{res}} = \sum_{k \in K} \text{reserved\_vnd}(k), \quad \text{Cost}_{\text{act}} = \sum_{k \in K} \text{actual\_vnd}(k)$$

### Frozen Gold Case Corpus Manifest Protocol
- Manifest Path: `data/manifests/eval_corpus_gold_cases.json`
- Frozen Corpus Protocol: The manifest file is created during the Phase 9 Task 8 implementation step; its exact canonical SHA-256 digest is computed at creation time and verified dynamically before every test run.
- Contains 10 gold benchmark test cases with explicit status oracle:

| Case ID | Name / Scenario Type | Mode | Expected `HypothesisStatus` |
|---|---|---|---|
| `gold-01` | Standard Money Muling Ring | `DEEPSEEK_ON` | `HYPOTHESIS_GENERATED` |
| `gold-02` | Multi-layer Structuring Flow | `DEEPSEEK_ON` | `HYPOTHESIS_GENERATED` |
| `gold-03` | Context Transaction Tree | `DEEPSEEK_ON` | `HYPOTHESIS_GENERATED` |
| `gold-04` | Adversarial: Out-of-Snapshot Citation | `DEEPSEEK_ON` | `AI_INVALID_OUTPUT` |
| `gold-05` | Adversarial: Uncited Material Claim | `DEEPSEEK_ON` | `AI_INVALID_OUTPUT` |
| `gold-06` | Adversarial: Malformed AI Output | `DEEPSEEK_ON` | `AI_INVALID_OUTPUT` |
| `gold-07` | Adversarial: Budget Cap Exhausted | `DEEPSEEK_ON` | `AI_UNAVAILABLE` |
| `gold-08` | Adversarial: Provider Network Timeout | `DEEPSEEK_ON` | `AI_UNAVAILABLE` |
| `gold-09` | Adversarial: Zero Evidence Snapshot | `DEEPSEEK_ON` | `INSUFFICIENT_EVIDENCE` |
| `gold-10` | Baseline: LLM_OFF Mode | `LLM_OFF` | `AI_UNAVAILABLE` |

---

## 8. Verification & Test Gate Plan
1. Focused Unit Tests: `uv run pytest tests/evidence tests/cases tests/agent tests/api -v`
2. Full Monorepo Quality Gate: `uv run pytest -q && uv run ruff check . && uv run mypy src`
3. Frontend Unit & Build: `npm test -- --run && npm run build` in `apps/investigator-web`
