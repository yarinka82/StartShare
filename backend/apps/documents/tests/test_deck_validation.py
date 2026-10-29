from unittest import mock

from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import SimpleTestCase, override_settings

from common import validators

PDF = b"%PDF-1.7\n" + b"0" * 100


def upload(name="deck.pdf", content=PDF):
    return SimpleUploadedFile(name, content)


def code_of(file):
    with mock.patch.object(validators, "get_max_deck_size_mb", return_value=1):
        try:
            validators.validate_deck_file(file)
        except ValidationError as exc:
            return exc.code
    return None


class DeckValidationTests(SimpleTestCase):
    def test_ok(self):
        self.assertIsNone(code_of(upload()))

    def test_empty(self):
        self.assertEqual(code_of(upload(content=b"")), "deck_empty")

    def test_wrong_extension(self):
        self.assertEqual(code_of(upload("deck.docx")), "deck_not_pdf")
        self.assertEqual(code_of(upload("deck")), "deck_not_pdf")

    def test_renamed_file_is_not_a_pdf(self):
        self.assertEqual(code_of(upload("deck.pdf", b"just text, not a pdf")), "deck_not_pdf")

    def test_pdf_with_leading_junk_is_accepted(self):
        self.assertIsNone(code_of(upload(content=b"\n\n  " + PDF)))

    def test_too_large(self):
        big = b"%PDF-" + b"0" * (1024 * 1024 + 10)
        self.assertEqual(code_of(upload(content=big)), "deck_too_large")

    def test_file_position_is_restored(self):
        f = upload()
        code_of(f)
        self.assertEqual(f.tell(), 0)

    @override_settings(DECK_MAX_MB_DEFAULT=7)
    def test_fallback_when_config_is_zero(self):
        cfg = mock.Mock(max_deck_size_mb=0)
        with mock.patch("apps.accounts.models.PlatformConfig.get_solo", return_value=cfg):
            self.assertEqual(validators.get_max_deck_size_mb(), 7)

    def test_fallback_without_setting_does_not_crash(self):
        cfg = mock.Mock(max_deck_size_mb=None)
        with mock.patch("apps.accounts.models.PlatformConfig.get_solo", return_value=cfg):
            self.assertEqual(validators.get_max_deck_size_mb(), 20)