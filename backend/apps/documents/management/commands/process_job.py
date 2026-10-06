
"""Запускает обработку дека прямо в этом процессе (без Redis и воркера) и печатает результат.

    python manage.py process_job            # последняя задача
    python manage.py process_job --deck 5   # по id дека
Задача в любом состоянии возвращается в QUEUED и обрабатывается заново.
"""
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import TeaserJob
from apps.documents.tasks import process_deck


class Command(BaseCommand):
    help = "Синхронно обработать задачу тизера и показать результат."

    def add_arguments(self, parser):
        parser.add_argument("--deck", type=int, help="id дека (по умолчанию: последняя задача)")

    def handle(self, *args, **opts):
        qs = TeaserJob.objects.all()
        job = qs.filter(deck_id=opts["deck"]).first() if opts["deck"] else qs.order_by("-id").first()
        if job is None:
            raise CommandError("Задач обработки нет.")
        field = TeaserJob._meta.get_field("deck").related_model
        self.stdout.write(f"Задача {job.id}, дек {job.deck_id}, модель дека: {field._meta.label}")

        TeaserJob.objects.filter(pk=job.pk).update(
            state=TeaserJob.State.QUEUED, error="", attempts=0, draft=None, risk_phrases=[],
            started_at=None, ready_at=None)
        self.stdout.write("Обработка запущена (вызов ШІ может занять до минуты)...")
        process_deck.apply(args=[job.id])
        call_command("show_draft", deck=job.deck_id)