import logging
import uuid
from datetime import UTC, datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from fincrime.agent.deepseek import (
    AIInvalidOutputError,
    AIProviderError,
    GuardedDeepSeekProvider,
)
from fincrime.agent.settings import BudgetExceededError, DeepSeekSettings
from fincrime.agent.tools import (
    InMemoryGraphRepository,
    ReferentialIntegrityError,
    get_fund_trace,
    get_mitigating_evidence,
    get_supporting_evidence,
)
from fincrime.cases.models import CaseSnapshot
from fincrime.cases.service import CaseService
from fincrime.evidence.models import EvidenceItem
from fincrime.evidence.store import EvidenceStore

logger = logging.getLogger(__name__)


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


def construct_investigator_prompt(case: CaseSnapshot, evidence: list[EvidenceItem]) -> str:
    evidence_lines = [
        f"- [{e.evidence_id}] ({e.polarity.value}): {e.payload_summary}" for e in evidence
    ]
    return (
        f"Investigate Case: {case.case_id}\nSeed: {case.seed_entity}\n"
        f"Evidence Items:\n" + "\n".join(evidence_lines) + "\n"
        "Generate JSON matching RawHypothesisOutput."
    )


def investigate_case_workflow(
    case_id: str,
    case_service: CaseService,
    evidence_store: EvidenceStore,
    graph_repo: InMemoryGraphRepository,
    settings: DeepSeekSettings | None = None,
    deepseek_provider: GuardedDeepSeekProvider | None = None,
) -> InvestigationHypothesis:
    # 1. Load trusted case
    case = case_service.get(case_id)
    now = datetime.now(UTC)
    hypo_id = f"hypo-{uuid.uuid4().hex[:12]}"
    active_settings = settings or DeepSeekSettings()

    # 2. Check sufficiency immediately (before graph/evidence calls)
    if len(case.evidence_ids) == 0:
        return InvestigationHypothesis(
            hypothesis_id=hypo_id,
            case_id=case_id,
            status=HypothesisStatus.INSUFFICIENT_EVIDENCE,
            summary="Case snapshot contains no evidence items",
            claims=(),
            generated_at=now,
            model_version=None,
        )

    # 3. Check LLM_OFF mode immediately
    if active_settings.api_key is None or deepseek_provider is None:
        return InvestigationHypothesis(
            hypothesis_id=hypo_id,
            case_id=case_id,
            status=HypothesisStatus.AI_UNAVAILABLE,
            summary="AI provider disabled (LLM_OFF mode)",
            claims=(),
            generated_at=now,
            model_version=None,
        )

    # 4. Retrieve evidence and trace
    supporting = get_supporting_evidence(case_id, case_service, evidence_store)
    mitigating = get_mitigating_evidence(case_id, case_service, evidence_store)
    try:
        get_fund_trace(case_id, case_service, graph_repo)
    except (ReferentialIntegrityError, ValueError) as exc:
        logger.debug("Trace lookup skipped or failed for case %s: %s", case_id, exc)

    # 5. Build prompt with trusted evidence summaries
    prompt = construct_investigator_prompt(case, supporting + mitigating)

    # 6. Execute budgeted AI call
    try:
        raw_output = deepseek_provider.generate_hypothesis(case_id, prompt)
    except BudgetExceededError:
        return InvestigationHypothesis(
            hypothesis_id=hypo_id,
            case_id=case_id,
            status=HypothesisStatus.AI_UNAVAILABLE,
            summary="AI investigation budget limit reached",
            claims=(),
            generated_at=now,
            model_version=active_settings.model_name,
        )
    except AIProviderError:
        return InvestigationHypothesis(
            hypothesis_id=hypo_id,
            case_id=case_id,
            status=HypothesisStatus.AI_UNAVAILABLE,
            summary="AI provider request failed or timed out",
            claims=(),
            generated_at=now,
            model_version=active_settings.model_name,
        )
    except AIInvalidOutputError:
        return InvestigationHypothesis(
            hypothesis_id=hypo_id,
            case_id=case_id,
            status=HypothesisStatus.AI_INVALID_OUTPUT,
            summary="AI provider returned invalid structured output",
            claims=(),
            generated_at=now,
            model_version=active_settings.model_name,
        )

    # 7. Validate citations and claims against loaded case
    allowed_ids = set(case.evidence_ids)
    valid_claims: list[MaterialClaim] = []

    for claim in raw_output.claims:
        # Citation rule: non-empty citations, all in allowed_ids
        if len(claim.cited_evidence_ids) == 0 or not set(claim.cited_evidence_ids).issubset(
            allowed_ids
        ):
            return InvestigationHypothesis(
                hypothesis_id=hypo_id,
                case_id=case_id,
                status=HypothesisStatus.AI_INVALID_OUTPUT,
                summary="AI hypothesis cited unauthorized or empty evidence",
                claims=(),
                generated_at=now,
                model_version=active_settings.model_name,
            )
        valid_claims.append(
            MaterialClaim(
                claim_text=claim.claim_text,
                cited_evidence_ids=claim.cited_evidence_ids,
            )
        )

    return InvestigationHypothesis(
        hypothesis_id=hypo_id,
        case_id=case_id,
        status=HypothesisStatus.HYPOTHESIS_GENERATED,
        summary=raw_output.summary,
        claims=tuple(valid_claims),
        generated_at=now,
        model_version=active_settings.model_name,
    )


class InvestigatorWorkflow:
    def __init__(
        self,
        case_service: CaseService,
        evidence_store: EvidenceStore,
        graph_repo: InMemoryGraphRepository,
        provider: GuardedDeepSeekProvider | None = None,
        settings: DeepSeekSettings | None = None,
        deepseek_provider: GuardedDeepSeekProvider | None = None,
    ) -> None:
        self._case_service = case_service
        self._evidence_store = evidence_store
        self._graph_repo = graph_repo
        self._provider = provider or deepseek_provider
        self._settings = settings or (
            self._provider._settings if self._provider else DeepSeekSettings()
        )

    def run(self, case_id: str) -> InvestigationHypothesis:
        return investigate_case_workflow(
            case_id=case_id,
            case_service=self._case_service,
            evidence_store=self._evidence_store,
            graph_repo=self._graph_repo,
            settings=self._settings,
            deepseek_provider=self._provider,
        )
