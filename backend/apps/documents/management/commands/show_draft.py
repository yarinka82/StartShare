
"""Печатает результат обработки дека: статус, тизер и найденные риски.

    python manage.py show_draft            # последний дек
    python manage.py show_draft --deck 3   # по id дека
    python manage.py show_draft --json     # сырой JSON
"""
import json

from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import PitchDeck, Teaser


class Command(BaseCommand):
    help = "Показать статус обработки дека, сгенерированный тизер и risk_phrases."

    def add_arguments(self, parser):
        parser.add_argument("--deck", type=int, help="id дека (по умолчанию: последний дек)")
        parser.add_argument("--json", action="store_true", help="вывести сырой JSON")

    def handle(self, *args, **opts):
        qs = PitchDeck.objects.select_related("startup_profile").prefetch_related("teaser__fields")
        deck = qs.filter(id=opts["deck"]).first() if opts["deck"] else qs.order_by("-id").first()
        
        if deck is None:
            raise CommandError("Презентаций (PitchDeck) нет в базе. Загрузите дек через API или админку.")

        out = self.stdout.write
        
        # Расчет времени выполнения (мс)
        duration_ms = "-"
        if deck.processing_started_at and deck.processing_finished_at:
            duration_ms = int((deck.processing_finished_at - deck.processing_started_at).total_seconds() * 1000)

        cost = f"€{deck.ai_cost_eur}" if deck.ai_cost_eur is not None else "€0.00"

        out(f"Дек ID: {deck.id} ({deck.original_name})   Статус: {deck.processing_state}")
        out(f"Попыток: {deck.attempt_count}   Время: {duration_ms} мс   Стоимость ШИ: {cost}")
        
        if deck.failure_reason:
            out(self.style.ERROR(f"Причина ошибки: {deck.failure_reason}"))

        if deck.processing_state != PitchDeck.ProcessingState.DRAFT_READY:
            hint = " Воркер Celery запущен?" if deck.processing_state == "QUEUED" else ""
            out(self.style.WARNING(f"\nЧернетка еще не готова (текущее состояние: {deck.processing_state}).{hint}"))
            return

        teaser = getattr(deck, "teaser", None) or Teaser.objects.filter(pitch_deck=deck).first()
        if not teaser:
            out(self.style.WARNING("\nСтатус DRAFT_READY, но запись Teaser отсутствует."))
            return

        # Собираем поля и риски
        fields_data = {}
        all_risks = []
        language = "de"

        for tf in teaser.fields.all().order_by("pk"):
            language = tf.language
            fields_data[tf.field_name] = tf.final_text or tf.ai_text or ""
            if isinstance(tf.risk_phrases, list):
                for rp in tf.risk_phrases:
                    if isinstance(rp, dict):
                        item = dict(rp)
                        item.setdefault("field", tf.field_name)
                        all_risks.append(item)

        if opts["json"]:
            payload = {
                "deck_id": deck.id,
                "teaser_id": teaser.id,
                "status": teaser.status,
                "language": language,
                "content": fields_data,
                "risk_phrases": all_risks,
            }
            out(json.dumps(payload, ensure_ascii=False, indent=2, default=str))
            return

        out(self.style.SUCCESS(f"\n=== ТИЗЕР (v{teaser.version}, статус: {teaser.status}, язык: {language}) ==="))
        for name, text in fields_data.items():
            out(f"\n[{name}]\n{text or '(пусто)'}")

        out(self.style.WARNING(f"\n=== НАЙДЕННЫЕ РИСКИ ({len(all_risks)}) ==="))
        if not all_risks:
            out("Рисковых фраз не обнаружено (тизер чистый).")
        else:
            for p in all_risks:
                cat = p.get("category_id", "R??")
                sev = p.get("severity", "warning")
                field = p.get("field", "-")
                quote = p.get("quote", "")
                out(f"{cat:<5} {sev:<10} [{field:<12}] {quote!r}")