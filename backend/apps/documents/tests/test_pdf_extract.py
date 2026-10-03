
import io

import pytest
from PIL import Image
from pypdf import PdfReader
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas

from apps.documents.pdf_extract import DeckExtractionError, extract_deck, strip_metadata


def make_pdf(pages, *, title="Lumora GmbH Deck", author="Anna Beispiel", encrypt=None):
    """pages: list[(text | None, with_image)]"""
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=(800, 450), encrypt=encrypt)
    c.setTitle(title)
    c.setAuthor(author)
    for text, with_image in pages:
        if text:
            c.setFont("Helvetica", 14)
            y = 400
            for line in text.split("\n"):
                c.drawString(40, y, line)
                y -= 20
        if with_image:
            img = Image.new("RGB", (200, 100), (30, 90, 160))
            c.drawImage(ImageReader(img), 300, 100, width=200, height=100)
        c.showPage()
    c.save()
    return io.BytesIO(buf.getvalue())


LONG = "Wir bauen Software fuer die ambulante Pflege.\nSchnellere Dokumentation, weniger Papier."


def test_text_and_image_slides():
    pdf = make_pdf([(LONG, False), (None, True), (LONG, True)])
    deck = extract_deck(pdf)
    assert deck.page_count == 3
    assert "ambulante Pflege" in deck.slides[0].text
    assert [s.is_image_slide for s in deck.slides] == [False, True, False]
    assert deck.image_slide_numbers == [2]
    assert deck.slides_with_images == [2, 3]
    assert deck.has_text


def test_all_images_has_no_text():
    deck = extract_deck(make_pdf([(None, True), (None, True)]))
    assert not deck.has_text
    assert deck.image_slide_numbers == [1, 2]


def test_too_many_pages():
    with pytest.raises(DeckExtractionError) as e:
        extract_deck(make_pdf([(LONG, False)] * 3), max_pages=2)
    assert e.value.code == "too_many_pages"


def test_corrupted():
    with pytest.raises(DeckExtractionError) as e:
        extract_deck(io.BytesIO(b"%PDF-1.4 not really a pdf"))
    assert e.value.code == "corrupted"


def test_encrypted():
    with pytest.raises(DeckExtractionError) as e:
        extract_deck(make_pdf([(LONG, False)], encrypt="secret"))
    assert e.value.code == "encrypted"


def test_strip_metadata():
    src = make_pdf([(LONG, False)])
    assert PdfReader(src).metadata.get("/Author") == "Anna Beispiel"
    src.seek(0)
    clean = PdfReader(io.BytesIO(strip_metadata(src)))
    meta = {k: v for k, v in (clean.metadata or {}).items() if k in ("/Author", "/Title", "/Creator")}
    assert meta == {}
    assert "ambulante Pflege" in clean.pages[0].extract_text()