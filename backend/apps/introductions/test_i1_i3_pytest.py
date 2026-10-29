import pytest
from django.core import mail

from backend.apps.analytics.models import EventLog
from backend.apps.introductions.models import IntroductionConsent, IntroductionStatus


pytestmark = pytest.mark.django_db


class TestI1StateMachine:
    def test_interest_transition_from_suggested_to_interested(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True},
            format="json",
        )

        introduction.refresh_from_db()
        assert response.status_code == 200
        assert response.json()["status"] == IntroductionStatus.INTERESTED
        assert introduction.status == IntroductionStatus.INTERESTED
        assert introduction.interested_at is not None
        assert introduction.expires_at is not None

    def test_duplicate_interest_returns_409(
        self,
        investor_api_client,
        introduction,
    ):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True},
            format="json",
        )

        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True},
            format="json",
        )

        assert response.status_code == 409
        assert "Invalid transition" in response.json()["detail"]

    def test_interest_requires_notification_confirmation(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {},
            format="json",
        )

        introduction.refresh_from_db()
        assert response.status_code == 400
        assert introduction.status == IntroductionStatus.SUGGESTED


class TestI2InvestorActions:
    def test_interest_rejects_message_with_private_contact_data(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {
                "notification_accepted": True,
                "message": "Reach me at investor@example.com",
            },
            format="json",
        )

        assert response.status_code == 400
        assert "cannot contain email" in response.json()["detail"].lower()

    def test_interest_records_consent_and_sanitized_event(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {
                "notification_accepted": True,
                "message": "Short strategic note",
            },
            format="json",
        )

        introduction.refresh_from_db()
        event = EventLog.objects.get(
            event_type=EventLog.EVENT_INTERESTED,
            startup=introduction.startup,
            investor=introduction.investor,
        )

        assert response.status_code == 200
        assert IntroductionConsent.objects.filter(introduction=introduction).exists()
        assert event.payload == {"has_message": True}
        assert "short strategic note" not in str(event.payload).lower()

    def test_decline_accepts_supported_reason_and_sets_declined_status(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/decline/",
            {"reason": "region"},
            format="json",
        )

        introduction.refresh_from_db()
        event = EventLog.objects.get(
            event_type=EventLog.EVENT_DECLINED,
            startup=introduction.startup,
            investor=introduction.investor,
        )

        assert response.status_code == 200
        assert response.json()["status"] == IntroductionStatus.DECLINED
        assert introduction.status == IntroductionStatus.DECLINED
        assert introduction.decline_reason == "region"
        assert event.payload == {"reason": "region"}

    def test_decline_rejects_unsupported_reason(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/decline/",
            {"reason": "invalid_reason"},
            format="json",
        )

        introduction.refresh_from_db()
        assert response.status_code == 400
        assert introduction.status == IntroductionStatus.SUGGESTED

    def test_repeated_decline_returns_409(
        self,
        investor_api_client,
        introduction,
    ):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/decline/",
            {"reason": "region"},
            format="json",
        )

        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/decline/",
            {"reason": "region"},
            format="json",
        )

        assert response.status_code == 409

    def test_startup_notification_email_is_sent_once_without_message_or_contact_details(
        self,
        investor_api_client,
        introduction,
    ):
        response = investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {
                "notification_accepted": True,
                "message": "Keep this private",
            },
            format="json",
        )

        assert response.status_code == 200
        assert len(mail.outbox) == 1
        body = mail.outbox[0].body
        assert "Northstar Capital" in body
        assert "Keep this private" not in body
        assert "@" not in body


class TestI3StartupRequests:
    def test_startup_owner_sees_request_list_and_detail(
        self,
        investor_api_client,
        startup_api_client,
        introduction,
    ):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True, "message": "Short note"},
            format="json",
        )

        list_response = startup_api_client.get("/api/introductions/requests/")
        detail_response = startup_api_client.get(f"/api/introductions/requests/{introduction.pk}/")

        assert list_response.status_code == 200
        assert detail_response.status_code == 200
        assert any(item["id"] == introduction.pk for item in list_response.json())
        assert detail_response.json()["id"] == introduction.pk

    def test_startup_detail_shows_org_data_but_not_investor_contacts_before_approval(
        self,
        investor_api_client,
        startup_api_client,
        introduction,
    ):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True, "message": "Short note"},
            format="json",
        )

        response = startup_api_client.get(f"/api/introductions/requests/{introduction.pk}/")
        payload = response.json()

        assert response.status_code == 200
        assert payload["organization"] == "Northstar Capital"
        assert payload["organization_type"] == "Fund"
        serialized = str(payload).lower()
        assert "investor-contact@example.com" not in serialized
        assert "contact_phone" not in serialized
        assert "contact_email" not in serialized

    def test_other_user_cannot_access_startup_request_list(
        self,
        investor_api_client,
        stranger_api_client,
        introduction,
    ):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True},
            format="json",
        )

        response = stranger_api_client.get("/api/introductions/requests/")

        assert response.status_code == 403

    def test_other_user_cannot_access_startup_request_detail(
        self,
        investor_api_client,
        stranger_api_client,
        introduction,
    ):
        investor_api_client.post(
            f"/api/introductions/{introduction.pk}/interest/",
            {"notification_accepted": True},
            format="json",
        )

        response = stranger_api_client.get(f"/api/introductions/requests/{introduction.pk}/")

        assert response.status_code == 403
