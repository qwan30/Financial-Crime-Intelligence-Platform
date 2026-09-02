from __future__ import annotations

import json
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

import httpx
from pydantic import SecretStr

from fincrime.agent.deepseek import (
    GuardedDeepSeekProvider,
)
from fincrime.agent.settings import (
    BudgetController,
    DeepSeekSettings,
)
from fincrime.agent.tools import (
    InMemoryGraphRepository,
    TraceEdge,
    TraceNode,
)
from fincrime.agent.workflow import (
    HypothesisStatus,
    InvestigationHypothesis,
    InvestigatorWorkflow,
)
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService
from fincrime.evidence.models import (
    EvidenceCategory,
    EvidenceItem,
    EvidencePolarity,
    compute_sha256_hex,
)
from fincrime.evidence.store import EvidenceStore


def create_sample_evidence(
    evidence_id: str, polarity: EvidencePolarity = EvidencePolarity.SUPPORTING
) -> EvidenceItem:
    raw: dict[str, Any] = {
        "evidence_id": evidence_id,
        "category": EvidenceCategory.OBSERVED,
        "source_reference": f"source:{evidence_id}",
        "polarity": polarity,
        "snapshot_time": datetime(2026, 3, 1, 10, 0, 0, tzinfo=UTC),
        "generation_method_version": "v1.0",
        "confidence": 0.9,
        "payload_summary": f"Observed activity for {evidence_id}",
    }
    h = compute_sha256_hex(raw)
    return EvidenceItem(**raw, integrity_hash=h)


def create_sample_case(
    case_id: str,
    evidence_ids: tuple[str, ...] = (),
    trace_edge_ids: tuple[str, ...] = (),
) -> CaseSnapshot:
    raw: dict[str, Any] = {
        "case_id": case_id,
        "seed_entity": "account:seed:001",
        "evidence_ids": evidence_ids,
        "trace_edge_ids": trace_edge_ids,
        "created_at": datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC),
    }
    h = compute_sha256_hex(raw)
    return CaseSnapshot(**raw, snapshot_hash=h)


_DEFAULT_API_KEY = SecretStr("sk-valid-key")


def setup_test_environment(
    evidence_ids: tuple[str, ...] = ("ev:001", "ev:002"),
    trace_edge_ids: tuple[str, ...] = ("edge:001",),
    api_key: SecretStr | None = _DEFAULT_API_KEY,
    mock_handler: Callable[[httpx.Request], httpx.Response] | None = None,
    monthly_cap_vnd: int = 200000,
    max_calls_per_case: int = 6,
) -> tuple[
    InvestigatorWorkflow, CaseService, EvidenceStore, InMemoryGraphRepository, BudgetController
]:
    evidence_store = EvidenceStore()
    for eid in evidence_ids:
        evidence_store.put(create_sample_evidence(eid))

    case_service = CaseService(evidence_store=evidence_store)
    case = create_sample_case(
        "case-test-01", evidence_ids=evidence_ids, trace_edge_ids=trace_edge_ids
    )
    case_service.create(case)

    graph_repo = InMemoryGraphRepository()
    graph_repo.add_node(TraceNode(node_id="account:seed:001", entity_type="account", is_seed=True))
    graph_repo.add_node(TraceNode(node_id="account:dest:002", entity_type="account"))
    if "edge:001" in trace_edge_ids:
        graph_repo.add_edge(
            TraceEdge(
                edge_id="edge:001",
                source="account:seed:001",
                target="account:dest:002",
                flow_amount=50000.0,
                relationship_type="TRANSFER",
                identity_confidence=0.99,
            )
        )

    settings = DeepSeekSettings(
        api_key=api_key,
        monthly_cap_vnd=monthly_cap_vnd,
        max_calls_per_case=max_calls_per_case,
    )
    controller = BudgetController(settings=settings)

    if mock_handler is not None:
        client = httpx.Client(transport=httpx.MockTransport(mock_handler))
    else:
        client = None

    provider = GuardedDeepSeekProvider(
        settings=settings,
        budget_controller=controller,
        client=client,
    )

    workflow = InvestigatorWorkflow(
        case_service=case_service,
        evidence_store=evidence_store,
        graph_repo=graph_repo,
        provider=provider,
        settings=settings,
    )

    return workflow, case_service, evidence_store, graph_repo, controller


# =========================================================================
# 7-Row Failure-to-Status Transition Matrix Tests
# =========================================================================


def test_transition_matrix_row1_zero_evidence() -> None:
    # Row 1: Zero evidence in case -> INSUFFICIENT_EVIDENCE
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    case = create_sample_case("case-empty-evidence", evidence_ids=(), trace_edge_ids=())
    case_service.create(case)

    graph_repo = InMemoryGraphRepository()
    graph_repo.add_node(TraceNode(node_id="account:seed:001", entity_type="account", is_seed=True))

    settings = DeepSeekSettings(api_key=SecretStr("sk-key"))
    controller = BudgetController(settings=settings)
    provider = GuardedDeepSeekProvider(settings=settings, budget_controller=controller)

    workflow = InvestigatorWorkflow(
        case_service=case_service,
        evidence_store=evidence_store,
        graph_repo=graph_repo,
        provider=provider,
        settings=settings,
    )

    hypothesis = workflow.run("case-empty-evidence")
    assert isinstance(hypothesis, InvestigationHypothesis)
    assert hypothesis.status == HypothesisStatus.INSUFFICIENT_EVIDENCE
    assert hypothesis.summary == "Case snapshot contains no evidence items"
    assert hypothesis.claims == ()
    assert hypothesis.model_version is None


def test_transition_matrix_row2_llm_off_mode() -> None:
    # Row 2: LLM_OFF / api_key is None -> AI_UNAVAILABLE
    workflow, _, _, _, _ = setup_test_environment(api_key=None)

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.AI_UNAVAILABLE
    assert hypothesis.summary == "AI provider disabled (LLM_OFF mode)"
    assert hypothesis.claims == ()
    assert hypothesis.model_version is None


def test_transition_matrix_row3_budget_cap_exceeded() -> None:
    # Row 3: Budget cap exceeded -> AI_UNAVAILABLE
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json={})

    workflow, _, _, _, controller = setup_test_environment(
        max_calls_per_case=1,
        mock_handler=handler,
    )

    # Exhaust budget for case-test-01
    controller.reserve("case-test-01", "Previous reservation")

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.AI_UNAVAILABLE
    assert hypothesis.summary == "AI investigation budget limit reached"
    assert hypothesis.claims == ()


def test_transition_matrix_row4_provider_transport_failure() -> None:
    # Row 4: Provider transport/timeout failure -> AI_UNAVAILABLE
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Network timed out", request=request)

    workflow, _, _, _, _ = setup_test_environment(mock_handler=handler)

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.AI_UNAVAILABLE
    assert hypothesis.summary == "AI provider request failed or timed out"
    assert hypothesis.claims == ()


def test_transition_matrix_row5_malformed_json_or_invalid_schema() -> None:
    # Row 5: Malformed JSON or schema parse error -> AI_INVALID_OUTPUT
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": "This is raw unformatted text without JSON"}}],
                "usage": {"prompt_tokens": 50, "completion_tokens": 20},
            },
        )

    workflow, _, _, _, _ = setup_test_environment(mock_handler=handler)

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.AI_INVALID_OUTPUT
    assert hypothesis.summary == "AI provider returned invalid structured output"
    assert hypothesis.claims == ()


def test_transition_matrix_row6_unauthorized_citation() -> None:
    # Row 6: Claim cites unauthorized evidence (not in case.evidence_ids) -> AI_INVALID_OUTPUT
    raw_ai_output = {
        "summary": "Suspected layering across unknown accounts.",
        "claims": [
            {
                "claim_text": "High risk transaction detected in external network.",
                "cited_evidence_ids": ["ev:UNAUTHORIZED:999"],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": json.dumps(raw_ai_output)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    # case-test-01 only has ("ev:001", "ev:002")
    workflow, _, _, _, _ = setup_test_environment(mock_handler=handler)

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.AI_INVALID_OUTPUT
    assert hypothesis.summary == "AI hypothesis cited unauthorized or empty evidence"
    assert hypothesis.claims == ()


def test_transition_matrix_row7_all_claims_valid_success() -> None:
    # Row 7: All claims have valid citations in case.evidence_ids -> HYPOTHESIS_GENERATED
    raw_ai_output = {
        "summary": "Coordinated fund movement matching classic structuring and layering pattern.",
        "claims": [
            {
                "claim_text": "Rapid fund pass-through from seed entity to intermediary destination.",
                "cited_evidence_ids": ["ev:001", "ev:002"],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": json.dumps(raw_ai_output)}}],
                "usage": {"prompt_tokens": 150, "completion_tokens": 90},
            },
        )

    workflow, _, _, _, _ = setup_test_environment(mock_handler=handler)

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.HYPOTHESIS_GENERATED
    assert (
        hypothesis.summary
        == "Coordinated fund movement matching classic structuring and layering pattern."
    )
    assert len(hypothesis.claims) == 1
    assert (
        hypothesis.claims[0].claim_text
        == "Rapid fund pass-through from seed entity to intermediary destination."
    )
    assert hypothesis.claims[0].cited_evidence_ids == ("ev:001", "ev:002")
    assert hypothesis.model_version == "deepseek-v4-flash"
    assert hypothesis.case_id == "case-test-01"
    assert hypothesis.generated_at.tzinfo is not None


def test_workflow_persistence_invariants() -> None:
    # Invariant: AI hypotheses are strictly read-only and NEVER written to EvidenceStore or CaseService
    raw_ai_output = {
        "summary": "Hypothesis generated.",
        "claims": [
            {
                "claim_text": "Valid claim text.",
                "cited_evidence_ids": ["ev:001"],
            }
        ],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            status_code=200,
            json={
                "choices": [{"message": {"content": json.dumps(raw_ai_output)}}],
                "usage": {"prompt_tokens": 100, "completion_tokens": 50},
            },
        )

    workflow, case_service, evidence_store, _, _ = setup_test_environment(mock_handler=handler)

    # Initial evidence store count
    initial_store_items = len(evidence_store._items)

    hypothesis = workflow.run("case-test-01")
    assert hypothesis.status == HypothesisStatus.HYPOTHESIS_GENERATED

    # Evidence store items must not have changed
    assert len(evidence_store._items) == initial_store_items

    # Case snapshot disposition / attributes must not have changed
    case = case_service.get("case-test-01")
    assert case.evidence_ids == ("ev:001", "ev:002")
