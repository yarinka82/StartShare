from dataclasses import dataclass
from decimal import Decimal

from pydantic import ValidationError

from anonymizer import detect

from ..pdf_extract import DeckContent, DeckExtractionError, extract_deck
from .contract import DraftResponse, check_response, response_schema, unsupported_fields, valid_phrases
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


def run_pipeline(
    content: DeckContent,
    form: dict,
    terms: list[ForbiddenTerm],
    client: LLMClient,
    max_retries: int = 2,
) -> PipelineResult:
    from anonymizer.categories import CATEGORIES

    if not content.has_text:
        # Пока нет vision: дек из одних картинок обработать нельзя
        raise PipelineError("no_text")

    # Шаг 5: regex до вызова ШИ, провайдер не видит e-mail, ссылки, телефоны, номера реестра
    slides = [detect(s.text).redacted_text for s in content.slides]

    deck_text = "\n".join(slides)
    system = build_system_prompt()
    schema = response_schema()
    feedback: "list[str] | None" = None
    total_cost: "Decimal | None" = None
    resp: "DraftResponse | None" = None
    attempts = 0

    for attempt in range(max_retries + 1):
        attempts += 1
        try:
            result = client.generate_json(
                system=system,
                user=build_user_prompt(slides, form, feedback),
                schema=schema,
            )
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
        problems = check_response(parsed, deck_text)
        if not problems:
            feedback = None
            break
        feedback = problems[:10]

    if resp is None:
        raise PipelineError("invalid_response", "; ".join(feedback or []))

    # Последняя попытка с остаточными проблемами: плейсхолдеры в тексте недопустимы, битые фразы чистим
    blanked = unsupported_fields(resp, deck_text)
    if blanked:
        resp = resp.model_copy(update={"teaser": resp.teaser.model_copy(update={n: "" for n in blanked})})
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
        "review": {"image_slides": content.slides_with_images, "blanked_fields": blanked},
    }
    return PipelineResult(draft, unique, total_cost, attempts)


def build_draft(pitch_deck):
    """
    Обёртка для tasks.process_deck: возвращает (draft, risk_phrases, cost_eur).
    Принимает объект PitchDeck.
    """
    from django.conf import settings

    # 1. Проверяем, существует ли файл и не был ли дек удалён
    if getattr(pitch_deck, "deleted_at", None) or not pitch_deck.file:
        raise PipelineError("deck_deleted")

    profile = getattr(pitch_deck, "startup_profile", None) or getattr(pitch_deck, "profile", None)

    # 2. Извлекаем текст из PDF
    try:
        with pitch_deck.file.open("rb") as f:
            content = extract_deck(f)
    except DeckExtractionError as exc:
        raise PipelineError(exc.code) from exc

    # 3. Формируем контекст формы стартапа из связанных довідників
    form = {
        "sector": profile.sector.name_de if profile and profile.sector else (getattr(profile, "sector_other_text", "") or ""),
        "stage": profile.stage.name_de if profile and profile.stage else "",
        "business_model": profile.business_model.name_de if profile and profile.business_model else (getattr(profile, "business_model_other_text", "") or ""),
        "country": profile.country.name_de if profile and profile.country else "",
    }

    # 4. Запускаем LLM пайплайн генерации
    result = run_pipeline(
        content,
        form,
        terms_from_profile(profile) if profile else [],
        get_client(),
        max_retries=getattr(settings, "TEASER_LLM_MAX_RETRIES", 2),
    )
    return result.draft, result.risk_phrases, result.cost_eur