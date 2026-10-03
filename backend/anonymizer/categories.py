
"""Справочник категорий риска (R01-R19 из BA-AI-risk-phrases.csv + N01-N13 из предложений).

Единый источник правды для regex-детектора, валидации ответа ШІ и UI.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Category:
    id: str
    name_uk: str
    detection: str  # regex | llm | regex+llm | image | meta
    action: str     # remove | generalize | highlight
    placeholder: str = ""


def _c(id, name, detection, action, placeholder=""):
    return id, Category(id, name, detection, action, placeholder)


CATEGORIES: dict[str, Category] = dict([
    _c("R01", "Назва компанії", "llm", "remove"),
    _c("R02", "Назва продукту", "llm", "remove"),
    _c("R03", "Імена людей", "llm", "remove"),
    _c("R04", "E-mail", "regex", "remove", "[REDACTED_EMAIL]"),
    _c("R05", "Посилання і домени", "regex", "remove", "[REDACTED_LINK]"),
    _c("R06", "Телефон", "regex", "remove", "[REDACTED_PHONE]"),
    _c("R07", "Соцмережі", "regex", "remove", "[REDACTED_SOCIAL]"),
    _c("R08", "Точна адреса", "llm", "generalize"),
    _c("R09", "Клієнти і партнери", "llm", "highlight"),
    _c("R10", "Інвестори", "llm", "highlight"),
    _c("R11", "Нагороди і акселератори", "llm", "highlight"),
    _c("R12", "Патенти", "llm", "highlight"),
    _c("R13", "Унікальні твердження", "llm", "highlight"),
    _c("R14", "Колишні роботодавці", "llm", "generalize"),
    _c("R15", "Університет-засновник", "llm", "generalize"),
    _c("R16", "Згадки в пресі", "llm", "highlight"),
    _c("R17", "Дата і місто заснування", "llm", "generalize"),
    _c("R18", "Номер у реєстрі", "regex", "remove", "[REDACTED_REGISTER]"),
    _c("R19", "Назва або логотип на зображенні", "image", "remove"),
    _c("N01", "Точні метрики", "llm", "generalize"),
    _c("N02", "Власні технології і терміни", "llm", "highlight"),
    _c("N03", "Сертифікати і регуляторика", "regex+llm", "highlight"),
    _c("N04", "Гранти і програми фінансування", "llm", "highlight"),
    _c("N05", "Регіональні ознаки", "llm", "generalize"),
    _c("N06", "Конкуренти з порівнянням", "llm", "highlight"),
    _c("N07", "IBAN / USt-IdNr / Steuernummer", "regex", "remove", "[REDACTED_FINANCE_ID]"),
    _c("N08", "QR- і штрих-коди", "image", "remove"),
    _c("N09", "Метадані PDF", "meta", "remove"),
    _c("N10", "Скріншоти продукту", "image", "remove"),
    _c("N11", "Фото людей", "image", "remove"),
    _c("N12", "Окремі точні дати", "llm", "generalize"),
    _c("N13", "Телефони без «+»", "regex", "remove", "[REDACTED_PHONE]"),
])