
from decimal import Decimal
from types import SimpleNamespace

import pytest

pytest.importorskip("google.genai")
from google.genai import errors  # noqa: E402

from apps.documents.pdf_extract import DeckContent, SlideContent  # noqa: E402
from apps.documents.teaser.gemini import GeminiClient  # noqa: E402
from apps.documents.teaser.llm import LLMError, RemoteProviderNotAllowed  # noqa: E402
from apps.documents.teaser.pipeline import run_pipeline  # noqa: E402

GOOD = ('{"teaser": {"headline": "Software fuer die Pflege", "problem": "Zeitverlust.", '
        '"solution": "Cloud-Loesung."}, "risk_phrases": [], "language": "de"}')


class FakeSDK:
    """Подменяет genai.Client: очередь ответов или исключений."""

    def __init__(self, *items):
        self.items, self.calls = list(items), []
        self.models = SimpleNamespace(generate_content=self._gen)

    def _gen(self, **kw):
        self.calls.append(kw)
        item = self.items.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def resp(text=GOOD, tin=100, tout=50, thoughts=10):
    return SimpleNamespace(text=text, usage_metadata=SimpleNamespace(
        prompt_token_count=tin, candidates_token_count=tout, thoughts_token_count=thoughts))


def client(sdk, **kw):
    sleeps = []
    c = GeminiClient("k", "test-model", free_tier=kw.pop("free_tier", True), client=sdk,
                     sleep=sleeps.append, **kw)
    return c, sleeps


def call(c):
    return c.generate_json(system="SYS", user="USER", schema={"type": "object"})


def test_parses_json_and_sends_expected_config():
    sdk = FakeSDK(resp())
    r = call(client(sdk)[0])
    assert r.data["language"] == "de" and r.cost_eur == Decimal("0")
    assert (r.input_tokens, r.output_tokens) == (100, 60)
    kw = sdk.calls[0]
    assert kw["model"] == "test-model" and kw["contents"] == "USER"
    cfg = kw["config"]
    assert cfg.system_instruction == "SYS"
    assert cfg.response_mime_type == "application/json"
    assert cfg.response_json_schema == {"type": "object"}


def test_markdown_fences_are_stripped():
    assert call(client(FakeSDK(resp("```json\n" + GOOD + "\n```")))[0]).data["language"] == "de"


def test_invalid_json_returns_empty_dict_so_pipeline_retries():
    assert call(client(FakeSDK(resp("not json {")))[0]).data == {}


def test_empty_response_is_error():
    with pytest.raises(LLMError):
        call(client(FakeSDK(resp(None)))[0])


def test_retries_on_429_then_succeeds():
    sdk = FakeSDK(errors.ClientError(429, {"error": {"message": "quota"}}), resp())
    c, sleeps = client(sdk)
    assert call(c).data["language"] == "de"
    assert len(sdk.calls) == 2 and sleeps == [2]


def test_gives_up_after_max_attempts_without_leaking_message():
    sdk = FakeSDK(*[errors.ServerError(503, {"error": {"message": "secret detail"}})] * 3)
    c, sleeps = client(sdk)
    with pytest.raises(LLMError) as e:
        call(c)
    assert "503" in str(e.value) and "secret" not in str(e.value)
    assert len(sdk.calls) == 3 and sleeps == [2, 4]


def test_client_error_is_not_retried():
    sdk = FakeSDK(errors.ClientError(400, {"error": {"message": "bad"}}))
    c, sleeps = client(sdk)
    with pytest.raises(LLMError):
        call(c)
    assert len(sdk.calls) == 1 and sleeps == []


def test_paid_cost_from_prices():
    c, _ = client(FakeSDK(resp(tin=1_000_000, tout=400_000, thoughts=100_000)), free_tier=False,
                  price_in_eur_per_m=Decimal("0.30"), price_out_eur_per_m=Decimal("2.00"))
    assert call(c).cost_eur == Decimal("1.30")           # 0.30 + 0.5M * 2.00


def test_paid_cost_unknown_without_prices():
    c, _ = client(FakeSDK(resp()), free_tier=False)
    assert call(c).cost_eur is None


# --- защитные условия ---
def settings(**kw):
    base = dict(DEBUG=True, TEASER_GEMINI_API_KEY="k", TEASER_AVV_SIGNED=False)
    base.update(kw)
    return SimpleNamespace(**base)


def test_free_tier_refused_outside_debug():
    with pytest.raises(RemoteProviderNotAllowed):
        GeminiClient.from_settings(settings(DEBUG=False), free_tier=True)


def test_missing_key_is_error():
    with pytest.raises(LLMError):
        GeminiClient.from_settings(settings(TEASER_GEMINI_API_KEY=""), free_tier=True)


def test_free_tier_allowed_in_debug():
    assert GeminiClient.from_settings(settings(), free_tier=True).free_tier is True


# --- вместе с пайплайном ---
def test_works_inside_pipeline():
    slides = [SlideContent(1, "Wir bauen Software fuer die ambulante Pflege und Dokumentation.", 0, False)]
    deck = DeckContent(1, slides)
    c, _ = client(FakeSDK(resp()))
    r = run_pipeline(deck, {}, [], c, max_retries=1)
    assert r.draft["language"] == "de" and r.cost_eur == Decimal("0")