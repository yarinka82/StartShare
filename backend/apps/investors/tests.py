from unittest.mock import patch

from django.core.cache import cache
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APIClient, APITestCase

from apps.accounts.models import User, UserConsent
from apps.analytics.models import Event, EventName
# Импортируем новые модели
from apps.investors.models import InvestorProfile, Mandate
from common.models import BusinessModel, Country, InvestorType, Region, Sector, Stage

# Актуальная структура мандата с новыми именами полей
MANDATE = {
    "sector_codes": ["fintech", "ai-data"],
    "stage_codes": ["seed", "series-a"],
    "country_codes": ["de"],
    "region_codes": ["dach"],
    "business_model_codes": ["saas-subscription"],
    "check_min_eur": "100000",
    "check_max_eur": "500000",
}


def make_user(email="inv@example.com", role="investor", verified=True):
    return User.objects.create_user(
        email,
        "correct-horse-battery",
        role=role,
        email_verified_at=timezone.now() if verified else None,
    )


class InvestorBase(APITestCase):
    def setUp(self):
        cache.clear()
        # Засеиваем юридические тексты и справочники
        call_command("seed_legal_documents", verbosity=0)
        call_command("seed_dictionaries", verbosity=0)

        self.user = make_user()

        # Создаем профиль инвестора для тестового пользователя
        investor_type = InvestorType.objects.first()
        country = Country.objects.first()

        self.profile = InvestorProfile.objects.create(
            user=self.user,
            organization_name="Test Fund",
            investor_type=investor_type,
            country=country,
            contact_person_name="John Doe",
            contact_email="inv@example.com",
        )

        self.client.force_authenticate(self.user)

    def confirm(self):
        return self.client.post("/api/investor/confirm-status/", {"accept": True}, format="json")


class AccessTests(InvestorBase):
    def test_only_verified_investors(self):
        for user in (make_user("s@example.com", role="startup"), make_user("u@example.com", verified=False)):
            c = APIClient()
            c.force_authenticate(user)
            for method, url in (
                ("get", "/api/investor/"),
                ("post", "/api/investor/confirm-status/"),
                ("put", "/api/investor/mandate/"),
            ):
                self.assertEqual(getattr(c, method)(url, {}, format="json").status_code, 403, (user.email, url))
        self.assertIn(APIClient().get("/api/investor/").status_code, (401, 403))

    def test_startup_endpoints_are_closed_for_investors(self):
        self.assertEqual(self.client.get("/api/profile/").status_code, 403)

    def test_mandate_is_blocked_until_text_c_is_confirmed(self):
        r = self.client.put("/api/investor/mandate/", MANDATE, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["detail"], "status_not_confirmed")
        self.assertEqual(Event.objects.filter(name=EventName.MANDATE_SAVED).count(), 0)


class ConfirmStatusTests(InvestorBase):
    def test_initial_state(self):
        r = self.client.get("/api/investor/")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.data, {"status_confirmed": False, "status_confirmed_at": None, "mandate": None})

    def test_requires_the_checkbox(self):
        for body in ({"accept": False}, {}):
            r = self.client.post("/api/investor/confirm-status/", body, format="json")
            self.assertEqual(r.status_code, 400)
        self.assertIn(
            "status_confirmation_required",
            str(self.client.post("/api/investor/confirm-status/", {"accept": False}, format="json").data),
        )
        self.assertEqual(UserConsent.objects.count(), 0)
        self.assertEqual(Event.objects.count(), 0)

    def test_confirm_stores_versioned_consent_and_event_once(self):
        r = self.confirm()
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.data["status_confirmed"])
        self.assertIsNotNone(r.data["status_confirmed_at"])
        c = UserConsent.objects.get(user=self.user)
        self.assertEqual((c.document_type, bool(c.document_version)), ("investor-status", True))
        self.assertEqual(Event.objects.filter(name=EventName.STATUS_CONFIRMED, user=self.user).count(), 1)

        self.confirm()  # идемпотентность: нет второго согласия и события
        self.assertEqual(UserConsent.objects.count(), 1)
        self.assertEqual(Event.objects.filter(name=EventName.STATUS_CONFIRMED).count(), 1)


class MandateTests(InvestorBase):
    def setUp(self):
        super().setUp()
        self.confirm()

    def put(self, **over):
        return self.client.put("/api/investor/mandate/", {**MANDATE, **over}, format="json")

    def test_first_save_emits_mandate_saved_and_state_returns_it(self):
        r = self.put()
        self.assertIn(r.status_code, (200, 201), r.data)
        self.assertEqual(r.data["sector_codes"], ["fintech", "ai-data"])
        self.assertEqual(r.data["version"], 1)
        self.assertTrue(r.data["is_current"])

        events = Event.objects.filter(name=EventName.MANDATE_SAVED)
        self.assertEqual(events.count(), 1)
        e = events.get()
        self.assertEqual(e.user, self.user)
        self.assertEqual(e.properties["check_min_eur"], "100000.00")
        self.assertEqual(e.properties["region_codes"], ["dach"])

        state = self.client.get("/api/investor/").data
        self.assertEqual(state["mandate"]["stage_codes"], ["seed", "series-a"])

    def test_identical_save_does_not_emit_a_change(self):
        self.put()
        self.put()
        self.assertEqual(Event.objects.filter(name=EventName.MANDATE_SAVED).count(), 1)
        self.assertEqual(Event.objects.filter(name=EventName.MANDATE_CHANGED).count(), 0)
        # Версия не должна увеличиваться при отсутствии изменений
        self.assertEqual(Mandate.objects.filter(investor_profile=self.profile).count(), 1)

    def test_real_change_emits_mandate_changed_with_source_and_fields(self):
        self.put()
        r = self.put(region_codes=["dach", "eu"], check_max_eur="900000")
        self.assertIn(r.status_code, (200, 201))
        self.assertEqual(r.data["version"], 2)

        e = Event.objects.get(name=EventName.MANDATE_CHANGED)
        self.assertEqual(e.properties["source"], "self")
        self.assertEqual(sorted(e.properties["changed"]), ["check_max_eur", "region_codes"])
        self.assertEqual(e.properties["check_max_eur"], "900000.00")
        self.assertEqual(Event.objects.filter(name=EventName.MANDATE_SAVED).count(), 1)

        # Должно быть 2 мандата в базе, но только 1 активный
        self.assertEqual(Mandate.objects.filter(investor_profile=self.profile).count(), 2)
        self.assertEqual(Mandate.objects.filter(investor_profile=self.profile, is_current=True).count(), 1)

    def test_selection_order_and_duplicates_do_not_count_as_change(self):
        self.put(sector_codes=["ai-data", "fintech", "fintech"])
        self.assertEqual(self.client.get("/api/investor/").data["mandate"]["sector_codes"], ["fintech", "ai-data"])
        self.put(sector_codes=["fintech", "ai-data"])
        self.assertEqual(Event.objects.filter(name=EventName.MANDATE_CHANGED).count(), 0)

    def test_business_model_is_optional(self):
        body = {k: v for k, v in MANDATE.items() if k != "business_model_codes"}
        r = self.client.put("/api/investor/mandate/", body, format="json")
        self.assertIn(r.status_code, (200, 201))
        self.assertEqual(r.data["business_model_codes"], [])
        self.assertIn(self.put(business_model_codes=[]).status_code, (200, 201))

    def test_validation(self):
        bad = [
            ({"sector_codes": []}, "mandate_list_required"),
            ({"stage_codes": []}, "mandate_list_required"),
            ({"country_codes": []}, "mandate_list_required"),
            ({"sector_codes": ["FinTech"]}, "not a valid choice"),
            ({"stage_codes": ["series-z"]}, "not a valid choice"),
            ({"country_codes": ["XX"]}, "not a valid choice"),
            ({"business_model_codes": ["magic"]}, "not a valid choice"),
            ({"check_min_eur": "0"}, "check_min_eur"),
            ({"check_min_eur": "600000", "check_max_eur": "500000"}, "ticket_max_below_min"),
            ({"check_max_eur": "abc"}, "check_max_eur"),
        ]
        for over, expect in bad:
            r = self.put(**over)
            self.assertEqual(r.status_code, 400, over)
            self.assertIn(expect, str(r.data), over)
        self.assertEqual(Event.objects.filter(name=EventName.MANDATE_SAVED).count(), 0)
        self.assertFalse(Mandate.objects.filter(investor_profile=self.profile).exists())

    def test_equal_min_and_max_is_allowed(self):
        self.assertIn(self.put(check_min_eur="250000", check_max_eur="250000").status_code, (200, 201))

    def test_event_log_failure_does_not_break_saving(self):
        with patch("apps.analytics.events.Event.objects.create", side_effect=RuntimeError("db down")), \
                self.assertLogs("apps.analytics.events", level="ERROR"):
            r = self.put()
        self.assertIn(r.status_code, (200, 201))
        self.assertEqual(self.client.get("/api/investor/").data["mandate"]["check_min_eur"], "100000.00")

    def test_events_contain_no_personal_data(self):
        self.put()
        for e in Event.objects.all():
            self.assertNotIn("inv@example.com", str(e.properties))


class SharedListsTests(APITestCase):
    def setUp(self):
        cache.clear()
        call_command("seed_dictionaries", verbosity=0)

    def test_mandate_uses_the_same_lists_as_the_startup_profile(self):
        r = APIClient().get("/api/dictionaries/")
        self.assertEqual(
            [i["code"] for i in r.data["sectors"]],
            list(Sector.objects.values_list("code", flat=True)),
        )
        self.assertEqual(
            [i["code"] for i in r.data["stages"]],
            list(Stage.objects.values_list("code", flat=True)),
        )
        self.assertEqual(
            [i["code"] for i in r.data["business_models"]],
            list(BusinessModel.objects.values_list("code", flat=True)),
        )