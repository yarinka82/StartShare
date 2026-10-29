"""Клиент Azure OpenAI за интерфейсом LLMClient.

В Azure в параметр model передаётся ИМЯ ДЕПЛОЯ (AZURE_OPENAI_DEPLOYMENT), а не имя модели.
Версию API (AZURE_OPENAI_API_VERSION) выбирайте так, чтобы она поддерживала Structured Outputs
для вашего деплоя; если нет, клиент сам переключится на обычный JSON mode.
"""
from .llm import LLMError, ensure_remote_allowed
from .openai_client import OpenAICompatClient, pricing_from_settings


class AzureOpenAIClient(OpenAICompatClient):
    provider_name = "Azure OpenAI"

    @classmethod
    def from_settings(cls, settings, *, temperature=None) -> "AzureOpenAIClient":
        ensure_remote_allowed()
        required = {
            "AZURE_OPENAI_API_KEY": getattr(settings, "AZURE_OPENAI_API_KEY", ""),
            "AZURE_OPENAI_ENDPOINT": getattr(settings, "AZURE_OPENAI_ENDPOINT", ""),
            "AZURE_OPENAI_DEPLOYMENT": getattr(settings, "AZURE_OPENAI_DEPLOYMENT", ""),
            "AZURE_OPENAI_API_VERSION": getattr(settings, "AZURE_OPENAI_API_VERSION", ""),
        }
        missing = [name for name, value in required.items() if not value]
        if missing:
            raise LLMError(f"Azure OpenAI is not configured: {', '.join(missing)}.")

        from openai import AzureOpenAI  # импорт здесь: проект работает и без установленного SDK

        client = AzureOpenAI(
            api_key=required["AZURE_OPENAI_API_KEY"],
            azure_endpoint=required["AZURE_OPENAI_ENDPOINT"],
            api_version=required["AZURE_OPENAI_API_VERSION"],
            timeout=float(getattr(settings, "AI_REQUEST_TIMEOUT", 60)),
            max_retries=0,  # повторы делаем сами, см. OpenAICompatClient._call
        )
        deployment = required["AZURE_OPENAI_DEPLOYMENT"]
        price_in, price_out = pricing_from_settings(settings, deployment)  # ключ цены = имя деплоя
        return cls(client, deployment,
                   temperature=0.2 if temperature is None else float(temperature),
                   price_in_eur_per_m=price_in, price_out_eur_per_m=price_out)