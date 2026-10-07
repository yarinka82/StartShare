from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver

from apps.startups.models import StartupProfile
from common.utils import get_private_storage, deck_upload_path



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



class TeaserJob(models.Model):
    class State(models.TextChoices):
        QUEUED = "QUEUED"
        PROCESSING = "PROCESSING"
        DRAFT_READY = "DRAFT_READY"
        FAILED = "FAILED"
    
    deck = models.OneToOneField("Deck", on_delete=models.CASCADE, related_name="job")
    state = models.CharField(max_length=16, choices=State.choices, default=State.QUEUED)
    attempts = models.PositiveSmallIntegerField(default=0)
    draft = models.JSONField(null=True, blank=True)
    risk_phrases = models.JSONField(default=list, blank=True)
    cost_eur = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    processing_ms = models.PositiveIntegerField(null=True, blank=True)
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    original_deleted_at = models.DateTimeField(null=True, blank=True)  # когда удалён оригинал файла (REQ-16)



class Teaser(models.Model):
    """Рабочая версия тизера. TeaserJob.draft остаётся неизменным исходным выводом ШІ (для оценки качества)."""
    
    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        APPROVED = "APPROVED"
    
    job = models.OneToOneField("TeaserJob", on_delete=models.CASCADE, related_name="teaser")
    content = models.JSONField()  # {headline, problem, solution, market, traction, team}
    risk_phrases = models.JSONField(default=list, blank=True)
    reviewed = models.JSONField(default=list, blank=True)  # поля, подтверждённые вручную (REQ-14)
    edited = models.JSONField(default=list, blank=True)  # поля, изменённые стартапом
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    declaration_a_accepted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)