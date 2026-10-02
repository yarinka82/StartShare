import io
import os

from django.core.cache import cache
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import override_settings
from django.utils import timezone
from pypdf import PdfWriter
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User
from apps.profiles.models import BusinessModel, Country, Deck, Sector, Stage


def make_pdf(password=None, pages=1):
    w = PdfWriter()
    for _ in range(pages):
        w.add_blank_page(width=200, height=200)
    if password:
        w.encrypt(password)
    buf = io.BytesIO()
    w.write(buf)
    return buf.getvalue()


def pdf_upload(data=None, name="deck.pdf", ctype="application/pdf"):
    return SimpleUploadedFile(name, data if data is not None else make_pdf(), content_type=ctype)


def make_user(email="s@example.com", role="startup", verified=True):
    return User.objects.create_user(
        email, "correct-horse-battery", role=role,
        email_verified_at=timezone.now() if verified else None,
    )


class ProfileTests(APITestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_dictionaries", verbosity=0)
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def test_dictionaries_public(self):
        r = APIClient().get("/api/dictionaries/")
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["sectors"] and r.data["stages"] and r.data["countries"])

    def test_approved_dictionary_sizes(self):
        self.assertEqual(Sector.objects.filter(is_active=True).count(), 20)
        self.assertEqual(Stage.objects.filter(is_active=True).count(), 5)
        self.assertEqual(BusinessModel.objects.filter(is_active=True).count(), 8)
        r = APIClient().get("/api/dictionaries/")
        self.assertEqual(len(r.data["business_models"]), 8)
        self.assertEqual(r.data["stages"][-1]["code"], "series-c-plus")  # sort order kept

    def test_seed_deactivates_obsolete_values_and_is_idempotent(self):
        old = Sector.objects.create(code="old-sector", name="Old")
        call_command("seed_dictionaries", verbosity=0)
        call_command("seed_dictionaries", verbosity=0)
        old.refresh_from_db()
        self.assertFalse(old.is_active)
        self.assertEqual(Sector.objects.filter(is_active=True).count(), 20)
        self.assertEqual(Sector.objects.filter(code="fintech").count(), 1)

    def test_value_removed_from_list_counts_as_missing(self):
        sector = Sector.objects.get(code="fintech")
        self.client.patch("/api/profile/", {"sector": sector.id}, format="json")
        self.assertNotIn("sector", self.client.get("/api/profile/").data["missing_fields"])
        sector.is_active = False
        sector.save()
        self.assertIn("sector", self.client.get("/api/profile/").data["missing_fields"])

    def test_business_model_is_optional_but_must_be_active(self):
        bm = BusinessModel.objects.get(code="licensing")
        r = self.client.patch("/api/profile/", {"business_model": bm.id}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/api/profile/").data["business_model"], bm.id)
        self.assertNotIn("business_model", self.client.get("/api/profile/").data["missing_fields"])
        bm.is_active = False
        bm.save()
        r = self.client.patch("/api/profile/", {"business_model": bm.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_draft_autosave_and_missing_fields(self):
        r = self.client.get("/api/profile/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "DRAFT")
        self.assertFalse(r.data["is_complete"])
        self.assertIn("deck", r.data["missing_fields"])

        sector = Sector.objects.first().id
        r = self.client.put("/api/profile/", {"sector": sector, "team_size": 4}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/profile/")
        self.assertEqual(r.data["sector"], sector)
        self.assertEqual(r.data["team_size"], 4)
        self.assertNotIn("sector", r.data["missing_fields"])

    def test_complete_profile(self):
        self.client.patch("/api/profile/", {
            "sector": Sector.objects.first().id, "stage": Stage.objects.first().id,
            "country": Country.objects.first().id, "amount_sought": "500000", "team_size": 3,
            "mrr": "12000", "growth_percent": "15.5", "growth_period": "mom",
        }, format="json")
        self.client.post("/api/profile/deck/", {"file": pdf_upload()}, format="multipart")
        r = self.client.get("/api/profile/")
        self.assertTrue(r.data["is_complete"], r.data["missing_fields"])

    def test_validation(self):
        bad = [
            {"amount_sought": "0"}, {"amount_sought": "-5"}, {"team_size": 0},
            {"mrr": "-1"}, {"sector": 99999}, {"growth_percent": "10"},  # growth without period
        ]
        for payload in bad:
            r = self.client.patch("/api/profile/", payload, format="json")
            self.assertEqual(r.status_code, 400, payload)

    def test_inactive_dictionary_value_rejected(self):
        s = Sector.objects.first()
        s.is_active = False
        s.save()
        r = self.client.patch("/api/profile/", {"sector": s.id}, format="json")
        self.assertEqual(r.status_code, 400)

    def test_status_is_read_only(self):
        self.client.patch("/api/profile/", {"status": "LIVE"}, format="json")
        self.assertEqual(self.client.get("/api/profile/").data["status"], "DRAFT")

    def test_access_rules(self):
        self.assertIn(APIClient().get("/api/profile/").status_code, (401, 403))
        investor = make_user("i@example.com", role="investor")
        c = APIClient(); c.force_authenticate(investor)
        self.assertEqual(c.get("/api/profile/").status_code, 403)
        unverified = make_user("u@example.com", verified=False)
        c = APIClient(); c.force_authenticate(unverified)
        self.assertEqual(c.get("/api/profile/").status_code, 403)


class DeckTests(APITestCase):
    def setUp(self):
        cache.clear()
        self.user = make_user()
        self.client.force_authenticate(self.user)

    def upload(self, **kw):
        return self.client.post("/api/profile/deck/", {"file": pdf_upload(**kw)}, format="multipart")

    def test_valid_pdf(self):
        r = self.upload()
        self.assertEqual(r.status_code, 201, r.data)
        self.assertEqual(r.data["original_name"], "deck.pdf")
        d = Deck.objects.get()
        self.assertTrue(os.path.exists(d.file.path))
        self.assertTrue(d.file.name.startswith("decks/") and "deck.pdf" not in d.file.name)  # random name

    def test_rejections(self):
        cases = {
            "deck_not_pdf": [
                dict(name="deck.docx"),
                dict(data=b"hello, not a pdf at all", name="deck.pdf"),   # renamed text file
                dict(name="deck.pdf", ctype="image/png"),
            ],
            "deck_empty": [dict(data=b"")],
            "deck_password_protected": [dict(data=make_pdf(password="secret"))],
            "deck_corrupted": [dict(data=b"%PDF-1.7 broken broken broken")],
        }
        for code, variants in cases.items():
            for kw in variants:
                r = self.upload(**kw)
                self.assertEqual(r.status_code, 400, (code, kw))
                self.assertIn(code, str(r.data), (code, kw))
        self.assertEqual(Deck.objects.count(), 0)

    @override_settings(DECK_MAX_BYTES=1000)
    def test_too_large(self):
        r = self.upload(data=make_pdf(pages=30))
        self.assertEqual(r.status_code, 400)
        self.assertIn("deck_too_large", str(r.data))

    def test_replace_removes_old_file(self):
        self.upload()
        first = Deck.objects.get().file.path
        self.upload(name="v2.pdf")
        self.assertEqual(Deck.objects.count(), 1)
        d = Deck.objects.get()
        self.assertEqual(d.original_name, "v2.pdf")
        self.assertFalse(os.path.exists(first))
        self.assertTrue(os.path.exists(d.file.path))

    def test_delete_removes_file(self):
        self.upload()
        path = Deck.objects.get().file.path
        self.assertEqual(self.client.delete("/api/profile/deck/").status_code, 204)
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.client.get("/api/profile/deck/").status_code, 404)

    def test_download_only_for_owner(self):
        self.upload()
        r = self.client.get("/api/profile/deck/download/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(r.streaming_content).startswith(b"%PDF-"))

        other = make_user("other@example.com")
        c = APIClient(); c.force_authenticate(other)
        self.assertEqual(c.get("/api/profile/deck/download/").status_code, 404)  # sees only own deck
        self.assertEqual(c.get("/api/profile/deck/").status_code, 404)
        self.assertIn(APIClient().get("/api/profile/deck/download/").status_code, (401, 403))
