import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

from apps.documents.models import Teaser
from apps.startups.models import StartupProfile
from common.models import Country, InvestorType, DeclineReason



class InvestorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="investor_profile",
    )
    organization_name = models.CharField(max_length=200)
    
    # Используем классы напрямую, БЕЗ кавычек:
    investor_type = models.ForeignKey(
        InvestorType,
        on_delete=models.PROTECT,
        related_name="+",
    )
    country = models.ForeignKey(
        Country,
        on_delete=models.PROTECT,
        related_name="+",
    )
    contact_person_name = models.CharField(max_length=150)
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=40, blank=True, default="")
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "investor_profiles"
    
    def __str__(self):
        return self.organization_name



class MandateSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    CRITERION_SUGGESTION = "criterion_suggestion", "Accepted suggestion"


class Mandate(models.Model):
    investor_profile = models.ForeignKey(
        InvestorProfile,
        on_delete=models.PROTECT,
        related_name="mandates",
    )
    version = models.PositiveIntegerField(default=1)
    is_current = models.BooleanField(default=True)
    
    check_min_eur = models.DecimalField(max_digits=14, decimal_places=2)
    check_max_eur = models.DecimalField(max_digits=14, decimal_places=2)
    
    source = models.CharField(
        max_length=24,
        choices=MandateSource.choices,
        default=MandateSource.MANUAL,
    )
    
    # ЕСЛИ CriterionSuggestion еще нет в проекте — закомментируйте эту строку:
    # criterion_suggestion = ...
    # ЕСЛИ ОНА ЕСТЬ в другом приложении — укажите точный путь, например: "analytics.CriterionSuggestion"
    
    sector_codes = models.JSONField(default=list)
    stage_codes = models.JSONField(default=list)
    country_codes = models.JSONField(default=list)
    region_codes = models.JSONField(default=list, blank=True)
    business_model_codes = models.JSONField(default=list, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "mandates"
        ordering = ["-version"]
        constraints = [
            models.UniqueConstraint(
                fields=["investor_profile", "version"],
                name="uq_mandates_version",
            ),
            models.UniqueConstraint(
                fields=["investor_profile"],
                condition=Q(is_current=True),
                name="uq_mandates_single_current",
            ),
        ]
    
    def clean(self):
        super().clean()
        if self.check_min_eur and self.check_max_eur:
            if self.check_min_eur <= 0:
                raise ValidationError({"check_min_eur": "Минимальный чек должен быть больше 0."})
            if self.check_max_eur < self.check_min_eur:
                raise ValidationError({"check_max_eur": "Максимальный чек не может быть меньше минимального."})
        
        if not self.sector_codes:
            raise ValidationError({"sector_codes": "Выберите хотя бы один сектор."})
        if not self.stage_codes:
            raise ValidationError({"stage_codes": "Выберите хотя бы одну стадию."})
        if not self.country_codes:
            raise ValidationError({"country_codes": "Выберите хотя бы одну страну."})
        
        self.sector_codes = list(dict.fromkeys(self.sector_codes or []))
        self.stage_codes = list(dict.fromkeys(self.stage_codes or []))
        self.country_codes = list(dict.fromkeys(self.country_codes or []))
        self.region_codes = list(dict.fromkeys(self.region_codes or []))
        self.business_model_codes = list(dict.fromkeys(self.business_model_codes or []))
    
    def __str__(self):
        return f"{self.investor_profile.organization_name} (v{self.version})"

    
    
class CriterionSuggestion(models.Model):
    """Подсказка инвестору об изменении мандата на основе частых отказов (REQ-23)."""

    investor_profile = models.ForeignKey(
        InvestorProfile,
        on_delete=models.PROTECT,
        related_name="criterion_suggestions",
    )
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="criterion_suggestions",
    )
    decline_reason = models.ForeignKey(
        DeclineReason,
        on_delete=models.PROTECT,
        related_name="+",
    )
    # Например: "region", "stage", "ticket_size"
    criterion = models.CharField(max_length=32)
    decline_count = models.PositiveSmallIntegerField(default=1)

    shown_at = models.DateTimeField(default=timezone.now)
    accepted_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "criterion_suggestions"
        ordering = ["-shown_at"]
        indexes = [
            models.Index(fields=["investor_profile", "shown_at"], name="idx_crit_sugg_investor"),
        ]

    def clean(self):
        super().clean()
        if self.accepted_at and self.dismissed_at:
            raise ValidationError("Подсказка не может быть одновременно принята и отклонена.")

    def __str__(self):
        return f"Suggestion ({self.criterion}) for {self.investor_profile}"


# =====================================================================
# ЗНАКОМСТВО / ИНТРО (INTRODUCTION)
# =====================================================================

class IntroductionStatus(models.TextChoices):
    SUGGESTED = "SUGGESTED", "Suggested"  # Предложено в дайджесте
    INTERESTED = "INTERESTED", "Interested"  # Инвестор проявил интерес
    ACCEPTED = "ACCEPTED", "Accepted"  # Стартап подтвердил (Freigabe)
    INTRODUCED = "INTRODUCED", "Introduced"  # Контакты раскрыты
    DECLINED = "DECLINED", "Declined"  # Отклонено (инвестором или стартапом)
    EXPIRED = "EXPIRED", "Expired"  # Истек срок ожидания ответа


class IntroductionDeclinedBy(models.TextChoices):
    INVESTOR = "investor", "Investor"
    STARTUP = "startup", "Startup"


class Introduction(models.Model):
    """Знакомство инвестор × стартап; пайплайн статусов (BA-04)."""
    
    Status = IntroductionStatus
    DeclinedBy = IntroductionDeclinedBy
    
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    investor_profile = models.ForeignKey(
        InvestorProfile,
        on_delete=models.PROTECT,
        related_name="introductions",
    )
    startup_profile = models.ForeignKey(
        StartupProfile,
        on_delete=models.PROTECT,
        related_name="introductions",
    )
    teaser = models.ForeignKey(
        Teaser,
        on_delete=models.PROTECT,
        related_name="introductions",
    )
    mandate = models.ForeignKey(
        Mandate,
        on_delete=models.PROTECT,
        related_name="introductions",
        help_text="Версия мандата, на основе которой произошел матч",
    )
    
    status = models.CharField(
        max_length=12,
        choices=IntroductionStatus.choices,
        default=IntroductionStatus.SUGGESTED,
    )
    
    # Таймлайны воронки
    suggested_at = models.DateTimeField(default=timezone.now)
    interested_at = models.DateTimeField(null=True, blank=True)
    investor_message = models.CharField(max_length=500, null=True, blank=True)
    request_expires_at = models.DateTimeField(null=True, blank=True)
    
    startup_responded_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    introduced_at = models.DateTimeField(null=True, blank=True)
    
    # Отклонение / Истечение
    declined_at = models.DateTimeField(null=True, blank=True)
    declined_by = models.CharField(
        max_length=8,
        choices=IntroductionDeclinedBy.choices,
        null=True,
        blank=True,
    )
    decline_reason = models.ForeignKey(
        DeclineReason,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+",
    )
    expired_at = models.DateTimeField(null=True, blank=True)
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "introductions"
        constraints = [
            # Защита от дублей: пара инвестор-стартап создается один раз
            models.UniqueConstraint(
                fields=["investor_profile", "startup_profile"],
                name="uq_introductions_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["startup_profile", "status"], name="idx_intro_startup_status"),
            models.Index(fields=["investor_profile", "status"], name="idx_intro_investor_status"),
            models.Index(fields=["status", "request_expires_at"], name="idx_intro_expiry"),
        ]
    
    def __str__(self):
        return f"Intro: {self.investor_profile} x {self.startup_profile} [{self.status}]"


# =====================================================================
#  ДАЙДЖЕСТ (WEEKLY DIGEST)
# =====================================================================

class DigestChannel(models.TextChoices):
    EMAIL = "email", "E-mail"
    CABINET = "cabinet", "Cabinet"


class Digest(models.Model):
    """Еженедельный дайджест инвестора с подборкой стартапов (REQ-20)."""
    
    Channel = DigestChannel
    
    # Если у вас есть своя функция public_id_field(), можете использовать её
    public_id = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    
    investor_profile = models.ForeignKey(
        InvestorProfile,
        on_delete=models.PROTECT,
        related_name="digests",
    )
    period_start = models.DateField(help_text="Понедельник недели дайджеста")
    card_count = models.PositiveSmallIntegerField(default=0)
    
    generated_at = models.DateTimeField(default=timezone.now)
    sent_at = models.DateTimeField(null=True, blank=True)
    first_opened_at = models.DateTimeField(null=True, blank=True)
    first_open_channel = models.CharField(
        max_length=8,
        choices=DigestChannel.choices,
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "digests"
        ordering = ["-period_start"]
        constraints = [
            # Защита: только один дайджест для инвестора на конкретную неделю
            models.UniqueConstraint(
                fields=["investor_profile", "period_start"],
                name="uq_digests_week",
            ),
        ]
    
    def clean(self):
        super().clean()
        if self.card_count > 5:
            raise ValidationError({"card_count": "В дайджесте не может быть более 5 карточек."})
        if self.first_opened_at and not self.first_open_channel:
            raise ValidationError({"first_open_channel": "Укажите канал первого открытия."})
    
    def __str__(self):
        return f"Digest {self.investor_profile.organization_name} ({self.period_start})"


class DigestCard(models.Model):
    """Показ конкретной карточки стартапа в дайджесте (позиция, причины скоринга)."""
    
    digest = models.ForeignKey(
        Digest,
        on_delete=models.CASCADE,
        related_name="cards",
    )
    introduction = models.ForeignKey(
        Introduction,
        on_delete=models.PROTECT,
        related_name="cards",
    )
    position = models.PositiveSmallIntegerField(help_text="Позиция в дайджесте от 1 до 5")
    
    match_reason_codes = models.JSONField(
        default=list,
        help_text="Коды причин совпадения: sector, stage, region, check_size, business_model",
    )
    soft_match_count = models.PositiveSmallIntegerField(default=0)
    profile_age_days = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = "digest_cards"
        ordering = ["digest", "position"]
        constraints = [
            # В одном дайджесте позиция (1..5) уникальна
            models.UniqueConstraint(
                fields=["digest", "position"],
                name="uq_digest_cards_position",
            ),
            # Одно интро не может быть добавлено дважды в один дайджест
            models.UniqueConstraint(
                fields=["digest", "introduction"],
                name="uq_digest_cards_intro",
            ),
        ]
        indexes = [
            models.Index(fields=["introduction"], name="idx_digest_cards_intro"),
        ]
    
    def clean(self):
        super().clean()
        if not (1 <= self.position <= 5):
            raise ValidationError({"position": "Позиция карточки должна быть от 1 до 5."})
    
    def __str__(self):
        return f"DigestCard #{self.position} (Digest {self.digest_id})"

