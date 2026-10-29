
"""Построение и объединение risk_phrases. Общий код для пайплайна и редактирования."""
from anonymizer import scan_fields
from anonymizer.categories import CATEGORIES

from .leak_check import ForbiddenTerm, find_leaks

DETERMINISTIC = {"regex", "leak"}  # находки, в которых мы уверены; они блокируют затверждение


def make_phrase(category_id: str, field: str, quote: str, reason: str, source: str, text: str) -> dict:
    start = text.find(quote)
    found = start >= 0
    return {
        "category_id": category_id, "field": field, "quote": quote,
        "action": CATEGORIES[category_id].action, "reason": reason, "source": source,
        "start": start if found else None, "end": start + len(quote) if found else None,
    }


def final_checks(fields: dict[str, str], terms: list[ForbiddenTerm]) -> list[dict]:
    """Шаг 8: regex-проход и проверка внутренних данных формы по текстовым полям тизера."""
    out = []
    for f in scan_fields(fields):
        sp = f.span
        out.append(make_phrase(sp.category_id, f.field, sp.text, "pattern match", "regex", fields[f.field]))
    for lk in find_leaks(fields, terms):
        out.append(make_phrase(lk.category_id, lk.field, lk.text, lk.reason, "leak", fields[lk.field]))
    return out


def merge_phrases(base: list[dict], deterministic: list[dict]) -> list[dict]:
    """Дубли по (field, quote) схлопываются; детерминированная версия побеждает (она блокирующая)."""
    merged: dict[tuple, dict] = {}
    for p in base:
        merged.setdefault((p["field"], p["quote"]), p)
    for p in deterministic:
        merged[(p["field"], p["quote"])] = p
    return list(merged.values())