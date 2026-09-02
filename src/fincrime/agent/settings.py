from __future__ import annotations

import threading
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, SecretStr


class AttemptStatus(StrEnum):
    RESERVED = "RESERVED"
    DISPATCHED = "DISPATCHED"
    RECONCILED = "RECONCILED"
    RELEASED = "RELEASED"


class BudgetExceededError(Exception):
    pass


class DeepSeekSettings(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    api_key: SecretStr | None = None
    model_name: str = "deepseek-v4-flash"
    api_base_url: str = "https://api.deepseek.com/v1"
    monthly_cap_vnd: int = Field(default=200000, gt=0, le=5000000)
    max_calls_per_case: int = Field(default=6, gt=0, le=20)
    max_input_tokens_per_case: int = Field(default=60000, gt=0, le=200000)
    max_output_tokens_per_case: int = Field(default=8000, gt=0, le=32000)
    timeout_seconds: float = Field(default=60.0, gt=0.0, le=300.0)


def calc_reserved_cost(input_tokens: int, max_output_tokens: int) -> int:
    if input_tokens < 0 or max_output_tokens < 0:
        raise ValueError("Token counts must be non-negative")
    return (7 * input_tokens + 28 * max_output_tokens + 1999) // 2000


def calc_actual_cost(actual_input: int, actual_output: int) -> int:
    return calc_reserved_cost(actual_input, actual_output)


def is_strict_int_gt_zero(val: Any) -> bool:
    return type(val) is int and not isinstance(val, bool) and val > 0


class AttemptRecord(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt_id: str
    case_id: str
    month_key: str
    reserved_input: int
    reserved_output: int
    reserved_vnd: int
    actual_input: int = 0
    actual_output: int = 0
    actual_vnd: int = 0
    status: AttemptStatus = AttemptStatus.RESERVED
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ReservationToken(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    attempt_id: str
    case_id: str
    reserved_input: int
    reserved_output: int
    reserved_vnd: int


class BudgetController:
    def __init__(self, settings: DeepSeekSettings | None = None) -> None:
        self._settings = settings or DeepSeekSettings()
        self._lock = threading.Lock()
        self._attempts: dict[str, AttemptRecord] = {}
        self._attempt_counter = 0

    def get_month_key(self, dt: datetime | None = None) -> str:
        d = dt or datetime.now(UTC)
        return d.strftime("%Y-%m")

    def reserve(self, case_id: str, prompt: str, now: datetime | None = None) -> ReservationToken:
        current_time = now or datetime.now(UTC)
        month_key = self.get_month_key(current_time)
        input_allowance = len(prompt.encode("utf-8"))

        with self._lock:
            case_attempts = [
                a
                for a in self._attempts.values()
                if a.case_id == case_id and a.status != AttemptStatus.RELEASED
            ]

            settled_calls = len([a for a in case_attempts if a.status == AttemptStatus.RECONCILED])
            pending_calls = len(
                [
                    a
                    for a in case_attempts
                    if a.status in (AttemptStatus.RESERVED, AttemptStatus.DISPATCHED)
                ]
            )
            if settled_calls + pending_calls + 1 > self._settings.max_calls_per_case:
                raise BudgetExceededError(
                    f"Case call limit exceeded / reached ({self._settings.max_calls_per_case})"
                )

            settled_in = sum(
                a.actual_input for a in case_attempts if a.status == AttemptStatus.RECONCILED
            )
            pending_in = sum(
                a.reserved_input
                for a in case_attempts
                if a.status in (AttemptStatus.RESERVED, AttemptStatus.DISPATCHED)
            )
            if settled_in + pending_in + input_allowance > self._settings.max_input_tokens_per_case:
                raise BudgetExceededError(
                    f"Case input token limit exceeded / reached ({self._settings.max_input_tokens_per_case})"
                )

            settled_out = sum(
                a.actual_output for a in case_attempts if a.status == AttemptStatus.RECONCILED
            )
            pending_out = sum(
                a.reserved_output
                for a in case_attempts
                if a.status in (AttemptStatus.RESERVED, AttemptStatus.DISPATCHED)
            )
            available_out = self._settings.max_output_tokens_per_case - settled_out - pending_out
            if available_out <= 0:
                raise BudgetExceededError(
                    f"Case output token limit reached ({self._settings.max_output_tokens_per_case})"
                )

            reserved_output = min(available_out, self._settings.max_output_tokens_per_case)
            reserved_vnd = calc_reserved_cost(input_allowance, reserved_output)

            month_attempts = [
                a
                for a in self._attempts.values()
                if a.month_key == month_key and a.status != AttemptStatus.RELEASED
            ]
            settled_vnd_month = sum(
                a.actual_vnd for a in month_attempts if a.status == AttemptStatus.RECONCILED
            )
            pending_vnd_month = sum(
                a.reserved_vnd
                for a in month_attempts
                if a.status in (AttemptStatus.RESERVED, AttemptStatus.DISPATCHED)
            )
            total_active_commitment = settled_vnd_month + pending_vnd_month

            if total_active_commitment + reserved_vnd > self._settings.monthly_cap_vnd:
                raise BudgetExceededError(
                    f"Monthly budget cap exceeded / reached ({self._settings.monthly_cap_vnd} VND, "
                    f"committed: {total_active_commitment + reserved_vnd})"
                )

            self._attempt_counter += 1
            attempt_id = f"att-{self._attempt_counter:06d}"
            record = AttemptRecord(
                attempt_id=attempt_id,
                case_id=case_id,
                month_key=month_key,
                reserved_input=input_allowance,
                reserved_output=reserved_output,
                reserved_vnd=reserved_vnd,
                status=AttemptStatus.RESERVED,
                created_at=current_time,
            )
            self._attempts[attempt_id] = record

            return ReservationToken(
                attempt_id=attempt_id,
                case_id=case_id,
                reserved_input=input_allowance,
                reserved_output=reserved_output,
                reserved_vnd=reserved_vnd,
            )

    def mark_dispatched(self, token: ReservationToken) -> None:
        with self._lock:
            rec = self._attempts.get(token.attempt_id)
            if not rec:
                raise KeyError(f"Attempt not found: {token.attempt_id}")
            if rec.status != AttemptStatus.RESERVED:
                raise ValueError(
                    f"Cannot mark dispatched: attempt '{token.attempt_id}' is in status '{rec.status}' (must be RESERVED)"
                )
            self._attempts[token.attempt_id] = AttemptRecord(
                attempt_id=rec.attempt_id,
                case_id=rec.case_id,
                month_key=rec.month_key,
                reserved_input=rec.reserved_input,
                reserved_output=rec.reserved_output,
                reserved_vnd=rec.reserved_vnd,
                status=AttemptStatus.DISPATCHED,
                created_at=rec.created_at,
            )

    def reconcile(
        self,
        token: ReservationToken,
        actual_in: int | None = None,
        actual_out: int | None = None,
        actual_input: int | None = None,
        actual_output: int | None = None,
    ) -> AttemptRecord:
        resolved_in = actual_in if actual_in is not None else actual_input
        resolved_out = actual_out if actual_out is not None else actual_output

        with self._lock:
            rec = self._attempts.get(token.attempt_id)
            if not rec:
                raise KeyError(f"Attempt not found: {token.attempt_id}")
            if rec.status != AttemptStatus.DISPATCHED:
                raise ValueError(
                    f"Cannot reconcile attempt '{token.attempt_id}' with status '{rec.status}' (must be DISPATCHED)"
                )

            # If either count is not a valid strict int > 0, retain conservative reservation
            if not is_strict_int_gt_zero(resolved_in) or not is_strict_int_gt_zero(resolved_out):
                act_in = rec.reserved_input
                act_out = rec.reserved_output
                act_vnd = rec.reserved_vnd
            else:
                act_in = resolved_in  # type: ignore[assignment]
                act_out = resolved_out  # type: ignore[assignment]
                act_vnd = calc_actual_cost(act_in, act_out)

            reconciled = AttemptRecord(
                attempt_id=rec.attempt_id,
                case_id=rec.case_id,
                month_key=rec.month_key,
                reserved_input=rec.reserved_input,
                reserved_output=rec.reserved_output,
                reserved_vnd=rec.reserved_vnd,
                actual_input=act_in,
                actual_output=act_out,
                actual_vnd=act_vnd,
                status=AttemptStatus.RECONCILED,
                created_at=rec.created_at,
            )
            self._attempts[token.attempt_id] = reconciled
            return reconciled

    def release(self, token: ReservationToken) -> None:
        with self._lock:
            rec = self._attempts.get(token.attempt_id)
            if not rec:
                raise KeyError(f"Attempt not found: {token.attempt_id}")
            if rec.status != AttemptStatus.RESERVED:
                raise ValueError(
                    f"Cannot release attempt with status '{rec.status}' (release permitted only if unattempted / RESERVED)"
                )
            self._attempts[token.attempt_id] = AttemptRecord(
                attempt_id=rec.attempt_id,
                case_id=rec.case_id,
                month_key=rec.month_key,
                reserved_input=rec.reserved_input,
                reserved_output=rec.reserved_output,
                reserved_vnd=rec.reserved_vnd,
                status=AttemptStatus.RELEASED,
                created_at=rec.created_at,
            )
