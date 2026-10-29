"""Тонкий интерфейс к провайдеру ШІ. Провайдера выбираем позже: меняется одна настройка."""
from dataclasses import dataclass
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


def get_client() -> LLMClient:
    """Выбор клиента по settings.TEASER_LLM_PROVIDER ('fake' по умолчанию).

    Удалённые провайдеры добавлять сюда и вызывать ensure_remote_allowed() перед созданием.
    """
    from django.conf import settings

    provider = getattr(settings, "TEASER_LLM_PROVIDER", "fake")
    if provider == "fake":
        return FakeLLMClient()
    if provider in ("gemini_free", "gemini"):
        from .gemini import GeminiClient
        return GeminiClient.from_settings(settings, free_tier=(provider == "gemini_free"))
    raise LLMError(f"Unknown TEASER_LLM_PROVIDER: {provider!r}")


def ensure_remote_allowed() -> None:
    from django.conf import settings

    if not getattr(settings, "TEASER_AVV_SIGNED", False):
        raise RemoteProviderNotAllowed("Remote LLM provider requires TEASER_AVV_SIGNED=True (REQ-39).")