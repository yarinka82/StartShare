"""API-тесты (Django TestCase). Запуск: python manage.py test apps.documents.tests.test_draft_api

Подправьте make_user() под вашу модель User, если create_user требует другие поля.
"""
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient
from apps.profiles.models import StartupProfile
from apps.analytics.models import Event
from apps.documents.models import PitchDeck, TeaserJob
from apps.documents.tests.test_pdf_extract import LONG, make_pdf
from apps.startups.models import StartupProfile

URL = "/api/decks/"


def make_user(name: str):
    user = get_user_model().objects.create_user(
        email=f"{name}@example.com",
        password="x",
        role="startup",
    )
    # Передаємо team_size=1, щоб база даних прийняла запис
    StartupProfile.objects.create(user=user, team_size=1)
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

    def make_job(self, state, error="", draft=None, user=None):
        user = user or self.user
        profile = StartupProfile.objects.get(user=user)
        deck = PitchDeck.objects.create(startup=profile, file="decks/x.pdf")
        return deck, TeaserJob.objects.create(deck=deck, state=state, error=error, draft=draft)

    # --- сквозной сценарий: загрузка -> очередь (eager) -> чернетка ---
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
        self.assertEqual(names, {"deck_uploaded", "ai_draft_created"})
        self.assertEqual(TeaserJob.objects.get().attempts, 1)

    def test_image_only_deck_fails_with_code(self):
        r = self.upload(pages=[(None, True)])
        self.assertEqual(r.status_code, 201)
        d = self.client.get(f"{URL}{r.data['id']}/draft/").data
        self.assertEqual((d["state"], d["error_code"], d["draft"]), ("FAILED", "no_text", None))

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
            email="investor@example.com",
            password="x",
        )
        self.client.force_login(investor)
        c = APIClient()
        c.force_authenticate(investor)
        r = c.post(URL, {"file": pdf_upload()}, format="multipart")
        self.assertEqual(r.status_code, 403)

    # --- чтение ---
    def test_draft_hidden_until_ready(self):
        deck, _ = self.make_job(TeaserJob.State.PROCESSING, draft={"teaser": {"headline": "x"}})
        d = self.client.get(f"{URL}{deck.id}/draft/").data
        self.assertEqual(d["state"], "PROCESSING")
        self.assertIsNone(d["draft"])
        self.assertEqual(d["risk_phrases"], [])

    def test_unknown_error_text_is_not_leaked(self):
        deck, _ = self.make_job(TeaserJob.State.FAILED, error="unexpected: /srv/secret/path boom")
        r = self.client.get(f"{URL}{deck.id}/draft/")
        self.assertEqual(r.data["error_code"], "unexpected")
        self.assertNotIn("secret", r.content.decode())

    def test_timeout_code(self):
        deck, _ = self.make_job(TeaserJob.State.FAILED, error="timeout: processing timed out")
        self.assertEqual(self.client.get(f"{URL}{deck.id}/draft/").data["error_code"], "timeout")

    def test_no_job_is_404(self):
        profile = StartupProfile.objects.get(user=self.user)
        deck = PitchDeck.objects.create(startup=profile, file="decks/x.pdf")
        self.assertEqual(self.client.get(f"{URL}{deck.id}/draft/").status_code, 404)

    def test_other_users_deck_is_404(self):
        other = make_user("boris")
        deck, _ = self.make_job(TeaserJob.State.DRAFT_READY, draft={"teaser": {}}, user=other)
        self.assertEqual(self.client.get(f"{URL}{deck.id}/draft/").status_code, 404)
        self.assertEqual(self.client.get(f"{URL}{deck.id}/").status_code, 404)

    def test_requires_authentication(self):
        deck, _ = self.make_job(TeaserJob.State.QUEUED)
        r = APIClient().get(f"{URL}{deck.id}/draft/")
        self.assertIn(r.status_code, (401, 403))

    def test_draft_is_get_only(self):
        deck, _ = self.make_job(TeaserJob.State.QUEUED)
        self.assertEqual(self.client.post(f"{URL}{deck.id}/draft/").status_code, 405)