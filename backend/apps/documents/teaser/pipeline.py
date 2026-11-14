from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from pydantic import ValidationError

from anonymizer import detect

from ..pdf_extract import DeckContent, DeckExtractionError, extract_deck
from .contract import DraftResponse, check_response, response_schema, unsupported_fields, valid_phrases
from .factory import LLMNotConfigured, get_client
from .leak_check import ForbiddenTerm, terms_from_profile
from .llm import LLMClient, LLMError
from .llm_retry import LLMUnavailable, generate_with_retries
from .phrases import final_checks, make_phrase, merge_phrases
from .prompt import build_system_prompt, build_user_prompt


class PipelineError(Exception):
    """code: deck_deleted | encrypted | corrupted | too_many_pages | empty | no_text | invalid_response | llm_error | llm_unavailable | llm_not_configured"""

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
            # temporary provider errors (503, 429, timeouts) are retried with backoff inside
            result = generate_with_retries(
                client,
                system=system,
                user=build_user_prompt(slides, form, feedback),
                schema=schema,
            )
        except LLMUnavailable as exc:
            raise PipelineError("llm_unavailable", str(exc)) from exc
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

    # Безпечні помічники для отримання назви довідника
    def get_ref_name(obj, fallback_attr=""):
        if not obj:
            return getattr(profile, fallback_attr, "") or ""
        return getattr(obj, "name_de", getattr(obj, "name", getattr(obj, "code", "")))

    # 3. Формируем контекст формы стартапа из связанных довідників
    form = {
        "sector": get_ref_name(getattr(profile, "sector", None), "sector_other_text"),
        "stage": get_ref_name(getattr(profile, "stage", None)),
        "business_model": get_ref_name(getattr(profile, "business_model", None), "business_model_other_text"),
        "country": get_ref_name(getattr(profile, "country", None)),
    }

    # 4. Провайдер выбирает единая фабрика (PlatformConfig из админки, иначе settings)
    try:
        client = get_client()
    except LLMNotConfigured as exc:
        raise PipelineError("llm_not_configured", str(exc)) from exc

    result = run_pipeline(
        content,
        form,
        terms_from_profile(profile) if profile else [],
        client,
        max_retries=settings.TEASER_MAX_RETRIES,
    )
    return result.draft, result.risk_phrases, result.cost_eur


# Backwards compatibility: other modules may still import the old name from here.
# New code should use factory.get_client.
get_active_llm_client = get_client