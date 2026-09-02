from __future__ import annotations

import concurrent.futures

import pytest
from pydantic import ValidationError

from fincrime.agent.settings import (
    AttemptStatus,
    BudgetController,
    BudgetExceededError,
    DeepSeekSettings,
    ReservationToken,
    calc_actual_cost,
    calc_reserved_cost,
)


def test_deepseek_settings_defaults_and_validation() -> None:
    settings = DeepSeekSettings()
    assert settings.api_key is None
    assert settings.model_name == "deepseek-v4-flash"
    assert settings.api_base_url == "https://api.deepseek.com/v1"
    assert settings.monthly_cap_vnd == 200000
    assert settings.max_calls_per_case == 6
    assert settings.max_input_tokens_per_case == 60000
    assert settings.max_output_tokens_per_case == 8000
    assert settings.timeout_seconds == 60.0


def test_deepseek_settings_immutability_and_bounds() -> None:
    settings = DeepSeekSettings()
    with pytest.raises(ValidationError):
        settings.monthly_cap_vnd = 300000  # type: ignore[misc]

    # Reject zero or negative bounds
    with pytest.raises(ValidationError):
        DeepSeekSettings(monthly_cap_vnd=0)

    with pytest.raises(ValidationError):
        DeepSeekSettings(max_calls_per_case=-1)

    with pytest.raises(ValidationError):
        DeepSeekSettings(timeout_seconds=0.0)


def test_cost_arithmetic_formulas() -> None:
    # calc_reserved_cost: ceil((7 * in + 28 * out + 1999) / 2000)
    # in=100, out=50 -> (700 + 1400 + 1999) // 2000 = 4099 // 2000 = 2 VND
    assert calc_reserved_cost(100, 50) == 2

    # in=0, out=0 -> 1999 // 2000 = 0 VND
    assert calc_reserved_cost(0, 0) == 0

    # in=1000, out=1000 -> (7000 + 28000 + 1999) // 2000 = 36999 // 2000 = 18 VND
    assert calc_reserved_cost(1000, 1000) == 18

    # calc_actual_cost: same exact fixed-point formula
    assert calc_actual_cost(100, 50) == 2
    assert calc_actual_cost(0, 0) == 0

    # Negative inputs raise ValueError
    with pytest.raises(ValueError, match="non-negative"):
        calc_reserved_cost(-1, 10)

    with pytest.raises(ValueError, match="non-negative"):
        calc_actual_cost(10, -5)


def test_budget_controller_reserve_success() -> None:
    settings = DeepSeekSettings(
        monthly_cap_vnd=100000,
        max_calls_per_case=6,
        max_input_tokens_per_case=60000,
        max_output_tokens_per_case=8000,
    )
    controller = BudgetController(settings=settings)

    prompt = "Hello, analyze this AML case."
    token = controller.reserve("case-001", prompt)

    assert isinstance(token, ReservationToken)
    assert token.case_id == "case-001"
    expected_in = len(prompt.encode("utf-8"))
    assert token.reserved_input == expected_in
    assert token.reserved_output == 8000
    expected_vnd = calc_reserved_cost(expected_in, 8000)
    assert token.reserved_vnd == expected_vnd


def test_budget_controller_case_call_cap_exceeded() -> None:
    settings = DeepSeekSettings(max_calls_per_case=3, max_output_tokens_per_case=30000)
    controller = BudgetController(settings=settings)

    # Make 3 reservations and reconcile them with small token usage
    t1 = controller.reserve("case-1", "Prompt 1")
    controller.mark_dispatched(t1)
    controller.reconcile(t1, actual_in=10, actual_out=20)

    t2 = controller.reserve("case-1", "Prompt 2")
    controller.mark_dispatched(t2)
    controller.reconcile(t2, actual_in=10, actual_out=20)

    t3 = controller.reserve("case-1", "Prompt 3")
    controller.mark_dispatched(t3)
    controller.reconcile(t3, actual_in=10, actual_out=20)

    # 4th reservation must exceed max_calls_per_case (settled_calls=3 >= max_calls=3)
    with pytest.raises(BudgetExceededError, match="Case call limit exceeded"):
        controller.reserve("case-1", "Prompt 4")

    # Another case should still succeed
    t_other = controller.reserve("case-2", "Prompt other")
    assert t_other.case_id == "case-2"


def test_budget_controller_case_input_token_cap_exceeded() -> None:
    settings = DeepSeekSettings(max_input_tokens_per_case=500, max_output_tokens_per_case=30000)
    controller = BudgetController(settings=settings)

    # Prompt with 300 bytes
    prompt_300 = "x" * 300
    t1 = controller.reserve("case-in", prompt_300)
    controller.mark_dispatched(t1)
    controller.reconcile(t1, actual_in=300, actual_out=10)

    # Next prompt with 250 bytes (300 + 250 = 550 > 500)
    prompt_250 = "y" * 250
    with pytest.raises(BudgetExceededError, match="Case input token limit exceeded"):
        controller.reserve("case-in", prompt_250)


def test_budget_controller_case_output_token_cap_exceeded() -> None:
    settings = DeepSeekSettings(
        max_output_tokens_per_case=1000,
    )
    controller = BudgetController(settings=settings)

    # First reservation takes up to avail_out = 1000
    t1 = controller.reserve("case-out", "Short prompt")
    assert t1.reserved_output == 1000

    # Second reservation has avail_out = 1000 - 1000 = 0 -> BudgetExceededError
    with pytest.raises(BudgetExceededError, match="output token limit"):
        controller.reserve("case-out", "Another prompt")


def test_budget_controller_monthly_vnd_cap_exceeded() -> None:
    # Monthly cap of 50 VND
    settings = DeepSeekSettings(
        monthly_cap_vnd=50,
        max_output_tokens_per_case=1000,
    )
    controller = BudgetController(settings=settings)

    # 1000 output tokens alone cost ceil(28 * 1000 / 2000) = 14 VND
    # 4 calls will be 4 * 14 = 56 VND > 50 VND
    controller.reserve("case-m1", "p1")
    controller.reserve("case-m2", "p2")
    controller.reserve("case-m3", "p3")

    with pytest.raises(BudgetExceededError, match="Monthly budget cap exceeded"):
        controller.reserve("case-m4", "p4")


def test_budget_controller_reconciliation_and_release() -> None:
    controller = BudgetController()
    token = controller.reserve("case-recon", "Analyze case")

    # Reconcile directly without dispatch must fail
    with pytest.raises(ValueError, match="must be DISPATCHED"):
        controller.reconcile(token, actual_in=150, actual_out=200)

    # Mark dispatched
    controller.mark_dispatched(token)

    # Cannot release once dispatched
    with pytest.raises(ValueError, match="release permitted only if unattempted"):
        controller.release(token)

    # Reconcile with actual tokens
    controller.reconcile(token, actual_in=150, actual_out=200)

    # Check that attempt is RECONCILED
    attempt = controller._attempts[token.attempt_id]
    assert attempt.status == AttemptStatus.RECONCILED
    assert attempt.actual_input == 150
    assert attempt.actual_output == 200
    assert attempt.actual_vnd == calc_actual_cost(150, 200)

    # Reconciling again must fail (no duplicate reconciliation)
    with pytest.raises(ValueError, match="must be DISPATCHED"):
        controller.reconcile(token, actual_in=150, actual_out=200)


def test_budget_controller_reconcile_retains_full_on_zero_or_boolean_actual() -> None:
    controller = BudgetController()
    token = controller.reserve("case-zero", "Prompt")
    controller.mark_dispatched(token)

    # Reconciliation with 0 tokens retains full reserved_vnd
    controller.reconcile(token, actual_in=0, actual_out=0)

    attempt = controller._attempts[token.attempt_id]
    assert attempt.status == AttemptStatus.RECONCILED
    assert attempt.actual_vnd == token.reserved_vnd

    # Reconciliation with booleans retains full reserved_vnd
    token2 = controller.reserve("case-bool", "Prompt")
    controller.mark_dispatched(token2)
    controller.reconcile(token2, actual_in=True, actual_out=True)  # type: ignore[arg-type]
    attempt2 = controller._attempts[token2.attempt_id]
    assert attempt2.actual_vnd == token2.reserved_vnd


def test_budget_controller_release_unattempted_frees_budget() -> None:
    settings = DeepSeekSettings(max_calls_per_case=1)
    controller = BudgetController(settings=settings)

    token = controller.reserve("case-rel", "Prompt")

    # Call cap is full
    with pytest.raises(BudgetExceededError):
        controller.reserve("case-rel", "Prompt 2")

    # Release unattempted token
    controller.release(token)

    # Call cap is now freed
    token2 = controller.reserve("case-rel", "Prompt 2")
    assert token2.case_id == "case-rel"


def test_budget_controller_concurrency_thread_safe() -> None:
    # Test 20 threads reserving concurrently on monthly_cap_vnd with different cases
    # Each reservation costs ceil((7 * 25 + 28 * 1000 + 1999) / 2000) = 30174 // 2000 = 15 VND
    # Cap of 150 VND allows exactly 10 reservations
    settings = DeepSeekSettings(
        monthly_cap_vnd=150,
        max_output_tokens_per_case=1000,
    )
    controller = BudgetController(settings=settings)

    successful_tokens: list[ReservationToken] = []
    exceeded_count = 0

    def attempt_reserve(idx: int) -> ReservationToken | None:
        return controller.reserve(f"case-concurrent-{idx}", "Prompt from thread text!")

    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
        futures = [executor.submit(attempt_reserve, i) for i in range(20)]
        for f in concurrent.futures.as_completed(futures):
            try:
                tok = f.result()
                if tok is not None:
                    successful_tokens.append(tok)
            except BudgetExceededError:
                exceeded_count += 1

    assert len(successful_tokens) == 10
    assert exceeded_count == 10
