from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal, Self

from pydantic import (
    AwareDatetime,
    BaseModel,
    ConfigDict,
    Field,
    model_validator,
)

from fincrime.data.provenance import Hash, NonBlank
from fincrime.evidence.models import canonical_json_bytes, compute_sha256_hex
from fincrime.graph.events import TransactionEvent


def format_iso_datetime(dt: datetime) -> str:
    """Format aware datetime in UTC with microsecond precision and 'Z' suffix."""
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError("datetime must be timezone-aware")
    return dt.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


_EPOCH_UTC = datetime(1970, 1, 1, tzinfo=UTC)
_CEILING_UTC = datetime(9999, 12, 31, 23, 59, 59, 999999, tzinfo=UTC)


def duration_microseconds(td: timedelta) -> int:
    """Exact integer microsecond duration: days * 86_400_000_000 + seconds * 1_000_000 + microseconds."""
    return td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds


timedelta_to_microseconds = duration_microseconds


def datetime_to_epoch_microseconds(dt: datetime) -> int:
    """Exact non-negative integer microseconds since UTC epoch."""
    td = dt.astimezone(UTC) - _EPOCH_UTC
    return td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds


datetime_to_usec = datetime_to_epoch_microseconds


def datetime_to_descending_usec(dt: datetime) -> int:
    """Exact non-negative integer microsecond distance to ceiling epoch for descending sorting."""
    td = _CEILING_UTC - dt.astimezone(UTC)
    return td.days * 86_400_000_000 + td.seconds * 1_000_000 + td.microseconds


def _deep_format_datetimes(val: Any) -> Any:
    """Recursively replace all datetime instances with formatted UTC microsecond strings."""
    if isinstance(val, datetime):
        return format_iso_datetime(val)
    if isinstance(val, dict):
        return {k: _deep_format_datetimes(v) for k, v in val.items()}
    if isinstance(val, (list, tuple)):
        return [_deep_format_datetimes(v) for v in val]
    return val


class TraceLabError(Exception):
    """Domain error for TraceLab operations with an explicit error code."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message


class AccountSeed(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["account"] = "account"
    account_id: NonBlank


class TransactionSeed(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    kind: Literal["transaction"] = "transaction"
    edge_id: NonBlank


class TraceRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    seed: Annotated[AccountSeed | TransactionSeed, Field(discriminator="kind")]
    direction: Literal["forward", "backward", "both"]
    window_start: AwareDatetime
    window_end: AwareDatetime
    max_gap_microseconds: int | None = Field(default=None, ge=0)
    max_hops: int = Field(default=4, ge=1, le=4)
    max_edges: int = Field(default=100, ge=1, le=100)

    @model_validator(mode="after")
    def _validate_window(self) -> Self:
        if self.window_start > self.window_end:
            raise ValueError("window_start must be <= window_end")
        return self


ReasonCode = Literal[
    "SEED_INCIDENT",
    "ANCHOR_TRANSACTION",
    "TEMPORAL_ORDER",
    "SAME_TIMESTAMP_ORDER_UNKNOWN",
    "WITHIN_GAP",
]

REASON_CODE_ORDER: tuple[ReasonCode, ...] = (
    "SEED_INCIDENT",
    "ANCHOR_TRANSACTION",
    "TEMPORAL_ORDER",
    "SAME_TIMESTAMP_ORDER_UNKNOWN",
    "WITHIN_GAP",
)


class TraceStep(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_id: NonBlank
    previous_edge_id: str | None = None
    delta_microseconds: int | None = Field(default=None, ge=0)
    reason_codes: tuple[ReasonCode, ...]


TerminalReason = Literal["DEAD_END", "HOP_LIMIT", "CYCLE_CLOSED"]


class TracePath(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path_id: Hash
    direction: Literal["forward", "backward"]
    edge_ids: tuple[str, ...]
    steps: tuple[TraceStep, ...]
    terminal_reason: TerminalReason | None = None


ExclusionReason = Literal[
    "OUTSIDE_WINDOW",
    "TEMPORAL_ORDER_VIOLATION",
    "GAP_EXCEEDED",
    "EDGE_ALREADY_IN_PATH",
]

EXCLUSION_REASONS: tuple[ExclusionReason, ...] = (
    "OUTSIDE_WINDOW",
    "TEMPORAL_ORDER_VIOLATION",
    "GAP_EXCEEDED",
    "EDGE_ALREADY_IN_PATH",
)


class ExcludedTransition(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    path_id: str | None = None
    direction: Literal["forward", "backward"]
    edge_id: NonBlank
    reason: ExclusionReason


class RootBranch(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    direction: Literal["forward", "backward"]
    counterparty_id: NonBlank


ResultStatus = Literal["EXHAUSTED_WITHIN_LIMITS", "TRUNCATED", "SEED_NOT_FOUND"]
StopReason = Literal["EDGE_BUDGET", "WORK_BUDGET", "PATH_BUDGET", "HOP_LIMIT"]

STOP_REASONS_ORDER: tuple[StopReason, ...] = (
    "EDGE_BUDGET",
    "WORK_BUDGET",
    "PATH_BUDGET",
    "HOP_LIMIT",
)


class TraceResult(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    edge_ids: tuple[str, ...]
    transactions: tuple[TransactionEvent, ...]
    paths: tuple[TracePath, ...]
    excluded_transition_counts: dict[str, int]
    excluded_transition_examples: tuple[ExcludedTransition, ...]
    exclusion_examples_truncated: bool
    examined_transitions: int = Field(ge=0)
    admitted_path_states: int = Field(ge=0)
    returned_root_branches: tuple[RootBranch, ...]
    status: ResultStatus
    stop_reasons: tuple[StopReason, ...]
    path_scope: Literal["ACCEPTED_PREFIXES"] = "ACCEPTED_PREFIXES"
    max_examined_transitions: int = 10000
    max_path_states: int = 1000
    max_exclusion_examples: int = 200


class SnapshotDescriptor(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    snapshot_id: Hash
    source_id: NonBlank
    artifact_sha256: Hash
    lineage_sha256: Hash
    cutoff: AwareDatetime
    transaction_count: int = Field(ge=0)
    time_basis: Literal["SYNTHETIC_TICKS", "EVENT_TIME"]
    observation_start: AwareDatetime | None = None
    tick_duration_microseconds: int | None = Field(default=None, ge=0)


class TraceExport(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    format_version: Literal["tracelab-1"] = "tracelab-1"
    algorithm_version: Literal["breadth-temporal-1"] = "breadth-temporal-1"
    interpretation: Literal["TEMPORALLY_FEASIBLE_CANDIDATES_NOT_FUNDS_ATTRIBUTION"] = (
        "TEMPORALLY_FEASIBLE_CANDIDATES_NOT_FUNDS_ATTRIBUTION"
    )
    snapshot: SnapshotDescriptor
    request: TraceRequest
    result: TraceResult
    result_sha256: Hash

    @classmethod
    def create(
        cls,
        snapshot: SnapshotDescriptor,
        request: TraceRequest,
        result: TraceResult,
    ) -> TraceExport:
        """Create a TraceExport computing result_sha256 over all fields except result_sha256."""
        payload = {
            "format_version": "tracelab-1",
            "algorithm_version": "breadth-temporal-1",
            "interpretation": "TEMPORALLY_FEASIBLE_CANDIDATES_NOT_FUNDS_ATTRIBUTION",
            "snapshot": snapshot.model_dump(mode="python"),
            "request": request.model_dump(mode="python"),
            "result": result.model_dump(mode="python"),
        }
        prepared = _deep_format_datetimes(payload)
        digest = compute_sha256_hex(prepared)
        return cls(
            format_version="tracelab-1",
            algorithm_version="breadth-temporal-1",
            interpretation="TEMPORALLY_FEASIBLE_CANDIDATES_NOT_FUNDS_ATTRIBUTION",
            snapshot=snapshot,
            request=request,
            result=result,
            result_sha256=digest,
        )

    def to_canonical_json_bytes(self) -> bytes:
        """Serialize export to canonical JSON bytes with microsecond UTC datetimes."""
        payload = self.model_dump(mode="python")
        prepared = _deep_format_datetimes(payload)
        return canonical_json_bytes(prepared)
