import logging

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import OperationalError, ProgrammingError

ALLOWED_DECK_EXTENSIONS = {".pdf"}
logger = logging.getLogger(__name__)


def get_max_deck_size_mb() -> int:
    """Лимит размера дека из PlatformConfig (его меняют в админке); запасное значение из settings."""
    from apps.accounts.models import PlatformConfig

    mb = None
    try:
        mb = PlatformConfig.get_solo().max_deck_size_mb
    except (OperationalError, ProgrammingError):
        # таблицы ещё нет (до миграций), используем дефолт
        logger.warning("PlatformConfig недоступен, использую DECK_MAX_MB_DEFAULT")

    if not mb or mb <= 0:
        # getattr: раньше здесь был AttributeError, если DECK_MAX_MB_DEFAULT не объявлен в settings
        mb = getattr(settings, "DECK_MAX_MB_DEFAULT", 20)
    return int(mb)


def get_max_deck_size_bytes() -> int:
    return get_max_deck_size_mb() * 1024 * 1024


def _looks_like_pdf(file) -> bool:
    """Every PDF has "%PDF-" in its first 1024 bytes (readers accept a little junk before it)."""
    try:
        position = file.tell()
    except (AttributeError, OSError):
        position = 0
    try:
        file.seek(0)
        head = file.read(1024)
    finally:
        file.seek(position)
    return b"%PDF-" in head


def validate_deck_file(file):
    # 1. Порожній файл (раньше эта проверка шла после расширения)
    if not file or getattr(file, "size", 0) == 0:
        raise ValidationError("Файл порожній.", code="deck_empty")

    # 2. Розширення (суворо PDF під ШІ-пайплайн)
    name = getattr(file, "name", "").lower()
    ext = "." + name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in ALLOWED_DECK_EXTENSIONS:
        raise ValidationError("Недопустимий формат файлу. Дозволено лише PDF-файли.", code="deck_not_pdf")

    # 3. Вміст: розширення легко підробити, перевіряємо сигнатуру
    if not _looks_like_pdf(file):
        raise ValidationError("Файл не є PDF-документом.", code="deck_not_pdf")

    # 4. ДИНАМІЧНА перевірка розміру з PlatformConfig
    max_mb = get_max_deck_size_mb()
    if file.size > max_mb * 1024 * 1024:
        raise ValidationError(
            f"Розмір файлу перевищує встановлений ліміт у {max_mb} МБ.",
            code="deck_too_large",
        )


