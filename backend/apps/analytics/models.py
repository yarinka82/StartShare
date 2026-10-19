from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models


class EventLog(models.Model):
    EVENT_INTERESTED = "interested"
    EVENT_DECLINED = "declined"
    EVENT_STATUS_CHANGED = "status_changed"
    EVENT_REPORT_SUBMITTED = "report_submitted"
    EVENT_SURVEY_ANSWERED = "survey_answered"
    EVENT_TYPE_CHOICES = [
        (EVENT_INTERESTED, "Interested"),
        (EVENT_DECLINED, "Declined"),
        (EVENT_STATUS_CHANGED, "Status changed"),
        (EVENT_REPORT_SUBMITTED, "Report submitted"),
        (EVENT_SURVEY_ANSWERED, "Survey answered"),
    ]

    event_type = models.CharField(max_length=32, choices=EVENT_TYPE_CHOICES)
    startup = models.ForeignKey("profiles.StartupProfile", on_delete=models.CASCADE, related_name="event_logs")
    investor = models.ForeignKey("investors.InvestorProfile", on_delete=models.CASCADE, related_name="event_logs")
    payload = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    @staticmethod
    def _sanitize_payload(payload):
        sanitized = {}
        for key, value in (payload or {}).items():
            if isinstance(value, str):
                lowered = value.lower()
                if any(token in lowered for token in ("@", "http://", "https://", "mailto:", "phone", "email", "message", "contact", "link", "tel:")):
                    continue
            sanitized[key] = value
        return sanitized

    def save(self, *args, **kwargs):
        self.payload = self._sanitize_payload(self.payload)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.event_type}::{self.startup_id}->{self.investor_id}"


class SurveyResponse(models.Model):
    startup = models.ForeignKey(
        "profiles.StartupProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_responses",
    )
    investor = models.ForeignKey(
        "investors.InvestorProfile",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="survey_responses",
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="survey_responses")
    days_after = models.PositiveSmallIntegerField()
    answer = models.CharField(max_length=32, blank=True, default="")
    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "days_after"], name="uniq_survey_user_days"),
        ]
        ordering = ["-submitted_at"]


class SurveyService:
    @staticmethod
    def should_send_survey(*, startup=None, investor=None, days_after=None):
        if not getattr(settings, "SURVEYS_ENABLED", False):
            return False
        if days_after not in {14, 30}:
            return False
        if startup is not None and getattr(startup, "profile_status", None) in {"PAUSED", "REMOVED"}:
            return False
        if investor is not None and getattr(investor, "owner", None) is None:
            return False
        return True

    @staticmethod
    def record_answer(*, user, answer, startup=None, investor=None, days_after=None):
        if not SurveyService.should_send_survey(startup=startup, investor=investor, days_after=days_after):
            raise ValidationError("Survey is disabled, not eligible, or not allowed for this participant.")
        response, created = SurveyResponse.objects.get_or_create(
            user=user,
            days_after=int(days_after),
            defaults={
                "startup": startup,
                "investor": investor,
                "answer": answer,
            },
        )
        if created:
            return response, True
        return response, False
