from unittest import mock

from django.test import SimpleTestCase, override_settings

from apps.documents.teaser import factory
from apps.documents.teaser.factory import get_client, LLMNotConfigured
from apps.documents.teaser.gemini import GeminiClient
from apps.documents.teaser.openai_client import OpenAIClient

BASE = dict(
    TEASER_LLM_PROVIDER="gemini",
    AI_ALLOW_FREE_TIER=False,
    TEASER_GEMINI_API_KEY="g-key",
    TEASER_GEMINI_MODEL="gemini-test",
    OPENAI_API_KEY="o-key",
    OPENAI_MODEL="gpt-test",
    AZURE_OPENAI_API_KEY="a-key",
    AZURE_OPENAI_ENDPOINT="https://example.openai.azure.com",
    AZURE_OPENAI_DEPLOYMENT="my-deployment",
    AZURE_OPENAI_API_VERSION="2099-01-01",
    AI_REQUEST_TIMEOUT=30,
    AI_PRICING_EUR_PER_MTOK={},
)


def config(provider, model="", temperature=0.2):
    return mock.patch.object(factory, "_read_config", return_value=(provider, model, temperature))


@override_settings(**BASE)
class FactoryTests(SimpleTestCase):
    def test_openai(self):
        with config("openai"):
            client = get_client()
        self.assertIsInstance(client, OpenAIClient)
        self.assertEqual(client.model, "gpt-test")

    def test_azure_uses_deployment_name(self):
        with config("azure_openai"):
            client = get_client()
        self.assertIsInstance(client, OpenAIClient)
        self.assertEqual(client.model, "my-deployment")

    def test_gemini_paid(self):
        with config("gemini"):
            self.assertIsInstance(get_client(), GeminiClient)

    def test_free_tier_blocked_in_production(self):
        with config("gemini_free"), self.assertRaises(LLMNotConfigured):
            get_client()

    @override_settings(TEASER_LLM_PROVIDER="gemini_free")
    def test_old_setting_still_marks_free_tier(self):
        with config("gemini"), self.assertRaises(LLMNotConfigured):
            get_client()

    @override_settings(AI_ALLOW_FREE_TIER=True)
    def test_free_tier_allowed_in_development(self):
        with config("gemini_free"):
            self.assertIsInstance(get_client(), GeminiClient)

    def test_unknown_provider(self):
        with config("claude-lite"), self.assertRaises(LLMNotConfigured):
            get_client()

    @override_settings(OPENAI_API_KEY="")
    def test_missing_key(self):
        with config("openai"), self.assertRaises(LLMNotConfigured):
            get_client()

    def test_config_unreadable_uses_settings_but_same_checks(self):
        from django.db import DatabaseError

        with mock.patch.object(factory, "_read_config", side_effect=DatabaseError("down")):
            self.assertIsInstance(get_client(), GeminiClient)  # TEASER_LLM_PROVIDER = "gemini"
        with override_settings(TEASER_LLM_PROVIDER="gemini_free"), \
                mock.patch.object(factory, "_read_config", side_effect=DatabaseError("down")), \
                self.assertRaises(LLMNotConfigured):
            get_client()


class StrictSchemaTests(SimpleTestCase):
    def test_objects_are_closed_and_fully_required(self):
        schema = {"type": "object", "properties": {"a": {"type": "string"}, "b": {"type": "object", "properties": {"c": {"type": "string"}}}}}
        out = _strictify(schema)
        self.assertEqual(out["required"], ["a", "b"])
        self.assertFalse(out["additionalProperties"])
        self.assertFalse(out["properties"]["b"]["additionalProperties"])
        self.assertNotIn("required", schema)  # the original is untouched