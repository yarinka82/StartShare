from django.conf import settings
from django.db import models



class EventName(models.TextChoices):
    """Events from the ТЗ table "Які події логувати". Only events that the code actually emits are listed."""

    REGISTERED = "registered", "Registered"
    STATUS_CONFIRMED = "status_confirmed", "Investor confirmed professional status (text C)"
    MANDATE_SAVED = "mandate_saved", "Investor saved the mandate for the first time"
    MANDATE_CHANGED = "mandate_changed", "Investor changed the mandate"
    DECK_UPLOADED = "deck_uploaded", "Startup uploaded a pitch deck"
    AI_DRAFT_CREATED = "ai_draft_created", "AI finished the teaser draft"
    FIELD_EDITED = "field_edited", "Teaser Field Edited"
    TEASER_APPROVED = "teaser_approved", "Teaser Approved"
    WENT_LIVE = "went_live", "Went live"



class Event(models.Model):
    name = models.CharField(max_length=50, choices=EventName.choices, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="+")
    properties = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.name} @ {self.created_at:%Y-%m-%d %H:%M}"
