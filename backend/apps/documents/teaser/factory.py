"""
The ONE place that decides which AI provider the teaser pipeline uses.
Replaces get_active_llm_client (pipeline.py), get_llm_client and the old get_client.

Rule: fail closed. A problem with the configuration must never silently
switch the data flow to a provider without a data processing agreement.
"""
import logging

from django.conf import settings
from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError

from .gemini import GeminiClient
from .llm import LLMClient, LLMError
from .openai_client import OpenAIClient

log = logging.getLogger(__name__)


class LLMNotConfigured(LLMError):
    """Provider unknown, key missing, or not allowed in this environment."""


def _read_config():
    from apps.accounts.models import PlatformConfig

    cfg = PlatformConfig.get_solo()
    return cfg.ai_provider, cfg.ai_model, cfg.ai_temperature


def _require(value: str, name: str) -> str:
    if not value:
        raise LLMNotConfigured(f"{name} is not set")
    return value


def get_client() -> LLMClient:
    provider = model = temperature = None
    try:
        provider, model, temperature = _read_config()
    except (DatabaseError, ObjectDoesNotExist, ImportError) as exc:
        # e.g. migrations not applied yet: use the settings value, but it goes through the same checks below
        log.warning("PlatformConfig unavailable (%s), using settings", exc)

    provider = (provider or settings.TEASER_LLM_PROVIDER or "").strip().lower()
    temperature = 0.2 if temperature is None else float(temperature)
    model = (model or "").strip()

    if provider in ("gemini", "gemini_free"):
        # the old setting TEASER_LLM_PROVIDER == "gemini_free" still marks the free tier
        free_tier = provider == "gemini_free" or settings.TEASER_LLM_PROVIDER == "gemini_free"
        if free_tier and not settings.AI_ALLOW_FREE_TIER:
            raise LLMNotConfigured("Gemini free tier is not allowed here (no data processing agreement)")
        return GeminiClient(
            api_key=_require(settings.TEASER_GEMINI_API_KEY, "GEMINI_API_KEY"),
            model=model or settings.TEASER_GEMINI_MODEL,
            free_tier=free_tier,
        )

    if provider == "openai":
        return OpenAIClient(
            _require(settings.OPENAI_API_KEY, "OPENAI_API_KEY"),
            model or settings.OPENAI_MODEL,
            temperature,
            timeout=settings.AI_REQUEST_TIMEOUT,
            pricing=settings.AI_PRICING_EUR_PER_MTOK,
        )

    if provider == "azure_openai":
        return OpenAIClient(
            _require(settings.AZURE_OPENAI_API_KEY, "AZURE_OPENAI_API_KEY"),
            model or _require(settings.AZURE_OPENAI_DEPLOYMENT, "AZURE_OPENAI_DEPLOYMENT"),
            temperature,
            timeout=settings.AI_REQUEST_TIMEOUT,
            azure_endpoint=_require(settings.AZURE_OPENAI_ENDPOINT, "AZURE_OPENAI_ENDPOINT"),
            api_version=_require(settings.AZURE_OPENAI_API_VERSION, "AZURE_OPENAI_API_VERSION"),
            pricing=settings.AI_PRICING_EUR_PER_MTOK,
        )

    raise LLMNotConfigured(f"Unknown AI provider: {provider!r}")