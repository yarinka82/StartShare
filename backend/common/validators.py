from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError
import logging
ALLOWED_DECK_EXTENSIONS = {".pdf"}
logger = logging.getLogger(__name__)



def get_max_deck_size_bytes() -> int:
    """Лимит размера дека из PlatformConfig; запасное значение из settings."""
    from apps.accounts.models import PlatformConfig

    mb = None
    try:
        mb = PlatformConfig.get_solo().max_deck_size_mb
    except (OperationalError, ProgrammingError):
        # таблицы ещё нет (до миграций) — используем дефолт
        logger.warning("PlatformConfig недоступен, использую DECK_MAX_MB_DEFAULT")

    if not mb or mb <= 0:
        mb = settings.DECK_MAX_MB_DEFAULT
    return int(mb) * 1024 * 1024


def validate_deck_file(file):
    name = getattr(file, "name", "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""

    # 1. Перевірка розширення (суворо PDF під ШІ-пайплайн)
    if ext not in ALLOWED_DECK_EXTENSIONS:
        raise ValidationError(
            f"Недопустимий формат файлу ({ext}). Дозволено лише PDF-файли.",
            code="deck_not_pdf"
        )

    # 2. Перевірка на порожній файл
    if not file or getattr(file, "size", 0) == 0:
        raise ValidationError("Файл порожній.", code="deck_empty")

    # 3. ДИНАМІЧНА перевірка розміру з PlatformConfig
    max_bytes = get_max_deck_size_bytes()
    if file.size > max_bytes:
        max_mb = max_bytes // (1024 * 1024)
        raise ValidationError(
            f"Розмір файлу перевищує встановлений ліміт у {max_mb} МБ.",
            code="deck_too_large"
        )