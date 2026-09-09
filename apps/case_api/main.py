from contextlib import asynccontextmanager
from datetime import UTC, datetime
import os
from typing import Annotated, Any, Literal

from fastapi import Depends, FastAPI, Header, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

from fincrime.agent.settings import DeepSeekSettings
from fincrime.agent.tools import (
    GraphRepository,
    InMemoryGraphRepository,
    ReferentialIntegrityError,
    TypologyTag,
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
    account_holder_name: str | None = None
    bank_short_name: str | None = None
    account_last4: str | None = None
    badge: TypologyTag | None = None


class TraceEdgeResponse(BaseDTO):
    edge_id: str
    source: str
    target: str
    flow_amount: float
    relationship_type: str
    identity_confidence: float
    currency: str | None = None
    timestamp: str | None = None


class TraceGraphResponse(BaseDTO):
    nodes: list[TraceNodeResponse]
    edges: list[TraceEdgeResponse]
    is_truncated: bool
    total_hops: int
    hop_by_node_id: dict[str, int] = Field(default_factory=dict)
    time_min: str | None = None
    time_max: str | None = None
    unknown_time_edge_count: int = 0


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

class PinnedEvidenceResponse(BaseDTO):
    edge_id: str
    evidence_id: str
    analyst_id: str
    typology_tag: TypologyTag | None = None
    updated_at: str
    transaction: TraceEdgeResponse


class PinEvidenceResult(BaseDTO):
    new_snapshot_hash: str = Field(serialization_alias="new_snapshot_hash")
    case: CaseResponse
    evidence: list[EvidenceResponse]
    pins: list[PinnedEvidenceResponse]


class PinEvidenceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: str = Field(min_length=1)
    analyst_id: str = Field(min_length=1)
    is_pinned: bool = Field(strict=True)
    typology_tag: TypologyTag | None = None

    @field_validator("edge_id", "analyst_id")
    @classmethod
    def _validate_non_blank(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("Field must be non-blank after trimming")
        return stripped


class ExpandGraphRequest(BaseDTO):
    node_id: str
    known_edge_ids: list[str]
    snapshot_hash: str


class WorkbenchData(BaseDTO):
    case: CaseResponse
    evidence: list[EvidenceResponse]
    trace: TraceGraphResponse
    hypothesis: HypothesisResponse
    pins: list[PinnedEvidenceResponse] = Field(default_factory=list)
    pinning_available: bool = False
    hypothesis_snapshot_hash: str | None = None
class GenerateHypothesisRequest(BaseDTO):
    snapshot_hash: str


class GenerateHypothesisResult(BaseDTO):
    snapshot_hash: str
    hypothesis: HypothesisResponse


HypothesisEnvelope = Annotated[
    SuccessEnvelope[GenerateHypothesisResult] | ErrorEnvelope, Field(discriminator="success")
]


CaseEnvelope = Annotated[
    SuccessEnvelope[CaseResponse] | ErrorEnvelope, Field(discriminator="success")
]
WorkbenchEnvelope = Annotated[
    SuccessEnvelope[WorkbenchData] | ErrorEnvelope, Field(discriminator="success")
]
PinEvidenceEnvelope = Annotated[
    SuccessEnvelope[PinEvidenceResult] | ErrorEnvelope, Field(discriminator="success")
]
TraceEnvelope = Annotated[
    SuccessEnvelope[TraceGraphResponse] | ErrorEnvelope, Field(discriminator="success")
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


def get_graph_repo(request: Request) -> GraphRepository:
    return request.app.state.graph_repo  # type: ignore[no-any-return]


def get_settings(request: Request) -> DeepSeekSettings:
    return request.app.state.settings  # type: ignore[no-any-return]


CaseServiceDep = Annotated[CaseService, Depends(get_case_service)]
EvidenceStoreDep = Annotated[EvidenceStore, Depends(get_evidence_store)]
GraphRepoDep = Annotated[GraphRepository, Depends(get_graph_repo)]
SettingsDep = Annotated[DeepSeekSettings, Depends(get_settings)]


def create_app(
    case_service: CaseService | None = None,
    evidence_store: EvidenceStore | None = None,
    graph_repo: GraphRepository | None = None,
    settings: DeepSeekSettings | None = None,
    deepseek_provider: Any = None,
    *,
    database_url: str | None = None,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import threading
        resolved_db_url = database_url or os.getenv("DATABASE_URL")
        engine = None
        http_client = None
        if (case_service is None and evidence_store is None and graph_repo is None) and resolved_db_url:
            from sqlalchemy import create_engine, text
            from fincrime.storage.postgres import (
                PostgresCaseRepository,
                PostgresEvidenceRepository,
                PostgresGraphRepository,
            )
            try:
                engine = create_engine(resolved_db_url)
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1 FROM cases LIMIT 1"))
            except Exception as exc:
                if engine is not None:
                    engine.dispose()
                raise RuntimeError(f"Database connection or schema check failed: {exc}") from exc

            pg_ev_repo = PostgresEvidenceRepository(engine)
            pg_ev_store = EvidenceStore(repository=pg_ev_repo)
            pg_case_repo = PostgresCaseRepository(engine)
            pg_case_service = CaseService(evidence_store=pg_ev_store, repository=pg_case_repo)
            pg_graph_repo = PostgresGraphRepository(engine)

            app.state.engine = engine
            app.state.evidence_store = pg_ev_store
            app.state.case_service = pg_case_service
            app.state.graph_repo = pg_graph_repo
            app.state.pinning_available = True
        else:
            app.state.engine = None
            app.state.pinning_available = False

        if deepseek_provider is not None:
            app.state.deepseek_provider = deepseek_provider
        else:
            api_key_str = os.getenv("DEEPSEEK_API_KEY")
            if api_key_str:
                import httpx
                from pydantic import SecretStr
                from fincrime.agent.deepseek import GuardedDeepSeekProvider
                from fincrime.agent.settings import BudgetController, DeepSeekSettings
                model_name = os.getenv("DEEPSEEK_MODEL", "deepseek-v4-flash")
                ds_settings = DeepSeekSettings(
                    api_key=SecretStr(api_key_str),
                    model_name=model_name,
                )
                budget_ctrl = BudgetController(settings=ds_settings)
                http_client = httpx.Client(timeout=ds_settings.timeout_seconds)
                app.state.settings = ds_settings
                app.state.deepseek_provider = GuardedDeepSeekProvider(
                    settings=ds_settings,
                    budget_controller=budget_ctrl,
                    client=http_client,
                )
            else:
                app.state.deepseek_provider = None

        yield

        if http_client is not None:
            http_client.close()
        if engine is not None:
            engine.dispose()

    application = FastAPI(title="Case API", version="0.1.0", lifespan=lifespan)

    import threading
    ev_store = evidence_store or EvidenceStore()
    application.state.evidence_store = ev_store
    application.state.case_service = case_service or CaseService(evidence_store=ev_store)
    application.state.graph_repo = graph_repo or InMemoryGraphRepository()
    application.state.settings = settings or DeepSeekSettings()
    application.state.deepseek_provider = deepseek_provider
    application.state.pinning_available = False
    application.state.engine = None
    application.state.hypothesis_cache = {}
    application.state.in_flight_locks = {}
    application.state.global_cache_lock = threading.Lock()
    application.state.settings = settings or DeepSeekSettings()
    application.state.deepseek_provider = deepseek_provider
    application.state.pinning_available = False
    application.state.engine = None
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

    @application.post("/cases/{case_id}/evidence/pin", response_model=PinEvidenceEnvelope)
    def pin_evidence(
        case_id: str,
        command: PinEvidenceRequest,
        request: Request,
        if_match: Annotated[str | None, Header()] = None,
    ) -> Any:
        if not if_match:
            return JSONResponse(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "SNAPSHOT_REQUIRED", "message": "If-Match header is required"},
                },
            )
        expected_hash = if_match.strip().strip('"')

        if not getattr(request.app.state, "pinning_available", False) or getattr(request.app.state, "engine", None) is None:
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "PERSISTENCE_UNAVAILABLE", "message": "PostgreSQL storage is not configured"},
                },
            )

        from fincrime.cases.canvas import SnapshotConflict
        from fincrime.cases.pinning import EdgeNotInCase, PinCommand, PinningService

        pin_service = PinningService(request.app.state.engine)
        cmd = PinCommand(
            edge_id=command.edge_id,
            analyst_id=command.analyst_id,
            is_pinned=command.is_pinned,
            typology_tag=command.typology_tag,
        )
        try:
            pinned_case = pin_service.set_pin(case_id, cmd, expected_hash)
        except CaseNotFound:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "CASE_NOT_FOUND", "message": f"Case not found: {case_id}"},
                },
            )
        except EdgeNotInCase:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "EDGE_NOT_IN_CASE", "message": f"Edge not in case: {command.edge_id}"},
                },
            )
        except SnapshotConflict as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "SNAPSHOT_CONFLICT", "message": str(exc)},
                },
            )
        except ReferentialIntegrityError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "TRACE_INTEGRITY_ERROR", "message": str(exc)},
                },
            )

        cs = pinned_case.case
        case_resp = CaseResponse(
            case_id=cs.case_id,
            seed_entity=cs.seed_entity,
            evidence_ids=list(cs.evidence_ids),
            trace_edge_ids=list(cs.trace_edge_ids),
            created_at=cs.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
            snapshot_hash=cs.snapshot_hash,
        )
        ev_list = [
            EvidenceResponse(
                evidence_id=it.evidence_id,
                category=it.category.value,
                source_reference=it.source_reference,
                polarity=it.polarity.value,
                snapshot_time=it.snapshot_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                generation_method_version=it.generation_method_version,
                payload_summary=it.payload_summary,
                integrity_hash=it.integrity_hash,
                confidence=it.confidence,
            )
            for it in pinned_case.evidence
        ]
        pins_list = [
            PinnedEvidenceResponse(
                edge_id=p.edge_id,
                evidence_id=p.evidence_id,
                analyst_id=p.analyst_id,
                typology_tag=p.typology_tag,
                updated_at=p.updated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                transaction=TraceEdgeResponse(
                    edge_id=p.transaction.edge_id,
                    source=p.transaction.source,
                    target=p.transaction.target,
                    flow_amount=p.transaction.flow_amount,
                    relationship_type=p.transaction.relationship_type,
                    identity_confidence=p.transaction.identity_confidence,
                    currency=p.transaction.currency,
                    timestamp=p.transaction.timestamp.isoformat() if p.transaction.timestamp else None,
                ),
            )
            for p in pinned_case.pins
        ]

        # Invalidate older cached revisions for this case
        cache_lock = getattr(request.app.state, "global_cache_lock", None)
        cache = getattr(request.app.state, "hypothesis_cache", None)
        if cache_lock is not None and cache is not None:
            with cache_lock:
                keys_to_del = [k for k in cache if k[0] == case_id]
                for k in keys_to_del:
                    del cache[k]

        return SuccessEnvelope[PinEvidenceResult](
            data=PinEvidenceResult(
                new_snapshot_hash=cs.snapshot_hash,
                case=case_resp,
                evidence=ev_list,
                pins=pins_list,
            )
        )

    @application.post("/cases/{case_id}/graph/expand", response_model=TraceEnvelope)
    def expand_graph(
        case_id: str,
        req: ExpandGraphRequest,
        service: CaseServiceDep,
        graph_repo_dep: GraphRepoDep,
    ) -> Any:
        from fincrime.cases.canvas import CanvasService, InvalidExpansion, SnapshotConflict

        canvas_svc = CanvasService(cases=service, graph=graph_repo_dep)
        try:
            trace_res = canvas_svc.expand(
                case_id=case_id,
                node_id=req.node_id,
                known_edge_ids=tuple(req.known_edge_ids),
                snapshot_hash=req.snapshot_hash,
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
        except SnapshotConflict as exc:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "SNAPSHOT_CONFLICT", "message": str(exc)},
                },
            )
        except InvalidExpansion as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "INVALID_EXPANSION", "message": str(exc)},
                },
            )
        except ReferentialIntegrityError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "TRACE_INTEGRITY_ERROR", "message": str(exc)},
                },
            )

        trace_resp = TraceGraphResponse(
            nodes=[
                TraceNodeResponse(
                    node_id=n.node_id,
                    entity_type=n.entity_type,
                    risk_score=n.risk_score,
                    is_seed=n.is_seed,
                    is_context=n.is_context,
                    account_holder_name=n.account_holder_name,
                    bank_short_name=n.bank_short_name,
                    account_last4=n.account_last4,
                    badge=n.badge,
                )
                for n in trace_res.graph.nodes
            ],
            edges=[
                TraceEdgeResponse(
                    edge_id=e.edge_id,
                    source=e.source,
                    target=e.target,
                    flow_amount=e.flow_amount,
                    relationship_type=e.relationship_type,
                    identity_confidence=e.identity_confidence,
                    currency=e.currency,
                    timestamp=e.timestamp.isoformat() if e.timestamp else None,
                )
                for e in trace_res.graph.edges
            ],
            is_truncated=trace_res.graph.is_truncated,
            total_hops=trace_res.graph.total_hops,
            hop_by_node_id=trace_res.hop_by_node_id,
            time_min=trace_res.time_min.isoformat() if trace_res.time_min else None,
            time_max=trace_res.time_max.isoformat() if trace_res.time_max else None,
            unknown_time_edge_count=trace_res.unknown_time_edge_count,
        )
        return SuccessEnvelope[TraceGraphResponse](data=trace_resp)


    @application.post("/cases/{case_id}/hypothesis", response_model=HypothesisEnvelope)
    def generate_hypothesis(
        case_id: str,
        body: GenerateHypothesisRequest,
        request: Request,
        service: CaseServiceDep,
        ev_store_dep: EvidenceStoreDep,
        graph_repo_dep: GraphRepoDep,
        settings_dep: SettingsDep,
    ) -> Any:
        import threading
        pinning_available = getattr(request.app.state, "pinning_available", False)
        engine = getattr(request.app.state, "engine", None)

        try:
            if pinning_available and engine is not None:
                from fincrime.cases.pinning import PinningService
                pin_svc = PinningService(engine)
                pinned_case = pin_svc.read(case_id)
                cs = pinned_case.case
                pinned_ids = tuple(p.evidence_id for p in pinned_case.pins)
            else:
                cs = service.get(case_id)
                pinned_ids = ()
        except CaseNotFound:
            return JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "CASE_NOT_FOUND", "message": f"Case not found: {case_id}"},
                },
            )

        # Validate snapshot hash before provider invocation
        if body.snapshot_hash != cs.snapshot_hash:
            return JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content={
                    "success": False,
                    "data": None,
                    "error": {
                        "code": "SNAPSHOT_CONFLICT",
                        "message": f"Snapshot hash conflict: expected {cs.snapshot_hash}, got {body.snapshot_hash}",
                    },
                },
            )

        cache_key = (case_id, cs.snapshot_hash)
        global_lock: threading.Lock = request.app.state.global_cache_lock
        cache: dict[tuple[str, str], HypothesisResponse] = request.app.state.hypothesis_cache
        locks: dict[tuple[str, str], threading.Lock] = request.app.state.in_flight_locks

        with global_lock:
            if cache_key in cache:
                return SuccessEnvelope(
                    data=GenerateHypothesisResult(
                        snapshot_hash=cs.snapshot_hash,
                        hypothesis=cache[cache_key],
                    )
                )
            if cache_key not in locks:
                locks[cache_key] = threading.Lock()
            key_lock = locks[cache_key]

        with key_lock:
            with global_lock:
                if cache_key in cache:
                    return SuccessEnvelope(
                        data=GenerateHypothesisResult(
                            snapshot_hash=cs.snapshot_hash,
                            hypothesis=cache[cache_key],
                        )
                    )

            from fincrime.agent.workflow import investigate_case_workflow
            provider = getattr(request.app.state, "deepseek_provider", None)
            res = investigate_case_workflow(
                case_id=case_id,
                case_service=service,
                evidence_store=ev_store_dep,
                graph_repo=graph_repo_dep,
                settings=settings_dep,
                deepseek_provider=provider,
                case_snapshot=cs,
                pinned_evidence_ids=pinned_ids,
            )

            # Recheck current case hash before caching
            if pinning_available and engine is not None:
                from fincrime.cases.pinning import PinningService
                rechecked = PinningService(engine).read(case_id)
                if rechecked.case.snapshot_hash != cs.snapshot_hash:
                    return JSONResponse(
                        status_code=status.HTTP_409_CONFLICT,
                        content={
                            "success": False,
                            "data": None,
                            "error": {
                                "code": "SNAPSHOT_CONFLICT",
                                "message": "Case snapshot hash changed during hypothesis generation",
                            },
                        },
                    )

            hyp_resp = HypothesisResponse(
                hypothesis_id=res.hypothesis_id,
                case_id=res.case_id,
                status=res.status.value,
                summary=res.summary,
                claims=[
                    MaterialClaimResponse(
                        claim_text=c.claim_text,
                        cited_evidence_ids=list(c.cited_evidence_ids),
                    )
                    for c in res.claims
                ],
                generated_at=res.generated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                model_version=res.model_version,
            )

            with global_lock:
                keys_to_del = [k for k in cache if k[0] == case_id]
                for k in keys_to_del:
                    del cache[k]
                cache[cache_key] = hyp_resp

            return SuccessEnvelope(
                data=GenerateHypothesisResult(
                    snapshot_hash=cs.snapshot_hash,
                    hypothesis=hyp_resp,
                )
            )

    @application.get("/cases/{case_id}/workbench", response_model=WorkbenchEnvelope)
    def get_workbench(
        case_id: str,
        request: Request,
        service: CaseServiceDep,
        ev_store_dep: EvidenceStoreDep,
        graph_repo_dep: GraphRepoDep,
    ) -> Any:
        try:
            pins_resp: list[PinnedEvidenceResponse] = []
            pinning_available = getattr(request.app.state, "pinning_available", False)
            if pinning_available and getattr(request.app.state, "engine", None) is not None:
                from fincrime.cases.pinning import PinningService

                pin_service = PinningService(request.app.state.engine)
                pinned_case = pin_service.read(case_id)
                cs = pinned_case.case
                ev_items = list(pinned_case.evidence)
                for p in pinned_case.pins:
                    pins_resp.append(
                        PinnedEvidenceResponse(
                            edge_id=p.edge_id,
                            evidence_id=p.evidence_id,
                            analyst_id=p.analyst_id,
                            typology_tag=p.typology_tag,
                            updated_at=p.updated_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                            transaction=TraceEdgeResponse(
                                edge_id=p.transaction.edge_id,
                                source=p.transaction.source,
                                target=p.transaction.target,
                                flow_amount=p.transaction.flow_amount,
                                relationship_type=p.transaction.relationship_type,
                                identity_confidence=p.transaction.identity_confidence,
                                currency=p.transaction.currency,
                                timestamp=p.transaction.timestamp.isoformat() if p.transaction.timestamp else None,
                            ),
                        )
                    )
            else:
                cs = service.get(case_id)
                ev_items = [ev_store_dep.get(eid) for eid in cs.evidence_ids]

            case_resp = CaseResponse(
                case_id=cs.case_id,
                seed_entity=cs.seed_entity,
                evidence_ids=list(cs.evidence_ids),
                trace_edge_ids=list(cs.trace_edge_ids),
                created_at=cs.created_at.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                snapshot_hash=cs.snapshot_hash,
            )

            ev_list: list[EvidenceResponse] = [
                EvidenceResponse(
                    evidence_id=item.evidence_id,
                    category=item.category.value,
                    source_reference=item.source_reference,
                    polarity=item.polarity.value,
                    snapshot_time=item.snapshot_time.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    generation_method_version=item.generation_method_version,
                    payload_summary=item.payload_summary,
                    integrity_hash=item.integrity_hash,
                    confidence=item.confidence,
                )
                for item in ev_items
            ]

            from fincrime.cases.canvas import CanvasService

            canvas_svc = CanvasService(cases=service, graph=graph_repo_dep)
            trace_res = canvas_svc.initial(case_id, case_snapshot=cs)
            trace_resp = TraceGraphResponse(
                nodes=[
                    TraceNodeResponse(
                        node_id=n.node_id,
                        entity_type=n.entity_type,
                        risk_score=n.risk_score,
                        is_seed=n.is_seed,
                        is_context=n.is_context,
                        account_holder_name=n.account_holder_name,
                        bank_short_name=n.bank_short_name,
                        account_last4=n.account_last4,
                        badge=n.badge,
                    )
                    for n in trace_res.graph.nodes
                ],
                edges=[
                    TraceEdgeResponse(
                        edge_id=e.edge_id,
                        source=e.source,
                        target=e.target,
                        flow_amount=e.flow_amount,
                        relationship_type=e.relationship_type,
                        identity_confidence=e.identity_confidence,
                        currency=e.currency,
                        timestamp=e.timestamp.isoformat() if e.timestamp else None,
                    )
                    for e in trace_res.graph.edges
                ],
                is_truncated=trace_res.graph.is_truncated,
                total_hops=trace_res.graph.total_hops,
                hop_by_node_id=trace_res.hop_by_node_id,
                time_min=trace_res.time_min.isoformat() if trace_res.time_min else None,
                time_max=trace_res.time_max.isoformat() if trace_res.time_max else None,
                unknown_time_edge_count=trace_res.unknown_time_edge_count,
            )

            ai_status = "INSUFFICIENT_EVIDENCE" if not cs.evidence_ids else "AI_UNAVAILABLE"
            cache = getattr(request.app.state, "hypothesis_cache", {})
            cache_key = (case_id, cs.snapshot_hash)
            if cache_key in cache:
                hyp_resp = cache[cache_key]
                hyp_hash = cs.snapshot_hash
            else:
                ai_status = "INSUFFICIENT_EVIDENCE" if not cs.evidence_ids else "AI_UNAVAILABLE"
                ai_summary = (
                    "AI provider disabled (LLM_OFF mode)"
                    if getattr(request.app.state, "deepseek_provider", None) is None
                    or getattr(settings_dep, "api_key", None) is None
                    else "Hypothesis not generated for this snapshot"
                )
                hyp_resp = HypothesisResponse(
                    hypothesis_id=f"hyp-avail-{cs.case_id}",
                    case_id=cs.case_id,
                    status=ai_status,
                    summary=ai_summary,
                    claims=[],
                    generated_at=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    model_version=None,
                )
                hyp_hash = None

            return SuccessEnvelope[WorkbenchData](
                data=WorkbenchData(
                    case=case_resp,
                    evidence=ev_list,
                    trace=trace_resp,
                    hypothesis=hyp_resp,
                    pins=pins_resp,
                    pinning_available=pinning_available,
                    hypothesis_snapshot_hash=hyp_hash,
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
        except ReferentialIntegrityError as exc:
            return JSONResponse(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                content={
                    "success": False,
                    "data": None,
                    "error": {"code": "TRACE_INTEGRITY_ERROR", "message": str(exc)},
                },
            )

    return application


app = create_app()
