from django.db import models
from django.db.models import F, Q
from django.utils import timezone

from apps.accounts.models import Language, UserConsent, created_at_field, updated_at_field
from apps.startups.models import StartupProfile

from common.utils import deck_upload_path, get_private_storage


# ==========================================
# 1. PITCH DECK (МЕТАДАННЫЕ И ОБРАБОТКА ИИ)
# ==========================================

class PitchDeckDeletionReason(models.TextChoices):
    AUTO_24H = "auto_24h", "Auto after 24h"
    PROFILE_REMOVED = "profile_removed", "Profile removed"
    USER_REQUEST = "user_request", "User request"
    REPLACED = "replaced", "Replaced"
    PROCESSING_FAILED = "processing_failed", "Processing failed"


class PitchDeckProcessingState(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    PROCESSING = "PROCESSING", "Processing"
    DRAFT_READY = "DRAFT_READY", "Draft ready"
    FAILED = "FAILED", "Failed"


class PitchDeckFailureReason(models.TextChoices):
    PDF_UNREADABLE = "pdf_unreadable", "PDF unreadable"
    INVALID_RESPONSE = "invalid_response", "Invalid AI response"
    PROVIDER_UNAVAILABLE = "provider_unavailable", "Provider unavailable"
    OTHER = "other", "Other"


class PitchDeck(models.Model):
    """pitch_decks — метаданные PDF в хранилище ЕС и статус обработки ИИ."""
    
    DeletionReason = PitchDeckDeletionReason
    ProcessingState = PitchDeckProcessingState
    FailureReason = PitchDeckFailureReason
    
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.PROTECT,
        related_name="pitch_decks",
    )
    
    # Файл в приватном хранилище
    file = models.FileField(
        upload_to=deck_upload_path,
        storage=get_private_storage,
        max_length=500,
        null=True,
        blank=True,
    )
    storage_key = models.CharField(max_length=500, null=True, blank=True)
    original_name = models.CharField(max_length=255, default="deck.pdf")
    mime_type = models.CharField(max_length=100, default="application/pdf", db_default="application/pdf")
    file_size_bytes = models.BigIntegerField()
    page_count = models.IntegerField(null=True, blank=True)
    
    # Политика хранения и автоудаления через 24 часа
    keep_original = models.BooleanField(default=False, db_default=False)
    keep_confirmed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now)
    
    # Статус и телеметрия ИИ
    processing_state = models.CharField(
        max_length=12,
        choices=ProcessingState.choices,
        default=ProcessingState.QUEUED,
        db_default=ProcessingState.QUEUED,
    )
    attempt_count = models.SmallIntegerField(default=0, db_default=0)
    failure_reason = models.CharField(max_length=24, choices=FailureReason.choices, null=True, blank=True)
    ai_provider = models.CharField(max_length=50, null=True, blank=True)
    ai_model = models.CharField(max_length=100, null=True, blank=True)
    prompt_version = models.CharField(max_length=30, null=True, blank=True)
    input_tokens = models.IntegerField(null=True, blank=True)
    output_tokens = models.IntegerField(null=True, blank=True)
    ai_cost_eur = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    
    # Таймстемпы обработки и удаления
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_finished_at = models.DateTimeField(null=True, blank=True)
    delete_after = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_reason = models.CharField(max_length=20, choices=DeletionReason.choices, null=True, blank=True)
    
    created_at = created_at_field()
    
    class Meta:
        db_table = "pitch_decks"
        constraints = [
            models.CheckConstraint(
                condition=Q(mime_type="application/pdf"),
                name="chk_pitch_decks_mime",
            ),
            models.CheckConstraint(
                condition=Q(file_size_bytes__gt=0) & (Q(page_count__isnull=True) | Q(page_count__gt=0)),
                name="chk_pitch_decks_size",
            ),
            models.CheckConstraint(
                condition=~Q(keep_original=True) | Q(keep_confirmed_at__isnull=False),
                name="chk_pitch_decks_keep",
            ),
            models.CheckConstraint(
                condition=Q(deletion_reason__isnull=True) | Q(deletion_reason__in=PitchDeckDeletionReason.values),
                name="chk_pitch_decks_deletion_reason",
            ),
            models.CheckConstraint(
                condition=Q(processing_state__in=PitchDeckProcessingState.values),
                name="chk_pitch_decks_state",
            ),
            models.CheckConstraint(
                condition=~Q(processing_state="FAILED") | Q(failure_reason__isnull=False),
                name="chk_pitch_decks_failure",
            ),
            models.CheckConstraint(
                condition=Q(failure_reason__isnull=True) | Q(failure_reason__in=PitchDeckFailureReason.values),
                name="chk_pitch_decks_failure_reason",
            ),
            models.CheckConstraint(
                condition=~Q(processing_state__in=["DRAFT_READY", "FAILED"]) | Q(processing_finished_at__isnull=False),
                name="chk_pitch_decks_finished",
            ),
            models.CheckConstraint(
                condition=Q(attempt_count__gte=0)
                          & (Q(input_tokens__isnull=True) | Q(input_tokens__gte=0))
                          & (Q(output_tokens__isnull=True) | Q(output_tokens__gte=0))
                          & (Q(ai_cost_eur__isnull=True) | Q(ai_cost_eur__gte=0)),
                name="chk_pitch_decks_ai_numbers",
            ),
        ]
        indexes = [
            models.Index(fields=["startup_profile"], name="idx_pitch_decks_profile"),
            models.Index(
                fields=["delete_after"],
                name="idx_pitch_decks_delete_due",
                condition=Q(deleted_at__isnull=True, keep_original=False),
            ),
            models.Index(
                fields=["processing_state", "uploaded_at"],
                name="idx_pitch_decks_queue",
                condition=Q(processing_state__in=["QUEUED", "PROCESSING"]),
            ),
        ]
    
    def __str__(self):
        return f"PitchDeck #{self.pk} for Startup #{self.startup_profile_id} ({self.processing_state})"


# ==========================================
# 2. TEASER (ВЕРСИИ ТИЗЕРА)
# ==========================================

class TeaserStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Approved"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class Teaser(models.Model):
    """teasers — версии «слепого» тизера; утверждение вместе с декларацией A."""
    
    Status = TeaserStatus
    
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.PROTECT,
        related_name="teasers",
    )
    pitch_deck = models.OneToOneField(
        PitchDeck,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="teaser",
    )
    version = models.IntegerField(default=1)
    status = models.CharField(
        max_length=12,
        choices=Status.choices,
        default=Status.DRAFT,
        db_default=Status.DRAFT,
    )
    is_current = models.BooleanField(default=False, db_default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    declaration_consent = models.OneToOneField(
        UserConsent,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="approved_teaser",
    )
    created_at = created_at_field()
    updated_at = updated_at_field()
    
    class Meta:
        db_table = "teasers"
        constraints = [
            models.UniqueConstraint(fields=["startup_profile", "version"], name="uq_teasers_version"),
            models.CheckConstraint(condition=Q(status__in=TeaserStatus.values), name="chk_teasers_status"),
            models.CheckConstraint(condition=Q(version__gte=1), name="chk_teasers_version"),
            models.CheckConstraint(
                condition=Q(status="DRAFT", approved_at__isnull=True, declaration_consent__isnull=True)
                | Q(status="APPROVED", approved_at__isnull=False, declaration_consent__isnull=False)
                | Q(status="SUPERSEDED"),
                name="chk_teasers_approval",
            ),
            models.UniqueConstraint(
                fields=["startup_profile"],
                condition=Q(is_current=True),
                name="uq_teasers_current",
            ),
        ]
    
    def __str__(self):
        return f"Teaser v{self.version} for Startup #{self.startup_profile_id} [{self.status}]"


# ==========================================
# 3. TEASER FIELD (ТЕКСТОВЫЕ ПОЛЯ DE / EN)
# ==========================================

class TeaserFieldFieldName(models.TextChoices):
    HEADLINE = "headline", "Headline"
    PROBLEM = "problem", "Problem"
    SOLUTION = "solution", "Solution"
    MARKET = "market", "Market"
    TRACTION = "traction", "Traction"
    TEAM = "team", "Team"
    TEAM_DESCRIPTION = "team_description", "Team description"
    BUSINESS_DESCRIPTION = "business_description", "Business description"


class TeaserField(models.Model):
    """teaser_fields — отдельные текстовые блоки тизера на двух языках (DE / EN)."""
    
    FieldName = TeaserFieldFieldName
    
    teaser = models.ForeignKey(
        Teaser,
        on_delete=models.CASCADE,
        related_name="fields",
    )
    field_name = models.CharField(max_length=32, choices=FieldName.choices)
    language = models.CharField(max_length=2, choices=Language.choices, default=Language.DE)
    ai_text = models.TextField(null=True, blank=True)
    final_text = models.TextField(null=True, blank=True)
    is_edited = models.BooleanField(default=False, db_default=False)
    risk_phrases = models.JSONField(default=list, blank=True)
    approved_at = models.DateTimeField(null=True, blank=True)
    
    created_at = created_at_field()
    updated_at = updated_at_field()
    
    class Meta:
        db_table = "teaser_fields"
        constraints = [
            models.UniqueConstraint(fields=["teaser", "field_name", "language"], name="uq_teaser_fields"),
            models.CheckConstraint(
                condition=Q(field_name__in=TeaserFieldFieldName.values),
                name="chk_teaser_fields_name",
            ),
            models.CheckConstraint(condition=Q(language__in=["de", "en"]), name="chk_teaser_fields_language"),
            models.CheckConstraint(
                condition=Q(approved_at__isnull=True) | Q(final_text__isnull=False),
                name="chk_teaser_fields_approved",
            ),
        ]
    
    def __str__(self):
        return f"{self.field_name} ({self.language}) for Teaser #{self.teaser_id}"


# from django.db import models
# from django.db.models.signals import post_delete
# from django.dispatch import receiver
#
# from apps.startups.models import StartupProfile
# from common.utils import get_private_storage, deck_upload_path
#
#
#
# class Deck(models.Model):
#     class Status(models.TextChoices):
#         PENDING = "pending", "Pending"  # reserved for async virus scan (ClamAV)
#         OK = "ok", "OK"
#         REJECTED = "rejected", "Rejected"
#
#     profile = models.OneToOneField(StartupProfile, on_delete=models.CASCADE, related_name="deck")
#     file = models.FileField(upload_to=deck_upload_path, storage=get_private_storage, max_length=255)
#     original_name = models.CharField(max_length=255)
#     size = models.PositiveIntegerField()
#     status = models.CharField(max_length=10, choices=Status.choices, default=Status.OK)
#     uploaded_at = models.DateTimeField(auto_now=True)
#
#
# @receiver(post_delete, sender=Deck)
# def delete_deck_file(sender, instance, **kwargs):
#     if instance.file:
#         instance.file.delete(save=False)
#
#
#
# class TeaserJob(models.Model):
#     class State(models.TextChoices):
#         QUEUED = "QUEUED"
#         PROCESSING = "PROCESSING"
#         DRAFT_READY = "DRAFT_READY"
#         FAILED = "FAILED"
#
#     deck = models.OneToOneField("Deck", on_delete=models.CASCADE, related_name="job")
#     state = models.CharField(max_length=16, choices=State.choices, default=State.QUEUED)
#     attempts = models.PositiveSmallIntegerField(default=0)
#     draft = models.JSONField(null=True, blank=True)
#     risk_phrases = models.JSONField(default=list, blank=True)
#     cost_eur = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
#     processing_ms = models.PositiveIntegerField(null=True, blank=True)
#     error = models.TextField(blank=True)
#     created_at = models.DateTimeField(auto_now_add=True)
#     started_at = models.DateTimeField(null=True, blank=True)
#     ready_at = models.DateTimeField(null=True, blank=True)
#     original_deleted_at = models.DateTimeField(null=True, blank=True)  # когда удалён оригинал файла (REQ-16)
#
#
#
# class Teaser(models.Model):
#     """Рабочая версия тизера. TeaserJob.draft остаётся неизменным исходным выводом ШІ (для оценки качества)."""
#
#     class Status(models.TextChoices):
#         DRAFT = "DRAFT"
#         APPROVED = "APPROVED"
#
#     job = models.OneToOneField("TeaserJob", on_delete=models.CASCADE, related_name="teaser")
#     content = models.JSONField()  # {headline, problem, solution, market, traction, team}
#     risk_phrases = models.JSONField(default=list, blank=True)
#     reviewed = models.JSONField(default=list, blank=True)  # поля, подтверждённые вручную (REQ-14)
#     edited = models.JSONField(default=list, blank=True)  # поля, изменённые стартапом
#     status = models.CharField(max_length=10, choices=Status.choices, default=Status.DRAFT)
#     declaration_a_accepted_at = models.DateTimeField(null=True, blank=True)
#     approved_at = models.DateTimeField(null=True, blank=True)
#     updated_at = models.DateTimeField(auto_now=True)