import re
from rest_framework.exceptions import ValidationError

# Регулярні вирази для пошуку контактів
URL_REGEX = re.compile(r"(https?://\S+|www\.\S+|\b[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}\b)", re.IGNORECASE)
EMAIL_REGEX = re.compile(r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE)
PHONE_REGEX = re.compile(r"(\+?\d[\d\s\-\(\)/]{7,}\d)")


def validate_investor_message(text: str) -> str:
    """
    Перевіряє коротке повідомлення інвестора на анти-лік:
    - максимум 500 символів
    - відхиляє email, URL та номери телефонів
    """
    if not text:
        return ""

    cleaned = text.strip()
    if len(cleaned) > 500:
        raise ValidationError("Повідомлення не може перевищувати 500 символів.")

    if EMAIL_REGEX.search(cleaned):
        raise ValidationError("Повідомлення не повинно містити адресу електронної пошти.")

    if URL_REGEX.search(cleaned):
        raise ValidationError("Повідомлення не повинно містити посилання або веб-сайти.")

    if PHONE_REGEX.search(cleaned):
        raise ValidationError("Повідомлення не повинно містити номери телефонів.")

    return cleaned