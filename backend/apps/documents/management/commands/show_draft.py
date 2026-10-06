
"""Печатает результат обработки дека: статус, тизер и найденные риски.

    python manage.py show_draft            # последняя задача
    python manage.py show_draft --deck 3   # по id дека
    python manage.py show_draft --json     # сырой JSON
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import TeaserJob


class Command(BaseCommand):
    help = "Показать статус, чернетку и risk_phrases задачи обработки дека."

    def add_arguments(self, parser):
        parser.add_argument("--deck", type=int, help="id дека (по умолчанию: последняя задача)")
        parser.add_argument("--json", action="store_true", help="вывести сырой JSON")

    def handle(self, *args, **opts):
        qs = TeaserJob.objects.select_related("deck")
        job = qs.filter(deck_id=opts["deck"]).first() if opts["deck"] else qs.order_by("-id").first()
        if job is None:
            raise CommandError("Задач обработки нет. Загрузите дек или вызовите start_teaser_job().")

        out = self.stdout.write
        out(f"Дек: {job.deck_id} ({job.deck.original_name})   Задача: {job.id}   Состояние: {job.state}")
        out(f"Попыток: {job.attempts}   Время: {job.processing_ms} мс   Стоимость: {job.cost_eur}")
        if job.error:
            out(f"Ошибка: {job.error}")
        if job.state != TeaserJob.State.DRAFT_READY:
            out("\nЧернетки пока нет." + (" Воркер Celery запущен?" if job.state == "QUEUED" else ""))
            return

        if opts["json"]:
            out(json.dumps({"draft": job.draft, "risk_phrases": job.risk_phrases}, ensure_ascii=False, indent=2))
            return

        out(f"\n=== ТИЗЕР (язык: {job.draft.get('language')}) ===")
        for name, text in job.draft["teaser"].items():
            out(f"\n[{name}]\n{text or '(пусто)'}")
        review = job.draft.get("review", {})
        if review.get("blanked_fields"):
            out(f"\nПоля очищены, в деке для них нет опоры: {review['blanked_fields']}")
        if review.get("image_slides"):
            out(f"\nСлайды с изображениями (проверьте логотипы): {review['image_slides']}")

        out(f"\n=== РИСКИ ({len(job.risk_phrases)}) ===")
        for p in job.risk_phrases:
            out(f"{p['category_id']:<4} {p['source']:<6} {p['action']:<10} [{p['field']}] {p['quote']!r}  {p.get('reason', '')}")