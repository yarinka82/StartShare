
"""Проверка «утёкших» сущностей: внутренние данные формы не должны быть в тексте тизера."""
import re
from dataclasses import dataclass
from decimal import Decimal

_SUFFIXES = (r"gmbh\s*&\s*co\.?\s*kg|gmbh|mbh|ug(?:\s*\(haftungsbeschränkt\))?|ag|se|kg|ohg|gbr|e\.v\.|"
             r"ltd\.?|limited|inc\.?|llc|corp\.?|plc|b\.v\.|bv|sas|sa|oy|ab")
_SUFFIX_RX = re.compile(rf"[\s,]+(?:{_SUFFIXES})\s*$", re.I)
_SEP = r"[ .,\u00a0\u202f'’]?"


@dataclass(frozen=True)
class ForbiddenTerm:
    pattern: "re.Pattern[str]"
    category_id: str
    label: str


@dataclass(frozen=True)
class Leak:
    field: str
    category_id: str
    start: int
    end: int
    text: str
    reason: str


def _text_term(term: str, category_id: str, label: str) -> "ForbiddenTerm | None":
    term = " ".join(term.split())
    if len(term) < 3:
        return None
    body = re.escape(term).replace(r"\ ", r"\s+")
    return ForbiddenTerm(re.compile(rf"(?<!\w){body}(?!\w)", re.I), category_id, label)


def company_terms(name: str) -> list[ForbiddenTerm]:
    """Полное название и короткая форма без юридического суффикса (Lumora GmbH -> Lumora)."""
    out = []
    name = (name or "").strip()
    if not name:
        return out
    short = _SUFFIX_RX.sub("", name).strip()
    for t in {name, short}:
        ft = _text_term(t, "R01", "company_name")
        if ft:
            out.append(ft)
    return out


def number_terms(value, label: str, category_id: str = "N01") -> list[ForbiddenTerm]:
    """Точное число в разных записях (47200, 47 200, 47.200, 47,200). Только значения >= 1000."""
    if value is None:
        return []
    n = int(Decimal(value))
    if n < 1000:
        return []
    groups = f"{n:,}".split(",")
    body = _SEP.join(groups)
    return [ForbiddenTerm(re.compile(rf"(?<!\d){body}(?!\d)"), category_id, label)]


def terms_from_profile(profile, extra_names: "list[str] | None" = None) -> list[ForbiddenTerm]:
    terms = company_terms(getattr(profile, "company_name", ""))
    terms += number_terms(getattr(profile, "mrr", None), "mrr")
    terms += number_terms(getattr(profile, "amount_sought", None), "amount_sought")
    for name in extra_names or []:  # например, имена основателей, когда появятся в данных
        ft = _text_term(name, "R03", "person_name")
        if ft:
            terms.append(ft)
    return terms


def find_leaks(fields: dict[str, str], terms: list[ForbiddenTerm]) -> list[Leak]:
    leaks = []
    for name, text in fields.items():
        if not isinstance(text, str):
            continue
        for t in terms:
            for m in t.pattern.finditer(text):
                leaks.append(Leak(name, t.category_id, m.start(), m.end(), m.group(),
                                  f"matches internal field '{t.label}'"))
    return leaks