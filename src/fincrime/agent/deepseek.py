from __future__ import annotations

import json
from typing import TYPE_CHECKING

import httpx
from pydantic import ValidationError

from fincrime.agent.settings import is_strict_int_gt_zero

if TYPE_CHECKING:
    from fincrime.agent.settings import BudgetController, DeepSeekSettings
    from fincrime.agent.workflow import RawHypothesisOutput


class AIProviderError(Exception):
    pass


class AIInvalidOutputError(Exception):
    pass


class GuardedDeepSeekProvider:
    def __init__(
        self,
        settings: DeepSeekSettings,
        budget_controller: BudgetController,
        client: httpx.Client | None = None,
    ) -> None:
        self._settings = settings
        self._budget_controller = budget_controller
        self._client = client

    def generate_hypothesis(self, case_id: str, prompt: str) -> RawHypothesisOutput:
        from fincrime.agent.workflow import RawHypothesisOutput

        if self._settings.api_key is None or self._settings.api_key.get_secret_value() == "":
            raise AIProviderError("AI provider disabled (LLM_OFF mode)")

        # 1. Atomic reservation (raises BudgetExceededError on limit reach)
        token = self._budget_controller.reserve(case_id=case_id, prompt=prompt)

        # 2. Mark dispatched
        self._budget_controller.mark_dispatched(token)

        # 3. HTTP Request
        url = f"{self._settings.api_base_url.rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self._settings.api_key.get_secret_value()}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": self._settings.model_name,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": token.reserved_output,
            "response_format": {"type": "json_object"},
        }

        client = self._client or httpx.Client()
        try:
            resp = client.post(
                url,
                headers=headers,
                json=payload,
                timeout=self._settings.timeout_seconds,
            )
            resp.raise_for_status()
            resp_data = resp.json()
        except (httpx.HTTPError, json.JSONDecodeError) as e:
            # Retain conservative reservation on transport/timeout failure
            self._budget_controller.reconcile(
                token,
                actual_input=token.reserved_input,
                actual_output=token.reserved_output,
            )
            raise AIProviderError(f"AI provider request failed or timed out: API error: {e}") from e

        # 4. Successful HTTP call -> Reconcile actual tokens safely (rejecting booleans/strings/negatives/zeros)
        usage = resp_data.get("usage")
        if isinstance(usage, dict):
            raw_in = usage.get("prompt_tokens")
            raw_out = usage.get("completion_tokens")
            if is_strict_int_gt_zero(raw_in) and is_strict_int_gt_zero(raw_out):
                actual_in = raw_in
                actual_out = raw_out
            else:
                actual_in = token.reserved_input
                actual_out = token.reserved_output
        else:
            actual_in = token.reserved_input
            actual_out = token.reserved_output

        self._budget_controller.reconcile(token, actual_input=actual_in, actual_output=actual_out)

        # 5. Parse structured output
        try:
            choices = resp_data.get("choices", [])
            if not choices or not isinstance(choices, list):
                raise KeyError("No choices returned from LLM provider")
            message_content = choices[0].get("message", {}).get("content", "")
            if not message_content:
                raise ValueError("Empty message content in choices")
            return RawHypothesisOutput.model_validate_json(message_content)
        except (json.JSONDecodeError, ValidationError, KeyError, TypeError, ValueError) as e:
            raise AIInvalidOutputError(
                f"AI provider returned invalid structured output: {e}"
            ) from e
