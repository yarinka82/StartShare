"""Правила редактирования и затверждения тизера (REQ-14). Без Django, тестируется отдельно."""
from pydantic import ValidationError

from .contract import FIELD_NAMES, PLACEHOLDER_PREFIX, TeaserFields
from .leak_check import ForbiddenTerm
from .phrases import DETERMINISTIC, final_checks, merge_phrases

REQUIRED_FIELDS = ("headline", "problem", "solution")


def validate_content(content: dict) -> dict[str, str]:
    """Возвращает {поле: сообщение} для невалидных полей; пусто = всё в порядке."""
    errors: dict[str, str] = {}
    try:
        TeaserFields.model_validate(content)
    except ValidationError as exc:
        for e in exc.errors():
            errors[str(e["loc"][0])] = e["msg"]
    for name, text in content.items():
        if PLACEHOLDER_PREFIX in text:
            errors[name] = "Text must not contain [REDACTED_*] markers."
    return errors


def refresh_phrases(content: dict, old: list[dict], terms: list[ForbiddenTerm]) -> list[dict]:
    """После правки: фразы ШІ остаются, только если цитата ещё в тексте; regex и leak считаются заново."""
    kept = []
    for p in old:
        if p["source"] == "llm" and p["field"] in content and p["quote"] in content[p["field"]]:
            start = content[p["field"]].find(p["quote"])
            kept.append({**p, "start": start, "end": start + len(p["quote"])})
    return merge_phrases(kept, final_checks(content, terms))


def risky_fields(phrases: list[dict]) -> set[str]:
    return {p["field"] for p in phrases if p["source"] in DETERMINISTIC}


def approval_blockers(content: dict, reviewed: list[str], phrases: list[dict]) -> list[dict]:
    blockers = []
    risky = risky_fields(phrases)
    for name in FIELD_NAMES:
        text = (content.get(name) or "").strip()
        if not text:
            if name in REQUIRED_FIELDS:
                blockers.append({"field": name, "code": "empty_required"})
            continue
        if name in risky:
            blockers.append({"field": name, "code": "risk_found"})
        if name not in reviewed:
            blockers.append({"field": name, "code": "not_reviewed"})
    return blockers