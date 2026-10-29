"""Клиент Gemini (SDK google-genai) за интерфейсом LLMClient.

Два режима:
  gemini_free  бесплатный тариф: данные могут использоваться Google для улучшения моделей,
               поэтому ТОЛЬКО для разработки на синтетических деках (требует DEBUG=True).
  gemini       платный тариф: только при подписанном AVV (TEASER_AVV_SIGNED=True, REQ-39).
"""
import json
import logging
import re
import time
from decimal import Decimal

from .llm import LLMError, LLMResult, RemoteProviderNotAllowed, ensure_remote_allowed

logger = logging.getLogger(__name__)

RETRY_CODES = {429, 500, 503}
BACKOFF_SECONDS = (2, 5, 15)  # 503 «high demand» на бесплатном тарифе часто проходит со 2-3 попытки
DEFAULT_MODEL = "gemini-3.5-flash-lite"  # имена моделей меняются: переопределяйте TEASER_GEMINI_MODEL
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


class GeminiClient:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL, *, free_tier: bool, client=None,
                 sleep=time.sleep, max_attempts: int = 4,
                 price_in_eur_per_m: "Decimal | None" = None, price_out_eur_per_m: "Decimal | None" = None):
        if client is None:
            from google import genai  # импорт здесь: проект работает и без установленного SDK
            client = genai.Client(api_key=api_key)
        self._client = client
        self.model = model
        self.free_tier = free_tier
        self._sleep = sleep
        self._max_attempts = max_attempts
        self._price_in = price_in_eur_per_m
        self._price_out = price_out_eur_per_m
 
    @classmethod
    def from_settings(cls, settings, *, free_tier: bool) -> "GeminiClient":
        if free_tier:
            if not getattr(settings, "DEBUG", False):
                raise RemoteProviderNotAllowed(
                    "gemini_free is for development with synthetic decks only (requires DEBUG=True).")
            logger.warning("Using Gemini FREE tier: data may be used by Google. Synthetic decks only.")
        else:
            ensure_remote_allowed()
        key = getattr(settings, "TEASER_GEMINI_API_KEY", "")
        if not key:
            raise LLMError("TEASER_GEMINI_API_KEY is not set.")
        return cls(
            key, getattr(settings, "TEASER_GEMINI_MODEL", DEFAULT_MODEL), free_tier=free_tier,
            price_in_eur_per_m=getattr(settings, "TEASER_GEMINI_PRICE_IN_EUR_PER_M", None),
            price_out_eur_per_m=getattr(settings, "TEASER_GEMINI_PRICE_OUT_EUR_PER_M", None),
        )
 
    def generate_json(self, *, system: str, user: str, schema: dict) -> LLMResult:
        from google.genai import types
 
        config = types.GenerateContentConfig(
            system_instruction=system,
            response_mime_type="application/json",
            response_json_schema=schema,
            temperature=0.2,
            max_output_tokens=8192,  # запас: токены «размышлений» входят в лимит вывода
            automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),  # инструментов нет
        )
        response = self._call(user, config)
 
        text = getattr(response, "text", None)
        if not text:
            raise LLMError("Gemini returned an empty response (possibly blocked).")
        try:
            data = json.loads(_FENCE.sub("", text))
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            data = {}  # невалидный JSON: пайплайн сам сделает повтор с обратной связью
 
        usage = getattr(response, "usage_metadata", None)
        tokens_in = getattr(usage, "prompt_token_count", None)
        tokens_out = (getattr(usage, "candidates_token_count", 0) or 0) + (getattr(usage, "thoughts_token_count", 0) or 0)
        return LLMResult(data=data, cost_eur=self._cost(tokens_in, tokens_out),
                         input_tokens=tokens_in, output_tokens=tokens_out)
 
    def _call(self, user: str, config):
        from google.genai import errors
 
        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._client.models.generate_content(model=self.model, contents=user, config=config)
            except errors.APIError as exc:
                status = getattr(exc, "status", None)
                detail = f"{exc.code} {status}" if status else f"{exc.code}"
                if exc.code == 429 and "perday" in str(exc).lower():
                    # дневная квота исчерпана: повторы бессмысленны, ждать нужно до завтра
                    raise LLMError(f"Gemini API error {detail} (daily quota exhausted)") from exc
                if exc.code in RETRY_CODES and attempt < self._max_attempts:
                    self._sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])
                    continue
                raise LLMError(f"Gemini API error {detail}") from exc
            except Exception as exc:
                raise LLMError(f"Gemini call failed: {type(exc).__name__}") from exc
        raise LLMError("Gemini call failed")  # недостижимо, для полноты
 
    def _cost(self, tokens_in, tokens_out) -> "Decimal | None":
        if self.free_tier:
            return Decimal("0")
        if tokens_in is None or self._price_in is None or self._price_out is None:
            return None
        return (Decimal(tokens_in) * Decimal(self._price_in) + Decimal(tokens_out) * Decimal(self._price_out)) / Decimal(1_000_000)