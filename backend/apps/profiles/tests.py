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
from apps.documents.models import PitchDeck
from apps.startups.models import StartupProfile
from common.models import Sector, Stage, BusinessModel, Country, Region


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
    
    def test_approved_lists_have_the_agreed_sizes(self):
        self.assertEqual(Sector.objects.count(), 20)
        self.assertEqual(Stage.objects.count(), 5)
        self.assertEqual(BusinessModel.objects.count(), 8)
        
        r = APIClient().get("/api/dictionaries/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.data["sectors"]), 20)
        self.assertEqual(len(r.data["business_models"]), 8)
        self.assertEqual(r.data["stages"][-1]["code"], "series-c-plus")
        self.assertTrue(r.data["countries"])
        self.assertTrue(all("code" in i and "name" in i for k in ("sectors", "stages", "countries") for i in r.data[k]))
    
    def test_choice_codes_are_unique_and_url_safe(self):
        for model in (Sector, Stage, BusinessModel, Region, Country):
            codes = list(model.objects.values_list("code", flat=True))
            self.assertEqual(len(codes), len(set(codes)))
            for code in codes:
                self.assertTrue(code.replace("-", "").isalnum())
    
    def test_draft_autosave_and_missing_fields(self):
        r = self.client.get("/api/profile/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["status"], "DRAFT")
        self.assertFalse(r.data["is_complete"])
        self.assertIn("deck", r.data["missing_fields"])
        self.assertEqual(r.data["sector"], "")  # empty draft is fine
        
        r = self.client.put("/api/profile/", {"sector": "fintech", "team_size": 4}, format="json")
        self.assertEqual(r.status_code, 200)
        r = self.client.get("/api/profile/")
        self.assertEqual(r.data["sector"], "fintech")
        self.assertEqual(r.data["team_size"], 4)
        self.assertNotIn("sector", r.data["missing_fields"])
    
    def test_complete_profile(self):
        self.client.patch("/api/profile/", {
            "company_name": "Acme AI",
            "sector": "ai-data",
            "stage": "seed",
            "business_model": "saas-subscription",
            "country": "de",
            "amount_sought": "500000",
            "team_size": 3,
            "mrr": "12000",
            "growth_percent": "15.5",
            "growth_period": "mom",
        }, format="json")
        self.client.post("/api/profile/deck/", {"file": pdf_upload()}, format="multipart")
        r = self.client.get("/api/profile/")
        self.assertTrue(r.data["is_complete"], r.data["missing_fields"])
        self.assertEqual(r.data["country"], "de")
    
    def test_invalid_choice_is_rejected(self):
        for payload in (
                {"sector": "not-a-sector"},
                {"stage": "series-z"},
                {"business_model": "magic"},
                {"sector": "FinTech"},  # label instead of code
        ):
            r = self.client.patch("/api/profile/", payload, format="json")
            self.assertEqual(r.status_code, 400, payload)
    
    def test_choice_can_be_cleared(self):
        self.client.patch("/api/profile/", {"sector": "biotech"}, format="json")
        r = self.client.patch("/api/profile/", {"sector": ""}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertIn("sector", r.data["missing_fields"])
    
    def test_validation(self):
        bad = [
            {"amount_sought": "0"},
            {"amount_sought": "-5"},
            {"team_size": 0},
            {"mrr": "-1"},
            {"country": "zz"},
            {"growth_percent": "10"},  # growth without period
        ]
        for payload in bad:
            r = self.client.patch("/api/profile/", payload, format="json")
            self.assertEqual(r.status_code, 400, payload)
    
    def test_value_no_longer_in_list_counts_as_missing(self):
        # 1. Створюємо сектор і робимо його неактивним (імітація застарілого значення)
        retired_sector = Sector.objects.create(
            code="retired-sector",
            name_de="Alt",
            name_en="Retired",
            is_active=False,
        )
        
        # 2. Прив'язуємо його до профілю
        profile = StartupProfile.objects.create(user=self.user, sector=retired_sector)
        
        # 3. Перевіряємо, що неактивний сектор потрапляє в missing_fields
        r = self.client.get("/api/profile/")
        self.assertIn("sector", r.data["missing_fields"])
    
    def test_business_model_is_optional(self):
        r = self.client.patch("/api/profile/", {"business_model": "licensing"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data["business_model"], "licensing")
        self.assertNotIn("business_model", r.data["missing_fields"])
        self.assertNotIn("business_model", self.client.get("/api/profile/").data["missing_fields"])
    
    def test_inactive_country_rejected(self):
        c = Country.objects.get(code="gb")
        c.is_active = False
        c.save()
        r = self.client.patch("/api/profile/", {"country": "gb"}, format="json")
        self.assertEqual(r.status_code, 400)
    
    def test_seed_countries_is_idempotent(self):
        call_command("seed_dictionaries", verbosity=0)
        self.assertEqual(Country.objects.filter(code="de").count(), 1)
    
    def test_status_is_read_only(self):
        self.client.patch("/api/profile/", {"status": "LIVE"}, format="json")
        self.assertEqual(self.client.get("/api/profile/").data["status"], "DRAFT")
    
    def test_access_rules(self):
        self.assertIn(APIClient().get("/api/profile/").status_code, (401, 403))
        investor = make_user("i@example.com", role="investor")
        c = APIClient();
        c.force_authenticate(investor)
        self.assertEqual(c.get("/api/profile/").status_code, 403)
        unverified = make_user("u@example.com", verified=False)
        c = APIClient();
        c.force_authenticate(unverified)
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
        
        # Получаем созданный активный дек
        d = PitchDeck.objects.filter(deleted_at__isnull=True).get()
        self.assertTrue(os.path.exists(d.file.path))
        self.assertTrue(d.file.name.startswith("decks/") and "deck.pdf" not in d.file.name)
    
    def test_rejections(self):
        cases = {
            "deck_not_pdf": [
                dict(name="deck.docx"),
                dict(data=b"hello, not a pdf at all", name="deck.pdf"),
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
        self.assertEqual(PitchDeck.objects.count(), 0)
    
    @override_settings(DECK_MAX_BYTES=1000)
    def test_too_large(self):
        r = self.upload(data=make_pdf(pages=30))
        self.assertEqual(r.status_code, 400)
        self.assertIn("deck_too_large", str(r.data))
    
    def test_replace_removes_old_file(self):
        self.upload()
        first = PitchDeck.objects.filter(deleted_at__isnull=True).get().file.path
        
        # Загружаем вторую версию файла
        self.upload(name="v2.pdf")
        
        # Активный дек должен быть ровно один:
        self.assertEqual(PitchDeck.objects.filter(deleted_at__isnull=True).count(), 1)
        d = PitchDeck.objects.filter(deleted_at__isnull=True).get()
        self.assertEqual(d.original_name, "v2.pdf")
        
        # Старый физический файл удалён, новый существует:
        self.assertFalse(os.path.exists(first))
        self.assertTrue(os.path.exists(d.file.path))
    
    def test_delete_removes_file(self):
        self.upload()
        path = PitchDeck.objects.filter(deleted_at__isnull=True).get().file.path
        
        # Удаляем дек
        self.assertEqual(self.client.delete("/api/profile/deck/").status_code, 204)
        
        # Файл удалён из хранилища, а GET возвращает 404
        self.assertFalse(os.path.exists(path))
        self.assertEqual(self.client.get("/api/profile/deck/").status_code, 404)
    
    def test_download_only_for_owner(self):
        self.upload()
        r = self.client.get("/api/profile/deck/download/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r["Content-Type"], "application/pdf")
        self.assertTrue(b"".join(r.streaming_content).startswith(b"%PDF-"))
        
        other = make_user("other@example.com")
        c = APIClient()
        c.force_authenticate(other)
        self.assertEqual(c.get("/api/profile/deck/download/").status_code, 404)
        self.assertEqual(c.get("/api/profile/deck/").status_code, 404)
        self.assertIn(APIClient().get("/api/profile/deck/download/").status_code, (401, 403))
