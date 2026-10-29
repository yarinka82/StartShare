
"""Контракт ответа ШІ (BA-AI-01 §4, черновик) и проверка risk_phrases."""
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from anonymizer.categories import CATEGORIES

FIELD_NAMES = ("headline", "problem", "solution", "market", "traction", "team")
PLACEHOLDER_PREFIX = "[REDACTED_"


class TeaserFields(BaseModel):
    model_config = ConfigDict(extra="ignore")

    headline: str = Field(min_length=1, max_length=200)
    problem: str = Field(min_length=1, max_length=800)
    solution: str = Field(min_length=1, max_length=800)
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


def response_schema() -> dict:
    return DraftResponse.model_json_schema()


def check_response(resp: DraftResponse) -> list[str]:
    """Смысловые проверки поверх схемы. Пустой список = ответ годен."""
    problems: list[str] = []
    fields = resp.teaser.model_dump()

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