from django.conf import settings
from django.db import models
from django.utils import timezone


class EventRole(models.TextChoices):
    STARTUP = "startup", "Startup"
    INVESTOR = "investor", "Investor"
    SYSTEM = "system", "System"


class EventName(models.TextChoices):
    REGISTERED = "registered", "Registered"
    STATUS_CONFIRMED = "status_confirmed", "Investor confirmed status (text C)"
    MANDATE_SAVED = "mandate_saved", "Investor saved mandate (v1)"
    MANDATE_CHANGED = "mandate_changed", "Investor changed mandate (vX)"
    DECK_UPLOADED = "deck_uploaded", "Startup uploaded pitch deck"
    AI_DRAFT_CREATED = "ai_draft_created", "AI finished teaser draft"
    FIELD_EDITED = "field_edited", "Teaser field edited"
    TEASER_APPROVED = "teaser_approved", "Teaser approved"
    WENT_LIVE = "went_live", "Went live"


class Event(models.Model):
    Role = EventRole
    Name = EventName
    
    name = models.CharField(max_length=64, choices=EventName.choices, db_index=True)
    role = models.CharField(max_length=10, choices=EventRole.choices, default=EventRole.SYSTEM)
    
    # Возвращаем ForeignKey, чтобы работали e.user и фильтры user=self.user
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    
    entity_type = models.CharField(max_length=32, null=True, blank=True)
    entity_id = models.BigIntegerField(null=True, blank=True)
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(default=timezone.now, db_index=True)
    
    class Meta:
        db_table = "events"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "created_at"], name="idx_events_user_time"),
            models.Index(fields=["name", "created_at"], name="idx_events_name_time"),
        ]
    
    def __str__(self):
        return f"[{self.role}] {self.name} @ {self.created_at:%Y-%m-%d %H:%M}"
