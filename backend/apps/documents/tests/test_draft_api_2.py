"""API и фоновые задачи вокруг profiles.Deck. python manage.py test apps.documents.tests.test_draft_api

Подправьте make_user() под вашу модель User, если create_user требует другие поля.
"""
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.analytics.models import Event
from apps.analytics.services import start_teaser_job, processing_status
from apps.documents.models import Teaser, TeaserJob

from apps.documents.tasks import purge_expired_decks
from apps.documents.tests.test_pdf_extract import LONG, make_pdf
from apps.profiles.models import Deck, StartupProfile


def make_user(name):
    user = get_user_model().objects.create_user(username=name, password="x")
    StartupProfile.objects.create(user=user, company_name="Lumora GmbH")
    return user


def make_deck(user, pages=None):
    data = make_pdf(pages or [(LONG, False)]).getvalue()
    return Deck.objects.create(profile=user.startup_profile, file=ContentFile(data, name="deck.pdf"),
                               original_name="01_lumora_de.pdf", size=len(data))


class DraftApiTests(TestCase):
    def setUp(self):
        self.user = make_user("anna")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def upload(self, **kw):
        """Имитирует вашу вьюху загрузки: сохранить Deck, затем start_teaser_job."""
        deck = make_deck(self.user, **kw)
        with self.captureOnCommitCallbacks(execute=True):
            start_teaser_job(deck, self.user)
        return deck

    def make_job(self, state, error="", draft=None, user=None):
        user = user or self.user
        deck = Deck.objects.create(profile=user.startup_profile, file="decks/x.pdf", original_name="x.pdf", size=1)
        return deck, TeaserJob.objects.create(deck=deck, state=state, error=error, draft=draft)

    # --- сквозной сценарий: загрузка -> очередь (eager) -> чернетка ---
    def test_upload_to_draft_end_to_end(self):
        deck = self.upload()
        d = self.client.get(f"/api/decks/{deck.id}/draft/")
        self.assertEqual(d.status_code, 200)
        self.assertEqual(d.data["state"], "DRAFT_READY")
        self.assertTrue(d.data["draft"]["teaser"]["headline"])
        self.assertIsNone(d.data["error_code"])
        self.assertEqual(d["Cache-Control"], "no-store")
        for hidden in ("cost_eur", "attempts", "processing_ms", "error", "started_at"):
            self.assertNotIn(hidden, d.data)
        self.assertEqual(processing_status(Deck.objects.get(pk=deck.pk)), "DRAFT_READY")
        self.assertEqual(set(Event.objects.values_list("name", flat=True)), {"deck_uploaded", "ai_draft_created"})
        self.assertEqual(TeaserJob.objects.get().attempts, 1)

    def test_image_only_deck_fails_with_code(self):
        deck = self.upload(pages=[(None, True)])
        d = self.client.get(f"/api/decks/{deck.id}/draft/").data
        self.assertEqual((d["state"], d["error_code"], d["draft"]), ("FAILED", "no_text", None))

    def test_processing_status_without_job_is_none(self):
        self.assertIsNone(processing_status(make_deck(self.user)))

    # --- чтение ---
    def test_draft_hidden_until_ready(self):
        deck, _ = self.make_job(TeaserJob.State.PROCESSING, draft={"teaser": {"headline": "x"}})
        d = self.client.get(f"/api/decks/{deck.id}/draft/").data
        self.assertEqual((d["state"], d["draft"], d["risk_phrases"]), ("PROCESSING", None, []))

    def test_unknown_error_text_is_not_leaked(self):
        deck, _ = self.make_job(TeaserJob.State.FAILED, error="unexpected: /srv/secret/path boom")
        r = self.client.get(f"/api/decks/{deck.id}/draft/")
        self.assertEqual(r.data["error_code"], "unexpected")
        self.assertNotIn("secret", r.content.decode())

    def test_timeout_code(self):
        deck, _ = self.make_job(TeaserJob.State.FAILED, error="timeout: processing timed out")
        self.assertEqual(self.client.get(f"/api/decks/{deck.id}/draft/").data["error_code"], "timeout")

    def test_no_job_is_404(self):
        deck = make_deck(self.user)
        self.assertEqual(self.client.get(f"/api/decks/{deck.id}/draft/").status_code, 404)

    def test_other_users_deck_is_404(self):
        deck, _ = self.make_job(TeaserJob.State.DRAFT_READY, draft={"teaser": {}}, user=make_user("boris"))
        self.assertEqual(self.client.get(f"/api/decks/{deck.id}/draft/").status_code, 404)

    def test_requires_authentication_and_get_only(self):
        deck, _ = self.make_job(TeaserJob.State.QUEUED)
        self.assertIn(APIClient().get(f"/api/decks/{deck.id}/draft/").status_code, (401, 403))
        self.assertEqual(self.client.post(f"/api/decks/{deck.id}/draft/").status_code, 405)


class PurgeAndLifecycleTests(TestCase):
    def setUp(self):
        self.user = make_user("anna")

    def processed(self):
        deck = make_deck(self.user)
        with self.captureOnCommitCallbacks(execute=True):
            job = start_teaser_job(deck, self.user)
        job.refresh_from_db()
        return deck, job

    def test_purge_removes_file_after_24h_but_keeps_everything_else(self):
        deck, job = self.processed()
        Teaser.objects.create(job=job, content={"headline": "x"})
        storage, name, uploaded = deck.file.storage, deck.file.name, deck.uploaded_at
        self.assertTrue(storage.exists(name))

        TeaserJob.objects.filter(pk=job.pk).update(ready_at=timezone.now() - timedelta(hours=25))
        purge_expired_decks()

        deck.refresh_from_db(); job.refresh_from_db()
        self.assertFalse(storage.exists(name))
        self.assertEqual(deck.file.name, "")
        self.assertIsNotNone(job.original_deleted_at)
        self.assertEqual(deck.uploaded_at, uploaded)                  # update(), а не save(): auto_now не тронут
        self.assertEqual(job.state, "DRAFT_READY")
        self.assertTrue(Teaser.objects.filter(job=job).exists())      # тизер не потерян

    def test_purge_is_idempotent_and_skips_fresh_jobs(self):
        deck, job = self.processed()
        purge_expired_decks()
        deck.refresh_from_db()
        self.assertTrue(deck.file.name)                               # ещё нет 24 часов
        TeaserJob.objects.filter(pk=job.pk).update(ready_at=timezone.now() - timedelta(hours=25))
        purge_expired_decks()
        purge_expired_decks()
        job.refresh_from_db()
        self.assertIsNotNone(job.original_deleted_at)

    def test_failed_job_file_is_purged_too(self):
        deck = make_deck(self.user, pages=[(None, True)])
        with self.captureOnCommitCallbacks(execute=True):
            job = start_teaser_job(deck, self.user)
        job.refresh_from_db()
        self.assertEqual(job.state, "FAILED")
        TeaserJob.objects.filter(pk=job.pk).update(created_at=timezone.now() - timedelta(hours=25))
        purge_expired_decks()
        deck.refresh_from_db()
        self.assertEqual(deck.file.name, "")

    def test_processing_a_purged_deck_fails_with_deck_deleted(self):
        from apps.documents.tasks import process_deck
        deck, job = self.processed()
        TeaserJob.objects.filter(pk=job.pk).update(
            state="QUEUED", original_deleted_at=timezone.now(), draft=None)
        process_deck.apply(args=[job.id])
        job.refresh_from_db()
        self.assertEqual((job.state, job.error.split(":")[0]), ("FAILED", "deck_deleted"))

    def test_deleting_deck_cascades_and_removes_file(self):
        deck, job = self.processed()
        storage, name = deck.file.storage, deck.file.name
        deck.delete()
        self.assertFalse(TeaserJob.objects.filter(pk=job.pk).exists())
        self.assertFalse(storage.exists(name))


# --- ваша вьюха загрузки (profiles.DeckView) вместе с обработкой ---
from django.core.files.uploadedfile import SimpleUploadedFile  # noqa: E402

DECK_URL = "/api/profile/deck/"


class DeckViewIntegrationTests(TestCase):
    def setUp(self):
        self.user = make_user("anna")
        self.client = APIClient()
        self.client.force_authenticate(self.user)

    def post_pdf(self, pages=None, name="01_lumora_de.pdf"):
        data = make_pdf(pages or [(LONG, False)]).getvalue()
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(DECK_URL, {"file": SimpleUploadedFile(name, data, "application/pdf")},
                                    format="multipart")

    def test_upload_returns_id_and_status_and_starts_processing(self):
        r = self.post_pdf()
        self.assertEqual(r.status_code, 201, r.content)
        self.assertEqual(r.data["original_name"], "01_lumora_de.pdf")
        self.assertEqual(r.data["processing_status"], "QUEUED")        # ответ уходит до запуска задачи
        d = self.client.get(f"/api/decks/{r.data['id']}/draft/")
        self.assertEqual(d.data["state"], "DRAFT_READY")               # eager-режим тестов уже обработал
        self.assertEqual(self.client.get(DECK_URL).data["processing_status"], "DRAFT_READY")

    def test_not_a_pdf_is_rejected_without_job(self):
        r = self.client.post(DECK_URL, {"file": SimpleUploadedFile("a.pdf", b"nope", "application/pdf")},
                             format="multipart")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(TeaserJob.objects.count(), 0)

    def test_replacement_resets_job_and_working_copy(self):
        first = self.post_pdf().data
        old_job = TeaserJob.objects.get()
        Teaser.objects.create(job=old_job, content={"headline": "edited"})
        old_name = Deck.objects.get().file.name

        second = self.post_pdf(name="other.pdf").data
        self.assertEqual(second["id"], first["id"])                    # тот же Deck, файл заменён
        self.assertEqual(second["original_name"], "other.pdf")
        job = TeaserJob.objects.get()
        self.assertNotEqual(job.pk, old_job.pk)                        # задача новая
        self.assertEqual(Teaser.objects.count(), 0)                    # старая рабочая копия сброшена
        self.assertFalse(Deck.objects.get().file.storage.exists(old_name))
        self.assertEqual(job.state, "DRAFT_READY")

    def test_replacement_and_delete_blocked_after_approval(self):
        self.post_pdf()
        Teaser.objects.create(job=TeaserJob.objects.get(), content={}, status=Teaser.Status.APPROVED)
        r = self.post_pdf()
        self.assertEqual((r.status_code, r.data["detail"]), (409, "teaser_approved"))
        self.assertEqual(self.client.delete(DECK_URL).status_code, 409)
        self.assertEqual((Deck.objects.count(), Teaser.objects.count()), (1, 1))

    def test_delete_before_approval_cascades(self):
        self.post_pdf()
        name = Deck.objects.get().file.name
        storage = Deck.objects.get().file.storage
        self.assertEqual(self.client.delete(DECK_URL).status_code, 204)
        self.assertEqual((Deck.objects.count(), TeaserJob.objects.count()), (0, 0))
        self.assertFalse(storage.exists(name))
        fresh = APIClient()                                              # как новый запрос: пользователь из БД
        fresh.force_authenticate(get_user_model().objects.get(pk=self.user.pk))
        self.assertEqual(fresh.get(DECK_URL).status_code, 404)

    def test_old_task_result_is_discarded_when_deck_replaced_mid_processing(self):
        from apps.documents.tasks import _finish, process_deck
        deck = make_deck(self.user)
        job = TeaserJob.objects.create(deck=deck, state=TeaserJob.State.PROCESSING)
        with self.captureOnCommitCallbacks(execute=True):
            start_teaser_job(deck, self.user)                          # замена: старая задача удалена
        self.assertFalse(_finish(job, state=TeaserJob.State.DRAFT_READY))   # результат старой задачи отброшен
        process_deck.apply(args=[job.pk])                              # и повторный запуск старой задачи безвреден
        self.assertEqual(TeaserJob.objects.get().state, "DRAFT_READY")