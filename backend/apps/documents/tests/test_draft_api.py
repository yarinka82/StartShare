"""API-тесты (Django TestCase). Запуск: python manage.py test apps.documents.tests.test_draft_api"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import Event
from apps.documents.models import PitchDeck, Teaser, TeaserField
from apps.documents.tests.test_pdf_extract import LONG, make_pdf
from apps.startups.models import StartupProfile

URL = "/api/decks/"


def make_user(name: str):
    user = get_user_model().objects.create_user(
        email=f"{name}@example.com",
        password="x",
        role="startup",
    )
    StartupProfile.objects.get_or_create(user=user, defaults={"team_size": 1})
    return user


def pdf_upload(pages=None):
    pages = pages or [(LONG, False)]
    return SimpleUploadedFile("deck.pdf", make_pdf(pages).getvalue(), content_type="application/pdf")


class DraftApiTests(TestCase):
    def setUp(self):
        self.user = make_user("anna")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def upload(self, **kw):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(URL, {"file": pdf_upload(**kw)}, format="multipart")

    def make_deck(self, state, failure_reason=None, draft=None, user=None):
        """Створює PitchDeck і Teaser відповідно до нової моделі та констрейнтів."""
        user = user or self.user
        profile = getattr(user, "startup_profile", getattr(user, "startupprofile", None))
        now = timezone.now()

        # Захист констрейнту: якщо FAILED, failure_reason обов'язковий
        if state == PitchDeck.ProcessingState.FAILED and not failure_reason:
            failure_reason = PitchDeck.FailureReason.OTHER

        # Захист констрейнту: якщо завершено, потрібен processing_finished_at
        finished_at = now if state in (PitchDeck.ProcessingState.DRAFT_READY, PitchDeck.ProcessingState.FAILED) else None

        deck = PitchDeck.objects.create(
            startup_profile=profile,
            file="decks/x.pdf",
            original_name="x.pdf",
            mime_type="application/pdf",
            file_size_bytes=1024,
            processing_state=state,
            failure_reason=failure_reason,
            processing_started_at=now,
            processing_finished_at=finished_at,
        )

        # Якщо створюємо чернетку DRAFT_READY — створюємо зв'язаний Teaser
        teaser = None
        if draft or state == PitchDeck.ProcessingState.DRAFT_READY:
            teaser, _ = Teaser.objects.get_or_create(
                startup_profile=profile,
                pitch_deck=deck,
                defaults={"version": 1, "status": Teaser.Status.DRAFT, "is_current": True},
            )
            headline_text = draft.get("teaser", {}).get("headline", "Default headline") if draft else "Default headline"
            TeaserField.objects.get_or_create(
                teaser=teaser,
                field_name="headline",
                defaults={"final_text": headline_text, "ai_text": headline_text},
            )

        return deck, teaser

    # --- наскрізний сценарій: завантаження -> чернетка ---
    def test_upload_to_draft_end_to_end(self):
        r = self.upload()
        self.assertEqual(r.status_code, 201, r.content)
        deck_id = r.data["id"]

        d = self.client.get(f"{URL}{deck_id}/draft/")
        self.assertEqual(d.status_code, 200)
        self.assertEqual(d.data["state"], "DRAFT_READY")
        self.assertTrue(d.data["draft"]["teaser"]["headline"])
        self.assertIsNone(d.data["error_code"])
        self.assertEqual(d["Cache-Control"], "no-store")
        for hidden in ("cost_eur", "attempts", "processing_ms", "error", "started_at"):
            self.assertNotIn(hidden, d.data)

        self.assertEqual(self.client.get(f"{URL}{deck_id}/").data["processing_status"], "DRAFT_READY")
        names = set(Event.objects.values_list("name", flat=True))
        self.assertIn("deck_uploaded", names)
        # У новій моделі attempts зберігаються в attempt_count
        self.assertEqual(PitchDeck.objects.get(id=deck_id).attempt_count, 1)

    def test_image_only_deck_fails_with_code(self):
        r = self.upload(pages=[(None, True)])
        self.assertEqual(r.status_code, 201)
        d = self.client.get(f"{URL}{r.data['id']}/draft/").data
        self.assertEqual(d["state"], "FAILED")
        self.assertIn(d["error_code"], ("pdf_unreadable", "no_text", "other"))

    def test_not_a_pdf_rejected(self):
        bad = SimpleUploadedFile("deck.pdf", b"not a pdf", content_type="application/pdf")
        r = self.client.post(URL, {"file": bad}, format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(PitchDeck.objects.count(), 0)

    def test_second_upload_is_400_not_500(self):
        self.assertEqual(self.upload().status_code, 201)
        self.assertEqual(self.upload().status_code, 400)

    def test_user_without_startup_profile_gets_403(self):
        investor = get_user_model().objects.create_user(
            email="inv@example.com",
            password="x",
            role="investor",
        )
        c = APIClient()
        c.force_authenticate(investor)
        r = c.post(URL, {"file": pdf_upload()}, format="multipart")
        self.assertEqual(r.status_code, 403)

    # --- читання статусу та безпека ---
    def test_draft_hidden_until_ready(self):
        deck, _ = self.make_deck(PitchDeck.ProcessingState.PROCESSING, draft={"teaser": {"headline": "x"}})
        d = self.client.get(f"{URL}{deck.id}/draft/").data
        self.assertEqual(d["state"], "PROCESSING")
        self.assertIsNone(d["draft"])
        self.assertEqual(d.get("risk_phrases", []), [])

    def test_unknown_error_text_is_not_leaked(self):
        deck, _ = self.make_deck(PitchDeck.ProcessingState.FAILED, failure_reason=PitchDeck.FailureReason.OTHER)
        r = self.client.get(f"{URL}{deck.id}/draft/")
        self.assertEqual(r.data["error_code"], "other")
        self.assertNotIn("secret", r.content.decode())

    def test_timeout_code(self):
        deck, _ = self.make_deck(
            PitchDeck.ProcessingState.FAILED,
            failure_reason=PitchDeck.FailureReason.PROVIDER_UNAVAILABLE,
        )
        self.assertEqual(self.client.get(f"{URL}{deck.id}/draft/").data["error_code"], "provider_unavailable")

    def test_no_job_is_404(self):
        # Перевірка неіснуючого деку
        self.assertEqual(self.client.get(f"{URL}99999/draft/").status_code, 404)

    def test_other_users_deck_is_404(self):
        other = make_user("boris")
        deck, _ = self.make_deck(PitchDeck.ProcessingState.DRAFT_READY, draft={"teaser": {}}, user=other)
        self.assertEqual(self.client.get(f"{URL}{deck.id}/draft/").status_code, 404)
        self.assertEqual(self.client.get(f"{URL}{deck.id}/").status_code, 404)

    def test_requires_authentication(self):
        deck, _ = self.make_deck(PitchDeck.ProcessingState.QUEUED)
        r = APIClient().get(f"{URL}{deck.id}/draft/")
        self.assertIn(r.status_code, (401, 403))

    def test_draft_is_get_only(self):
        deck, _ = self.make_deck(PitchDeck.ProcessingState.QUEUED)
        self.assertEqual(self.client.post(f"{URL}{deck.id}/draft/").status_code, 405)