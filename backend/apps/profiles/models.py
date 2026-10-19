from django.conf import settings
from django.db import models


class StartupProfile(models.Model):
    class Meta:
        app_label = "profiles"

    STATUS_DRAFT = "DRAFT"
    STATUS_LIVE = "LIVE"
    STATUS_PAUSED = "PAUSED"
    STATUS_REMOVED = "REMOVED"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_LIVE, "Live"),
        (STATUS_PAUSED, "Paused"),
        (STATUS_REMOVED, "Removed"),
    ]

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="startup_profiles",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, blank=True, default="")
    company_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_name = models.CharField(max_length=255, blank=True, default="")
    profile_status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_DRAFT)
    is_live = models.BooleanField(default=False)

    def __str__(self):
        return self.company_name or self.name or f"Startup {self.pk}"
