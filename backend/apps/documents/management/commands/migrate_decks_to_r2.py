from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import FileSystemStorage, storages
from django.core.management.base import BaseCommand, CommandError

from apps.documents.models import PitchDeck


class Command(BaseCommand):
    help = "Копирует локальные файлы деков из PRIVATE_MEDIA_ROOT в R2 (имена сохраняются)."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true")
        parser.add_argument("--delete-local", action="store_true",
                            help="Удалять локальный файл после успешной загрузки")

    def handle(self, *args, dry_run, delete_local, **opts):
        target = storages["private"]
        if isinstance(target, FileSystemStorage):
            raise CommandError("Сейчас storage 'private' это диск, а не R2. Проверь переменные CLOUDFLARE_R2_*.")

        root = Path(settings.PRIVATE_MEDIA_ROOT)
        uploaded = skipped = missing = 0

        for deck in PitchDeck.objects.exclude(file="").iterator():
            name = deck.file.name
            local = root / name

            if not local.is_file():
                self.stderr.write(f"НЕТ ЛОКАЛЬНО: {name} (deck id={deck.pk})")
                missing += 1
                continue
            if target.exists(name):
                self.stdout.write(f"уже в R2: {name}")
                skipped += 1
                continue
            if dry_run:
                self.stdout.write(f"[dry-run] загрузил бы {name}")
                continue

            with local.open("rb") as fh:
                saved = target.save(name, File(fh))
            if saved != name:
                raise CommandError(f"Имя изменилось при загрузке: {name} -> {saved}")

            uploaded += 1
            self.stdout.write(f"ок: {name}")
            if delete_local:
                local.unlink()

        self.stdout.write(self.style.SUCCESS(
            f"Загружено: {uploaded}, пропущено: {skipped}, не найдено локально: {missing}"))
    
