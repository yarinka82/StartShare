import uuid

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from .choices import BusinessModel, Sector, Stage


def get_private_storage():
    """Deck files live outside MEDIA_ROOT and are never served directly."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def deck_upload_path(instance, filename):
    return f"decks/{uuid.uuid4().hex}.pdf"  # random name; original name stored in DB


class Dictionary(models.Model):
    """Base for list values kept in the DB (editable in Django admin). Only countries for now."""

    code = models.SlugField(max_length=40, unique=True)
    name = models.CharField(max_length=100)
    sort_order = models.PositiveSmallIntegerField(default=100)
    is_active = models.BooleanField(default=True)

    class Meta:
        abstract = True
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Country(Dictionary):
    class Meta(Dictionary.Meta):
        verbose_name_plural = "countries"


class StartupProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        LIVE = "LIVE", "Live"
        PAUSED = "PAUSED", "Paused"
        REMOVED = "REMOVED", "Removed"

    class GrowthPeriod(models.TextChoices):
        MOM = "mom", "Month over month"
        YOY = "yoy", "Year over year"

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="startup_profile"
    )
    # Internal only, never shown on the blind teaser. (Open question: keep this field?)
    company_name = models.CharField(max_length=200, blank=True)
    # Empty string = "not chosen yet": a DRAFT is saved field by field, so these cannot be required here.
    # Completeness is checked in the serializer (missing_fields).
    sector = models.CharField(max_length=40, choices=Sector.choices, blank=True, default="")
    stage = models.CharField(max_length=20, choices=Stage.choices, blank=True, default="")
    business_model = models.CharField(max_length=30, choices=BusinessModel.choices, blank=True, default="")
    country = models.ForeignKey(Country, null=True, blank=True, on_delete=models.PROTECT, related_name="+")
    amount_sought = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)  # EUR
    mrr = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)  # EUR
    growth_percent = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    growth_period = models.CharField(max_length=3, choices=GrowthPeriod.choices, blank=True)
    team_size = models.PositiveIntegerField(null=True, blank=True)
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Profile of {self.user_id} [{self.status}]"


class Deck(models.Model):
    class Status(models.TextChoices):
        PENDING = "pending", "Pending"  # reserved for async virus scan (ClamAV)
        OK = "ok", "OK"
        REJECTED = "rejected", "Rejected"

    profile = models.OneToOneField(StartupProfile, on_delete=models.CASCADE, related_name="deck")
    file = models.FileField(upload_to=deck_upload_path, storage=get_private_storage, max_length=255)
    original_name = models.CharField(max_length=255)
    size = models.PositiveIntegerField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
    uploaded_at = models.DateTimeField(auto_now=True)


@receiver(post_delete, sender=Deck)
def delete_deck_file(sender, instance, **kwargs):
    if instance.file:
        instance.file.delete(save=False)
