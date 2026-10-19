import pytest
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import override_settings
from django.utils import timezone

from backend.apps.analytics.models import EventLog, SurveyService
from backend.apps.introductions.models import Introduction, IntroductionService, IntroductionStatus
from backend.apps.profiles.models import StartupProfile


pytestmark = pytest.mark.django_db


class TestL10LaunchReadiness:
    def test_fail_closed_provider_blocks_intro_email(self, startup_profile, investor_profile):
        intro = Introduction.objects.create(
            startup=startup_profile,
            investor=investor_profile,
            status=IntroductionStatus.ACCEPTED,
        )

        with override_settings(INTRO_EMAIL_PROVIDER_ALLOWED=False):
            with pytest.raises(ValidationError):
                IntroductionService.send_intro(intro.pk)

    def test_sms_reminder_is_blocked_when_provider_disallowed(self, startup_profile, investor_profile):
        intro = Introduction.objects.create(
            startup=startup_profile,
            investor=investor_profile,
            status=IntroductionStatus.INTERESTED,
            interested_at=timezone.now() - timezone.timedelta(days=6),
            expires_at=timezone.now() + timezone.timedelta(days=2),
        )
        startup_profile.contact_email = "startup@example.com"
        startup_profile.save(update_fields=["contact_email"])

        with override_settings(INTRO_SMS_PROVIDER_ALLOWED=False):
            with pytest.raises(ValidationError):
                IntroductionService.send_due_reminders(now=timezone.now(), channel="sms")

    def test_pause_closes_active_intro_without_leaking_private_data(self, startup_profile, investor_profile):
        intro = Introduction.objects.create(
            startup=startup_profile,
            investor=investor_profile,
            status=IntroductionStatus.INTERESTED,
        )
        startup_profile.profile_status = StartupProfile.STATUS_PAUSED
        startup_profile.save(update_fields=["profile_status"])

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            closed = IntroductionService.close_startup_intros_on_profile_status_change(startup_profile, now=timezone.now())

        intro.refresh_from_db()
        assert closed == [intro.pk]
        assert intro.status == IntroductionStatus.EXPIRED
        assert mock_send.call_count == 1
        body = mock_send.call_args.kwargs["message"]
        assert "@" not in body
        assert "contact" not in body.lower()

    def test_non_owner_cannot_access_startup_requests(self, investor_api_client, stranger_api_client, introduction):
        response = stranger_api_client.get("/api/introductions/requests/")
        assert response.status_code == 403

        response_detail = stranger_api_client.get(f"/api/introductions/requests/{introduction.pk}/")
        assert response_detail.status_code == 403

    def test_event_logs_remain_sanitized_for_launch_audit(self, startup_profile, investor_profile):
        payload = {
            "message": "Contact me at founder@example.com",
            "link": "https://example.com/private",
            "reason": "region",
        }

        event = EventLog.objects.create(
            event_type=EventLog.EVENT_STATUS_CHANGED,
            startup=startup_profile,
            investor=investor_profile,
            payload=payload,
        )

        assert event.payload == {"reason": "region"}
        assert "example.com" not in str(event.payload)
        assert "https://" not in str(event.payload)

    @override_settings(SURVEYS_ENABLED=False)
    def test_survey_is_disabled_by_default(self, startup_user, startup_profile):
        with pytest.raises(ValidationError):
            SurveyService.record_answer(
                user=startup_user,
                answer="positive",
                startup=startup_profile,
                days_after=14,
            )

    def test_duplicate_survey_answer_is_not_overwritten(self, startup_user, startup_profile):
        with override_settings(SURVEYS_ENABLED=True):
            first, created = SurveyService.record_answer(
                user=startup_user,
                answer="positive",
                startup=startup_profile,
                days_after=14,
            )
            second, created_again = SurveyService.record_answer(
                user=startup_user,
                answer="negative",
                startup=startup_profile,
                days_after=14,
            )

        assert created is True
        assert created_again is False
        assert first.answer == "positive"
        assert second.answer == "positive"
