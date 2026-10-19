import pytest
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.test import override_settings

from backend.apps.analytics.models import EventLog, SurveyService
from backend.apps.introductions.models import Introduction, IntroductionService, IntroductionStatus
from backend.apps.profiles.models import StartupProfile


pytestmark = pytest.mark.django_db


class TestI7StartupPauseAndInvestorCleanup:
    def test_pause_closes_open_intro_requests(self, startup_profile, investor_profile):
        intro = Introduction.objects.create(
            startup=startup_profile,
            investor=investor_profile,
            status=IntroductionStatus.INTERESTED,
        )
        startup_profile.profile_status = StartupProfile.STATUS_PAUSED
        startup_profile.save(update_fields=["profile_status"])

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            closed = IntroductionService.close_startup_intros_on_profile_status_change(startup_profile)

        intro.refresh_from_db()
        assert closed == [intro.pk]
        assert intro.status == IntroductionStatus.EXPIRED
        assert mock_send.call_count == 1

    def test_remove_investor_closes_open_intros(self, startup_profile, investor_profile):
        open_intro = Introduction.objects.create(
            startup=startup_profile,
            investor=investor_profile,
            status=IntroductionStatus.INTERESTED,
        )
        other_startup = startup_profile.__class__.objects.create(
            owner=startup_profile.owner,
            company_name="Other Startup",
            contact_email="other@example.com",
            profile_status=StartupProfile.STATUS_LIVE,
        )
        accepted_intro = Introduction.objects.create(
            startup=other_startup,
            investor=investor_profile,
            status=IntroductionStatus.ACCEPTED,
        )

        removed = IntroductionService.remove_investor_open_intros(investor_profile)

        assert sorted(removed) == sorted([open_intro.pk, accepted_intro.pk])
        assert not Introduction.objects.filter(pk=open_intro.pk).exists()
        assert not Introduction.objects.filter(pk=accepted_intro.pk).exists()

    def test_startup_remove_does_not_send_private_data(self, startup_profile, investor_profile):
        intro = Introduction.objects.create(
            startup=startup_profile,
            investor=investor_profile,
            status=IntroductionStatus.INTERESTED,
        )
        startup_profile.profile_status = StartupProfile.STATUS_REMOVED
        startup_profile.save(update_fields=["profile_status"])

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            IntroductionService.close_startup_intros_on_profile_status_change(startup_profile)

        intro.refresh_from_db()
        assert intro.status == IntroductionStatus.EXPIRED
        assert mock_send.call_count == 1
        body = mock_send.call_args.kwargs["message"]
        assert "@" not in body
        assert "contact" not in body.lower()


class TestI8PrivacySafeEventLogging:
    def test_event_log_sanitizes_private_payload(self, startup_profile, investor_profile):
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

    def test_report_event_records_structured_data(self, startup_profile, investor_profile):
        event = EventLog.objects.create(
            event_type=EventLog.EVENT_REPORT_SUBMITTED,
            startup=startup_profile,
            investor=investor_profile,
            payload={"type": "profile", "reason": "misleading"},
        )

        assert event.event_type == EventLog.EVENT_REPORT_SUBMITTED
        assert event.payload["type"] == "profile"
        assert event.payload["reason"] == "misleading"


class TestI9Surveys:
    @override_settings(SURVEYS_ENABLED=True)
    def test_survey_answer_is_created_once_per_user_and_days(self, startup_user, startup_profile, investor_profile):
        response, created = SurveyService.record_answer(
            user=startup_user,
            answer="positive",
            startup=startup_profile,
            days_after=14,
        )

        assert created is True
        assert response.answer == "positive"

        response_2, created_2 = SurveyService.record_answer(
            user=startup_user,
            answer="negative",
            startup=startup_profile,
            days_after=14,
        )

        assert created_2 is False
        assert response_2.answer == "positive"

    @override_settings(SURVEYS_ENABLED=False)
    def test_survey_is_rejected_when_disabled(self, startup_user, startup_profile):
        with pytest.raises(ValidationError):
            SurveyService.record_answer(
                user=startup_user,
                answer="positive",
                startup=startup_profile,
                days_after=14,
            )

    @override_settings(SURVEYS_ENABLED=True)
    def test_survey_rejects_ineligible_paused_profile(self, startup_user, startup_profile):
        startup_profile.profile_status = StartupProfile.STATUS_PAUSED
        startup_profile.save(update_fields=["profile_status"])

        with pytest.raises(ValidationError):
            SurveyService.record_answer(
                user=startup_user,
                answer="positive",
                startup=startup_profile,
                days_after=14,
            )
