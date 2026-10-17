import logging

import requests
from django.conf import settings
from django.core.mail.backends.base import BaseEmailBackend

from apps.accounts.compliance import ProviderBlocked, assert_provider_allowed

logger = logging.getLogger(__name__)


class BrevoEmailBackend(BaseEmailBackend):
    """Email backend that enforces the Brevo EU provider gate before sending."""

    def __init__(self, fail_silently=False, **kwargs):
        super().__init__(fail_silently=fail_silently)
        self.api_url = getattr(settings, "BREVO_API_URL", "https://api.brevo.com/v3")
        self.api_key = getattr(settings, "BREVO_API_KEY", "")
        self.track_opens = bool(getattr(settings, "BREVO_OPEN_TRACKING_ENABLED", False))

    def open(self):
        return True

    def close(self):
        return None

    def send_messages(self, email_messages):
        sent = 0
        for message in email_messages:
            try:
                assert_provider_allowed("brevo")
            except ProviderBlocked as exc:
                logger.warning("Email delivery blocked for provider 'brevo': %s", str(exc))
                if not self.fail_silently:
                    continue
                continue

            payload = {
                "sender": {"name": "Start Share", "email": settings.DEFAULT_FROM_EMAIL},
                "to": [{"email": recipient} for recipient in message.to],
                "subject": message.subject,
                "textContent": message.body,
                "htmlContent": message.body,
                "tag": "notification",
                "trackOpen": self.track_opens,
                "trackedLinks": "disabled" if not self.track_opens else "enabled",
            }
            headers = {
                "Content-Type": "application/json",
                "api-key": self.api_key,
                "Accept": "application/json",
            }
            try:
                response = requests.post(
                    f"{self.api_url.rstrip('/')}/smtp/email",
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()
            except requests.RequestException as exc:
                logger.warning("Brevo email delivery failed: %s", exc)
                if self.fail_silently:
                    continue
                raise
            sent += 1
        return sent
