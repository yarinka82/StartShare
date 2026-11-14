"""Retry with backoff for temporary AI provider errors (503 overloaded, 429 rate limit, timeouts)."""
import logging
import random
import re
import time

from .llm import LLMError

log = logging.getLogger(__name__)


class LLMUnavailable(LLMError):
    """The provider kept answering with a temporary error after all retries."""


_TRANSIENT_STATUS = re.compile(r"\b(429|500|502|503|504)\b")
_TRANSIENT_WORDS = ("unavailable", "overloaded", "resource_exhausted", "rate limit", "timed out", "timeout", "connection")

# Признаки исчерпания СУТОЧНОЙ квоты — при них ретраи бессмысленны
_FATAL_QUOTA_MARKERS = (
    "daily quota",
    "retry in",
    "quota exceeded",
    "limit exceeded",
    "plan and billing",
)


def is_transient(exc: Exception) -> bool:
    """
    Определяет, имеет ли смысл повторять запрос.
    Кратковременные ошибки (503, секундные 429) -> True.
    Суточный лимит, ошибки авторизации, невалидный JSON -> False (падаем сразу).
    """
    text = str(exc).lower()

    # 1. Если это дневной бан/лимит — выходим СРАЗУ, не тратя 60 секунд на ретраи
    if any(marker in text for marker in _FATAL_QUOTA_MARKERS):
        return False

    # 2. Проверяем статус-код
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    if isinstance(status, int) and status in (429, 500, 502, 503, 504):
        return True

    # 3. Проверяем текст ошибки на временные сбои
    return bool(_TRANSIENT_STATUS.search(text)) or any(w in text for w in _TRANSIENT_WORDS)


def generate_with_retries(client, *, system: str, user: str, schema: dict,
                          attempts: int = 4, base_delay: float = 3.0, sleep=time.sleep):
    """
    Calls client.generate_json. Temporary errors are retried with exponential backoff (3s, 6s, 12s, with jitter),
    everything else (bad request, auth, refusal, daily quota ...) is raised at once: retrying would not help.
    """
    last: "Exception | None" = None
    for attempt in range(1, attempts + 1):
        try:
            return client.generate_json(system=system, user=user, schema=schema)
        except LLMError as exc:
            # Если ошибка постоянная (включая daily quota) — вылетаем СРАЗУ на первом же сбое
            if not is_transient(exc):
                raise
            last = exc
            if attempt == attempts:
                break
            delay = base_delay * (2 ** (attempt - 1)) * random.uniform(0.8, 1.2)
            log.warning("AI provider temporary error (attempt %d/%d), retrying in %.0fs: %s", attempt, attempts, delay, exc)
            sleep(delay)
    raise LLMUnavailable(f"provider unavailable after {attempts} attempts: {last}") from last