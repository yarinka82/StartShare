from django.conf import settings
from django.db import models


class InvestorProfile(models.Model):
    class Meta:
        app_label = "investors"

    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="investor_profiles",
        null=True,
        blank=True,
    )
    name = models.CharField(max_length=255, blank=True, default="")
    organization_name = models.CharField(max_length=255, blank=True, default="")
    organization_type = models.CharField(max_length=64, blank=True, default="Fund")
    contact_name = models.CharField(max_length=255, blank=True, default="")
    contact_email = models.EmailField(blank=True, default="")
    contact_phone = models.CharField(max_length=32, blank=True, default="")
    is_professional = models.BooleanField(default=True)

    def __str__(self):
        return self.organization_name or self.name or f"Investor {self.pk}"
