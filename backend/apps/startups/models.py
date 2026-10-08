from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import  Q

from apps.accounts.models import created_at_field, updated_at_field
from common.models import Sector, Stage, Country, BusinessModel
from common.utils import public_id_field
from common.models import ReportType  # справочник типов нарушений


class StartupProfileStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    LIVE = "LIVE", "Live"
    PAUSED = "PAUSED", "Paused"
    REMOVED = "REMOVED", "Removed"



class StartupProfileRemovedBy(models.TextChoices):
    STARTUP = "startup", "Startup"
    SYSTEM = "system", "System (30 days)"
    STAFF = "staff", "Staff (reports)"



class StartupProfile(models.Model):
    """startup_profiles — публічний профіль стартапу (Blind Teaser)."""

    Status = StartupProfileStatus
    RemovedBy = StartupProfileRemovedBy

    public_id = public_id_field()
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="startup_profile",
    )
    status = models.CharField(
        max_length=8,
        choices=Status.choices,
        default=Status.DRAFT,
        db_default=Status.DRAFT,
    )

    # ДОВІДНИКИ (ForeignKeys)
    sector = models.ForeignKey(
        Sector,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="sector_code",
        related_name="+",
        db_index=False,
    )
    sector_other_text = models.CharField(max_length=100, null=True, blank=True)

    stage = models.ForeignKey(
        Stage,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="stage_code",
        related_name="+",
    )

    business_model = models.ForeignKey(
        BusinessModel,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="business_model_code",
        related_name="+",
    )
    business_model_other_text = models.CharField(max_length=100, null=True, blank=True)

    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="country_code",
        related_name="+",
    )

    # МЕТРИКИ ТА ФІНАНСИ
    round_amount_eur = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    mrr_eur = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    growth_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    team_size = models.SmallIntegerField(null=True, blank=True)

    # ЖИТТЄВИЙ ЦИКЛ ТА ТАЙМСТЕЙМПИ
    draft_expires_at = models.DateTimeField(null=True, blank=True)
    went_live_at = models.DateTimeField(null=True, blank=True)
    paused_at = models.DateTimeField(null=True, blank=True)
    removed_at = models.DateTimeField(null=True, blank=True)
    removed_by = models.CharField(max_length=8, choices=RemovedBy.choices, null=True, blank=True)
    moderation_hidden_at = models.DateTimeField(null=True, blank=True)

    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "startup_profiles"
        constraints = [
            models.CheckConstraint(
                condition=Q(status__in=StartupProfileStatus.values),
                name="chk_startup_profiles_status",
            ),
            models.CheckConstraint(
                condition=Q(sector_other_text__isnull=True) | Q(sector="other"),
                name="chk_startup_profiles_sector_other",
            ),
            models.CheckConstraint(
                condition=Q(business_model_other_text__isnull=True) | Q(business_model="other"),
                name="chk_startup_profiles_bm_other",
            ),
            models.CheckConstraint(
                condition=(Q(round_amount_eur__isnull=True) | Q(round_amount_eur__gt=0))
                & (Q(mrr_eur__isnull=True) | Q(mrr_eur__gte=0)),
                name="chk_startup_profiles_amounts",
            ),
            models.CheckConstraint(
                condition=Q(team_size__isnull=True) | Q(team_size__gte=1),
                name="chk_startup_profiles_team",
            ),
            # Валідація заповненості при переході в LIVE / PAUSED
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "REMOVED"])
                | Q(
                    sector__isnull=False,
                    stage__isnull=False,
                    business_model__isnull=False,
                    country__isnull=False,
                    round_amount_eur__isnull=False,
                    team_size__isnull=False,
                    went_live_at__isnull=False,
                ),
                name="chk_startup_profiles_live_complete",
            ),
            models.CheckConstraint(
                condition=~Q(status="PAUSED") | Q(paused_at__isnull=False),
                name="chk_startup_profiles_paused",
            ),
            models.CheckConstraint(
                condition=Q(status="REMOVED", removed_at__isnull=False, removed_by__isnull=False)
                | (~Q(status="REMOVED") & Q(removed_at__isnull=True, removed_by__isnull=True)),
                name="chk_startup_profiles_removed",
            ),
            models.CheckConstraint(
                condition=Q(removed_by__isnull=True) | Q(removed_by__in=StartupProfileRemovedBy.values),
                name="chk_startup_profiles_removed_by",
            ),
        ]
        indexes = [
            # Виправлено: прибрано 'region'
            models.Index(
                fields=["sector", "stage", "country"],
                name="idx_startup_matching",
                condition=Q(status="LIVE", moderation_hidden_at__isnull=True),
            ),
            models.Index(
                fields=["draft_expires_at"],
                name="idx_startup_draft_expiry",
                condition=Q(status="DRAFT"),
            ),
        ]

    def __str__(self):
        return f"Startup #{self.pk} ({self.status})"



class StartupPrivateDetails(models.Model):
    """startup_private_details — приватні контакти; віддаються ТІЛЬКИ після взаємного інтересу."""

    startup_profile = models.OneToOneField(
        StartupProfile,
        on_delete=models.CASCADE,
        primary_key=True,
        related_name="private_details",
    )
    company_name = models.CharField(max_length=200)
    contact_person_name = models.CharField(max_length=150)
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=40, null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "startup_private_details"

    def __str__(self):
        return f"Contacts for Startup #{self.startup_profile_id} ({self.company_name})"
    

class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_REVIEW = "IN_REVIEW", "In review"
    RESOLVED = "RESOLVED", "Resolved"


class ReportDecision(models.TextChoices):
    NO_ACTION = "no_action", "No action"
    PROFILE_HIDDEN = "profile_hidden", "Profile hidden"
    PROFILE_REMOVED = "profile_removed", "Profile removed"


class Report(models.Model):
    """Жалобы на профили («Melden», DSA ст. 16)."""

    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.PROTECT,
        related_name="reports",
    )
    reporter_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="reports_submitted",
    )
    report_type = models.ForeignKey(
        ReportType,
        on_delete=models.PROTECT,
        related_name="+",
    )
    description = models.TextField()

    status = models.CharField(
        max_length=12,
        choices=ReportStatus.choices,
        default=ReportStatus.OPEN,
    )
    decision = models.CharField(
        max_length=16,
        choices=ReportDecision.choices,
        null=True,
        blank=True,
    )
    decision_note = models.TextField(null=True, blank=True)

    decided_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="reports_decided",
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    reporter_notified_at = models.DateTimeField(null=True, blank=True)
    startup_notified_at = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "reports"
        ordering = ["-created_at"]
        constraints = [
            # Один пользователь не может спамить жалобами на один и тот же стартап
            models.UniqueConstraint(
                fields=["startup_profile", "reporter_user"],
                name="uq_reports_reporter",
            ),
        ]
        indexes = [
            models.Index(fields=["startup_profile", "status"], name="idx_reports_profile_status"),
            models.Index(fields=["status", "created_at"], name="idx_reports_status_created"),
        ]

    def clean(self):
        super().clean()
        if self.status == ReportStatus.RESOLVED and not self.decision:
            raise ValidationError({"decision": "Для закрытой жалобы должно быть указано решение."})

    def __str__(self):
        return f"Report #{self.id} on {self.startup_profile} ({self.status})"


