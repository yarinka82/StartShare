from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone

from apps.matching.models import Digest, Introduction
from apps.startups.models import StartupProfile



class EmailNotificationType(models.TextChoices):
    EMAIL_VERIFICATION = "email_verification", "E-mail verification"
    PASSWORD_RESET = "password_reset", "Password reset"
    DRAFT_READY = "draft_ready", "Draft ready"
    DRAFT_DELETION_REMINDER = "draft_deletion_reminder", "Draft deletion reminder"
    DIGEST = "digest", "Digest"
    DIGEST_EMPTY = "digest_empty", "Empty digest"
    INTRODUCTION_REQUEST = "introduction_request", "Introduction request (D)"
    INTRODUCTION = "introduction", "Introduction (E)"
    SURVEY_INVITE = "survey_invite", "Survey invite"


class EmailNotificationStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class InterfaceLanguage(models.TextChoices):
    DE = "de", "German"
    EN = "en", "English"
    UK = "uk", "Ukrainian"


class EmailNotification(models.Model):
    """Журнал служебных писем (аудит отправок без сохранения тела письма)."""

    Type = EmailNotificationType
    Status = EmailNotificationStatus
    Language = InterfaceLanguage

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="email_notifications",
    )
    type = models.CharField(max_length=32, choices=EmailNotificationType.choices)
    language = models.CharField(
        max_length=2,
        choices=InterfaceLanguage.choices,
        default=InterfaceLanguage.DE,
    )

    # Привязки к сущностям (в зависимости от типа уведомления)
    introduction = models.ForeignKey(
        Introduction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="email_notifications",
    )
    digest = models.ForeignKey(
        Digest,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="email_notifications",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="email_notifications",
    )

    status = models.CharField(
        max_length=8,
        choices=EmailNotificationStatus.choices,
        default=EmailNotificationStatus.QUEUED,
    )
    provider_message_id = models.CharField(max_length=200, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        db_table = "email_notifications"
        ordering = ["-created_at"]
        indexes = [
            # Индекс для Celery-воркеров, выбирающих письма в очереди
            models.Index(fields=["status", "created_at"], name="idx_email_queue"),
            # Индекс для проверки частоты отправок юзеру (anti-spam / rate limit)
            models.Index(fields=["user", "type", "created_at"], name="idx_email_user_type"),
        ]

    def clean(self):
        super().clean()
        if self.status == EmailNotificationStatus.SENT and not self.sent_at:
            raise ValidationError({"sent_at": "Для отправленного письма должна быть дата отправки."})
        if self.status == EmailNotificationStatus.FAILED and not self.error_code:
            raise ValidationError({"error_code": "Для неуспешной отправки должен быть указан код ошибки."})

    def mark_sent(self, provider_id: str | None = None):
        """Удобный хелпер для сервиса отправки."""
        self.status = EmailNotificationStatus.SENT
        self.sent_at = timezone.now()
        self.provider_message_id = provider_id
        self.save(update_fields=["status", "sent_at", "provider_message_id"])

    def mark_failed(self, error: str):
        """Удобный хелпер при сбое отправки."""
        self.status = EmailNotificationStatus.FAILED
        self.error_code = error[:100]
        self.save(update_fields=["status", "error_code"])

    def __str__(self):
        return f"Email {self.type} to user #{self.user_id} [{self.status}]"