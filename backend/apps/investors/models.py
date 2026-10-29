
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils import timezone

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