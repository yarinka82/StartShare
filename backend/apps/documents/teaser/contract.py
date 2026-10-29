
"""Контракт ответа ШІ (BA-AI-01 §4, черновик) и проверка risk_phrases."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from anonymizer.categories import CATEGORIES

FIELD_NAMES = ("headline", "problem", "solution", "market", "traction", "team")
PLACEHOLDER_PREFIX = "[REDACTED_"


class TeaserFields(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: str = Field(min_length=1, max_length=200)
    problem: str = Field(default="", max_length=800)    # пусто, если в деке об этом ничего нет
    solution: str = Field(default="", max_length=800)
    market: str = Field(default="", max_length=800)
    traction: str = Field(default="", max_length=800)
    team: str = Field(default="", max_length=800)


class RiskPhrase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    category_id: str
    field: str
    quote: str = Field(min_length=1, max_length=300)
    reason: str = Field(default="", max_length=300)


class DraftResponse(BaseModel):
    model_config = ConfigDict(extra="ignore")

    teaser: TeaserFields
    risk_phrases: list[RiskPhrase] = Field(default_factory=list)
    language: Literal["de", "en"]
    # Для каждого непустого поля тизера: дословная цитата из дека, на которой оно основано.
    # Используется только для проверки и НЕ сохраняется (в цитатах могут быть названия).
    evidence: dict[str, str] = Field(default_factory=dict)


def response_schema() -> dict:
    return DraftResponse.model_json_schema()


def _norm(text: str) -> str:
    return " ".join(text.split()).casefold()


def unsupported_fields(resp: DraftResponse, deck_text: str) -> list[str]:
    """Непустые поля тизера без дословной цитаты-опоры из (уже очищенного) текста дека."""
    deck_norm = _norm(deck_text)
    out = []
    for name, text in resp.teaser.model_dump().items():
        if text.strip():
            quote = _norm(resp.evidence.get(name, ""))
            if len(quote) < 8 or quote not in deck_norm:
                out.append(name)
    return out


def check_response(resp: DraftResponse, deck_text: "str | None" = None) -> list[str]:
    """Смысловые проверки поверх схемы. Пустой список = ответ годен."""
    problems: list[str] = []
    fields = resp.teaser.model_dump()
    if deck_text is not None:
        for name in unsupported_fields(resp, deck_text):
            problems.append(
                f"Field '{name}' has no verbatim supporting quote from the deck in `evidence`. "
                "Copy a short exact quote from the deck, or return an empty string if the deck does not say it.")

    for name, text in fields.items():
        if PLACEHOLDER_PREFIX in text:
            problems.append(f"Field '{name}' contains a [REDACTED_*] placeholder; never output placeholders.")

    for i, rp in enumerate(resp.risk_phrases):
        if rp.category_id not in CATEGORIES:
            problems.append(f"risk_phrases[{i}]: unknown category_id '{rp.category_id}'.")
        if rp.field not in FIELD_NAMES:
            problems.append(f"risk_phrases[{i}]: unknown field '{rp.field}'.")
        elif rp.quote not in fields[rp.field]:
            problems.append(
                f"risk_phrases[{i}]: quote {rp.quote!r} is not a verbatim substring of field '{rp.field}'.")
    return problems


def valid_phrases(resp: DraftResponse) -> list[RiskPhrase]:
    """Оставляет только фразы, прошедшие проверку (последняя попытка: чистим, а не падаем)."""
    fields = resp.teaser.model_dump()
    return [
        rp for rp in resp.risk_phrases
        if rp.category_id in CATEGORIES and rp.field in FIELD_NAMES and rp.quote in fields[rp.field]
    ]