import re
from unittest.mock import patch

from django.core import mail
from django.core.cache import cache
from django.core.management import call_command
from rest_framework.test import APIClient, APITestCase
from rest_framework.throttling import ScopedRateThrottle

from django.test import SimpleTestCase, TestCase, override_settings

from apps.documents.teaser.llm import AzureOpenAIClient, LLMError, get_client

from .compliance import ProviderBlocked, VendorComplianceError, assert_provider_allowed, vendor_allowed
from .email_backend import BrevoEmailBackend
from .models import Consent, User, VendorCompliance

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


class VendorComplianceTests(TestCase):
    @override_settings(
        ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"],
        EXTERNAL_PROVIDER_CONFIGS={
            "azure_openai": {
                "enabled": True,
                "dpa_signed": True,
                "dpa_valid_until": "2999-12-31",
                "no_model_training": True,
                "allowed_data_types": ["ai_prompt"],
            }
        },
    )
    def test_vendor_allowed_when_contract_is_valid(self):
        self.assertTrue(vendor_allowed("azure_openai", "ai_prompt", vendor_type="ai"))

    @override_settings(
        ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"],
        EXTERNAL_PROVIDER_CONFIGS={
            "azure_openai": {
                "enabled": True,
                "dpa_signed": False,
                "dpa_valid_until": "2999-12-31",
                "no_model_training": True,
                "allowed_data_types": ["ai_prompt"],
            }
        },
    )
    def test_vendor_blocked_without_dpa(self):
        self.assertFalse(vendor_allowed("azure_openai", "ai_prompt", vendor_type="ai"))

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_assert_provider_allowed_requires_db_registration(self):
        with self.assertRaises(ProviderBlocked):
            assert_provider_allowed("missing_vendor")

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_assert_provider_allowed_blocks_missing_dpa(self):
        VendorCompliance.objects.create(
            provider_name="azure_openai",
            name="azure_openai",
            vendor_type="ai",
            provider_type="ai",
            region="sweden-central",
            dpa_signed=False,
            no_model_training=True,
            allowed_data_types=["ai_prompt"],
        )
        with self.assertRaises(ProviderBlocked):
            assert_provider_allowed("azure_openai")

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_assert_provider_allowed_blocks_expired_dpa(self):
        VendorCompliance.objects.create(
            provider_name="azure_openai",
            name="azure_openai",
            vendor_type="ai",
            provider_type="ai",
            region="sweden-central",
            dpa_signed=True,
            dpa_valid_until="2000-01-01",
            no_model_training=True,
            allowed_data_types=["ai_prompt"],
        )
        with self.assertRaises(ProviderBlocked):
            assert_provider_allowed("azure_openai")

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_assert_provider_allowed_blocks_foreign_region(self):
        VendorCompliance.objects.create(
            provider_name="foreign_ai",
            name="foreign_ai",
            vendor_type="ai",
            provider_type="ai",
            region="us-east",
            dpa_signed=True,
            dpa_valid_until="2999-12-31",
            no_model_training=True,
            allowed_data_types=["ai_prompt"],
        )
        with self.assertRaises(ProviderBlocked):
            assert_provider_allowed("foreign_ai")

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_assert_provider_allowed_blocks_llm_without_no_model_training(self):
        VendorCompliance.objects.create(
            provider_name="bad_llm",
            name="bad_llm",
            vendor_type="ai",
            provider_type="ai",
            region="sweden-central",
            dpa_signed=True,
            dpa_valid_until="2999-12-31",
            no_model_training=False,
            allowed_data_types=["ai_prompt"],
        )
        with self.assertRaises(ProviderBlocked):
            assert_provider_allowed("bad_llm")

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_assert_provider_allowed_allows_valid_provider(self):
        VendorCompliance.objects.create(
            provider_name="azure_openai",
            name="azure_openai",
            vendor_type="ai",
            provider_type="ai",
            region="sweden-central",
            dpa_signed=True,
            dpa_valid_until="2999-12-31",
            no_model_training=True,
            allowed_data_types=["ai_prompt"],
        )
        assert_provider_allowed("azure_openai")

    @override_settings(ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_ai_notice_enabled_uses_db_source_of_truth(self):
        from .compliance import is_ai_notice_enabled

        VendorCompliance.objects.create(
            provider_name="azure_openai",
            name="azure_openai",
            vendor_type="ai",
            provider_type="ai",
            region="sweden-central",
            dpa_signed=True,
            dpa_valid_until="2999-12-31",
            no_model_training=True,
            allowed_data_types=["ai_prompt"],
        )
        self.assertTrue(is_ai_notice_enabled())

        VendorCompliance.objects.filter(provider_name="azure_openai").update(dpa_signed=False)
        self.assertFalse(is_ai_notice_enabled())

    @override_settings(LLM_PROVIDER="fake", DEBUG=False, ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"])
    def test_fake_provider_is_forbidden_in_production(self):
        with self.assertRaises(LLMError):
            get_client()

    @override_settings(
        LLM_PROVIDER="azure_openai",
        AZURE_OPENAI_ENDPOINT="https://example.invalid",
        AZURE_OPENAI_API_KEY="secret",
        AZURE_OPENAI_DEPLOYMENT="gpt-test",
        ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"],
    )
    def test_azure_client_blocks_before_network_call_without_dpa(self):
        client = AzureOpenAIClient("https://example.invalid", "secret", "gpt-test")
        vendor = VendorCompliance.objects.create(
            provider_name="azure_openai",
            name="azure_openai",
            vendor_type="ai",
            provider_type="ai",
            region="sweden-central",
            dpa_signed=False,
            no_model_training=True,
            allowed_data_types=["ai_prompt"],
        )
        with self.assertRaises(LLMError):
            client.generate_json(system="s", user="u", schema={"type": "object"})

    @override_settings(
        EMAIL_BACKEND="apps.accounts.email_backend.BrevoEmailBackend",
        BREVO_API_URL="https://api.brevo.example/v3",
        BREVO_API_KEY="secret",
        BREVO_OPEN_TRACKING_ENABLED=False,
        ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"],
    )
    def test_brevo_backend_blocks_without_dpa(self):
        VendorCompliance.objects.create(
            provider_name="brevo",
            name="brevo",
            vendor_type="email",
            provider_type="email",
            region="eu",
            dpa_signed=False,
            no_model_training=True,
            allowed_data_types=["email_address"],
        )

        with patch("apps.accounts.email_backend.requests.post") as mock_post:
            sent = BrevoEmailBackend().send_messages([mail.EmailMessage("subj", "body", to=["a@example.com"])])
        self.assertEqual(sent, 0)
        mock_post.assert_not_called()

    @override_settings(
        EMAIL_BACKEND="apps.accounts.email_backend.BrevoEmailBackend",
        BREVO_API_URL="https://api.brevo.example/v3",
        BREVO_API_KEY="secret",
        BREVO_OPEN_TRACKING_ENABLED=False,
        ALLOWED_REGIONS=["eu", "sweden-central", "west-europe"],
    )
    def test_brevo_backend_disables_tracking_and_sends_with_gate(self):
        VendorCompliance.objects.create(
            provider_name="brevo",
            name="brevo",
            vendor_type="email",
            provider_type="email",
            region="eu",
            dpa_signed=True,
            dpa_valid_until="2999-12-31",
            no_model_training=True,
            allowed_data_types=["email_address"],
        )

        with patch("apps.accounts.email_backend.requests.post") as mock_post:
            mock_post.return_value.raise_for_status.return_value = None
            mock_post.return_value.status_code = 200
            sent = BrevoEmailBackend().send_messages([mail.EmailMessage("subj", "body", to=["a@example.com"])])

        self.assertEqual(sent, 1)
        payload = mock_post.call_args.kwargs["json"]
        self.assertFalse(payload["trackOpen"])
        self.assertEqual(payload["trackedLinks"], "disabled")
        self.assertNotIn("open_tracking", payload)

    def test_seed_vendors_creates_default_records(self):
        call_command("seed_vendors")
        created_names = {v.provider_name for v in VendorCompliance.objects.all()}
        self.assertTrue({"azure_openai", "azure_blob", "brevo"}.issubset(created_names))
        for vendor in VendorCompliance.objects.filter(provider_name__in=["azure_openai", "azure_blob", "brevo"]):
            self.assertFalse(vendor.dpa_signed)
            self.assertTrue(vendor.is_active)

    def test_seed_vendors_is_idempotent_and_preserves_manual_data(self):
        obj, _ = VendorCompliance.objects.get_or_create(
            provider_name="brevo",
            defaults={"name": "brevo", "vendor_type": "email", "provider_type": "email", "dpa_signed": True, "notes": "custom"},
        )
        obj.dpa_signed = True
        obj.notes = "custom"
        obj.save()

        call_command("seed_vendors")
        vendor = VendorCompliance.objects.get(provider_name="brevo")
        self.assertTrue(vendor.dpa_signed)
        self.assertEqual(vendor.notes, "custom")
        self.assertEqual(VendorCompliance.objects.filter(provider_name="brevo").count(), 1)


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
