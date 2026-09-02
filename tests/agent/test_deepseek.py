from __future__ import annotations

import json

import httpx
import pytest
from pydantic import SecretStr

from fincrime.agent.deepseek import (
    AIInvalidOutputError,
    AIProviderError,
    GuardedDeepSeekProvider,
)
from fincrime.agent.settings import (
    AttemptStatus,
    BudgetController,
    BudgetExceededError,
    DeepSeekSettings,
)
from fincrime.agent.workflow import RawHypothesisOutput, RawMaterialClaim


def test_deepseek_provider_llm_off_mode_raises_provider_error() -> None:
    settings = DeepSeekSettings(api_key=None)
    controller = BudgetController(settings=settings)
    provider = GuardedDeepSeekProvider(settings=settings, budget_controller=controller)

    with pytest.raises(AIProviderError, match="LLM_OFF"):
        provider.generate_hypothesis(case_id="case-llm-off", prompt="Test prompt")


def test_deepseek_provider_budget_exceeded_propagates() -> None:
    settings = DeepSeekSettings(
        api_key=SecretStr("sk-test-key"),
        max_calls_per_case=1,
    )
    controller = BudgetController(settings=settings)
    provider = GuardedDeepSeekProvider(settings=settings, budget_controller=controller)

    # Exhaust budget
    controller.reserve("case-budget-exceeded", "First prompt")

    with pytest.raises(BudgetExceededError):
        provider.generate_hypothesis(case_id="case-budget-exceeded", prompt="Second prompt")


def test_deepseek_provider_transport_error_reconciles_conservative_cost() -> None:
    settings = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings)

    # Mock transport that raises ConnectTimeout
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectTimeout("Connection timed out", request=request)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GuardedDeepSeekProvider(
        settings=settings,
        budget_controller=controller,
        client=client,
    )

    with pytest.raises(AIProviderError, match="request failed or timed out"):
        provider.generate_hypothesis(case_id="case-timeout", prompt="Analyze case")

    # Verify attempt was reconciled conservatively
    attempts = list(controller._attempts.values())
    assert len(attempts) == 1
    attempt = attempts[0]
    assert attempt.status == AttemptStatus.RECONCILED
    assert attempt.actual_vnd == attempt.reserved_vnd


def test_deepseek_provider_http_500_error_reconciles_conservative_cost() -> None:
    settings = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings)

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=500, text="Internal Server Error")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GuardedDeepSeekProvider(
        settings=settings,
        budget_controller=controller,
        client=client,
    )

    with pytest.raises(AIProviderError, match="API error"):
        provider.generate_hypothesis(case_id="case-500", prompt="Analyze case")

    attempt = next(iter(controller._attempts.values()))
    assert attempt.status == AttemptStatus.RECONCILED
    assert attempt.actual_vnd == attempt.reserved_vnd


def test_deepseek_provider_invalid_json_raises_invalid_output_error() -> None:
    settings = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings)

    mock_resp = {
        "choices": [
            {
                "message": {
                    "content": "Not a valid JSON object at all",
                }
            }
        ],
        "usage": {
            "prompt_tokens": 120,
            "completion_tokens": 80,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=mock_resp)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GuardedDeepSeekProvider(
        settings=settings,
        budget_controller=controller,
        client=client,
    )

    with pytest.raises(AIInvalidOutputError, match="invalid structured output"):
        provider.generate_hypothesis(case_id="case-bad-json", prompt="Analyze case")

    attempt = next(iter(controller._attempts.values()))
    assert attempt.status == AttemptStatus.RECONCILED
    assert attempt.actual_input == 120
    assert attempt.actual_output == 80


def test_deepseek_provider_invalid_schema_raises_invalid_output_error() -> None:
    settings = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings)

    # Valid JSON but missing required "claims" field
    bad_schema_json = json.dumps({"summary": "Incomplete summary without claims"})
    mock_resp = {
        "choices": [
            {
                "message": {
                    "content": bad_schema_json,
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(status_code=200, json=mock_resp)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GuardedDeepSeekProvider(
        settings=settings,
        budget_controller=controller,
        client=client,
    )

    with pytest.raises(AIInvalidOutputError, match="invalid structured output"):
        provider.generate_hypothesis(case_id="case-bad-schema", prompt="Analyze case")


def test_deepseek_provider_happy_path_success() -> None:
    settings = DeepSeekSettings(api_key=SecretStr("sk-test-key"))
    controller = BudgetController(settings=settings)

    valid_payload = {
        "summary": "Suspected layering operation identified across accounts.",
        "claims": [
            {
                "claim_text": "High volume velocity between seed account and destination.",
                "cited_evidence_ids": ["ev:001", "ev:002"],
            }
        ],
    }
    mock_resp = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(valid_payload),
                }
            }
        ],
        "usage": {
            "prompt_tokens": 250,
            "completion_tokens": 180,
        },
    }

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test-key"
        return httpx.Response(status_code=200, json=mock_resp)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    provider = GuardedDeepSeekProvider(
        settings=settings,
        budget_controller=controller,
        client=client,
    )

    result = provider.generate_hypothesis(case_id="case-success", prompt="Analyze case")
    assert isinstance(result, RawHypothesisOutput)
    assert result.summary == "Suspected layering operation identified across accounts."
    assert len(result.claims) == 1
    assert isinstance(result.claims[0], RawMaterialClaim)
    assert (
        result.claims[0].claim_text == "High volume velocity between seed account and destination."
    )
    assert result.claims[0].cited_evidence_ids == ("ev:001", "ev:002")

    attempt = next(iter(controller._attempts.values()))
    assert attempt.status == AttemptStatus.RECONCILED
    assert attempt.actual_input == 250
    assert attempt.actual_output == 180
