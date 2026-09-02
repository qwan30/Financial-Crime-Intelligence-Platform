from __future__ import annotations

import json
from pathlib import Path

import httpx
import pytest
from pydantic import SecretStr, ValidationError

from fincrime.agent.deepseek import (
    GuardedDeepSeekProvider,
)
from fincrime.agent.evaluation import (
    CaseEvalSummary,
    EvaluationResult,
    ManifestIntegrityError,
    calculate_abstention_rate,
    calculate_citation_precision,
    calculate_claim_coverage,
    calculate_percentile,
    compute_manifest_hash,
    create_mock_deepseek_transport,
    evaluate_corpus,
    populate_corpus_fixtures,
    verify_manifest_integrity,
)
from fincrime.agent.settings import (
    BudgetController,
    DeepSeekSettings,
)
from fincrime.agent.tools import (
    InMemoryGraphRepository,
)
from fincrime.agent.workflow import (
    HypothesisStatus,
    InvestigatorWorkflow,
)
from fincrime.cases.service import CaseService
from fincrime.evidence.store import EvidenceStore

_MANIFEST_PATH = Path("data/manifests/eval_corpus_gold_cases.json")


# =========================================================================
# 1. Manifest Integrity & SHA-256 Tests
# =========================================================================


def test_manifest_file_exists_and_computes_sha256() -> None:
    assert _MANIFEST_PATH.is_file(), f"Manifest missing at {_MANIFEST_PATH}"
    digest = compute_manifest_hash(_MANIFEST_PATH)
    assert len(digest) == 64
    assert digest == digest.lower()
    assert all(c in "0123456789abcdef" for c in digest)


def test_verify_manifest_integrity_success() -> None:
    digest = compute_manifest_hash(_MANIFEST_PATH)
    verified = verify_manifest_integrity(_MANIFEST_PATH, expected_sha256=digest)
    assert verified == digest


def test_verify_manifest_integrity_rejects_corrupted_hash() -> None:
    fake_hash = "0" * 64
    with pytest.raises(ManifestIntegrityError, match="Manifest hash mismatch"):
        verify_manifest_integrity(_MANIFEST_PATH, expected_sha256=fake_hash)


def test_verify_manifest_integrity_nonexistent_file(tmp_path: Path) -> None:
    missing_file = tmp_path / "nonexistent_manifest.json"
    with pytest.raises(ManifestIntegrityError, match="not found"):
        compute_manifest_hash(missing_file)


# =========================================================================
# 2. Fixture Population & Case Count Tests
# =========================================================================


def test_populate_corpus_fixtures() -> None:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()

    populated_ids = populate_corpus_fixtures(
        manifest_path=_MANIFEST_PATH,
        case_service=case_service,
        evidence_store=evidence_store,
        graph_repo=graph_repo,
    )

    assert len(populated_ids) == 10
    assert populated_ids == [f"gold-{i:02d}" for i in range(1, 11)]

    # Verify idempotency
    re_populated = populate_corpus_fixtures(
        manifest_path=_MANIFEST_PATH,
        case_service=case_service,
        evidence_store=evidence_store,
        graph_repo=graph_repo,
    )
    assert re_populated == populated_ids


# =========================================================================
# 3. Full 10 Gold Cases Evaluation (Gate 8 Benchmark)
# =========================================================================


def test_evaluate_corpus_all_10_gold_cases_benchmark() -> None:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    settings = DeepSeekSettings(api_key=SecretStr("sk-test-key"))

    expected_hash = compute_manifest_hash(_MANIFEST_PATH)
    result = evaluate_corpus(
        manifest_path=_MANIFEST_PATH,
        case_service=case_service,
        evidence_store=evidence_store,
        graph_repo=graph_repo,
        settings=settings,
        expected_manifest_hash=expected_hash,
    )

    assert isinstance(result, EvaluationResult)
    assert result.cases_evaluated == 10
    assert result.cases_passed_oracle == 10
    assert result.manifest_hash == expected_hash

    # 8 Metric Families Verification
    assert result.citation_precision == pytest.approx(1.0)
    assert result.claim_coverage == pytest.approx(1.0)
    assert result.unsupported_claims_count == 0
    assert result.abstention_rate == pytest.approx(0.40)
    assert result.tool_calls_total == 24
    assert result.latency_ms_p50 > 0.0
    assert result.latency_ms_p95 >= result.latency_ms_p50
    assert result.input_tokens_total > 0
    assert result.output_tokens_total > 0
    assert result.reserved_cost_vnd > 0
    assert result.actual_cost_vnd > 0

    # Summary array length
    assert len(result.case_summaries) == 10
    for summary in result.case_summaries:
        assert summary.status_matched is True
        assert summary.actual_status == summary.expected_status
        assert summary.tool_calls in (0, 3)


# =========================================================================
# 4. LLM_OFF vs DEEPSEEK_ON Modes
# =========================================================================


def test_evaluation_llm_off_mode_baseline() -> None:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()

    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    settings_off = DeepSeekSettings(api_key=None)
    controller = BudgetController(settings=settings_off)
    provider = GuardedDeepSeekProvider(settings=settings_off, budget_controller=controller)

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_off)
    hypothesis = wf.run("gold-10")

    assert hypothesis.status == HypothesisStatus.AI_UNAVAILABLE
    assert hypothesis.summary == "AI provider disabled (LLM_OFF mode)"
    assert hypothesis.claims == ()


def test_evaluation_deepseek_on_standard_cases() -> None:
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()

    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    transport = create_mock_deepseek_transport(manifest_data)
    client = httpx.Client(transport=transport)
    provider = GuardedDeepSeekProvider(settings_on, controller, client=client)

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)

    # Standard gold-01: Money muling ring
    hyp1 = wf.run("gold-01")
    assert hyp1.status == HypothesisStatus.HYPOTHESIS_GENERATED
    assert len(hyp1.claims) == 2
    for claim in hyp1.claims:
        assert len(claim.cited_evidence_ids) >= 1
        assert set(claim.cited_evidence_ids).issubset(
            {"ev:gold-01-01", "ev:gold-01-02", "ev:gold-01-03"}
        )

    # Standard gold-02: Structuring flow
    hyp2 = wf.run("gold-02")
    assert hyp2.status == HypothesisStatus.HYPOTHESIS_GENERATED
    assert len(hyp2.claims) == 2

    # Standard gold-03: Context tree
    hyp3 = wf.run("gold-03")
    assert hyp3.status == HypothesisStatus.HYPOTHESIS_GENERATED
    assert len(hyp3.claims) == 1


# =========================================================================
# 5. All 6 Adversarial Cases
# =========================================================================


def test_adversarial_case_1_citation_injection_gold_04() -> None:
    # Adversarial 1: Hallucinated / out-of-snapshot citation ID
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    transport = create_mock_deepseek_transport(manifest_data)
    provider = GuardedDeepSeekProvider(
        settings_on, controller, client=httpx.Client(transport=transport)
    )

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)
    hyp = wf.run("gold-04")

    assert hyp.status == HypothesisStatus.AI_INVALID_OUTPUT
    assert "unauthorized or empty evidence" in hyp.summary
    assert hyp.claims == ()


def test_adversarial_case_2_uncited_claims_gold_05() -> None:
    # Adversarial 2: Uncited material claim with empty cited_evidence_ids
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    transport = create_mock_deepseek_transport(manifest_data)
    provider = GuardedDeepSeekProvider(
        settings_on, controller, client=httpx.Client(transport=transport)
    )

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)
    hyp = wf.run("gold-05")

    assert hyp.status == HypothesisStatus.AI_INVALID_OUTPUT
    assert hyp.claims == ()


def test_adversarial_case_3_malformed_json_gold_06() -> None:
    # Adversarial 3: Provider returns non-JSON / broken output
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    transport = create_mock_deepseek_transport(manifest_data)
    provider = GuardedDeepSeekProvider(
        settings_on, controller, client=httpx.Client(transport=transport)
    )

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)
    hyp = wf.run("gold-06")

    assert hyp.status == HypothesisStatus.AI_INVALID_OUTPUT
    assert "invalid structured output" in hyp.summary
    assert hyp.claims == ()


def test_adversarial_case_4_budget_cap_exhausted_gold_07() -> None:
    # Adversarial 4: Budget limit reached
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    transport = create_mock_deepseek_transport(manifest_data)
    provider = GuardedDeepSeekProvider(
        settings_on, controller, client=httpx.Client(transport=transport)
    )

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)
    hyp = wf.run("gold-07")

    assert hyp.status == HypothesisStatus.AI_UNAVAILABLE
    assert "budget limit reached" in hyp.summary
    assert hyp.claims == ()


def test_adversarial_case_5_provider_network_timeout_gold_08() -> None:
    # Adversarial 5: Network failure or timeout
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    with _MANIFEST_PATH.open("r", encoding="utf-8") as f:
        manifest_data = json.load(f)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    transport = create_mock_deepseek_transport(manifest_data)
    provider = GuardedDeepSeekProvider(
        settings_on, controller, client=httpx.Client(transport=transport)
    )

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)
    hyp = wf.run("gold-08")

    assert hyp.status == HypothesisStatus.AI_UNAVAILABLE
    assert "failed or timed out" in hyp.summary
    assert hyp.claims == ()


def test_adversarial_case_6_zero_evidence_snapshot_gold_09() -> None:
    # Adversarial 6: Case contains zero evidence items
    evidence_store = EvidenceStore()
    case_service = CaseService(evidence_store=evidence_store)
    graph_repo = InMemoryGraphRepository()
    populate_corpus_fixtures(_MANIFEST_PATH, case_service, evidence_store, graph_repo)

    settings_on = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings_on)
    provider = GuardedDeepSeekProvider(settings_on, controller)

    wf = InvestigatorWorkflow(case_service, evidence_store, graph_repo, provider, settings_on)
    hyp = wf.run("gold-09")

    assert hyp.status == HypothesisStatus.INSUFFICIENT_EVIDENCE
    assert "no evidence items" in hyp.summary
    assert hyp.claims == ()


# =========================================================================
# 6. Metric Formulas & Percentiles Unit Tests
# =========================================================================


def test_calculate_citation_precision_formula() -> None:
    assert calculate_citation_precision(valid_citations=10, total_citations=10) == 1.0
    assert calculate_citation_precision(valid_citations=5, total_citations=10) == 0.5
    assert calculate_citation_precision(valid_citations=0, total_citations=0) == 1.0


def test_calculate_claim_coverage_formula() -> None:
    assert calculate_claim_coverage(claims_with_valid=4, total_claims=4) == 1.0
    assert calculate_claim_coverage(claims_with_valid=3, total_claims=4) == 0.75
    assert calculate_claim_coverage(claims_with_valid=0, total_claims=0) == 1.0


def test_calculate_abstention_rate_formula() -> None:
    statuses = [
        HypothesisStatus.HYPOTHESIS_GENERATED,
        HypothesisStatus.HYPOTHESIS_GENERATED,
        HypothesisStatus.AI_UNAVAILABLE,
        HypothesisStatus.INSUFFICIENT_EVIDENCE,
    ]
    assert calculate_abstention_rate(statuses) == 0.5
    assert calculate_abstention_rate([]) == 0.0


def test_calculate_percentile_formula() -> None:
    values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0, 70.0, 80.0, 90.0, 100.0]
    # N=10, p=0.5 -> ceil(5) - 1 = index 4 -> 50.0
    assert calculate_percentile(values, 0.50) == 50.0
    # N=10, p=0.95 -> ceil(9.5) - 1 = index 9 -> 100.0
    assert calculate_percentile(values, 0.95) == 100.0
    assert calculate_percentile([], 0.50) == 0.0

    with pytest.raises(ValueError, match="Percentile p must be between"):
        calculate_percentile(values, 1.5)


# =========================================================================
# 7. Wire DTOs & CamelCase Serialization Tests
# =========================================================================


def test_evaluation_result_camel_case_wire_format() -> None:
    res = EvaluationResult(
        citation_precision=0.95,
        claim_coverage=0.90,
        unsupported_claims_count=1,
        abstention_rate=0.20,
        tool_calls_total=15,
        latency_ms_p50=12.5,
        latency_ms_p95=45.0,
        input_tokens_total=1200,
        output_tokens_total=600,
        reserved_cost_vnd=50,
        actual_cost_vnd=42,
        cases_evaluated=5,
        cases_passed_oracle=5,
        manifest_hash="a" * 64,
    )

    dumped = res.model_dump(by_alias=True)
    assert "citationPrecision" in dumped
    assert "claimCoverage" in dumped
    assert "unsupportedClaimsCount" in dumped
    assert "abstentionRate" in dumped
    assert "toolCallsTotal" in dumped
    assert "latencyMsP50" in dumped
    assert "latencyMsP95" in dumped
    assert "inputTokensTotal" in dumped
    assert "outputTokensTotal" in dumped
    assert "reservedCostVnd" in dumped
    assert "actualCostVnd" in dumped
    assert "casesEvaluated" in dumped
    assert "casesPassedOracle" in dumped
    assert "manifestHash" in dumped


def test_evaluation_result_frozen_immutability() -> None:
    res = EvaluationResult(
        citation_precision=1.0,
        claim_coverage=1.0,
        unsupported_claims_count=0,
        abstention_rate=0.0,
        tool_calls_total=3,
        latency_ms_p50=1.0,
        latency_ms_p95=1.0,
        input_tokens_total=10,
        output_tokens_total=10,
        reserved_cost_vnd=1,
        actual_cost_vnd=1,
    )

    with pytest.raises(ValidationError):
        res.citation_precision = 0.5  # type: ignore[misc]


def test_case_eval_summary_camel_case_wire_format() -> None:
    summary = CaseEvalSummary(
        case_id="gold-01",
        name="Standard Money Muling Ring",
        mode="DEEPSEEK_ON",
        expected_status=HypothesisStatus.HYPOTHESIS_GENERATED,
        actual_status=HypothesisStatus.HYPOTHESIS_GENERATED,
        status_matched=True,
        claims_count=2,
        valid_citations_count=4,
        total_citations_count=4,
        unsupported_claims_count=0,
        latency_ms=12.5,
        tool_calls=3,
    )
    dumped = summary.model_dump(by_alias=True)
    assert dumped["caseId"] == "gold-01"
    assert dumped["expectedStatus"] == "HYPOTHESIS_GENERATED"
    assert dumped["statusMatched"] is True
    assert dumped["validCitationsCount"] == 4
    assert dumped["totalCitationsCount"] == 4
