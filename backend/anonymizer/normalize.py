
"""Нормализация текста перед regex-проходом.

Снимает обфускацию («info [at] x [dot] de»), переносы слов, юникод-мусор.
Сохраняет карту смещений, чтобы найденные спаны можно было вернуть
в координаты ИСХОДНОГО текста (нужно для подсветки в UI).
"""
import re
import unicodedata
from dataclasses import dataclass


@dataclass
class NormalizedText:
    text: str
    starts: list[int]  # для каждого символа normalized -> начало в оригинале
    ends: list[int]    # ... -> конец (exclusive) в оригинале

    def to_original(self, start: int, end: int) -> tuple[int, int]:
        """Диапазон [start, end) в normalized -> диапазон в оригинале."""
        return self.starts[start], self.ends[end - 1]


class _Buf:
    def __init__(self, text: str):
        self.text = text
        self.starts = list(range(len(text)))
        self.ends = [i + 1 for i in range(len(text))]

    def sub(self, pattern: "re.Pattern[str]", repl: str) -> None:
        out, starts, ends, pos = [], [], [], 0
        for m in pattern.finditer(self.text):
            s, e = m.span()
            if s == e:
                continue
            out.append(self.text[pos:s])
            starts += self.starts[pos:s]
            ends += self.ends[pos:s]
            if repl:
                out.append(repl)
                starts += [self.starts[s]] * len(repl)
                ends += [self.ends[e - 1]] * len(repl)
            pos = e
        out.append(self.text[pos:])
        starts += self.starts[pos:]
        ends += self.ends[pos:]
        self.text, self.starts, self.ends = "".join(out), starts, ends

    def nfkc(self) -> None:
        t, out, starts, ends, i = self.text, [], [], [], 0
        while i < len(t):
            j = i + 1
            while j < len(t) and unicodedata.combining(t[j]):
                j += 1
            g = unicodedata.normalize("NFKC", t[i:j])
            out.append(g)
            starts += [self.starts[i]] * len(g)
            ends += [self.ends[j - 1]] * len(g)
            i = j
        self.text, self.starts, self.ends = "".join(out), starts, ends


_INVISIBLE = re.compile(r"[\u00ad\u200b-\u200d\u2060\ufeff]")
_DASHES = re.compile(r"[\u2010-\u2015\u2212]")
_SPACES = re.compile(r"[\u00a0\u2007\u202f\t]")
_MULTISPACE = re.compile(r" {2,}")
_HYPHEN_BREAK = re.compile(r"(?<=[a-zäöüß])-[ ]*\n[ ]*(?=[a-zäöüß])")
_AT = re.compile(r"\s*[\[({<]\s*(?:at|ät)\s*[\])}>]\s*", re.I)
_DOT = re.compile(r"\s*[\[({<]\s*(?:dot|punkt)\s*[\])}>]\s*", re.I)
_SPACED_AT = re.compile(r"(?<=\w) +@ +(?=\w)")
_SPACED_TLD = re.compile(r"(?<=\w) \. (?=(?:de|com|io|ai|at|ch|eu)\b)", re.I)


def normalize(text: str) -> NormalizedText:
    b = _Buf(text)
    b.nfkc()
    b.sub(_INVISIBLE, "")
    b.sub(_DASHES, "-")
    b.sub(_SPACES, " ")
    b.sub(_MULTISPACE, " ")
    b.sub(_HYPHEN_BREAK, "")
    b.sub(_AT, "@")
    b.sub(_DOT, ".")
    b.sub(_SPACED_AT, "@")
    b.sub(_SPACED_TLD, ".")
    return NormalizedText(b.text, b.starts, b.ends)