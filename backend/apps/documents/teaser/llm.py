
"""Тонкий интерфейс к провайдеру ШІ. Провайдера выбираем позже: меняется одна настройка."""
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol




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
        marker = "[Slide 1]\n"
        i = user.find(marker)
        quote = user[i + len(marker):].split("\n")[0][:80] if i >= 0 else ""
        return LLMResult(
            data={
                "evidence": {k: quote for k in ("headline", "problem", "solution")},
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


def _resolve_config() -> dict:
    """PlatformConfig (админка) в приоритете, settings.TEASER_LLM_PROVIDER как запасной вариант."""
    from django.conf import settings
    
    cfg = {
        "provider": getattr(settings, "TEASER_LLM_PROVIDER", "gemini"),
        "model": None,
        "temperature": None,
    }
    try:
        from apps.accounts.models import PlatformConfig
        
        pc = PlatformConfig.get_solo()
        cfg["provider"] = pc.ai_provider or cfg["provider"]
        cfg["model"] = pc.ai_model or None
        cfg["temperature"] = pc.ai_temperature
    except Exception:
        pass  # до миграций и в тестах работаем от settings
    return cfg



def get_client() -> LLMClient:
    from django.conf import settings
    
    cfg = _resolve_config()
    provider = cfg["provider"]
    extra = {k: cfg[k] for k in ("model", "temperature") if cfg[k] is not None}
    
    if provider == "fake":
        if not settings.DEBUG:
            raise LLMError("Provider 'fake' is only allowed with DEBUG=True.")
        return FakeLLMClient()
    
    if provider in ("gemini", "gemini_free"):
        # AVV и DEBUG для free-tier проверяются внутри GeminiClient.from_settings
        from .gemini import GeminiClient
        return GeminiClient.from_settings(settings, free_tier=(provider == "gemini_free"), **extra)
    
    if provider == "openai":
        ensure_remote_allowed()
        from .openai_client import OpenAIClient  # TODO
        return OpenAIClient.from_settings(settings, **extra)
    
    if provider == "azure_openai":
        ensure_remote_allowed()
        from .azure_openai import AzureOpenAIClient  # TODO; модель = AZURE_OPENAI_DEPLOYMENT
        return AzureOpenAIClient.from_settings(settings, temperature=cfg["temperature"])
    
    raise LLMError(f"Unknown LLM provider: {provider!r}")


def ensure_remote_allowed() -> None:
    from django.conf import settings

    if not getattr(settings, "TEASER_AVV_SIGNED", False):
        raise RemoteProviderNotAllowed("Remote LLM provider requires TEASER_AVV_SIGNED=True (REQ-39).")