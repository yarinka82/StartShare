import re
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from rest_framework.test import APIClient, APITestCase
from rest_framework.throttling import ScopedRateThrottle

from .models import Consent, User

PASSWORD = "correct-horse-battery"


def reg_payload(**over):
    data = {
        "email": "Founder@Example.com",
        "password": PASSWORD,
        "role": "startup",
        "accept_agb": True,
        "accept_datenschutz": True,
    }
    data.update(over)
    return data


class RegistrationTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_requires_both_checkboxes(self):
        for field in ("accept_agb", "accept_datenschutz"):
            r = self.client.post("/api/auth/register/", reg_payload(**{field: False}), format="json")
            self.assertEqual(r.status_code, 400)
            self.assertIn(f"{field}_required", str(r.data))
        # missing entirely (direct API call)
        payload = reg_payload()
        del payload["accept_agb"]
        r = self.client.post("/api/auth/register/", payload, format="json")
        self.assertEqual(r.status_code, 400)
        self.assertEqual(User.objects.count(), 0)

    def test_register_stores_versioned_consents_and_sends_mail(self):
        r = self.client.post("/api/auth/register/", reg_payload(), format="json")
        self.assertEqual(r.status_code, 201)
        user = User.objects.get(email="founder@example.com")
        self.assertIsNone(user.email_verified_at)
        docs = {c.document_type: c.document_version for c in Consent.objects.filter(user=user)}
        self.assertEqual(set(docs), {"agb", "datenschutz"})
        self.assertTrue(all(docs.values()))
        self.assertEqual(len(mail.outbox), 1)

    def test_weak_password_rejected(self):
        r = self.client.post("/api/auth/register/", reg_payload(password="short"), format="json")
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/auth/register/", reg_payload(password="password123"), format="json")
        self.assertEqual(r.status_code, 400)

    def test_minimum_length_is_8(self):
        r = self.client.post("/api/auth/register/", reg_payload(password="Zq7mK2p"), format="json")  # 7
        self.assertEqual(r.status_code, 400)
        r = self.client.post("/api/auth/register/", reg_payload(password="Zq7mK2pw"), format="json")  # 8
        self.assertEqual(r.status_code, 201)

    def test_existing_email_gives_same_response_and_no_second_user(self):
        self.client.post("/api/auth/register/", reg_payload(), format="json")
        r = self.client.post("/api/auth/register/", reg_payload(), format="json")
        self.assertEqual(r.status_code, 201)
        self.assertEqual(User.objects.count(), 1)
        self.assertEqual(len(mail.outbox), 1)


class LoginFlowTests(APITestCase):
    def setUp(self):
        cache.clear()

    def _register_and_get_token(self):
        self.client.post("/api/auth/register/", reg_payload(), format="json")
        body = mail.outbox[-1].body
        return re.search(r"token=(\S+)", body).group(1)

    def test_login_blocked_until_email_verified(self):
        token = self._register_and_get_token()
        r = self.client.post("/api/auth/login/", {"email": "founder@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 403)
        self.assertEqual(r.data["detail"], "email_not_verified")

        r = self.client.post("/api/auth/verify-email/", {"token": token}, format="json")
        self.assertEqual(r.status_code, 200)

        r = self.client.post("/api/auth/login/", {"email": "FOUNDER@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(self.client.get("/api/auth/me/").data["role"], "startup")

        self.assertEqual(self.client.post("/api/auth/logout/").status_code, 204)
        self.assertIn(self.client.get("/api/auth/me/").status_code, (401, 403))

    def test_bad_token_and_bad_credentials(self):
        r = self.client.post("/api/auth/verify-email/", {"token": "garbage"}, format="json")
        self.assertEqual(r.status_code, 400)
        for email in ("nobody@example.com", "founder@example.com"):
            self.client.post("/api/auth/register/", reg_payload(), format="json")
            r = self.client.post("/api/auth/login/", {"email": email, "password": "wrong-password-1"}, format="json")
            self.assertEqual(r.status_code, 400)
            self.assertEqual(r.data["detail"], "invalid_credentials")

    def test_login_requires_csrf_token(self):
        User.objects.create_user("a@example.com", PASSWORD, role="startup", email_verified_at="2026-10-01T10:00:00Z")
        strict = APIClient(enforce_csrf_checks=True)
        r = strict.post("/api/auth/login/", {"email": "a@example.com", "password": PASSWORD}, format="json")
        self.assertEqual(r.status_code, 403)
        strict.get("/api/auth/csrf/")
        token = strict.cookies["csrftoken"].value
        r = strict.post(
            "/api/auth/login/", {"email": "a@example.com", "password": PASSWORD},
            format="json", HTTP_X_CSRFTOKEN=token,
        )
        self.assertEqual(r.status_code, 200)

    def test_login_is_rate_limited(self):
        rates = {"login": "3/min", "register": "10/hour", "password_reset": "5/hour", "verify": "20/hour"}
        with patch.object(ScopedRateThrottle, "THROTTLE_RATES", rates):
            cache.clear()
            codes = [
                self.client.post("/api/auth/login/", {"email": "x@example.com", "password": "nope-nope-1"}, format="json").status_code
                for _ in range(5)
            ]
        self.assertEqual(codes[:3], [400, 400, 400])
        self.assertEqual(codes[-1], 429)

    def test_password_reset(self):
        User.objects.create_user("a@example.com", PASSWORD, role="startup", email_verified_at="2026-10-01T10:00:00Z")
        self.client.post("/api/auth/password-reset/", {"email": "a@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), 1)
        m = re.search(r"uid=(\S+?)&token=(\S+)", mail.outbox[0].body)
        r = self.client.post(
            "/api/auth/password-reset/confirm/",
            {"uid": m.group(1), "token": m.group(2), "new_password": "another-long-pass-9"}, format="json",
        )
        self.assertEqual(r.status_code, 200)
        r = self.client.post("/api/auth/login/", {"email": "a@example.com", "password": "another-long-pass-9"}, format="json")
        self.assertEqual(r.status_code, 200)
        # unknown e-mail: same answer, no mail
        r = self.client.post("/api/auth/password-reset/", {"email": "none@example.com"}, format="json")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)


class ResendAndLanguageTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_resend_only_for_unverified_and_same_answer(self):
        self.client.post("/api/auth/register/", reg_payload(), format="json")
        self.assertEqual(len(mail.outbox), 1)
        r = self.client.post("/api/auth/resend-verification/", {"email": "founder@example.com"}, format="json")
        self.assertEqual((r.status_code, len(mail.outbox)), (200, 2))
        r = self.client.post("/api/auth/resend-verification/", {"email": "nobody@example.com"}, format="json")
        self.assertEqual((r.status_code, len(mail.outbox)), (200, 2))
        User.objects.update(email_verified_at="2026-10-01T10:00:00Z")
        self.client.post("/api/auth/resend-verification/", {"email": "founder@example.com"}, format="json")
        self.assertEqual(len(mail.outbox), 2)

    def test_validation_messages_follow_accept_language(self):
        r = self.client.post(
            "/api/auth/register/", reg_payload(password="short"), format="json", HTTP_ACCEPT_LANGUAGE="de"
        )
        self.assertEqual(r.status_code, 400)
        self.assertIn("Passwort", str(r.data))


class RegisteredEventTests(APITestCase):
    def setUp(self):
        cache.clear()

    def test_registered_event_for_both_roles_without_personal_data(self):
        from apps.analytics.models import Event, EventName

        self.client.post("/api/auth/register/", reg_payload(), format="json")
        self.client.post("/api/auth/register/", reg_payload(email="inv@example.com", role="investor"), format="json")
        events = {e.properties["role"]: e for e in Event.objects.filter(name=EventName.REGISTERED)}
        self.assertEqual(set(events), {"startup", "investor"})
        self.assertEqual(events["investor"].user.email, "inv@example.com")
        self.assertNotIn("@", str(events["investor"].properties))

    def test_duplicate_registration_does_not_emit_again(self):
        from apps.analytics.models import Event, EventName

        self.client.post("/api/auth/register/", reg_payload(), format="json")
        self.client.post("/api/auth/register/", reg_payload(), format="json")
        self.assertEqual(Event.objects.filter(name=EventName.REGISTERED).count(), 1)
