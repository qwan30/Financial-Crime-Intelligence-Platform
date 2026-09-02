from datetime import UTC, datetime
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from fincrime.agent.settings import DeepSeekSettings
from fincrime.agent.tools import (
    InMemoryGraphRepository,
    ReferentialIntegrityError,
    get_fund_trace,
)
from fincrime.agent.workflow import (
    investigate_case_workflow,
)
from fincrime.cases.models import (
    AdjudicationStatus,
    AnalystFeedbackEvent,
    CaseSnapshot,
    Disposition,
)
from fincrime.cases.service import (
    CaseConflict,
    CaseNotFound,
    CaseService,
    FeedbackConflict,
)
from fincrime.evidence.models import compute_sha256_hex
from fincrime.evidence.store import EvidenceNotFound, EvidenceStore


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


class SuccessEnvelope[T](BaseDTO):
    success: Literal[True] = True
    data: T
    error: None = None


class ErrorEnvelope(BaseDTO):
    success: Literal[False] = False
    data: None = None
    error: ErrorDetail


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
    is_seed: bool = False
    is_context: bool = False


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


CaseEnvelope = Annotated[
    SuccessEnvelope[CaseResponse] | ErrorEnvelope, Field(discriminator="success")
]
WorkbenchEnvelope = Annotated[
    SuccessEnvelope[WorkbenchData] | ErrorEnvelope, Field(discriminator="success")
]
FeedbackEnvelope = Annotated[
    SuccessEnvelope[dict[str, str]] | ErrorEnvelope, Field(discriminator="success")
]


class CreateCaseRequest(BaseDTO):
    case_id: str = Field(min_length=1, max_length=128)
    seed_entity: str = Field(min_length=1, max_length=128)
    evidence_ids: list[str] = Field(default_factory=list, max_length=1000)
    trace_edge_ids: list[str] = Field(default_factory=list, max_length=1000)
    created_at: datetime | None = None
    snapshot_hash: str = Field(min_length=64, max_length=64)


class FeedbackRequest(BaseDTO):
    analyst_id: str = Field(min_length=1, max_length=128)
    disposition: Disposition
    reason: str = Field(min_length=1, max_length=2000)
    model_version: str | None = Field(default=None, max_length=128)
    event_id: str | None = Field(default=None, max_length=128)
    created_at: datetime | None = None
    snapshot_hash: str | None = Field(default=None, min_length=64, max_length=64)
    adjudication_status: AdjudicationStatus = AdjudicationStatus.PENDING


def get_case_service(request: Request) -> CaseService:
    return request.app.state.case_service  # type: ignore[no-any-return]


def get_evidence_store(request: Request) -> EvidenceStore:
    return request.app.state.evidence_store  # type: ignore[no-any-return]


def get_graph_repo(request: Request) -> InMemoryGraphRepository:
    return request.app.state.graph_repo  # type: ignore[no-any-return]


def get_settings(request: Request) -> DeepSeekSettings:
    return request.app.state.settings  # type: ignore[no-any-return]


CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
EvidenceStoreDep = Annotated[EvidenceStore, Depends(get_evidence_store)]
GraphRepoDep = Annotated[InMemoryGraphRepository, Depends(get_graph_repo)]
SettingsDep = Annotated[DeepSeekSettings, Depends(get_settings)]


def create_app(
    case_service: CaseService | None = None,
    evidence_store: EvidenceStore | None = None,
    graph_repo: InMemoryGraphRepository | None = None,
    settings: DeepSeekSettings | None = None,
    deepseek_provider: Any = None,
) -> FastAPI:
    application = FastAPI(title="Case API", version="0.1.0")

    ev_store = evidence_store or EvidenceStore()
    application.state.evidence_store = ev_store
    application.state.case_service = case_service or CaseService(evidence_store=ev_store)
    application.state.graph_repo = graph_repo or InMemoryGraphRepository()
    application.state.settings = settings or DeepSeekSettings()
    application.state.deepseek_provider = deepseek_provider

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content={
                "success": False,
                "data": None,
                "error": {"code": "VALIDATION_ERROR", "message": str(exc)},
            },
        )

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.get("/cases/{case_id}", response_model=CaseEnvelope)
    def get_case(
        case_id: str,
        service: CaseServiceDep,
    ) -> Any:
        try:
            cs = service.get(case_id)
            return SuccessEnvelope[CaseResponse](
                data=CaseResponse(
                    case_id=cs.case_id,
                    seed_entity=cs.seed_entity,
                    evidence_ids=list(cs.evidence_ids),
                    trace_edge_ids=list(cs.trace_edge_ids),
                    created_at=cs.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    snapshot_hash=cs.snapshot_hash,
                )
            )
        except CaseNotFound:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "CASE_NOT_FOUND", "message": f"Case not found: {case_id}"},
                },
            )

    @application.post("/cases", response_model=CaseEnvelope, status_code=status.HTTP_200_OK)
    def create_case(
        req: CreateCaseRequest,
        service: CaseServiceDep,
        ev_store_dep: EvidenceStoreDep,
    ) -> Any:
        dt = req.created_at or datetime.now(UTC)
        expected_hash = compute_sha256_hex(
            {
                "case_id": req.case_id,
                "seed_entity": req.seed_entity,
                "evidence_ids": tuple(sorted(set(req.evidence_ids))),
                "trace_edge_ids": tuple(sorted(set(req.trace_edge_ids))),
                "created_at": dt,
            }
        )
        if req.snapshot_hash != expected_hash:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "VALIDATION_ERROR",
                        "message": f"Snapshot hash mismatch: expected {expected_hash}, got {req.snapshot_hash}",
                    },
                },
            )

        try:
            snapshot = CaseSnapshot(
                case_id=req.case_id,
                seed_entity=req.seed_entity,
                evidence_ids=tuple(sorted(set(req.evidence_ids))),
                trace_edge_ids=tuple(sorted(set(req.trace_edge_ids))),
                created_at=dt,
                snapshot_hash=req.snapshot_hash,
            )
            created = service.create(snapshot, evidence_store=ev_store_dep)
            return SuccessEnvelope[CaseResponse](
                data=CaseResponse(
                    case_id=created.case_id,
                    seed_entity=created.seed_entity,
                    evidence_ids=list(created.evidence_ids),
                    trace_edge_ids=list(created.trace_edge_ids),
                    created_at=created.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    snapshot_hash=created.snapshot_hash,
                )
            )
        except CaseConflict as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "CASE_CONFLICT", "message": str(exc)},
                },
            )
        except EvidenceNotFound as exc:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "EVIDENCE_NOT_FOUND", "message": str(exc)},
                },
            )
        except (ValueError, ValidationError) as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "VALIDATION_ERROR", "message": str(exc)},
                },
            )

    @application.post("/cases/{case_id}/feedback", response_model=FeedbackEnvelope)
    def submit_feedback(
        case_id: str,
        req: FeedbackRequest,
        service: CaseServiceDep,
    ) -> Any:
        try:
            cs = service.get(case_id)
            event_id = req.event_id or f"fb-{case_id}-{req.analyst_id}"
            fb_dt = req.created_at or datetime.now(UTC)
            event = AnalystFeedbackEvent(
                event_id=event_id,
                analyst_id=req.analyst_id,
                case_id=case_id,
                disposition=req.disposition,
                reason=req.reason,
                created_at=fb_dt,
                snapshot_hash=req.snapshot_hash or cs.snapshot_hash,
                model_version=req.model_version,
                adjudication_status=req.adjudication_status,
            )
            service.append_feedback(event)
            return SuccessEnvelope[dict[str, str]](
                data={"status": "accepted", "eventId": event.event_id, "caseId": event.case_id}
            )
        except CaseNotFound:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "CASE_NOT_FOUND", "message": f"Case not found: {case_id}"},
                },
            )
        except FeedbackConflict as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "FEEDBACK_CONFLICT", "message": str(exc)},
                },
            )
        except (ValueError, ValidationError) as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "VALIDATION_ERROR", "message": str(exc)},
                },
            )

    @application.get("/cases/{case_id}/workbench", response_model=WorkbenchEnvelope)
    def get_workbench(
        case_id: str,
        service: CaseServiceDep,
        ev_store_dep: EvidenceStoreDep,
        graph_repo_dep: GraphRepoDep,
        settings_dep: SettingsDep,
    ) -> Any:
        try:
            cs = service.get(case_id)
            case_resp = CaseResponse(
                case_id=cs.case_id,
                seed_entity=cs.seed_entity,
                evidence_ids=list(cs.evidence_ids),
                trace_edge_ids=list(cs.trace_edge_ids),
                created_at=cs.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                snapshot_hash=cs.snapshot_hash,
            )

            # Resolve evidence items
            ev_list: list[EvidenceResponse] = []
            for eid in cs.evidence_ids:
                item = ev_store_dep.get(eid)
                ev_list.append(
                    EvidenceResponse(
                        evidence_id=item.evidence_id,
                        category=item.category.value,
                        source_reference=item.source_reference,
                        polarity=item.polarity.value,
                        snapshot_time=item.snapshot_time.astimezone(UTC).strftime(
                            "%Y-%m-%dT%H:%M:%SZ"
                        ),
                        generation_method_version=item.generation_method_version,
                        payload_summary=item.payload_summary,
                        integrity_hash=item.integrity_hash,
                        confidence=item.confidence,
                    )
                )

            # Resolve trace gracefully
            try:
                trace_res = get_fund_trace(
                    case_id=case_id,
                    case_service=service,
                    graph_repo=graph_repo_dep,
                )
                trace_resp = TraceGraphResponse(
                    nodes=[
                        TraceNodeResponse(
                            node_id=n.node_id,
                            entity_type=n.entity_type,
                            risk_score=n.risk_score,
                            is_seed=n.is_seed,
                            is_context=n.is_context,
                        )
                        for n in trace_res.nodes
                    ],
                    edges=[
                        TraceEdgeResponse(
                            edge_id=e.edge_id,
                            source=e.source,
                            target=e.target,
                            flow_amount=e.flow_amount,
                            relationship_type=e.relationship_type,
                            identity_confidence=e.identity_confidence,
                        )
                        for e in trace_res.edges
                    ],
                    is_truncated=trace_res.is_truncated,
                    total_hops=trace_res.total_hops,
                )
            except (ReferentialIntegrityError, ValueError):
                trace_resp = TraceGraphResponse(
                    nodes=[],
                    edges=[],
                    is_truncated=False,
                    total_hops=0,
                )

            # Generate hypothesis via workflow
            hyp = investigate_case_workflow(
                case_id=case_id,
                case_service=service,
                evidence_store=ev_store_dep,
                graph_repo=graph_repo_dep,
                settings=settings_dep,
                deepseek_provider=application.state.deepseek_provider,
            )
            hyp_resp = HypothesisResponse(
                hypothesis_id=hyp.hypothesis_id,
                case_id=hyp.case_id,
                status=hyp.status.value,
                summary=hyp.summary,
                claims=[
                    MaterialClaimResponse(
                        claim_text=c.claim_text,
                        cited_evidence_ids=list(c.cited_evidence_ids),
                    )
                    for c in hyp.claims
                ],
                generated_at=hyp.generated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                model_version=hyp.model_version,
            )

            return SuccessEnvelope[WorkbenchData](
                data=WorkbenchData(
                    case=case_resp,
                    evidence=ev_list,
                    trace=trace_resp,
                    hypothesis=hyp_resp,
                )
            )
        except CaseNotFound:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "CASE_NOT_FOUND", "message": f"Case not found: {case_id}"},
                },
            )

    return application


app = create_app()
