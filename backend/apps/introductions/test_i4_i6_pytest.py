import pytest
from datetime import timedelta
from unittest.mock import patch

from django.core import mail
from django.utils import timezone

from backend.apps.introductions.models import (
    Introduction,
    IntroductionEmailLog,
    IntroductionService,
    IntroductionStatus,
)


pytestmark = pytest.mark.django_db


@pytest.fixture
def interested_intro(db, startup_profile, investor_profile):
    return Introduction.objects.create(
        startup=startup_profile,
        investor=investor_profile,
        status=IntroductionStatus.INTERESTED,
        interested_at=timezone.now() - timedelta(days=1),
        expires_at=timezone.now() + timedelta(days=6),
    )


@pytest.fixture
def expired_intro(db, startup_profile, investor_profile):
    return Introduction.objects.create(
        startup=startup_profile,
        investor=investor_profile,
        status=IntroductionStatus.INTERESTED,
        interested_at=timezone.now() - timedelta(days=10),
        expires_at=timezone.now() - timedelta(days=1),
    )


@pytest.fixture
def accepted_intro(db, startup_profile, investor_profile):
    return Introduction.objects.create(
        startup=startup_profile,
        investor=investor_profile,
        status=IntroductionStatus.ACCEPTED,
        interested_at=timezone.now() - timedelta(days=1),
        expires_at=timezone.now() + timedelta(days=5),
    )


class TestI4FreigabeNein:
    def test_freigabe_success_requires_owner_and_interested_status(
        self,
        startup_api_client,
        interested_intro,
    ):
        response = startup_api_client.post(
            f"/api/introductions/{interested_intro.pk}/freigabe/",
            {},
            format="json",
        )

        interested_intro.refresh_from_db()
        assert response.status_code == 200
        assert interested_intro.status == IntroductionStatus.ACCEPTED

    def test_freigabe_after_expiry_returns_409(
        self,
        startup_api_client,
        expired_intro,
    ):
        response = startup_api_client.post(
            f"/api/introductions/{expired_intro.pk}/freigabe/",
            {},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["can_respond"] is False

    def test_freigabe_twice_returns_409(
        self,
        startup_api_client,
        interested_intro,
    ):
        first = startup_api_client.post(
            f"/api/introductions/{interested_intro.pk}/freigabe/",
            {},
            format="json",
        )
        second = startup_api_client.post(
            f"/api/introductions/{interested_intro.pk}/freigabe/",
            {},
            format="json",
        )

        assert first.status_code == 200
        assert second.status_code == 409

    def test_freigabe_by_non_owner_returns_403(
        self,
        investor_api_client,
        interested_intro,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{interested_intro.pk}/freigabe/",
            {},
            format="json",
        )

        assert response.status_code == 403

    def test_nein_success_closes_flow(
        self,
        startup_api_client,
        interested_intro,
    ):
        response = startup_api_client.post(
            f"/api/introductions/{interested_intro.pk}/nein/",
            {},
            format="json",
        )

        interested_intro.refresh_from_db()
        assert response.status_code == 200
        assert interested_intro.status == IntroductionStatus.DECLINED

    def test_nein_after_expiry_returns_409(
        self,
        startup_api_client,
        expired_intro,
    ):
        response = startup_api_client.post(
            f"/api/introductions/{expired_intro.pk}/nein/",
            {},
            format="json",
        )

        assert response.status_code == 409
        assert response.json()["can_respond"] is False


class TestI5IntroEmailAndIntroduced:
    def test_intro_email_not_sent_before_freigabe(self, startup_api_client, investor_api_client, introduction):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True},
            format="json",
        )
        assert len(mail.outbox) == 1
        introduction.refresh_from_db()
        assert introduction.status == IntroductionStatus.INTERESTED

    def test_send_intro_sends_two_emails_and_marks_introduced(self, accepted_intro):
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            result = IntroductionService.send_intro(accepted_intro.pk)

        accepted_intro.refresh_from_db()
        assert result is True
        assert mock_send.call_count == 2
        assert accepted_intro.status == IntroductionStatus.INTRODUCED
        assert accepted_intro.sent_to_startup is True
        assert accepted_intro.sent_to_investor is True
        assert IntroductionEmailLog.objects.filter(introduction=accepted_intro).count() == 2

    def test_send_intro_is_idempotent_and_does_not_duplicate_first_side(
        self,
        accepted_intro,
    ):
        first_side_effects = [None, RuntimeError("provider failed")]

        with patch("backend.apps.introductions.models.send_mail", side_effect=first_side_effects):
            with pytest.raises(RuntimeError):
                IntroductionService.send_intro(accepted_intro.pk)

        accepted_intro.refresh_from_db()
        assert accepted_intro.sent_to_startup is True
        assert accepted_intro.sent_to_investor is False

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            IntroductionService.send_intro(accepted_intro.pk)

        assert mock_send.call_count == 1

    def test_send_intro_skips_when_investor_missing(self, accepted_intro):
        accepted_intro.investor.owner = None
        accepted_intro.investor.save(update_fields=["owner"])

        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            result = IntroductionService.send_intro(accepted_intro.pk)

        assert result is False
        assert mock_send.call_count == 0


class TestI6ExpiryReminderAndProviderGate:
    def test_interest_expires_after_deadline(self, expired_intro):
        intro = IntroductionService.expire(expired_intro.pk)
        assert intro.status == IntroductionStatus.EXPIRED

    def test_reminder_sent_once_before_deadline(self, interested_intro):
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            result = IntroductionService.send_reminder_if_due(interested_intro.pk)

        assert result is True
        assert mock_send.call_count == 1

    def test_reminder_not_sent_twice(self, interested_intro):
        with patch("backend.apps.introductions.models.send_mail") as mock_send:
            IntroductionService.send_reminder_if_due(interested_intro.pk)
            IntroductionService.send_reminder_if_due(interested_intro.pk)

        assert mock_send.call_count == 1

    def test_sms_provider_gate_blocks_sms_when_not_allowed(self):
        assert IntroductionService.can_send_sms(provider_allowed=False) is False

    def test_expired_intro_blocks_freigabe_and_nein(self, expired_intro, startup_api_client):
        freigabe = startup_api_client.post(
            f"/api/introductions/{expired_intro.pk}/freigabe/",
            {},
            format="json",
        )
        nein = startup_api_client.post(
            f"/api/introductions/{expired_intro.pk}/nein/",
            {},
            format="json",
        )

        assert freigabe.status_code == 409
        assert nein.status_code == 409
