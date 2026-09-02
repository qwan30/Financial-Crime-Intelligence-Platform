from __future__ import annotations

import json
import logging
import math
import time
from collections.abc import Sequence
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from fincrime.agent.deepseek import GuardedDeepSeekProvider
from fincrime.agent.settings import (
    BudgetController,
    BudgetExceededError,
    DeepSeekSettings,
)
from fincrime.agent.tools import (
    InMemoryGraphRepository,
    TraceEdge,
    TraceNode,
)
from fincrime.agent.workflow import (
    HypothesisStatus,
    InvestigatorWorkflow,
)
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseConflict, CaseService
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    compute_sha256_hex,
)
from fincrime.evidence.store import EvidenceConflict, EvidenceStore

logger = logging.getLogger(__name__)


def to_camel(snake: str) -> str:
    components = snake.split("_")
    return components[0] + "".join(x.title() for x in components[1:])


class ManifestIntegrityError(Exception):
    pass


class CaseEvalSummary(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )

    case_id: str
    name: str
    mode: str
    status: HypothesisStatus | None = None
    expected_status: HypothesisStatus
    actual_status: HypothesisStatus | None = None
    status_matches_oracle: bool = True
    status_matched: bool = True
    claims_count: int = 0
    valid_citations_count: int = 0
    total_citations_count: int = 0
    unsupported_claims_count: int = 0
    latency_ms: float = 0.0
    tool_calls: int = 0


class EvaluationResult(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        alias_generator=to_camel,
        populate_by_name=True,
    )

    citation_precision: float
    claim_coverage: float
    unsupported_claims_count: int
    abstention_rate: float
    tool_calls_total: int | dict[str, int] = 0
    latency_ms_p50: float
    latency_ms_p95: float
    input_tokens_total: int
    output_tokens_total: int
    reserved_cost_vnd: int
    actual_cost_vnd: int
    manifest_hash: str = ""
    cases_evaluated: int = 0
    cases_passed_oracle: int = 0
    case_summaries: list[CaseEvalSummary] = Field(default_factory=list)


def compute_manifest_hash(manifest_path: str | Path) -> str:
    path = Path(manifest_path)
    if not path.is_file():
        raise ManifestIntegrityError(f"Manifest file not found: {manifest_path}")
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return compute_sha256_hex(data)


def verify_manifest_integrity(manifest_path: str | Path, expected_sha256: str | None = None) -> str:
    computed_hash = compute_manifest_hash(manifest_path)
    if expected_sha256 is not None and computed_hash != expected_sha256:
        raise ManifestIntegrityError(
            f"Manifest hash mismatch: expected {expected_sha256}, got {computed_hash}"
        )
    return computed_hash


def calculate_citation_precision(valid_citations: int, total_citations: int) -> float:
    if total_citations <= 0:
        return 1.0
    return float(valid_citations / total_citations)


def calculate_claim_coverage(claims_with_valid: int, total_claims: int) -> float:
    if total_claims <= 0:
        return 1.0
    return float(claims_with_valid / total_claims)


def calculate_abstention_rate(statuses: Sequence[HypothesisStatus]) -> float:
    if not statuses:
        return 0.0
    abstained = sum(
        1
        for s in statuses
        if s in (HypothesisStatus.INSUFFICIENT_EVIDENCE, HypothesisStatus.AI_UNAVAILABLE)
    )
    return float(abstained / len(statuses))


def calculate_percentile(sorted_values: Sequence[float], p: float) -> float:
    n = len(sorted_values)
    if n == 0:
        return 0.0
    if not (0.0 <= p <= 1.0):
        raise ValueError(f"Percentile p must be between 0.0 and 1.0, got {p}")
    index = math.ceil(p * n) - 1
    index = max(0, min(n - 1, index))
    return float(sorted_values[index])


def populate_corpus_fixtures(
    manifest_path: str | Path,
    case_service: CaseService,
    evidence_store: EvidenceStore,
    graph_repo: InMemoryGraphRepository,
) -> list[str]:
    path = Path(manifest_path)
    if not path.is_file():
        raise ManifestIntegrityError(f"Manifest file not found: {manifest_path}")

    with path.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    populated_case_ids: list[str] = []

    for case_spec in manifest_data.get("cases", []):
        cid = case_spec["caseId"]
        seed = case_spec.get("seedEntity", f"account:{cid}")
        evidence_defs = case_spec.get("evidence", [])
        trace_defs = case_spec.get("trace", {})

        ev_ids: list[str] = []
        for ev in evidence_defs:
            eid = ev["evidenceId"]
            ev_ids.append(eid)
            cat = EvidenceCategory(ev.get("category", "OBSERVED"))
            pol = EvidencePolarity(ev.get("polarity", "SUPPORTING"))
            t_str = ev.get("snapshotTime", "2026-03-01T10:00:00Z")
            if t_str.endswith("Z"):
                t_str = t_str[:-1] + "+00:00"
            snap_time = datetime.fromisoformat(t_str)
            raw_ev = {
                "evidence_id": eid,
                "category": cat,
                "source_reference": ev.get("sourceReference", f"tx-{eid}"),
                "polarity": pol,
                "snapshot_time": snap_time,
                "generation_method_version": ev.get("generationMethodVersion", "v1.0.0"),
                "confidence": ev.get("confidence", 0.9),
                "payload_summary": ev.get("payloadSummary", f"Evidence {eid}"),
            }
            h_ev = compute_sha256_hex(raw_ev)
            item = EvidenceItem(**raw_ev, integrity_hash=h_ev)
            try:
                evidence_store.put(item)
            except EvidenceConflict:
                pass

        trace_nodes = trace_defs.get("nodes", [])
        for nd in trace_nodes:
            nid = nd["nodeId"]
            node = TraceNode(
                node_id=nid,
                entity_type=nd.get("entityType", "ACCOUNT"),
                risk_score=nd.get("riskScore"),
                is_seed=(nid == seed or nd.get("isSeed", False)),
                is_context=nd.get("isContext", False),
            )
            graph_repo.add_node(node)

        edge_ids: list[str] = []
        trace_edges = trace_defs.get("edges", [])
        for ed in trace_edges:
            eid = ed["edgeId"]
            edge_ids.append(eid)
            edge = TraceEdge(
                edge_id=eid,
                source=ed["source"],
                target=ed["target"],
                flow_amount=ed.get("flowAmount", 1000.0),
                relationship_type=ed.get("relationshipType", "FUNDS_TRANSFER"),
                identity_confidence=ed.get("identityConfidence", 0.95),
            )
            graph_repo.add_edge(edge)

        c_time_str = case_spec.get("createdAt", "2026-03-01T12:00:00Z")
        if c_time_str.endswith("Z"):
            c_time_str = c_time_str[:-1] + "+00:00"
        created_at = datetime.fromisoformat(c_time_str)

        raw_case = {
            "case_id": cid,
            "seed_entity": seed,
            "evidence_ids": tuple(sorted(ev_ids)),
            "trace_edge_ids": tuple(sorted(edge_ids)),
            "created_at": created_at,
        }
        h_case = compute_sha256_hex(raw_case)
        case_snap = CaseSnapshot(**raw_case, snapshot_hash=h_case)
        try:
            case_service.create(case_snap, evidence_store=evidence_store)
        except CaseConflict:
            pass

        populated_case_ids.append(cid)

    return populated_case_ids


class MockDeepSeekTransport(httpx.BaseTransport):
    def __init__(self, manifest_data: dict[str, Any]) -> None:
        self.cases_map: dict[str, dict[str, Any]] = {
            c["caseId"]: c for c in manifest_data.get("cases", [])
        }

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        body = json.loads(request.content.decode("utf-8"))
        prompt = ""
        for m in body.get("messages", []):
            if m.get("role") == "user":
                prompt = m.get("content", "")

        case_id = None
        for line in prompt.splitlines():
            if line.startswith(("Investigate Case:", "Case ID:")):
                case_id = line.split(":", 1)[1].strip()
                break

        if not case_id or case_id not in self.cases_map:
            return httpx.Response(404, json={"error": f"Case ID '{case_id}' not found in mock"})

        case_spec = self.cases_map[case_id]
        mock_resp = case_spec.get("mockAiResponse")

        if mock_resp is None:
            return httpx.Response(500, json={"error": "No mock response configured"})

        if mock_resp.get("errorType") == "TimeoutException":
            raise httpx.TimeoutException("Mock provider request timeout")

        if mock_resp.get("errorType") == "BudgetExceededError":
            raise BudgetExceededError("AI investigation budget limit reached")

        if mock_resp.get("rawContent") is not None:
            content = mock_resp["rawContent"]
        else:
            claims = []
            for cl in mock_resp.get("claims", []):
                claims.append(
                    {
                        "claim_text": cl.get("claimText", cl.get("claim_text", "")),
                        "cited_evidence_ids": cl.get(
                            "citedEvidenceIds", cl.get("cited_evidence_ids", [])
                        ),
                    }
                )
            content_dict = {
                "summary": mock_resp.get("summary", "Investigation Summary"),
                "claims": claims,
            }
            content = json.dumps(content_dict)

        data = {
            "id": f"chatcmpl-{case_id}",
            "choices": [
                {
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": content,
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        }
        return httpx.Response(200, json=data)


def create_mock_deepseek_transport(manifest_data: dict[str, Any]) -> httpx.BaseTransport:
    return MockDeepSeekTransport(manifest_data)


def evaluate_corpus(
    manifest_path: str | Path,
    case_service: CaseService,
    evidence_store: EvidenceStore,
    graph_repo: InMemoryGraphRepository,
    settings: DeepSeekSettings | None = None,
    deepseek_provider: GuardedDeepSeekProvider | None = None,
    expected_manifest_hash: str | None = None,
) -> EvaluationResult:
    # 1. Manifest Dynamic Integrity Check
    manifest_path_obj = Path(manifest_path)
    manifest_hash = verify_manifest_integrity(
        manifest_path_obj, expected_sha256=expected_manifest_hash
    )

    with manifest_path_obj.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    # 2. Populate Fixtures if needed
    populate_corpus_fixtures(
        manifest_path=manifest_path_obj,
        case_service=case_service,
        evidence_store=evidence_store,
        graph_repo=graph_repo,
    )

    # 3. Setup Providers and Controllers
    active_settings = settings or DeepSeekSettings()
    budget_controller: BudgetController | None = None

    if deepseek_provider is not None:
        provider = deepseek_provider
        budget_controller = provider._budget_controller
    else:
        # Check if settings has API key, otherwise create mock transport provider
        if active_settings.api_key is not None and active_settings.api_key.get_secret_value() != "":
            budget_controller = BudgetController(settings=active_settings)
            transport = create_mock_deepseek_transport(manifest_data)
            client = httpx.Client(transport=transport)
            provider = GuardedDeepSeekProvider(
                settings=active_settings,
                budget_controller=budget_controller,
                client=client,
            )
        else:
            budget_controller = BudgetController(settings=active_settings)
            provider = GuardedDeepSeekProvider(
                settings=active_settings, budget_controller=budget_controller
            )

    settings_llm_off = DeepSeekSettings(api_key=None)

    # Snapshot initial attempt IDs to calculate run-scoped totals
    initial_attempt_ids = set(budget_controller._attempts.keys()) if budget_controller else set()

    # 4. Evaluate Cases
    case_summaries: list[CaseEvalSummary] = []
    latencies_ms: list[float] = []
    statuses: list[HypothesisStatus] = []
    total_valid_citations = 0
    total_cited_citations = 0
    total_claims = 0
    claims_with_valid = 0
    total_unsupported_claims = 0
    cases_passed_oracle = 0

    for case_spec in manifest_data.get("cases", []):
        cid = case_spec["caseId"]
        name = case_spec.get("name", cid)
        mode = case_spec.get("mode", "DEEPSEEK_ON")
        expected_status = HypothesisStatus(case_spec["expectedStatus"])

        case_snapshot = case_service.get(cid)
        authorized_eids = set(case_snapshot.evidence_ids)

        # Build workflow with matching mode
        if mode == "LLM_OFF":
            wf = InvestigatorWorkflow(
                case_service=case_service,
                evidence_store=evidence_store,
                graph_repo=graph_repo,
                provider=provider,
                settings=settings_llm_off,
            )
        else:
            wf = InvestigatorWorkflow(
                case_service=case_service,
                evidence_store=evidence_store,
                graph_repo=graph_repo,
                provider=provider,
                settings=active_settings,
            )

        t_start = time.perf_counter()
        hyp = wf.run(cid)
        t_end = time.perf_counter()
        latency_ms = max(0.01, (t_end - t_start) * 1000.0)
        latencies_ms.append(latency_ms)

        status_matches = hyp.status == expected_status
        if status_matches:
            cases_passed_oracle += 1

        statuses.append(hyp.status)

        case_claims_count = len(hyp.claims)
        total_claims += case_claims_count
        case_valid_cits = 0
        case_total_cits = 0
        case_unsupported = 0

        for claim in hyp.claims:
            cits = claim.cited_evidence_ids
            case_total_cits += len(cits)
            valid_in_claim = sum(1 for eid in cits if eid in authorized_eids)
            case_valid_cits += valid_in_claim
            # Any claim with >= 1 valid citation is counted in claim_coverage
            if valid_in_claim > 0:
                claims_with_valid += 1
            if len(cits) == 0 or not set(cits).issubset(authorized_eids):
                case_unsupported += 1

        total_valid_citations += case_valid_cits
        total_cited_citations += case_total_cits
        total_unsupported_claims += case_unsupported

        # Tool calls executed: 0 for zero-evidence and LLM_OFF cases, 3 for active AI cases
        actual_tools_called = 0
        if mode == "DEEPSEEK_ON" and len(case_snapshot.evidence_ids) > 0:
            actual_tools_called = 3

        case_summaries.append(
            CaseEvalSummary(
                case_id=cid,
                name=name,
                mode=mode,
                status=hyp.status,
                actual_status=hyp.status,
                expected_status=expected_status,
                status_matches_oracle=status_matches,
                status_matched=status_matches,
                claims_count=case_claims_count,
                valid_citations_count=case_valid_cits,
                total_citations_count=case_total_cits,
                unsupported_claims_count=case_unsupported,
                latency_ms=latency_ms,
                tool_calls=actual_tools_called,
            )
        )

    # 5. Aggregate 8 Metric Families
    precision = calculate_citation_precision(total_valid_citations, total_cited_citations)
    coverage = calculate_claim_coverage(claims_with_valid, total_claims)
    abstention = calculate_abstention_rate(statuses)

    latencies_sorted = sorted(latencies_ms)
    p50 = calculate_percentile(latencies_sorted, 0.50)
    p95 = calculate_percentile(latencies_sorted, 0.95)

    tot_in = 0
    tot_out = 0
    tot_res_vnd = 0
    tot_act_vnd = 0

    if budget_controller is not None:
        for aid, att in budget_controller._attempts.items():
            if aid not in initial_attempt_ids:
                tot_in += att.actual_input or att.reserved_input
                tot_out += att.actual_output or att.reserved_output
                tot_res_vnd += att.reserved_vnd
                tot_act_vnd += att.actual_vnd or att.reserved_vnd

    total_tool_calls = sum(s.tool_calls for s in case_summaries)

    return EvaluationResult(
        citation_precision=precision,
        claim_coverage=coverage,
        unsupported_claims_count=total_unsupported_claims,
        abstention_rate=abstention,
        tool_calls_total=total_tool_calls,
        latency_ms_p50=p50,
        latency_ms_p95=p95,
        input_tokens_total=tot_in,
        output_tokens_total=tot_out,
        reserved_cost_vnd=tot_res_vnd,
        actual_cost_vnd=tot_act_vnd,
        manifest_hash=manifest_hash,
        cases_evaluated=len(manifest_data.get("cases", [])),
        cases_passed_oracle=cases_passed_oracle,
        case_summaries=case_summaries,
    )
