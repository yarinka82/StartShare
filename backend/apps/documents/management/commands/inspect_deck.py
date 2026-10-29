"""Показывает, что наш алгоритм делает с PDF, без БД, очереди и провайдера ШІ.

    python manage.py inspect_deck path/to/deck.pdf
    python manage.py inspect_deck path/to/deck.pdf --prompt   # + точный запрос, который уйдёт провайдеру
"""
from django.core.management.base import BaseCommand, CommandError

from anonymizer import detect
from anonymizer.categories import CATEGORIES
from apps.documents.pdf_extract import DeckExtractionError, extract_deck
from apps.documents.teaser.prompt import build_system_prompt, build_user_prompt


class Command(BaseCommand):
    help = "Показать извлечение текста и regex-находки для PDF-дека."

    def add_arguments(self, parser):
        parser.add_argument("path")
        parser.add_argument("--prompt", action="store_true", help="напечатать промпт, который получит ШІ")

    def handle(self, *args, **opts):
        try:
            with open(opts["path"], "rb") as f:
                deck = extract_deck(f)
        except FileNotFoundError:
            raise CommandError(f"Файл не найден: {opts['path']}")
        except DeckExtractionError as exc:
            raise CommandError(f"Не удалось прочитать PDF: {exc.code}")

        out = self.stdout.write
        out(f"Слайдов: {deck.page_count}. Слайды-картинки: {deck.image_slide_numbers or '-'}. "
            f"Слайды с изображениями: {deck.slides_with_images or '-'}")
        if not deck.has_text:
            out("\nТекста нет: такой дек получит ошибку no_text (нужен vision, Q-31).")
            return

        redacted_slides, total = [], {}
        for s in deck.slides:
            r = detect(s.text)
            redacted_slides.append(r.redacted_text)
            out(f"\n=== Слайд {s.number} ===")
            if not r.spans:
                out("  regex: ничего не найдено")
            for sp in r.spans:
                cat = CATEGORIES[sp.category_id]
                total[sp.category_id] = total.get(sp.category_id, 0) + 1
                out(f"  [{sp.category_id} {cat.name_uk}] {sp.text!r}  ->  {cat.placeholder}")

        out("\n=== Итого regex-находок по категориям ===")
        for cid, n in sorted(total.items()):
            out(f"  {cid} {CATEGORIES[cid].name_uk}: {n}")
        out("\nНазвания, имена, клиенты, инвесторы, награды, уникальные утверждения и т.п. "
            "regex не ловит: это работа ШІ (категории с detection=llm).")

        if opts["prompt"]:
            out("\n=== SYSTEM PROMPT ===\n" + build_system_prompt())
            out("\n=== USER PROMPT (то, что получит провайдер; контакты уже вырезаны) ===\n"
                + build_user_prompt(redacted_slides, {"sector": "...", "stage": "..."}))