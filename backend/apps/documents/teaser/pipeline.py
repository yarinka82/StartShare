"""Пайплайн чернетки тизера (шаги 4-8). run_pipeline() не зависит от Django, build_draft() — обёртка."""
from dataclasses import dataclass
from decimal import Decimal

from pydantic import ValidationError

from anonymizer import detect

from ..pdf_extract import DeckContent, DeckExtractionError, extract_deck
from .contract import DraftResponse, check_response, response_schema, valid_phrases
from .leak_check import ForbiddenTerm, terms_from_profile
from .llm import LLMClient, LLMError, get_client
from .phrases import final_checks, make_phrase, merge_phrases
from .prompt import build_system_prompt, build_user_prompt


class PipelineError(Exception):
    """code: deck_deleted | encrypted | corrupted | too_many_pages | empty | no_text | invalid_response | llm_error"""

    def __init__(self, code: str, message: str = ""):
        super().__init__(f"{code}: {message}" if message else code)
        self.code = code


@dataclass
class PipelineResult:
    draft: dict
    risk_phrases: list[dict]
    cost_eur: "Decimal | None"
    attempts: int


def run_pipeline(content: DeckContent, form: dict, terms: list[ForbiddenTerm],
                 client: LLMClient, max_retries: int = 2) -> PipelineResult:
    from anonymizer.categories import CATEGORIES

    if not content.has_text:
        # Пока нет vision (Q-31): дек из одних картинок обработать нельзя
        raise PipelineError("no_text")

    # Шаг 5: regex до вызова ШІ, провайдер не видит e-mail, ссылки, телефоны, номера реестра
    slides = [detect(s.text).redacted_text for s in content.slides]

    system = build_system_prompt()
    schema = response_schema()
    feedback: "list[str] | None" = None
    total_cost: "Decimal | None" = None
    resp: "DraftResponse | None" = None
    attempts = 0

    for attempt in range(max_retries + 1):
        attempts += 1
        try:
            result = client.generate_json(system=system, user=build_user_prompt(slides, form, feedback),
                                          schema=schema)
        except LLMError as exc:
            raise PipelineError("llm_error", str(exc)) from exc
        if result.cost_eur is not None:
            total_cost = (total_cost or Decimal("0")) + result.cost_eur

        # Шаг 7: схема и смысловые проверки; при сбое повтор с обратной связью
        try:
            parsed = DraftResponse.model_validate(result.data)
        except ValidationError as exc:
            feedback = [f"{'.'.join(map(str, e['loc']))}: {e['msg']}" for e in exc.errors()][:10]
            continue
        resp = parsed
        problems = check_response(parsed)
        if not problems:
            feedback = None
            break
        feedback = problems[:10]

    if resp is None:
        raise PipelineError("invalid_response", "; ".join(feedback or []))

    # Последняя попытка с остаточными проблемами: плейсхолдеры в тексте недопустимы, битые фразы чистим
    fields = resp.teaser.model_dump()
    if any("[REDACTED_" in v for v in fields.values()):
        raise PipelineError("invalid_response", "placeholder left in teaser text")

    phrases = [
        make_phrase(rp.category_id, rp.field, rp.quote, rp.reason, "llm", fields[rp.field])
        for rp in valid_phrases(resp)
    ]
    # Шаг 8: финальные проверки regex и внутренних данных формы
    unique = merge_phrases(phrases, final_checks(fields, terms))

    draft = {
        "teaser": fields,
        "language": resp.language,
        "review": {"image_slides": content.slides_with_images},  # R19: «проверьте логотипы на слайдах …»
    }
    return PipelineResult(draft, unique, total_cost, attempts)


def build_draft(job):
    """Обёртка для tasks.process_deck: возвращает (draft, risk_phrases, cost_eur)."""
    from django.conf import settings

    deck = job.deck
    if job.original_deleted_at or not deck.file:
        raise PipelineError("deck_deleted")
    profile = deck.profile

    try:
        with deck.file.open("rb") as f:
            content = extract_deck(f)
    except DeckExtractionError as exc:
        raise PipelineError(exc.code) from exc

    form = {
        "sector": profile.get_sector_display() if profile.sector else "",
        "stage": profile.get_stage_display() if profile.stage else "",
        "business_model": profile.get_business_model_display() if profile.business_model else "",
    }
    result = run_pipeline(
        content, form, terms_from_profile(profile), get_client(),
        max_retries=getattr(settings, "TEASER_LLM_MAX_RETRIES", 2),
    )
    return result.draft, result.risk_phrases, result.cost_eur