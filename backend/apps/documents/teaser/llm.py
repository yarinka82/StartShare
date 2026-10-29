"""Тонкий интерфейс к провайдеру ШІ. Провайдера выбираем позже: меняется одна настройка."""
import json
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

import requests

from apps.accounts.compliance import ProviderBlocked, assert_provider_allowed, ensure_vendor_allowed, is_ai_notice_enabled


class LLMError(Exception):
    pass


class RemoteProviderNotAllowed(LLMError):
    """REQ-39: данные деки уходят удалённому провайдеру только при подписанном AVV."""


@dataclass
class LLMResult:
    data: dict
    cost_eur: "Decimal | None" = None
    input_tokens: "int | None" = None
    output_tokens: "int | None" = None


class LLMClient(Protocol):
    def generate_json(self, *, system: str, user: str, schema: dict) -> LLMResult: ...


class LLMProvider(Protocol):
    def generate_teaser(self, deck_text: str) -> dict: ...


class FakeLLMClient:
    """Для тестов и разработки без провайдера. Ответы можно задать очередью.

    Элемент очереди: dict (ответ) или Exception (будет брошено).
    Без очереди возвращает нейтральную заглушку.
    """

    def __init__(self, responses: "list[dict | Exception] | None" = None):
        self.responses = list(responses or [])
        self.calls: list[dict] = []

    def generate_json(self, *, system: str, user: str, schema: dict) -> LLMResult:
        self.calls.append({"system": system, "user": user})
        if self.responses:
            item = self.responses.pop(0)
            if isinstance(item, Exception):
                raise item
            return LLMResult(data=item, cost_eur=Decimal("0"))
        return LLMResult(
            data={
                "teaser": {
                    "headline": "Software fuer ein Nischenproblem im Gesundheitswesen",
                    "problem": "Ein haeufiges Problem kostet Betriebe Zeit und Geld.",
                    "solution": "Eine cloudbasierte Loesung automatisiert den Ablauf.",
                },
                "risk_phrases": [],
                "language": "de",
            },
            cost_eur=Decimal("0"),
        )


class FakeLLMProvider(FakeLLMClient):
    """Dev/test provider: no external call, fixed valid structure matching BA-AI-01."""

    def generate_teaser(self, deck_text: str) -> dict:
        return {
            "teaser": {
                "headline": "Software fuer ein Nischenproblem im Gesundheitswesen",
                "problem": "Ein haeufiges Problem kostet Betriebe Zeit und Geld.",
                "solution": "Eine cloudbasierte Loesung automatisiert den Ablauf.",
            },
            "risk_phrases": [],
            "language": "de",
        }


class AzureOpenAIClient:
    """Azure OpenAI client behind the compliance gate and with a no-training guarantee."""

    def __init__(self, endpoint: str, api_key: str, deployment: str, *, api_version: str = "2024-02-01"):
        self.endpoint = endpoint.rstrip("/")
        self.api_key = api_key
        self.deployment = deployment
        self.api_version = api_version

    def _request_json(self, payload: dict) -> dict:
        assert_provider_allowed("azure_openai")
        url = f"{self.endpoint}/openai/deployments/{self.deployment}/chat/completions?api-version={self.api_version}"
        headers = {"Content-Type": "application/json", "api-key": self.api_key}
        response = requests.post(url, headers=headers, json=payload, timeout=60)
        response.raise_for_status()
        return response.json()

    def generate_json(self, *, system: str, user: str, schema: dict) -> LLMResult:
        payload = {
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        try:
            body = self._request_json(payload)
        except ProviderBlocked as exc:
            raise RemoteProviderNotAllowed(str(exc)) from exc
        except requests.HTTPError as exc:
            raise LLMError(f"Azure OpenAI request failed: {exc}") from exc

        choices = body.get("choices") or []
        if not choices:
            raise LLMError("Azure OpenAI returned no choices.")
        message = choices[0].get("message") or {}
        content = message.get("content") or "{}"
        try:
            data = json.loads(content)
        except json.JSONDecodeError as exc:
            raise LLMError("Azure OpenAI returned invalid JSON.") from exc
        usage = body.get("usage") or {}
        return LLMResult(
            data=data,
            cost_eur=None,
            input_tokens=usage.get("prompt_tokens"),
            output_tokens=usage.get("completion_tokens"),
        )

    def generate_teaser(self, deck_text: str) -> dict:
        return self.generate_json(
            system="Create a teaser draft for a startup profile in German or English.",
            user=deck_text,
            schema={"type": "object"},
        ).data


def get_client() -> LLMClient:
    """Выбор клиента по settings.LLM_PROVIDER с совместимостью со старым TEASER_LLM_PROVIDER."""
    from django.conf import settings

    provider = getattr(settings, "LLM_PROVIDER", None) or getattr(settings, "TEASER_LLM_PROVIDER", "fake")
    if provider == "fake":
        if not getattr(settings, "DEBUG", False):
            raise LLMError("Production requires a non-fake LLM provider. Set LLM_PROVIDER to a real provider.")
        return FakeLLMClient()
    if provider == "azure_openai":
        endpoint = getattr(settings, "AZURE_OPENAI_ENDPOINT", "")
        key = getattr(settings, "AZURE_OPENAI_API_KEY", "")
        deployment = getattr(settings, "AZURE_OPENAI_DEPLOYMENT", "")
        if not endpoint or not key or not deployment:
            raise LLMError("Azure OpenAI is not configured: set AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY and AZURE_OPENAI_DEPLOYMENT.")
        return AzureOpenAIClient(endpoint, key, deployment)
    if provider in ("gemini_free", "gemini"):
        from .gemini import GeminiClient
        return GeminiClient.from_settings(settings, free_tier=(provider == "gemini_free"))
    raise LLMError(f"Unknown LLM provider: {provider!r}")


def ensure_remote_allowed() -> None:
    from django.conf import settings

    provider = getattr(settings, "LLM_PROVIDER", None) or getattr(settings, "TEASER_LLM_PROVIDER", "fake")
    if provider in ("fake", "debug"):
        return

    try:
        ensure_vendor_allowed("azure_openai", "ai_prompt", vendor_type="ai")
    except Exception as exc:  # pragma: no cover - clarity for deployment gate
        raise RemoteProviderNotAllowed(str(exc)) from exc

    if not is_ai_notice_enabled():
        raise RemoteProviderNotAllowed(
            "Remote LLM provider requires a signed and active azure_openai vendor record with no_model_training=True."
        )