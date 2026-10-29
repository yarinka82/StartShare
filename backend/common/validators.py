
from django.core.exceptions import ValidationError

ALLOWED_DECK_EXTENSIONS = {".pdf", ".ppt", ".pptx"}
MAX_DECK_SIZE_MB = 20

def validate_deck_file(file):
    ext = "." + file.name.rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_DECK_EXTENSIONS:
        raise ValidationError(f"Недопустимый формат файла: {ext}")
    if file.size > MAX_DECK_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Файл больше {MAX_DECK_SIZE_MB} МБ")