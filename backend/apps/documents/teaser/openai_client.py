"""Клиент OpenAI (SDK openai) за интерфейсом LLMClient.

Общая логика Chat Completions (структурированный JSON, повторы, стоимость) лежит в
OpenAICompatClient, её же использует AzureOpenAIClient (azure_openai.py).

Только платный доступ с DPA: перед созданием вызывается ensure_remote_allowed() (REQ-39).
"""
import json
import logging
import re
import time
from decimal import Decimal

from .llm import LLMError, LLMResult, ensure_remote_allowed

logger = logging.getLogger(__name__)

RETRY_CODES = {429, 500, 502, 503, 504}
# Три попытки: 3 x AI_REQUEST_TIMEOUT + 7 c. Проверьте, что 3 AI-попытки пайплайна помещаются в CELERY_TASK_SOFT_TIME_LIMIT.
BACKOFF_SECONDS = (2, 5)
DEFAULT_MODEL = "gpt-4o-mini"  # имена моделей меняются: переопределяйте OPENAI_MODEL
SCHEMA_NAME = "teaser_response"
_FENCE = re.compile(r"^\s*```(?:json)?\s*|\s*```\s*$", re.I)


def pricing_from_settings(settings, model: str) -> "tuple[Decimal | None, Decimal | None]":
    """Цены EUR за 1M токенов из settings.AI_PRICING_EUR_PER_MTOK[model] = {"in": ..., "out": ...}."""
    entry = (getattr(settings, "AI_PRICING_EUR_PER_MTOK", None) or {}).get(model)
    if not entry or "in" not in entry or "out" not in entry:
        return None, None
    return Decimal(str(entry["in"])), Decimal(str(entry["out"]))


class OpenAICompatClient:
    provider_name = "OpenAI"

    def __init__(self, client, model: str, *, temperature: float = 0.2, sleep=time.sleep,
                 max_attempts: int = 3, max_output_tokens: int = 8192, strict_schema: bool = True,
                 token_param: str = "max_tokens",
                 price_in_eur_per_m: "Decimal | None" = None, price_out_eur_per_m: "Decimal | None" = None):
        self._client = client
        self.model = model
        self.temperature = temperature
        self._sleep = sleep
        self._max_attempts = max_attempts
        self._max_output_tokens = max_output_tokens
        self._strict = strict_schema
        # Для моделей-«рассуждалок» (o-серия, gpt-5) нужен "max_completion_tokens" и без temperature.
        self._token_param = token_param
        self._price_in = price_in_eur_per_m
        self._price_out = price_out_eur_per_m
        self._use_schema = True       # сбросится в False, если API не принимает json_schema
        self._send_temperature = True  # сбросится в False, если модель не принимает temperature

    # ---- запрос ----

    def generate_json(self, *, system: str, user: str, schema: dict) -> LLMResult:
        response = self._call(system, user, schema)

        choice = response.choices[0] if getattr(response, "choices", None) else None
        if choice is None:
            raise LLMError(f"{self.provider_name} returned no choices.")
        if choice.finish_reason == "content_filter":
            raise LLMError(f"{self.provider_name} response was blocked by the content filter.")

        message = choice.message
        text = getattr(message, "content", None)
        if not text:
            if getattr(message, "refusal", None):
                raise LLMError(f"{self.provider_name} refused to answer.")
            raise LLMError(f"{self.provider_name} returned an empty response.")
        try:
            data = json.loads(_FENCE.sub("", text))
            if not isinstance(data, dict):
                data = {}
        except json.JSONDecodeError:
            data = {}  # в том числе обрезанный ответ (finish_reason="length"): пайплайн сделает повтор

        usage = getattr(response, "usage", None)
        tokens_in = getattr(usage, "prompt_tokens", None)
        tokens_out = getattr(usage, "completion_tokens", None)
        return LLMResult(data=data, cost_eur=self._cost(tokens_in, tokens_out),
                         input_tokens=tokens_in, output_tokens=tokens_out)

    def _request(self, system: str, user: str, schema: dict) -> dict:
        system_prompt = system
        kwargs = {
            "model": self.model,
            self._token_param: self._max_output_tokens,
        }
        if self._send_temperature:
            kwargs["temperature"] = self.temperature
        if self._use_schema:
            kwargs["response_format"] = {
                "type": "json_schema",
                "json_schema": {"name": SCHEMA_NAME, "schema": schema, "strict": self._strict},
            }
        else:
            # Запасной режим: обычный JSON mode, схема передаётся в тексте (слово JSON обязательно).
            kwargs["response_format"] = {"type": "json_object"}
            system_prompt = (f"{system}\n\nReturn ONLY a JSON object matching this JSON schema:\n"
                             f"{json.dumps(schema, ensure_ascii=False)}")
        kwargs["messages"] = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user},
        ]
        return kwargs

    def _call(self, system: str, user: str, schema: dict):
        from openai import APIConnectionError, APIStatusError, BadRequestError

        name = self.provider_name
        for attempt in range(1, self._max_attempts + 1):
            try:
                return self._client.chat.completions.create(**self._request(system, user, schema))
            except BadRequestError as exc:
                # 400: либо API не знает json_schema / temperature (меняем режим и повторяем), либо запрос неверный.
                if attempt < self._max_attempts and self._adapt_to_bad_request(exc):
                    continue
                raise LLMError(f"{name} API error 400{_code_suffix(exc)}") from exc
            except APIStatusError as exc:
                code = exc.status_code
                if getattr(exc, "code", None) == "insufficient_quota":
                    # квота/баланс исчерпаны: повторы бессмысленны
                    raise LLMError(f"{name} API error {code} (quota exhausted)") from exc
                if code in RETRY_CODES and attempt < self._max_attempts:
                    self._backoff(attempt)
                    continue
                raise LLMError(f"{name} API error {code}{_code_suffix(exc)}") from exc
            except APIConnectionError as exc:  # включает APITimeoutError
                if attempt < self._max_attempts:
                    self._backoff(attempt)
                    continue
                raise LLMError(f"{name} connection failed: {type(exc).__name__}") from exc
            except Exception as exc:
                raise LLMError(f"{name} call failed: {type(exc).__name__}") from exc
        raise LLMError(f"{name} call failed")  # недостижимо, для полноты

    def _adapt_to_bad_request(self, exc) -> bool:
        msg = str(exc).lower()  # только для сопоставления, в логи и ошибки не попадает
        if self._use_schema and any(w in msg for w in ("response_format", "json_schema", "structured")):
            logger.warning("%s: json_schema is not accepted, falling back to JSON mode.", self.provider_name)
            self._use_schema = False
            return True
        if self._send_temperature and "temperature" in msg:
            logger.warning("%s: model does not accept temperature, sending without it.", self.provider_name)
            self._send_temperature = False
            return True
        return False

    def _backoff(self, attempt: int) -> None:
        self._sleep(BACKOFF_SECONDS[min(attempt - 1, len(BACKOFF_SECONDS) - 1)])

    def _cost(self, tokens_in, tokens_out) -> "Decimal | None":
        if tokens_in is None or tokens_out is None or self._price_in is None or self._price_out is None:
            return None
        return (Decimal(tokens_in) * self._price_in + Decimal(tokens_out) * self._price_out) / Decimal(1_000_000)


def _code_suffix(exc) -> str:
    code = getattr(exc, "code", None)
    return f" ({code})" if code else ""


class OpenAIClient(OpenAICompatClient):
    provider_name = "OpenAI"

    @classmethod
    def from_settings(cls, settings, *, model=None, temperature=None) -> "OpenAIClient":
        ensure_remote_allowed()
        key = getattr(settings, "OPENAI_API_KEY", "")
        if not key:
            raise LLMError("OPENAI_API_KEY is not set.")
        from openai import OpenAI  # импорт здесь: проект работает и без установленного SDK

        model = model or getattr(settings, "OPENAI_MODEL", DEFAULT_MODEL)
        client = OpenAI(
            api_key=key,
            timeout=float(getattr(settings, "AI_REQUEST_TIMEOUT", 60)),
            max_retries=0,  # повторы делаем сами, см. _call
        )
        price_in, price_out = pricing_from_settings(settings, model)
        return cls(client, model,
                   temperature=0.2 if temperature is None else float(temperature),
                   price_in_eur_per_m=price_in, price_out_eur_per_m=price_out)