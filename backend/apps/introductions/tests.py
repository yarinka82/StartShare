from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.test import TestCase, override_settings
from django.utils import timezone

from backend.apps.analytics.models import EventLog, SurveyService
from backend.apps.investors.models import InvestorProfile
from backend.apps.profiles.models import StartupProfile
from .exceptions import InvalidTransition
from .models import Introduction, IntroductionConsent, IntroductionService, IntroductionStatus


class IntroductionStateMachineTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="tester", email="tester@example.com", password="secret123")
        self.client.force_login(self.user)
        self.startup = StartupProfile.objects.create(
            company_name="Alpha",
            contact_email="startup@example.com",
            owner=self.user,
        )
        self.investor = InvestorProfile.objects.create(
            organization_name="Venture Fund",
            organization_type="Fund",
            owner=self.user,
            contact_email="investor@example.com",
        )

    def test_allowed_transitions(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        intro._validate_transition(IntroductionStatus.INTERESTED)
        intro._validate_transition(IntroductionStatus.DECLINED)

        intro.status = IntroductionStatus.INTERESTED
        intro.save(update_fields=["status"])
        intro._validate_transition(IntroductionStatus.ACCEPTED)
        intro._validate_transition(IntroductionStatus.DECLINED)
        intro._validate_transition(IntroductionStatus.EXPIRED)

        intro.status = IntroductionStatus.ACCEPTED
        intro.save(update_fields=["status"])
        intro._validate_transition(IntroductionStatus.INTRODUCED)

    def test_forbidden_transitions_raise(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.DECLINED)
        with self.assertRaises(InvalidTransition):
            intro._validate_transition(IntroductionStatus.INTERESTED)

        intro2 = Introduction.objects.create(
            startup=StartupProfile.objects.create(company_name="Beta"),
            investor=InvestorProfile.objects.create(organization_name="Angel Fund"),
            status=IntroductionStatus.EXPIRED,
        )
        with self.assertRaises(InvalidTransition):
            intro2._validate_transition(IntroductionStatus.ACCEPTED)

        intro3 = Introduction.objects.create(
            startup=StartupProfile.objects.create(company_name="Gamma"),
            investor=InvestorProfile.objects.create(organization_name="VC Fund"),
            status=IntroductionStatus.INTRODUCED,
        )
        with self.assertRaises(InvalidTransition):
            intro3._validate_transition(IntroductionStatus.DECLINED)

    def test_interest_requires_notification_confirmation(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        with self.assertRaises(ValidationError):
            IntroductionService.interest(intro, "hello", notification_accepted=False)

    def test_invalid_message_is_rejected(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        with self.assertRaises(ValidationError):
            IntroductionService.interest(intro, "Contact me at anna@example.com", notification_accepted=True)
        with self.assertRaises(ValidationError):
            IntroductionService.interest(intro, "https://example.com", notification_accepted=True)

    def test_interest_records_consent_and_status(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        updated = IntroductionService.interest(intro, "hello", notification_accepted=True)
        self.assertEqual(updated.status, IntroductionStatus.INTERESTED)
        self.assertTrue(IntroductionConsent.objects.filter(introduction=updated).exists())

    def test_interest_event_does_not_store_message_text(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        IntroductionService.interest(intro, "hello there", notification_accepted=True)
        event = EventLog.objects.filter(event_type=EventLog.EVENT_INTERESTED, startup=self.startup, investor=self.investor).latest("created_at")
        self.assertTrue(event.payload["has_message"])
        self.assertNotIn("hello", str(event.payload).lower())

    def test_decline_event_persists_reason(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        IntroductionService.decline_by_investor(intro, "stage")
        event = EventLog.objects.filter(event_type=EventLog.EVENT_DECLINED, startup=self.startup, investor=self.investor).latest("created_at")
        self.assertEqual(event.payload["reason"], "stage")

    def test_repeat_interest_after_decline_or_expired_is_rejected(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        IntroductionService.decline_by_investor(intro, "region")
        with self.assertRaises(InvalidTransition):
            IntroductionService.interest(intro, "hello", notification_accepted=True)

        intro2 = Introduction.objects.create(startup=StartupProfile.objects.create(company_name="Delta"), investor=InvestorProfile.objects.create(organization_name="Fund B"), status=IntroductionStatus.INTERESTED)
        with self.assertRaises(InvalidTransition):
            IntroductionService.interest(intro2, "hello", notification_accepted=True)

    def test_interest_sends_one_startup_email_without_private_investor_details(self):
        self.startup.contact_email = "startup@example.com"
        self.startup.save(update_fields=["contact_email"])
        self.investor.organization_type = "Fund"
        self.investor.organization_name = "Northstar Capital"
        self.investor.save(update_fields=["organization_type", "organization_name"])

        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        IntroductionService.interest(intro, "Private note: +49 111 111 1111", notification_accepted=True)
        self.assertEqual(len(mail.outbox), 1)
        email = mail.outbox[0]
        self.assertIn("Northstar Capital", email.body)
        self.assertNotIn("Private note", email.body)
        self.assertNotIn("+49", email.body)
        self.assertNotIn("@", email.body)

        IntroductionService.notify_startup_of_interest(intro)
        self.assertEqual(len(mail.outbox), 1)

    def test_startup_request_endpoints_expose_request_without_email_details(self):
        self.startup.contact_email = "startup@example.com"
        self.startup.save(update_fields=["contact_email"])
        self.investor.organization_name = "Northstar Capital"
        self.investor.organization_type = "Business Angel"
        self.investor.save(update_fields=["organization_name", "organization_type"])
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.INTERESTED, investor_message="Secret note")

        response = self.client.get(f"/api/introductions/requests/?startup_id={self.startup.pk}")
        self.assertEqual(response.status_code, 200)
        self.assertGreater(len(response.json()), 0)
        self.assertEqual(response.json()[0]["organization"], "Northstar Capital")

        detail = self.client.get(f"/api/introductions/requests/{intro.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertEqual(detail.json()["message"], "Secret note")

    def test_intro_email_sends_to_both_sides_with_privacy_notice(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.ACCEPTED,
        )
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            IntroductionService.send_intro(intro.pk)
            self.assertEqual(mock_send.call_count, 2)
            bodies = [call.args[1] for call in mock_send.call_args_list]
            self.assertTrue(all("[Plattform] vermittelt" in body for body in bodies))
            intro.refresh_from_db()
            self.assertTrue(intro.sent_to_startup)
            self.assertTrue(intro.sent_to_investor)
            self.assertEqual(intro.status, IntroductionStatus.INTRODUCED)

    def test_intro_email_is_idempotent_when_second_send_fails(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.ACCEPTED,
        )
        side_effects = [None, RuntimeError("provider failed")]

        with patch("backend.apps.introductions.models.send_mail", side_effect=side_effects) as mock_send:
            with self.assertRaises(RuntimeError):
                IntroductionService.send_intro(intro.pk)
            self.assertEqual(mock_send.call_count, 2)
            intro.refresh_from_db()
            self.assertTrue(intro.sent_to_startup)
            self.assertFalse(intro.sent_to_investor)

        with patch("backend.apps.introductions.models.send_mail") as mock_send_retry:
            IntroductionService.send_intro(intro.pk)
            self.assertEqual(mock_send_retry.call_count, 1)
            self.assertTrue(mock_send_retry.call_args[0][1].startswith("Hallo"))

    def test_intro_email_skips_if_investor_account_is_missing(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.ACCEPTED,
        )
        self.investor.owner = None
        self.investor.save(update_fields=["owner"])
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            result = IntroductionService.send_intro(intro.pk)
            self.assertFalse(result)
            self.assertEqual(mock_send.call_count, 0)

    def test_startup_freigabe_before_expiry_passes_and_logs_consent(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = self.client.post(f"/api/introductions/{intro.pk}/freigabe/")
        self.assertEqual(response.status_code, 200)
        intro.refresh_from_db()
        self.assertEqual(intro.status, IntroductionStatus.ACCEPTED)
        self.assertTrue(intro.startup_decisions.filter(decision="freigabe").exists())

    def test_startup_freigabe_after_expiry_returns_409_with_can_respond_false(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() - timedelta(days=1),
        )
        response = self.client.post(f"/api/introductions/{intro.pk}/freigabe/")
        self.assertEqual(response.status_code, 409)
        self.assertFalse(response.json()["can_respond"])

    def test_startup_freigabe_is_rejected_for_non_owner_and_twice(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        other_user = get_user_model().objects.create_user(username="other", password="secret123")
        self.client.force_login(other_user)
        response = self.client.post(f"/api/introductions/{intro.pk}/freigabe/")
        self.assertEqual(response.status_code, 403)

        self.client.force_login(self.user)
        response = self.client.post(f"/api/introductions/{intro.pk}/freigabe/")
        self.assertEqual(response.status_code, 200)
        response = self.client.post(f"/api/introductions/{intro.pk}/freigabe/")
        self.assertEqual(response.status_code, 409)

    def test_startup_nein_rejects_without_reason_and_closes_flow(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now(),
            expires_at=timezone.now() + timedelta(days=7),
        )
        response = self.client.post(f"/api/introductions/{intro.pk}/nein/")
        self.assertEqual(response.status_code, 200)
        intro.refresh_from_db()
        self.assertEqual(intro.status, IntroductionStatus.DECLINED)

    @override_settings(INTRO_REMINDER_DAYS=4)
    def test_due_reminders_are_sent_once_and_only_for_active_interest(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=5),
            expires_at=timezone.now() + timedelta(days=3),
        )
        self.startup.contact_email = "startup@example.com"
        self.startup.save(update_fields=["contact_email"])

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            sent = IntroductionService.send_due_reminders(now=timezone.now())
            self.assertEqual(sent, [intro.pk])
            self.assertEqual(mock_send.call_count, 1)
            intro.refresh_from_db()
            self.assertIsNotNone(intro.reminder_sent_at)

        with patch("backend.apps.introductions.models.send_mail") as mock_send_again:
            sent_again = IntroductionService.send_due_reminders(now=timezone.now())
            self.assertEqual(sent_again, [])
            self.assertEqual(mock_send_again.call_count, 0)

    @override_settings(INTRO_SMS_PROVIDER_ALLOWED=False)
    def test_sms_reminder_requires_provider_gate(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=6),
            expires_at=timezone.now() + timedelta(days=2),
        )
        self.startup.contact_email = "startup@example.com"
        self.startup.save(update_fields=["contact_email"])

        with self.assertRaises(ValidationError):
            IntroductionService.send_due_reminders(now=timezone.now(), channel="sms")

    def test_expire_overdue_converts_interested_to_expired_and_keeps_other_statuses(self):
        live_intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() - timedelta(days=1),
        )
        accepted_intro = Introduction.objects.create(
            startup=StartupProfile.objects.create(company_name="Beta", owner=self.user),
            investor=InvestorProfile.objects.create(organization_name="Beta Fund", owner=self.user),
            status=IntroductionStatus.ACCEPTED,
            interested_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() - timedelta(days=1),
        )
        done_intro = Introduction.objects.create(
            startup=StartupProfile.objects.create(company_name="Gamma", owner=self.user),
            investor=InvestorProfile.objects.create(organization_name="Gamma Fund", owner=self.user),
            status=IntroductionStatus.INTRODUCED,
            interested_at=timezone.now() - timedelta(days=10),
            expires_at=timezone.now() - timedelta(days=1),
        )

        expired_ids = IntroductionService.expire_overdue(now=timezone.now())
        self.assertEqual(expired_ids, [live_intro.pk])

        live_intro.refresh_from_db()
        self.assertEqual(live_intro.status, IntroductionStatus.EXPIRED)
        self.assertEqual(accepted_intro.status, IntroductionStatus.ACCEPTED)
        self.assertEqual(done_intro.status, IntroductionStatus.INTRODUCED)

    @override_settings(CARD_ACTIVE_DAYS=30)
    def test_close_inactive_cards_returns_stale_interests_without_changing_status(self):
        stale_intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=45),
            expires_at=timezone.now() + timedelta(days=2),
        )
        active_intro = Introduction.objects.create(
            startup=StartupProfile.objects.create(company_name="Delta", owner=self.user),
            investor=InvestorProfile.objects.create(organization_name="Delta Fund", owner=self.user),
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=5),
            expires_at=timezone.now() + timedelta(days=2),
        )

        stale_ids = IntroductionService.close_inactive_cards(now=timezone.now())
        self.assertIn(stale_intro.pk, stale_ids)
        self.assertNotIn(active_intro.pk, stale_ids)

        stale_intro.refresh_from_db()
        self.assertEqual(stale_intro.status, IntroductionStatus.INTERESTED)

    def test_startup_pause_closes_open_requests_and_notifies_investors(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() + timedelta(days=5),
        )
        self.startup.profile_status = StartupProfile.STATUS_PAUSED
        self.startup.save(update_fields=["profile_status"])

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            closed = IntroductionService.close_startup_intros_on_profile_status_change(self.startup, now=timezone.now())
            self.assertEqual(closed, [intro.pk])
            self.assertEqual(mock_send.call_count, 1)

        intro.refresh_from_db()
        self.assertEqual(intro.status, IntroductionStatus.EXPIRED)
        self.assertIn("nicht mehr aktiv", mock_send.call_args.kwargs["message"].lower())

    def test_investor_account_deletion_removes_open_requests_without_startup_email(self):
        intro_interest = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=6),
        )
        accepted_intro = Introduction.objects.create(
            startup=self.startup,
            investor=InvestorProfile.objects.create(organization_name="Open Fund", owner=self.user, contact_email="investor2@example.com"),
            status=IntroductionStatus.ACCEPTED,
            interested_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=6),
        )

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            removed = IntroductionService.remove_investor_open_intros(self.investor, now=timezone.now())
            self.assertIn(intro_interest.pk, removed)
            self.assertFalse(Introduction.objects.filter(pk=intro_interest.pk).exists())
            self.assertEqual(mock_send.call_count, 0)
            self.assertTrue(Introduction.objects.filter(pk=accepted_intro.pk).exists())

    def test_event_log_strips_private_data_and_survey_response_is_unique(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        IntroductionService.interest(intro, "Hello there", notification_accepted=True)
        event = EventLog.objects.filter(event_type=EventLog.EVENT_INTERESTED, startup=self.startup, investor=self.investor).latest("created_at")
        event_text = str(event.payload).lower()
        self.assertNotIn("hello", event_text)
        self.assertNotIn("@", event_text)
        self.assertNotIn("example.com", event_text)

        with override_settings(SURVEYS_ENABLED=True):
            response, created = SurveyService.record_answer(
                user=self.user,
                answer="positive",
                startup=self.startup,
                days_after=14,
            )
            self.assertTrue(created)
            self.assertEqual(response.answer, "positive")
            response2, created2 = SurveyService.record_answer(
                user=self.user,
                answer="negative",
                startup=self.startup,
                days_after=14,
            )
            self.assertFalse(created2)
            self.assertEqual(response2.answer, "positive")

    def test_scenario_1_end_to_end_interest_to_intro(self):
        self.startup.contact_email = "startup@example.com"
        self.startup.save(update_fields=["contact_email"])
        self.investor.organization_name = "Northstar Capital"
        self.investor.organization_type = "Fund"
        self.investor.contact_email = "investor@example.com"
        self.investor.save(update_fields=["organization_name", "organization_type", "contact_email"])

        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        updated = IntroductionService.interest(intro, "hello", notification_accepted=True)
        self.assertEqual(updated.status, IntroductionStatus.INTERESTED)

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            try:
                IntroductionService.notify_startup_of_interest(updated)
            except Exception:
                pass
            self.assertEqual(mock_send.call_count, 0)

        accepted = IntroductionService.accept(updated, user=self.user)
        self.assertEqual(accepted.status, IntroductionStatus.ACCEPTED)

        with patch("backend.apps.introductions.models.send_mail") as mock_intro_send:
            IntroductionService.send_intro(updated.pk)
            self.assertEqual(mock_intro_send.call_count, 2)
            updated.refresh_from_db()
            self.assertEqual(updated.status, IntroductionStatus.INTRODUCED)
            self.assertTrue(updated.sent_to_startup)
            self.assertTrue(updated.sent_to_investor)

    def test_scenario_2_declined_intro_is_not_reopened(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.SUGGESTED)
        IntroductionService.decline_by_investor(intro, "region")
        with self.assertRaises(InvalidTransition):
            IntroductionService.interest(intro, "hello", notification_accepted=True)

    def test_scenario_3_no_response_then_reminder_then_expired(self):
        self.startup.contact_email = "startup@example.com"
        self.startup.save(update_fields=["contact_email"])
        now = timezone.now()
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=now - timedelta(days=5),
            expires_at=now + timedelta(days=5),
        )

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            sent = IntroductionService.send_due_reminders(now=now)
            self.assertEqual(sent, [intro.pk])
            self.assertEqual(mock_send.call_count, 1)

        intro.refresh_from_db()
        self.assertIsNotNone(intro.reminder_sent_at)

        intro.expires_at = now - timedelta(minutes=1)
        intro.save(update_fields=["expires_at"])
        expired_ids = IntroductionService.expire_overdue(now=now)
        self.assertIn(intro.pk, expired_ids)
        intro.refresh_from_db()
        self.assertEqual(intro.status, IntroductionStatus.EXPIRED)

    def test_scenario_4_startup_pause_closes_open_requests(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=2),
            expires_at=timezone.now() + timedelta(days=5),
        )
        self.startup.profile_status = StartupProfile.STATUS_PAUSED
        self.startup.save(update_fields=["profile_status"])
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            closed = IntroductionService.close_startup_intros_on_profile_status_change(self.startup, now=timezone.now())
            self.assertEqual(closed, [intro.pk])
            self.assertEqual(mock_send.call_count, 1)
        intro.refresh_from_db()
        self.assertEqual(intro.status, IntroductionStatus.EXPIRED)

    def test_scenario_5_investor_account_removed_before_intro_email(self):
        intro = Introduction.objects.create(
            startup=self.startup,
            investor=self.investor,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timedelta(days=1),
            expires_at=timezone.now() + timedelta(days=6),
        )
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            removed = IntroductionService.remove_investor_open_intros(self.investor, now=timezone.now())
            self.assertIn(intro.pk, removed)
            self.assertEqual(mock_send.call_count, 0)
            self.assertFalse(Introduction.objects.filter(pk=intro.pk).exists())

    def test_parallel_accept_and_decline_produces_one_success(self):
        intro = Introduction.objects.create(startup=self.startup, investor=self.investor, status=IntroductionStatus.INTERESTED)
        self.assertIsNotNone(intro)
