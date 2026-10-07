
from django.db import models
from django.db.models import Q


class ReferenceModel(models.Model):
    name_de = models.CharField(max_length=120)
    name_en = models.CharField(max_length=120)
    sort_order = models.SmallIntegerField(default=0, db_default=0)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        abstract = True
        ordering = ["sort_order", "name_de"]

    def __str__(self):
        return self.name_de



class Country(ReferenceModel):
    code = models.CharField(max_length=10, primary_key=True)

    class Meta(ReferenceModel.Meta):
        db_table = "countries"
        constraints = [
            models.CheckConstraint(
                condition=Q(code__regex=r"^[a-z]{2,10}$"),  # <--- виправлено
                name="chk_countries_code",
            )
        ]



class Region(ReferenceModel):
    """regions — географічний фокус інвестора (DACH, EU, Europe, Worldwide)."""

    code = models.CharField(max_length=32, primary_key=True)

    class Meta(ReferenceModel.Meta):
        db_table = "regions"
        
        

class Sector(ReferenceModel):
    """sectors — жорсткий фільтр; 20 значень (BA-02, списки значень)."""

    code = models.CharField(max_length=32, primary_key=True)
    is_other = models.BooleanField(default=False, db_default=False)

    class Meta(ReferenceModel.Meta):
        db_table = "sectors"
        constraints = [
            models.UniqueConstraint(fields=["is_other"], condition=Q(is_other=True), name="uq_sectors_other")
        ]


class Stage(ReferenceModel):
    """stages — жорсткий фільтр; 5 значень."""

    code = models.CharField(max_length=32, primary_key=True)

    class Meta(ReferenceModel.Meta):
        db_table = "stages"



class BusinessModel(ReferenceModel):
    """business_models — м'який критерій; 8 значень."""

    code = models.CharField(max_length=32, primary_key=True)
    is_other = models.BooleanField(default=False, db_default=False)

    class Meta(ReferenceModel.Meta):
        db_table = "business_models"
        constraints = [
            models.UniqueConstraint(fields=["is_other"], condition=Q(is_other=True), name="uq_business_models_other")
        ]



class InvestorType(ReferenceModel):
    """investor_types — фонд, business angel, family office."""

    code = models.CharField(max_length=32, primary_key=True)

    class Meta(ReferenceModel.Meta):
        db_table = "investor_types"



class DeclineReasonCriterion(models.TextChoices):
    SECTOR = "sector", "Sector"
    STAGE = "stage", "Stage"
    REGION = "region", "Region"
    CHECK_SIZE = "check_size", "Check size"



class DeclineReason(ReferenceModel):
    """decline_reasons — причини «Ні» інвестора; mandate_criterion — для пропозицій змінити критерій."""

    Criterion = DeclineReasonCriterion

    code = models.CharField(max_length=32, primary_key=True)
    mandate_criterion = models.CharField(max_length=16, choices=Criterion.choices, null=True, blank=True)

    class Meta(ReferenceModel.Meta):
        db_table = "decline_reasons"
        constraints = [
            models.CheckConstraint(
                condition=Q(mandate_criterion__isnull=True) | Q(mandate_criterion__in=DeclineReasonCriterion.values),
                name="chk_decline_reasons_criterion",
            )
        ]



class ReportType(ReferenceModel):
    """report_types — типи скарг «Melden» (список — Q-09)."""

    code = models.CharField(max_length=32, primary_key=True)

    class Meta(ReferenceModel.Meta):
        db_table = "report_types"



class RiskCategoryDetection(models.TextChoices):
    LLM = "llm", "LLM"
    REGEX = "regex", "Regex"
    IMAGE = "image", "Image"



class RiskCategoryAction(models.TextChoices):
    REMOVE = "remove", "Remove"
    GENERALIZE = "generalize", "Generalize"
    HIGHLIGHT = "highlight", "Highlight"



class RiskCategory(models.Model):
    """risk_categories — 19 категорій ризикових фраз (BA-AI-risk-phrases)."""

    Detection = RiskCategoryDetection
    Action = RiskCategoryAction

    code = models.CharField(max_length=3, primary_key=True)
    name_de = models.CharField(max_length=120)
    name_en = models.CharField(max_length=120)
    detection = models.CharField(max_length=8, choices=Detection.choices)
    action = models.CharField(max_length=12, choices=Action.choices)
    regex_pattern = models.TextField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_default=True)

    class Meta:
        db_table = "risk_categories"
        ordering = ["code"]
        constraints = [
            models.CheckConstraint(condition=Q(code__regex=r"^R[0-9]{2}$"), name="chk_risk_categories_code"),
            models.CheckConstraint(
                condition=Q(detection__in=RiskCategoryDetection.values), name="chk_risk_categories_detection"
            ),
            models.CheckConstraint(
                condition=Q(action__in=RiskCategoryAction.values), name="chk_risk_categories_action"
            ),
            models.CheckConstraint(
                condition=~Q(detection="regex") | Q(regex_pattern__isnull=False), name="chk_risk_categories_regex"
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.name_de}"
