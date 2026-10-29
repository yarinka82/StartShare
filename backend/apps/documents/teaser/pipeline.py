from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from pydantic import ValidationError

from anonymizer import detect
from .gemini import GeminiClient

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

    # 4. Запускаем LLM пайплайн генерации через ДИНАМІЧНИЙ клієнт
    result = run_pipeline(
        content,
        form,
        terms_from_profile(profile) if profile else [],
        get_active_llm_client(),  # 🚀 ВИПРАВЛЕНО: викликаємо динамічний клієнт із налаштувань адмінки!
        max_retries=getattr(settings, "TEASER_LLM_MAX_RETRIES", 2),
    )
    return result.draft, result.risk_phrases, result.cost_eur



def get_active_llm_client():
    """
    Визначає активного провайдера та модель:
    спочатку дивиться у динамічний PlatformConfig, якщо немає — бере з settings.
    """
    provider = "gemini"
    model = None
    temperature = 0.2

    try:
        from apps.accounts.models import PlatformConfig
        cfg = PlatformConfig.get_solo()
        provider = cfg.ai_provider or "gemini"
        model = cfg.ai_model
        temperature = cfg.ai_temperature
    except Exception:
        provider = getattr(settings, "TEASER_LLM_PROVIDER", "gemini_free")
        model = getattr(settings, "TEASER_GEMINI_MODEL", "gemini-2.0-flash")

    # Якщо обрано Gemini (Free або з підписаним AVV)
    if provider in ("gemini", "gemini_free"):
        free_tier = (provider == "gemini_free" or getattr(settings, "TEASER_LLM_PROVIDER", "") == "gemini_free")
        return GeminiClient(
            api_key=settings.TEASER_GEMINI_API_KEY,
            model=model or "gemini-2.0-flash",
            free_tier=free_tier,
        )

    # Якщо для продакшну обрано OpenAI
    if provider == "openai":
        from .openai_client import OpenAIClient
        return OpenAIClient(
            api_key=getattr(settings, "OPENAI_API_KEY", ""),
            model=model or "gpt-4o-mini",
            temperature=temperature,
        )

    raise ValueError(f"Невідомий або ненадійний AI провайдер: {provider}")