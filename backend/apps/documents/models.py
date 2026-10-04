from django.db import models

from common.validators import validate_deck_file


class PitchDeck(models.Model):
    startup = models.OneToOneField("profiles.StartupProfile", on_delete=models.CASCADE)
    file = models.FileField(upload_to="decks/%Y/%m/", validators=[validate_deck_file], blank=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)


class TeaserJob(models.Model):
    class State(models.TextChoices):
        QUEUED = "QUEUED"
        PROCESSING = "PROCESSING"
        DRAFT_READY = "DRAFT_READY"
        FAILED = "FAILED"

    deck = models.OneToOneField("PitchDeck", on_delete=models.CASCADE, related_name="job")
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


class Teaser(models.Model):
    """Рабочая версия тизера. TeaserJob.draft остаётся неизменным исходным выводом ШІ (для оценки качества)."""

    class Status(models.TextChoices):
        DRAFT = "DRAFT"
        APPROVED = "APPROVED"

    job = models.OneToOneField("TeaserJob", on_delete=models.CASCADE, related_name="teaser")
    content = models.JSONField()                          # {headline, problem, solution, market, traction, team}
    risk_phrases = models.JSONField(default=list, blank=True)
    reviewed = models.JSONField(default=list, blank=True)  # поля, подтверждённые вручную (REQ-14)
    edited = models.JSONField(default=list, blank=True)    # поля, изменённые стартапом
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
    declaration_a_accepted_at = models.DateTimeField(null=True, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)