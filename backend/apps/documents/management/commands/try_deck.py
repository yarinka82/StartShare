"""Прогоняет PDF через весь пайплайн (с настоящим провайдером из настроек) без БД и очереди.

    python manage.py try_deck testdecks/01_lumora_de.pdf --company "Lumora GmbH"
    python manage.py try_deck testdecks/04_injection.pdf --company "NordPay GmbH"
Только синтетические деки, пока TEASER_LLM_PROVIDER = gemini_free.
"""
from django.core.management.base import BaseCommand, CommandError

from apps.documents.pdf_extract import DeckExtractionError, extract_deck
from apps.documents.teaser.leak_check import company_terms
from apps.documents.teaser.llm import LLMError, get_client
from apps.documents.teaser.pipeline import PipelineError, run_pipeline


class Command(BaseCommand):
    help = "Полный прогон пайплайна на одном PDF, результат в консоль."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--company", default="", help="внутреннее название компании для проверки утечек")
        parser.add_argument("--retries", type=int, default=2)

    def handle(self, *args, **opts):
        try:
            with open(opts["path"], "rb") as f:
                content = extract_deck(f)
            client = get_client()
        except FileNotFoundError:
            raise CommandError(f"Файл не найден: {opts['path']}")
        except DeckExtractionError as exc:
            raise CommandError(f"Не удалось прочитать PDF: {exc.code}")
        except LLMError as exc:
            raise CommandError(f"Провайдер ШІ недоступен: {exc}")

        self.stdout.write("Вызов ШІ (до минуты)...")
        try:
            r = run_pipeline(content, {"sector": "", "stage": ""}, company_terms(opts["company"]),
                             client, max_retries=opts["retries"])
        except PipelineError as exc:
            raise CommandError(f"Пайплайн остановлен: {exc}")

        out = self.stdout.write
        out(f"Попыток: {r.attempts}   Стоимость: {r.cost_eur}   Язык: {r.draft['language']}")
        for name, text in r.draft["teaser"].items():
            out(f"\n[{name}]\n{text or '(пусто)'}")
        blanked = r.draft["review"]["blanked_fields"]
        if blanked:
            out(f"\nПоля очищены, в деке для них нет опоры: {blanked}")
        out(f"\n=== РИСКИ ({len(r.risk_phrases)}) ===")
        for p in r.risk_phrases:
            out(f"{p['category_id']:<4} {p['source']:<6} {p['action']:<10} [{p['field']}] {p['quote']!r}  {p.get('reason', '')}")
        leaks = [p for p in r.risk_phrases if p["source"] in ("regex", "leak")]
        out("\nПРОВЕРКА УТЕЧЕК: " + ("ЧИСТО (regex и сверка с названием ничего не нашли)" if not leaks else
            f"НАЙДЕНО {len(leaks)}: модель пропустила данные, которые не должны попасть в тизер"))