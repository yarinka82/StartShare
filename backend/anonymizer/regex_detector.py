
"""Regex-детектор категорий R04-R07, R18, N07, N13.

Работает на нормализованном тексте, спаны возвращает в координатах оригинала.
Приоритеты при пересечении: e-mail > финансовые ID > реестр > соцсети > URL/домен > телефон.
"""
import re
from dataclasses import dataclass, field

from .categories import CATEGORIES
from .normalize import NormalizedText, normalize

_TRAIL = ".,;:!?)]}'\""


@dataclass(frozen=True)
class Span:
    category_id: str
    start: int       # координаты в ИСХОДНОМ тексте
    end: int
    text: str
    norm_start: int  # координаты в нормализованном тексте
    norm_end: int


@dataclass
class DetectionResult:
    normalized_text: str
    redacted_text: str
    spans: list[Span] = field(default_factory=list)

    @property
    def has_findings(self) -> bool:
        return bool(self.spans)


@dataclass(frozen=True)
class FieldFinding:
    field: str
    span: Span


def _iban_ok(compact: str) -> bool:
    if not (15 <= len(compact) <= 34):
        return False
    rearranged = compact[4:] + compact[:4]
    num = "".join(str(int(c, 36)) for c in rearranged)
    return int(num) % 97 == 1


def _iban_trim(m: "re.Match[str]") -> "tuple[int, int] | None":
    s, e = m.span()
    raw = m.group()
    for cut in range(len(raw), 14, -1):
        compact = raw[:cut].replace(" ", "")
        if _iban_ok(compact):
            return s, s + cut
    return None


def _digits_9_15(m: "re.Match[str]") -> "tuple[int, int] | None":
    n = sum(ch.isdigit() for ch in m.group())
    return m.span() if 9 <= n <= 15 else None


def _plain(m: "re.Match[str]") -> "tuple[int, int]":
    return m.span()


def _trimmed(m: "re.Match[str]") -> "tuple[int, int]":
    s, e = m.span()
    raw = m.group()
    stripped = raw.rstrip(_TRAIL)
    return s, s + len(stripped)


_SOCIAL_HOSTS = r"(?:linkedin|xing|facebook|instagram|twitter|tiktok|youtube)\.com|x\.com|t\.me"

# (приоритет, category_id, regex, обработчик спана)
_RULES = [
    (1, "R04", re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+"), _trimmed),
    (2, "N07", re.compile(r"\b[A-Z]{2}\d{2}(?: ?[A-Z0-9]){11,30}"), _iban_trim),
    (2, "N07", re.compile(r"\bDE ?\d{9}\b"), _plain),
    (2, "N07", re.compile(r"\bSteuer(?:nummer|-Nr\.?)\s*:?\s*\d[\d/ ]{6,}\d", re.I), _plain),
    (3, "R18", re.compile(r"\bHR[AB]\s?\d+\b|\bCompany\s+No\.?\s?\d+\b", re.I), _plain),
    (4, "R07", re.compile(rf"(?:https?://)?(?:www\.)?(?:{_SOCIAL_HOSTS})/\S+", re.I), _trimmed),
    (4, "R07", re.compile(r"(?<![\w@.])@[A-Za-z0-9_]{3,}"), _plain),
    (5, "R05", re.compile(r"(?:https?://|www\.)[^\s<>\"')\]]+", re.I), _trimmed),
    (5, "R05", re.compile(
        r"\b[A-Za-z][\w-]*(?:\.[\w-]+)*\.(?:de|com|io|ai|at|ch|eu)\b(?:/[^\s<>\"')\]]*)?", re.I), _trimmed),
    (6, "R06", re.compile(
        r"(?<![\w+])(?:\+|00)[1-9]\d{0,2}[ .\-/]?(?:\(0\)[ .\-/]?)?\d(?:[ .\-/]?\d){5,13}"), _digits_9_15),
    (7, "N13", re.compile(
        r"(?<![\w.,+/-])\(?0[1-9]\d{1,4}\)?[ /-]?\d{3,}(?:[ -]\d{2,})*"), _digits_9_15),
]


def _resolve(cands: list[list]) -> list[list]:
    """cands: [prio, start, end, category]. Пересечения поглощаются спаном с высшим приоритетом."""
    cands.sort(key=lambda c: (c[0], c[1], -(c[2] - c[1])))
    accepted: list[list] = []
    for c in cands:
        for a in accepted:
            if c[1] < a[2] and c[2] > a[1]:
                a[1], a[2] = min(a[1], c[1]), max(a[2], c[2])
                break
        else:
            accepted.append(list(c))
    accepted.sort(key=lambda a: a[1])
    merged: list[list] = []
    for a in accepted:
        if merged and a[1] < merged[-1][2]:
            merged[-1][2] = max(merged[-1][2], a[2])
        else:
            merged.append(a)
    return merged


def detect(text: str) -> DetectionResult:
    nt: NormalizedText = normalize(text)
    cands: list[list] = []
    for prio, cat, rx, handler in _RULES:
        for m in rx.finditer(nt.text):
            r = handler(m)
            if r and r[1] > r[0]:
                cands.append([prio, r[0], r[1], cat])

    spans: list[Span] = []
    redacted = nt.text
    for _, s, e, cat in _resolve(cands):
        os_, oe = nt.to_original(s, e)
        spans.append(Span(cat, os_, oe, text[os_:oe], s, e))
    for sp in reversed(spans):
        redacted = redacted[:sp.norm_start] + CATEGORIES[sp.category_id].placeholder + redacted[sp.norm_end:]
    return DetectionResult(nt.text, redacted, spans)


def scan_fields(fields: dict[str, str]) -> list[FieldFinding]:
    """Финальная проверка текстовых полей тизера (шаг 8). Спаны — в координатах поля."""
    out: list[FieldFinding] = []
    for name, value in fields.items():
        if isinstance(value, str) and value:
            out += [FieldFinding(name, sp) for sp in detect(value).spans]
    return out