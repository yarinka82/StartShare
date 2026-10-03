
"""Извлечение содержимого PDF-дека (шаг 4 пайплайна).

Библиотеки: pdfplumber (текст, изображения на странице), pypdf (очистка метаданных).
Не зависит от Django: принимает путь или файловый объект.
"""
from dataclasses import dataclass, field
from io import BytesIO
from typing import BinaryIO

import pdfplumber
from pypdf import PdfReader, PdfWriter
from pypdf.errors import PdfReadError

MAX_PAGES = 60          # защита от «бомб»; подберите по ТЗ
MIN_TEXT_CHARS = 50     # меньше — слайд считаем изображением (Q-31)


class DeckExtractionError(Exception):
    """code: encrypted | corrupted | too_many_pages | empty"""

    def __init__(self, code: str, message: str = ""):
        super().__init__(message or code)
        self.code = code


@dataclass
class SlideContent:
    number: int              # с 1
    text: str
    image_count: int
    is_image_slide: bool     # почти нет текста: содержимое, вероятно, в картинке


@dataclass
class DeckContent:
    page_count: int
    slides: list[SlideContent] = field(default_factory=list)

    @property
    def image_slide_numbers(self) -> list[int]:
        """Слайды, где ШІ и regex не видят часть содержимого (R19, N08, N10, N11)."""
        return [s.number for s in self.slides if s.is_image_slide]

    @property
    def slides_with_images(self) -> list[int]:
        """Слайды с любыми изображениями: стартапу показываем «проверьте логотипы»."""
        return [s.number for s in self.slides if s.image_count > 0]

    @property
    def has_text(self) -> bool:
        return any(s.text.strip() for s in self.slides)


def extract_deck(source: "str | BinaryIO", *, max_pages: int = MAX_PAGES,
                 min_text_chars: int = MIN_TEXT_CHARS) -> DeckContent:
    try:
        with pdfplumber.open(source) as pdf:
            total = len(pdf.pages)
            if total > max_pages:
                raise DeckExtractionError("too_many_pages", f"{total} > {max_pages}")
            slides = []
            for i, page in enumerate(pdf.pages, start=1):
                text = (page.extract_text() or "").strip()
                images = len(page.images)
                slides.append(SlideContent(i, text, images, len(text) < min_text_chars))
    except DeckExtractionError:
        raise
    except Exception as exc:  # pdfminer/pdfplumber бросают разные типы
        names = [type(exc).__name__] + [type(a).__name__ for a in exc.args]
        if any("Password" in n or "Encrypt" in n for n in names):
            raise DeckExtractionError("encrypted") from exc
        raise DeckExtractionError("corrupted", names[-1]) from exc

    content = DeckContent(page_count=total, slides=slides)
    if total == 0:
        raise DeckExtractionError("empty", "no pages")
    return content


def strip_metadata(source: "str | BinaryIO") -> bytes:
    """Копия PDF без метаданных (Author, Title, Creator, XMP): N09.

    Нужна, только если сам файл уходит провайдеру ШІ (при подписанном AVV, REQ-39).
    Если провайдеру уходит один извлечённый текст, метаданные вообще не передаются.
    """
    try:
        reader = PdfReader(source)
        if reader.is_encrypted:
            raise DeckExtractionError("encrypted")
        writer = PdfWriter()
        for page in reader.pages:
            writer.add_page(page)
        writer.add_metadata({})        # без полей документа
        buf = BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except DeckExtractionError:
        raise
    except PdfReadError as exc:
        raise DeckExtractionError("corrupted") from exc