"""
Start Share — Django-моделі бази даних (MVP).

Відповідають startshare_schema_postgres.sql (еталонна DDL) і описам таблиць у docs/. Версія: 2026-10-05.

Вимоги: Django 5.2+, PostgreSQL 16+ (ArrayField, JSONField/JSONB, BrinIndex, RandomUUID).

Що НЕ створюють ці моделі і що треба додати міграцією migrations.RunSQL (розділи з позначкою
[Django: міграція RunSQL] у startshare_schema_postgres.sql):
  * секціоновану таблицю events (модель Event має managed = False), секцію events_default і функції
    ensure_event_partitions(), purge_expired_data(), get_param_int();
  * тригер set_updated_at() для оновлення updated_at при змінах в обхід ORM;
  * тригери машин станів trg_startup_profiles_status і trg_introductions_status (BA-04);
  * тригери-перевірки trg_mandates_codes (коди в масивах мандату), trg_teaser_fields_risk_phrases
    (структура ризикових фраз), trg_subscriptions_plan (тариф відповідає ролі; платна підписка має
    спосіб оплати й реквізити), trg_subscription_payments_immutable (рахунок не змінюється й не видаляється);
  * початкові дані довідників, способів оплати, безкоштовних тарифів і параметрів — або data migration;
  * аналітичний шар — розділ «Аналітичний шар (схема analytics)» того ж файлу.

Щоночі (Celery beat / cron через management command):
  SELECT ensure_event_partitions(); SELECT * FROM purge_expired_data();
  SELECT * FROM analytics.refresh_all(); SELECT analytics.take_daily_snapshot();

Правила, що не виражаються обмеженнями БД (перевіряє сервісний шар):
  * роль користувача відповідає профілю (startup → StartupProfile, investor → InvestorProfile);
  * DRAFT → LIVE лише з чинним затвердженим тизером;
  * контакти стартапу читаються для інвестора лише в статусах ACCEPTED / INTRODUCED.
  * кожен перехід статусу знайомства пишеться подією status_changed в events (окремої таблиці історії немає);
  * опитування 14/30 днів — подія survey_answered в events (одна відповідь на опитування на користувача);
  * підписка не впливає на матчинг і порядок карток;
  * стартова фаза безкоштовна: новий користувач отримує підписку free_launch_<роль>; після підключення оплати
    (параметри billing_enabled, free_period_ends_at) безкоштовні підписки завершуються з end_reason free_period_ended;
  * ставку ПДВ і reverse charge для рахунку визначає сервіс оплати (параметр vat_rate_de_pct, DB-15);
  * обраний спосіб оплати має бути активним (payment_methods.is_active).
"""

import uuid

from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.contrib.postgres.fields import ArrayField
from django.contrib.postgres.functions import RandomUUID
from django.contrib.postgres.indexes import BrinIndex, GinIndex
from django.db import models
from django.db.models import F, Func, Q, Value
from django.db.models.functions import Coalesce, Left, Lower, Now
from django.db.models.lookups import Exact
from django.utils import timezone

# =====================================================================
# Спільні допоміжні поля
# =====================================================================


def created_at_field():
    return models.DateTimeField(default=timezone.now, db_default=Now(), editable=False)


def updated_at_field():
    return models.DateTimeField(auto_now=True, db_default=Now())


def public_id_field():
    return models.UUIDField(default=uuid.uuid4, db_default=RandomUUID(), unique=True, editable=False)


def iff(a: Q, b: Q) -> Q:
    """a ⇔ b: умова a виконується тоді й лише тоді, коли виконується b."""
    return (a & b) | (~a & ~b)


class Language(models.TextChoices):
    DE = "de", "Deutsch"
    EN = "en", "English"


class InterfaceLanguage(models.TextChoices):
    DE = "de", "Deutsch"
    EN = "en", "English"
    UK = "uk", "Українська"  # лише інтерфейс (переклад бекенду); контент БД — DE/EN (DB-03)


# =====================================================================
# Користувачі та юридичні згоди
# =====================================================================


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, **extra):
        if not email:
            raise ValueError("E-mail is required")
        user = self.model(email=self.normalize_email(email).lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(role=User.Role.STAFF, is_staff=True, is_superuser=True)
        return self._create_user(email, password, **extra)


class UserRole(models.TextChoices):
    STARTUP = "startup", "Startup"
    INVESTOR = "investor", "Investor"
    STAFF = "staff", "Staff"


class User(AbstractBaseUser, PermissionsMixin):
    """users — акаунт: стартап, інвестор або співробітник платформи."""

    Role = UserRole

    email = models.EmailField(max_length=254, unique=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    preferred_language = models.CharField(
        max_length=2, choices=InterfaceLanguage.choices, default=InterfaceLanguage.DE, db_default=InterfaceLanguage.DE
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True, db_default=True)
    is_staff = models.BooleanField(default=False, db_default=False)
    is_superuser = models.BooleanField(default=False, db_default=False)
    is_test = models.BooleanField(default=False, db_default=False)
    created_at = created_at_field()
    updated_at = updated_at_field()
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        db_table = "users"
        constraints = [
            models.CheckConstraint(condition=Q(Exact(F("email"), Lower("email"))), name="chk_users_email_lower"),
            models.CheckConstraint(condition=Q(role__in=["startup", "investor", "staff"]), name="chk_users_role"),
            models.CheckConstraint(condition=Q(preferred_language__in=["de", "en", "uk"]), name="chk_users_language"),
            models.CheckConstraint(condition=Q(is_staff=False) | Q(role="staff"), name="chk_users_staff_role"),
            models.CheckConstraint(
                condition=Q(deleted_at__isnull=True) | Q(is_active=False), name="chk_users_deleted_inactive"
            ),
        ]
        indexes = [models.Index(fields=["role", "created_at"], name="idx_users_role_created")]

    def __str__(self):
        return f"{self.email} ({self.role})"


class LegalDocumentCode(models.TextChoices):
    A = "A", "A — Erklärung des Startups"
    B = "B", "B — Hinweis auf dem Teaser"
    C = "C", "C — Bestätigung Investor"
    D = "D", "D — Anfrage an das Startup"
    E = "E", "E — Signatur Intro-E-Mail"
    F = "F", "F — Auswahlkriterien"
    G = "G", "G — Hinweis KI"
    AGB = "AGB", "AGB"
    DSE = "DSE", "Datenschutzerklärung"


class LegalDocument(models.Model):
    """legal_documents — версії юридичних текстів A–G, AGB, Datenschutzerklärung."""

    Code = LegalDocumentCode

    code = models.CharField(max_length=8, choices=Code.choices)
    language = models.CharField(max_length=2, choices=Language.choices)
    version = models.IntegerField()
    title = models.CharField(max_length=200)
    body = models.TextField()
    legal_approved_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = created_at_field()

    class Meta:
        db_table = "legal_documents"
        constraints = [
            models.CheckConstraint(condition=Q(code__in=LegalDocumentCode.values), name="chk_legal_documents_code"),
            models.CheckConstraint(condition=Q(language__in=["de", "en"]), name="chk_legal_documents_language"),
            models.CheckConstraint(condition=Q(version__gte=1), name="chk_legal_documents_version"),
            models.CheckConstraint(
                condition=Q(valid_from__isnull=True) | Q(legal_approved_at__isnull=False),
                name="chk_legal_documents_publish",
            ),
            models.CheckConstraint(
                condition=Q(valid_to__isnull=True) | Q(valid_to__gt=F("valid_from")), name="chk_legal_documents_period"
            ),
            models.UniqueConstraint(fields=["code", "language", "version"], name="uq_legal_documents_version"),
            models.UniqueConstraint(
                fields=["code", "language"],
                condition=Q(valid_from__isnull=False, valid_to__isnull=True),
                name="uq_legal_documents_current",
            ),
        ]

    def __str__(self):
        return f"{self.code} {self.language} v{self.version}"


class UserConsentContext(models.TextChoices):
    REGISTRATION = "registration", "Registration (AGB, DSE)"
    TEASER_APPROVAL = "teaser_approval", "Teaser approval (A)"
    INVESTOR_STATUS = "investor_status", "Investor status (C)"


class UserConsent(models.Model):
    """user_consents — яку редакцію тексту і в якому контексті прийняв користувач (append-only)."""

    Context = UserConsentContext

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="consents", db_index=False)
    legal_document = models.ForeignKey(LegalDocument, on_delete=models.PROTECT, related_name="consents")
    context = models.CharField(max_length=24, choices=Context.choices)
    accepted_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "user_consents"
        constraints = [
            models.CheckConstraint(condition=Q(context__in=UserConsentContext.values), name="chk_user_consents_context")
        ]
        indexes = [models.Index(fields=["user", "context"], name="idx_user_consents_user")]


# =====================================================================
# Довідники (код — стабільний ключ для матчингу, подій і аналітики)
# =====================================================================


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
    """countries — 27 країн ЄС (ISO 3166-1 alpha-2)."""

    code = models.CharField(max_length=2, primary_key=True)

    class Meta(ReferenceModel.Meta):
        db_table = "countries"
        constraints = [models.CheckConstraint(condition=Q(code__regex=r"^[A-Z]{2}$"), name="chk_countries_code")]


class Region(ReferenceModel):
    """regions — федеральні землі Німеччини (ISO 3166-2, DE-BY)."""

    code = models.CharField(max_length=6, primary_key=True)
    country = models.ForeignKey(Country, on_delete=models.PROTECT, db_column="country_code", related_name="regions")

    class Meta(ReferenceModel.Meta):
        db_table = "regions"
        constraints = [
            models.CheckConstraint(condition=Q(Exact(Left("code", 2), F("country"))), name="chk_regions_code_country")
        ]


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


# =====================================================================
# Стартап
# =====================================================================


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
    """startup_profiles — профіль стартапу; статуси DRAFT → LIVE → PAUSED / REMOVED (BA-04)."""

    Status = StartupProfileStatus
    RemovedBy = StartupProfileRemovedBy

    public_id = public_id_field()
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="startup_profile")
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.DRAFT, db_default=Status.DRAFT)
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
        Stage, on_delete=models.PROTECT, null=True, blank=True, db_column="stage_code", related_name="+"
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
        Country, on_delete=models.PROTECT, null=True, blank=True, db_column="country_code", related_name="+"
    )
    region = models.ForeignKey(
        Region, on_delete=models.PROTECT, null=True, blank=True, db_column="region_code", related_name="+"
    )
    round_amount_eur = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    mrr_eur = models.DecimalField(max_digits=14, decimal_places=2, null=True, blank=True)
    growth_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    team_size = models.SmallIntegerField(null=True, blank=True)
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
                condition=Q(status__in=StartupProfileStatus.values), name="chk_startup_profiles_status"
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
                condition=Q(region__isnull=True) | Q(Exact(Left("region", 2), F("country"))),
                name="chk_startup_profiles_region_country",
            ),
            models.CheckConstraint(
                condition=(Q(round_amount_eur__isnull=True) | Q(round_amount_eur__gt=0))
                & (Q(mrr_eur__isnull=True) | Q(mrr_eur__gte=0)),
                name="chk_startup_profiles_amounts",
            ),
            models.CheckConstraint(
                condition=Q(team_size__isnull=True) | Q(team_size__gte=1), name="chk_startup_profiles_team"
            ),
            models.CheckConstraint(
                condition=Q(status__in=["DRAFT", "REMOVED"])
                | (
                    Q(
                        sector__isnull=False,
                        stage__isnull=False,
                        business_model__isnull=False,
                        country__isnull=False,
                        round_amount_eur__isnull=False,
                        team_size__isnull=False,
                        went_live_at__isnull=False,
                    )
                    & (~Q(country="DE") | Q(region__isnull=False))
                ),
                name="chk_startup_profiles_live_complete",
            ),
            models.CheckConstraint(
                condition=iff(Q(status="PAUSED"), Q(paused_at__isnull=False)), name="chk_startup_profiles_paused"
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
            models.Index(
                fields=["sector", "stage", "country", "region"],
                name="idx_startup_matching",
                condition=Q(status="LIVE", moderation_hidden_at__isnull=True),
            ),
            models.Index(fields=["draft_expires_at"], name="idx_startup_draft_expiry", condition=Q(status="DRAFT")),
        ]

    def __str__(self):
        return f"Startup #{self.pk} ({self.status})"


class StartupPrivateDetails(models.Model):
    """startup_private_details — назва і контакти; розкриваються лише після Freigabe."""

    startup_profile = models.OneToOneField(
        StartupProfile, on_delete=models.CASCADE, primary_key=True, related_name="private_details"
    )
    company_name = models.CharField(max_length=200)
    contact_person_name = models.CharField(max_length=150)
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=40, null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "startup_private_details"


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
    """pitch_decks — метадані PDF у сховищі ЄС і стан його обробки ШІ (BA-AI-02); видалення через 24 год,
    якщо стартап не залишив дек. Один дек = одна обробка; текст деку і відповідь ШІ не зберігаються."""

    DeletionReason = PitchDeckDeletionReason
    ProcessingState = PitchDeckProcessingState
    FailureReason = PitchDeckFailureReason

    startup_profile = models.ForeignKey(
        StartupProfile, on_delete=models.PROTECT, related_name="pitch_decks", db_index=False
    )
    storage_key = models.CharField(max_length=500, null=True, blank=True)
    mime_type = models.CharField(max_length=100, default="application/pdf", db_default="application/pdf")
    file_size_bytes = models.BigIntegerField()
    page_count = models.IntegerField(null=True, blank=True)
    keep_original = models.BooleanField(default=False, db_default=False)
    keep_confirmed_at = models.DateTimeField(null=True, blank=True)
    uploaded_at = models.DateTimeField(default=timezone.now, db_default=Now())
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
    processing_started_at = models.DateTimeField(null=True, blank=True)
    processing_finished_at = models.DateTimeField(null=True, blank=True)
    delete_after = models.DateTimeField(null=True, blank=True)
    deleted_at = models.DateTimeField(null=True, blank=True)
    deletion_reason = models.CharField(max_length=20, choices=DeletionReason.choices, null=True, blank=True)
    created_at = created_at_field()

    class Meta:
        db_table = "pitch_decks"
        constraints = [
            models.CheckConstraint(condition=Q(mime_type="application/pdf"), name="chk_pitch_decks_mime"),
            models.CheckConstraint(
                condition=Q(file_size_bytes__gt=0) & (Q(page_count__isnull=True) | Q(page_count__gt=0)),
                name="chk_pitch_decks_size",
            ),
            models.CheckConstraint(
                condition=iff(Q(keep_original=True), Q(keep_confirmed_at__isnull=False)), name="chk_pitch_decks_keep"
            ),
            models.CheckConstraint(
                condition=Q(deleted_at__isnull=True, deletion_reason__isnull=True, storage_key__isnull=False)
                | Q(deleted_at__isnull=False, deletion_reason__isnull=False, storage_key__isnull=True),
                name="chk_pitch_decks_deleted",
            ),
            models.CheckConstraint(
                condition=Q(deletion_reason__isnull=True) | Q(deletion_reason__in=PitchDeckDeletionReason.values),
                name="chk_pitch_decks_deletion_reason",
            ),
            models.CheckConstraint(
                condition=Q(processing_state__in=PitchDeckProcessingState.values), name="chk_pitch_decks_state"
            ),
            models.CheckConstraint(
                condition=iff(Q(processing_state="FAILED"), Q(failure_reason__isnull=False)),
                name="chk_pitch_decks_failure",
            ),
            models.CheckConstraint(
                condition=Q(failure_reason__isnull=True) | Q(failure_reason__in=PitchDeckFailureReason.values),
                name="chk_pitch_decks_failure_reason",
            ),
            models.CheckConstraint(
                condition=iff(
                    Q(processing_state__in=["DRAFT_READY", "FAILED"]), Q(processing_finished_at__isnull=False)
                ),
                name="chk_pitch_decks_finished",
            ),
            models.CheckConstraint(
                condition=Q(attempt_count__gte=0)
                & (Q(input_tokens__isnull=True) | Q(input_tokens__gte=0))
                & (Q(output_tokens__isnull=True) | Q(output_tokens__gte=0))
                & (Q(ai_cost_eur__isnull=True) | Q(ai_cost_eur__gte=0)),
                name="chk_pitch_decks_ai_numbers",
            ),
            models.CheckConstraint(
                condition=(Q(processing_started_at__isnull=True) | Q(processing_started_at__gte=F("uploaded_at")))
                & (
                    Q(processing_finished_at__isnull=True)
                    | Q(processing_started_at__isnull=True)
                    | Q(processing_finished_at__gte=F("processing_started_at"))
                ),
                name="chk_pitch_decks_times",
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


class TeaserStatus(models.TextChoices):
    DRAFT = "DRAFT", "Draft"
    APPROVED = "APPROVED", "Approved"
    SUPERSEDED = "SUPERSEDED", "Superseded"


class Teaser(models.Model):
    """teasers — версії «сліпого» тизера; затвердження разом із декларацією A."""

    Status = TeaserStatus

    startup_profile = models.ForeignKey(
        StartupProfile, on_delete=models.PROTECT, related_name="teasers", db_index=False
    )
    pitch_deck = models.OneToOneField(PitchDeck, on_delete=models.PROTECT, null=True, blank=True, related_name="teaser")
    version = models.IntegerField()
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT, db_default=Status.DRAFT)
    is_current = models.BooleanField(default=False, db_default=False)
    approved_at = models.DateTimeField(null=True, blank=True)
    declaration_consent = models.OneToOneField(
        UserConsent, on_delete=models.PROTECT, null=True, blank=True, related_name="approved_teaser"
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
                | (~Q(status="DRAFT") & Q(approved_at__isnull=False, declaration_consent__isnull=False)),
                name="chk_teasers_approval",
            ),
            models.UniqueConstraint(
                fields=["startup_profile"], condition=Q(is_current=True), name="uq_teasers_current"
            ),
        ]


class TeaserFieldFieldName(models.TextChoices):
    TEAM_DESCRIPTION = "team_description", "Team description"
    BUSINESS_DESCRIPTION = "business_description", "Business description"


class TeaserField(models.Model):
    """teaser_fields — текстові поля тизера окремо для DE і EN; затвердження кожного поля (REQ-14)."""

    FieldName = TeaserFieldFieldName

    teaser = models.ForeignKey(Teaser, on_delete=models.CASCADE, related_name="fields", db_index=False)
    field_name = models.CharField(max_length=32, choices=FieldName.choices)
    language = models.CharField(max_length=2, choices=Language.choices)
    ai_text = models.TextField(null=True, blank=True)
    final_text = models.TextField(null=True, blank=True)
    is_edited = models.BooleanField(default=False, db_default=False)
    # [{"category": "R09", "source": "llm", "fragment": ..., "reason": ..., "resolution": ..., "resolved_at": ...}]
    # Структуру й коди категорій перевіряє тригер trg_teaser_fields_risk_phrases; fragment і reason
    # видаляються після затвердження тизера.
    risk_phrases = models.JSONField(default=list, db_default=Value([], output_field=models.JSONField()))
    approved_at = models.DateTimeField(null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "teaser_fields"
        constraints = [
            models.UniqueConstraint(fields=["teaser", "field_name", "language"], name="uq_teaser_fields"),
            models.CheckConstraint(
                condition=Q(field_name__in=TeaserFieldFieldName.values), name="chk_teaser_fields_name"
            ),
            models.CheckConstraint(condition=Q(language__in=["de", "en"]), name="chk_teaser_fields_language"),
            models.CheckConstraint(
                condition=Q(approved_at__isnull=True) | Q(final_text__isnull=False), name="chk_teaser_fields_approved"
            ),
            models.CheckConstraint(
                condition=Q(
                    Exact(Func(F("risk_phrases"), function="jsonb_typeof", output_field=models.CharField()), "array")
                ),
                name="chk_teaser_fields_risk_array",
            ),
        ]


# =====================================================================
# Інвестор і мандат
# =====================================================================


class InvestorProfile(models.Model):
    """investor_profiles — професійний інвестор; назва і тип показуються стартапу в запиті."""

    public_id = public_id_field()
    user = models.OneToOneField(User, on_delete=models.PROTECT, related_name="investor_profile")
    organization_name = models.CharField(max_length=200)
    investor_type = models.ForeignKey(
        InvestorType, on_delete=models.PROTECT, db_column="investor_type_code", related_name="+"
    )
    country = models.ForeignKey(Country, on_delete=models.PROTECT, db_column="country_code", related_name="+")
    contact_person_name = models.CharField(max_length=150)
    contact_email = models.EmailField(max_length=254)
    contact_phone = models.CharField(max_length=40, null=True, blank=True)
    status_consent = models.OneToOneField(
        UserConsent, on_delete=models.PROTECT, null=True, blank=True, related_name="investor_profile"
    )
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "investor_profiles"

    def __str__(self):
        return self.organization_name


class MandateSource(models.TextChoices):
    MANUAL = "manual", "Manual"
    CRITERION_SUGGESTION = "criterion_suggestion", "Accepted criterion suggestion"


class Mandate(models.Model):
    """mandates — незмінні версії мандату (REQ-19); чинна — одна на інвестора."""

    Source = MandateSource

    investor_profile = models.ForeignKey(
        InvestorProfile, on_delete=models.PROTECT, related_name="mandates", db_index=False
    )
    version = models.IntegerField()
    is_current = models.BooleanField(default=True, db_default=True)
    check_min_eur = models.DecimalField(max_digits=14, decimal_places=2)
    check_max_eur = models.DecimalField(max_digits=14, decimal_places=2)
    source = models.CharField(max_length=24, choices=Source.choices, default=Source.MANUAL, db_default=Source.MANUAL)
    criterion_suggestion = models.OneToOneField(
        "CriterionSuggestion", on_delete=models.PROTECT, null=True, blank=True, related_name="resulting_mandate"
    )
    created_at = created_at_field()

    # Багатозначні критерії — масиви кодів довідників (рішення 05.10.2026). Існування кодів і відсутність дублів
    # перевіряє тригер trg_mandates_codes (FK на елементи масиву в PostgreSQL неможливі).
    sector_codes = ArrayField(models.CharField(max_length=32))
    stage_codes = ArrayField(models.CharField(max_length=32))
    country_codes = ArrayField(models.CharField(max_length=2))
    region_codes = ArrayField(
        models.CharField(max_length=6),
        default=list,
        db_default=Value([], output_field=ArrayField(models.CharField(max_length=6))),
    )
    business_model_codes = ArrayField(
        models.CharField(max_length=32),
        default=list,
        db_default=Value([], output_field=ArrayField(models.CharField(max_length=32))),
    )

    class Meta:
        db_table = "mandates"
        constraints = [
            models.UniqueConstraint(fields=["investor_profile", "version"], name="uq_mandates_version"),
            models.CheckConstraint(condition=Q(version__gte=1), name="chk_mandates_version"),
            models.CheckConstraint(
                condition=Q(check_min_eur__gt=0) & Q(check_max_eur__gte=F("check_min_eur")), name="chk_mandates_check"
            ),
            models.CheckConstraint(condition=Q(source__in=MandateSource.values), name="chk_mandates_source"),
            models.CheckConstraint(
                condition=iff(Q(source="criterion_suggestion"), Q(criterion_suggestion__isnull=False)),
                name="chk_mandates_suggestion",
            ),
            models.UniqueConstraint(
                fields=["investor_profile"], condition=Q(is_current=True), name="uq_mandates_current"
            ),
            models.CheckConstraint(
                condition=Q(sector_codes__len__gte=1, stage_codes__len__gte=1, country_codes__len__gte=1),
                name="chk_mandates_hard_filters",
            ),
            models.CheckConstraint(
                condition=Q(region_codes__len=0) | Q(country_codes__contains=["DE"]), name="chk_mandates_regions_de"
            ),
        ]
        indexes = [
            GinIndex(fields=["sector_codes"], name="gin_mandates_sectors"),
            GinIndex(fields=["stage_codes"], name="gin_mandates_stages"),
            GinIndex(fields=["country_codes"], name="gin_mandates_countries"),
            GinIndex(fields=["region_codes"], name="gin_mandates_regions"),
        ]


# =====================================================================
# Матчинг, дайджест і знайомство
# =====================================================================


class DigestChannel(models.TextChoices):
    EMAIL = "email", "E-mail"
    CABINET = "cabinet", "Cabinet"


class Digest(models.Model):
    """digests — щотижневий дайджест інвестора (REQ-20)."""

    Channel = DigestChannel

    public_id = public_id_field()
    investor_profile = models.ForeignKey(
        InvestorProfile, on_delete=models.PROTECT, related_name="digests", db_index=False
    )
    period_start = models.DateField()
    card_count = models.SmallIntegerField()
    generated_at = models.DateTimeField(default=timezone.now, db_default=Now())
    sent_at = models.DateTimeField(null=True, blank=True)
    first_opened_at = models.DateTimeField(null=True, blank=True)
    first_open_channel = models.CharField(max_length=8, choices=Channel.choices, null=True, blank=True)
    created_at = created_at_field()

    class Meta:
        db_table = "digests"
        constraints = [
            models.UniqueConstraint(fields=["investor_profile", "period_start"], name="uq_digests_week"),
            models.CheckConstraint(condition=Q(period_start__iso_week_day=1), name="chk_digests_monday"),
            models.CheckConstraint(condition=Q(card_count__gte=0, card_count__lte=5), name="chk_digests_cards"),
            models.CheckConstraint(
                condition=iff(Q(first_opened_at__isnull=True), Q(first_open_channel__isnull=True))
                & (Q(first_open_channel__isnull=True) | Q(first_open_channel__in=DigestChannel.values)),
                name="chk_digests_opened",
            ),
            models.CheckConstraint(
                condition=Q(first_opened_at__isnull=True) | Q(sent_at__isnull=False, first_opened_at__gte=F("sent_at")),
                name="chk_digests_open_after_send",
            ),
        ]


class IntroductionStatus(models.TextChoices):
    SUGGESTED = "SUGGESTED", "Suggested"
    INTERESTED = "INTERESTED", "Interested"
    ACCEPTED = "ACCEPTED", "Accepted (Freigabe)"
    INTRODUCED = "INTRODUCED", "Introduced"
    DECLINED = "DECLINED", "Declined"
    EXPIRED = "EXPIRED", "Expired"


class IntroductionDeclinedBy(models.TextChoices):
    INVESTOR = "investor", "Investor"
    STARTUP = "startup", "Startup"


class Introduction(models.Model):
    """introductions — знайомство інвестор × стартап; статуси та переходи BA-04."""

    Status = IntroductionStatus
    DeclinedBy = IntroductionDeclinedBy

    public_id = public_id_field()
    investor_profile = models.ForeignKey(
        InvestorProfile, on_delete=models.PROTECT, related_name="introductions", db_index=False
    )
    startup_profile = models.ForeignKey(
        StartupProfile, on_delete=models.PROTECT, related_name="introductions", db_index=False
    )
    teaser = models.ForeignKey(Teaser, on_delete=models.PROTECT, related_name="introductions")
    mandate = models.ForeignKey(Mandate, on_delete=models.PROTECT, related_name="introductions")
    status = models.CharField(
        max_length=10, choices=Status.choices, default=Status.SUGGESTED, db_default=Status.SUGGESTED
    )
    suggested_at = models.DateTimeField(default=timezone.now, db_default=Now())
    interested_at = models.DateTimeField(null=True, blank=True)
    investor_message = models.CharField(max_length=500, null=True, blank=True)
    request_expires_at = models.DateTimeField(null=True, blank=True)
    startup_responded_at = models.DateTimeField(null=True, blank=True)
    accepted_at = models.DateTimeField(null=True, blank=True)
    introduced_at = models.DateTimeField(null=True, blank=True)
    declined_at = models.DateTimeField(null=True, blank=True)
    declined_by = models.CharField(max_length=8, choices=DeclinedBy.choices, null=True, blank=True)
    decline_reason = models.ForeignKey(
        DeclineReason,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        db_column="decline_reason_code",
        related_name="+",
    )
    expired_at = models.DateTimeField(null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "introductions"
        constraints = [
            models.UniqueConstraint(fields=["investor_profile", "startup_profile"], name="uq_introductions_pair"),
            models.CheckConstraint(condition=Q(status__in=IntroductionStatus.values), name="chk_introductions_status"),
            models.CheckConstraint(
                condition=(
                    Q(interested_at__isnull=True)
                    & (Q(status="SUGGESTED") | Q(status="DECLINED", declined_by="investor"))
                )
                | (
                    Q(interested_at__isnull=False)
                    & ~Q(status="SUGGESTED")
                    & ~(Q(status="DECLINED") & Q(Exact(Coalesce("declined_by", Value("")), "investor")))
                ),
                name="chk_introductions_interest",
            ),
            models.CheckConstraint(
                condition=Q(investor_message__isnull=True) | Q(interested_at__isnull=False),
                name="chk_introductions_message",
            ),
            models.CheckConstraint(
                condition=iff(Q(interested_at__isnull=True), Q(request_expires_at__isnull=True)),
                name="chk_introductions_expiry",
            ),
            models.CheckConstraint(
                condition=iff(Q(status__in=["ACCEPTED", "INTRODUCED"]), Q(accepted_at__isnull=False)),
                name="chk_introductions_accepted",
            ),
            models.CheckConstraint(
                condition=iff(Q(status="INTRODUCED"), Q(introduced_at__isnull=False)),
                name="chk_introductions_introduced",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="DECLINED", declined_at__isnull=False, declined_by__isnull=False)
                    | (~Q(status="DECLINED") & Q(declined_at__isnull=True, declined_by__isnull=True))
                )
                & (Q(declined_by__isnull=True) | Q(declined_by__in=IntroductionDeclinedBy.values)),
                name="chk_introductions_declined",
            ),
            models.CheckConstraint(
                condition=Q(decline_reason__isnull=True) | Q(Exact(Coalesce("declined_by", Value("")), "investor")),
                name="chk_introductions_reason",
            ),
            models.CheckConstraint(
                condition=iff(Q(status="EXPIRED"), Q(expired_at__isnull=False)), name="chk_introductions_expired"
            ),
            models.CheckConstraint(
                condition=iff(
                    Q(startup_responded_at__isnull=False),
                    Q(accepted_at__isnull=False) | Q(Exact(Coalesce("declined_by", Value("")), "startup")),
                )
                & (Q(startup_responded_at__isnull=True) | Q(startup_responded_at__lte=F("request_expires_at"))),
                name="chk_introductions_response",
            ),
        ]
        indexes = [
            models.Index(fields=["startup_profile", "status"], name="idx_intro_startup_status"),
            models.Index(fields=["investor_profile", "status"], name="idx_intro_investor_status"),
            models.Index(fields=["request_expires_at"], name="idx_intro_expiry_due", condition=Q(status="INTERESTED")),
        ]


DIGEST_MATCH_REASONS = ["sector", "stage", "region", "check_size", "business_model"]


class DigestCard(models.Model):
    """digest_cards — показ картки в дайджесті: позиція, причини показу, складові сортування."""

    digest = models.ForeignKey(Digest, on_delete=models.CASCADE, related_name="cards", db_index=False)
    introduction = models.ForeignKey(Introduction, on_delete=models.PROTECT, related_name="cards", db_index=False)
    position = models.SmallIntegerField()
    match_reason_codes = ArrayField(models.CharField(max_length=32))
    soft_match_count = models.SmallIntegerField()
    profile_age_days = models.IntegerField()
    created_at = created_at_field()

    class Meta:
        db_table = "digest_cards"
        ordering = ["digest", "position"]
        constraints = [
            models.UniqueConstraint(fields=["digest", "position"], name="uq_digest_cards_position"),
            models.UniqueConstraint(fields=["digest", "introduction"], name="uq_digest_cards_intro"),
            models.CheckConstraint(condition=Q(position__gte=1, position__lte=5), name="chk_digest_cards_position"),
            models.CheckConstraint(
                condition=Q(match_reason_codes__len__gte=1) & Q(match_reason_codes__contained_by=DIGEST_MATCH_REASONS),
                name="chk_digest_cards_reasons",
            ),
            models.CheckConstraint(
                condition=Q(soft_match_count__gte=0, profile_age_days__gte=0), name="chk_digest_cards_ranking"
            ),
        ]
        indexes = [models.Index(fields=["introduction"], name="idx_digest_cards_intro")]


# =====================================================================
# Зворотний зв'язок і довіра
# =====================================================================


class CriterionSuggestion(models.Model):
    """criterion_suggestions — «Ви тричі відхилили через регіон. Змінити критерій?» (REQ-23)."""

    investor_profile = models.ForeignKey(
        InvestorProfile, on_delete=models.PROTECT, related_name="criterion_suggestions", db_index=False
    )
    mandate = models.ForeignKey(Mandate, on_delete=models.PROTECT, related_name="criterion_suggestions")
    decline_reason = models.ForeignKey(
        DeclineReason, on_delete=models.PROTECT, db_column="decline_reason_code", related_name="+"
    )
    criterion = models.CharField(max_length=16, choices=DeclineReason.Criterion.choices)
    decline_count = models.SmallIntegerField()
    shown_at = models.DateTimeField(default=timezone.now, db_default=Now())
    accepted_at = models.DateTimeField(null=True, blank=True)
    dismissed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "criterion_suggestions"
        constraints = [
            models.CheckConstraint(
                condition=Q(criterion__in=DeclineReason.Criterion.values), name="chk_criterion_suggestions_criterion"
            ),
            models.CheckConstraint(condition=Q(decline_count__gte=1), name="chk_criterion_suggestions_count"),
            models.CheckConstraint(
                condition=Q(accepted_at__isnull=True) | Q(dismissed_at__isnull=True),
                name="chk_criterion_suggestions_answer",
            ),
        ]
        indexes = [models.Index(fields=["investor_profile", "shown_at"], name="idx_crit_sugg_investor")]


class ReportStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    IN_REVIEW = "IN_REVIEW", "In review"
    RESOLVED = "RESOLVED", "Resolved"


class ReportDecision(models.TextChoices):
    NO_ACTION = "no_action", "No action"
    PROFILE_HIDDEN = "profile_hidden", "Profile hidden"
    PROFILE_REMOVED = "profile_removed", "Profile removed"


class Report(models.Model):
    """reports — скарги «Melden» (DSA ст. 16); одна скарга від автора на профіль."""

    Status = ReportStatus
    Decision = ReportDecision

    startup_profile = models.ForeignKey(
        StartupProfile, on_delete=models.PROTECT, related_name="reports", db_index=False
    )
    reporter_user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="reports_submitted")
    report_type = models.ForeignKey(
        ReportType, on_delete=models.PROTECT, db_column="report_type_code", related_name="+"
    )
    description = models.TextField()
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_default=Status.OPEN)
    decision = models.CharField(max_length=16, choices=Decision.choices, null=True, blank=True)
    decision_note = models.TextField(null=True, blank=True)
    decided_by_user = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="reports_decided"
    )
    decided_at = models.DateTimeField(null=True, blank=True)
    reporter_notified_at = models.DateTimeField(null=True, blank=True)
    startup_notified_at = models.DateTimeField(null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "reports"
        constraints = [
            models.UniqueConstraint(fields=["startup_profile", "reporter_user"], name="uq_reports_reporter"),
            models.CheckConstraint(condition=Q(status__in=ReportStatus.values), name="chk_reports_status"),
            models.CheckConstraint(
                condition=Q(decision__isnull=True) | Q(decision__in=ReportDecision.values), name="chk_reports_decision"
            ),
            models.CheckConstraint(
                condition=Q(
                    status="RESOLVED",
                    decision__isnull=False,
                    decision_note__isnull=False,
                    decided_by_user__isnull=False,
                    decided_at__isnull=False,
                )
                | (
                    ~Q(status="RESOLVED")
                    & Q(
                        decision__isnull=True,
                        decision_note__isnull=True,
                        decided_by_user__isnull=True,
                        decided_at__isnull=True,
                    )
                ),
                name="chk_reports_resolved",
            ),
        ]
        indexes = [
            models.Index(fields=["startup_profile", "status"], name="idx_reports_profile_status"),
            models.Index(fields=["created_at"], name="idx_reports_open", condition=~Q(status="RESOLVED")),
        ]


# =====================================================================
# Підписки та оплати
# Підписка НЕ впливає на матчинг, порядок карток і видимість профілю (текст F, REQ-03).
# Даних карток і банківських рахунків тут немає — лише ідентифікатори платіжного провайдера.
# =====================================================================


class PaymentMethod(ReferenceModel):
    """payment_methods — способи оплати, доступні в Німеччині та ЄС (картка, SEPA, PayPal, Apple Pay, Google Pay,
    Klarna, переказ). Усі вимкнені, доки не підключено провайдера (DB-15); вмикає PM через is_active."""

    code = models.CharField(max_length=32, primary_key=True)
    is_active = models.BooleanField(default=False, db_default=False)

    class Meta(ReferenceModel.Meta):
        db_table = "payment_methods"
        constraints = [
            models.CheckConstraint(condition=Q(code__regex=r"^[a-z][a-z0-9_]*$"), name="chk_payment_methods_code")
        ]


class SubscriptionAudience(models.TextChoices):
    INVESTOR = "investor", "Investor"
    STARTUP = "startup", "Startup"


class SubscriptionPlanBillingPeriod(models.TextChoices):
    MONTH = "month", "Monthly"
    YEAR = "year", "Yearly"


class SubscriptionPlan(models.Model):
    """subscription_plans — тарифи з версіями; зміна ціни = нова версія з тим самим кодом.
    Стартова фаза: безкоштовні тарифи free_launch_investor / free_launch_startup (is_free). Платні тарифи і ціни — DB-14."""

    Audience = SubscriptionAudience
    BillingPeriod = SubscriptionPlanBillingPeriod

    code = models.CharField(max_length=32)
    version = models.IntegerField()
    audience = models.CharField(max_length=8, choices=Audience.choices)
    name_de = models.CharField(max_length=120)
    name_en = models.CharField(max_length=120)
    is_free = models.BooleanField(default=False, db_default=False)
    billing_period = models.CharField(max_length=8, choices=BillingPeriod.choices, null=True, blank=True)
    price_net_eur = models.DecimalField(max_digits=10, decimal_places=2, default=0, db_default=0)
    trial_days = models.SmallIntegerField(default=0, db_default=0)
    is_active = models.BooleanField(default=True, db_default=True)
    created_at = created_at_field()

    class Meta:
        db_table = "subscription_plans"
        constraints = [
            models.UniqueConstraint(fields=["code", "version"], name="uq_subscription_plans_version"),
            models.CheckConstraint(condition=Q(code__regex=r"^[a-z][a-z0-9_]*$"), name="chk_subscription_plans_code"),
            models.CheckConstraint(condition=Q(version__gte=1), name="chk_subscription_plans_version"),
            models.CheckConstraint(
                condition=Q(audience__in=SubscriptionAudience.values), name="chk_subscription_plans_audience"
            ),
            models.CheckConstraint(
                condition=Q(billing_period__isnull=True) | Q(billing_period__in=SubscriptionPlanBillingPeriod.values),
                name="chk_subscription_plans_period",
            ),
            models.CheckConstraint(
                condition=Q(is_free=True, price_net_eur=0, billing_period__isnull=True, trial_days=0)
                | Q(is_free=False, price_net_eur__gt=0, billing_period__isnull=False, trial_days__gte=0),
                name="chk_subscription_plans_pricing",
            ),
            models.UniqueConstraint(fields=["code"], condition=Q(is_active=True), name="uq_subscription_plans_active"),
        ]

    def __str__(self):
        return f"{self.code} v{self.version}"


class SubscriptionStatus(models.TextChoices):
    TRIALING = "TRIALING", "Trialing"
    ACTIVE = "ACTIVE", "Active"
    PAST_DUE = "PAST_DUE", "Past due"
    ENDED = "ENDED", "Ended"


class SubscriptionEndReason(models.TextChoices):
    FREE_PERIOD_ENDED = "free_period_ended", "Free launch phase ended"
    CANCELED = "canceled", "Canceled by user"
    PAYMENT_FAILED = "payment_failed", "Payment failed"
    TRIAL_EXPIRED = "trial_expired", "Trial expired"
    PLAN_CHANGE = "plan_change", "Plan change"
    ACCOUNT_DELETED = "account_deleted", "Account deleted"


class Subscription(models.Model):
    """subscriptions — підписка користувача на версію тарифу; зміна тарифу = завершення + нова підписка.
    Тригер trg_subscriptions_plan: тариф відповідає ролі; платна має current_period_end, спосіб оплати й
    реквізити платника; безкоштовна — без способу оплати. current_period_end = NULL — безкоштовно безстроково."""

    Status = SubscriptionStatus
    EndReason = SubscriptionEndReason

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="subscriptions", db_index=False)
    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, related_name="subscriptions")
    status = models.CharField(max_length=10, choices=Status.choices)
    started_at = models.DateTimeField(default=timezone.now, db_default=Now())
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    current_period_start = models.DateTimeField()
    current_period_end = models.DateTimeField(null=True, blank=True)
    cancel_at_period_end = models.BooleanField(default=False, db_default=False)
    canceled_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    end_reason = models.CharField(max_length=20, choices=EndReason.choices, null=True, blank=True)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, null=True, blank=True, related_name="subscriptions",
        db_column="payment_method_code",
    )
    billing_name = models.CharField(max_length=200, null=True, blank=True)
    billing_street = models.CharField(max_length=200, null=True, blank=True)
    billing_postal_code = models.CharField(max_length=16, null=True, blank=True)
    billing_city = models.CharField(max_length=100, null=True, blank=True)
    billing_country = models.ForeignKey(
        Country, on_delete=models.PROTECT, null=True, blank=True, related_name="+", db_column="billing_country_code"
    )
    billing_vat_id = models.CharField(max_length=20, null=True, blank=True)
    payment_provider = models.CharField(max_length=30, null=True, blank=True)
    provider_subscription_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["payment_provider", "provider_subscription_id"], name="uq_subscriptions_provider"
            ),
            models.CheckConstraint(condition=Q(status__in=SubscriptionStatus.values), name="chk_subscriptions_status"),
            models.CheckConstraint(
                condition=Q(current_period_start__gte=F("started_at"))
                & (Q(current_period_end__isnull=True) | Q(current_period_end__gt=F("current_period_start"))),
                name="chk_subscriptions_period",
            ),
            models.CheckConstraint(
                condition=~Q(status="TRIALING") | Q(trial_ends_at__isnull=False), name="chk_subscriptions_trial"
            ),
            models.CheckConstraint(
                condition=Q(cancel_at_period_end=False) | Q(canceled_at__isnull=False), name="chk_subscriptions_cancel"
            ),
            models.CheckConstraint(
                condition=Q(status="ENDED", ended_at__isnull=False, end_reason__isnull=False)
                | (~Q(status="ENDED") & Q(ended_at__isnull=True, end_reason__isnull=True)),
                name="chk_subscriptions_ended",
            ),
            models.CheckConstraint(
                condition=Q(end_reason__isnull=True) | Q(end_reason__in=SubscriptionEndReason.values),
                name="chk_subscriptions_end_reason",
            ),
            models.CheckConstraint(
                condition=iff(Q(payment_provider__isnull=True), Q(provider_subscription_id__isnull=True)),
                name="chk_subscriptions_provider",
            ),
            models.CheckConstraint(
                condition=Q(billing_vat_id__isnull=True) | Q(billing_vat_id__regex=r"^[A-Z]{2}[A-Za-z0-9+*]{2,13}$"),
                name="chk_subscriptions_vat_id",
            ),
            models.UniqueConstraint(fields=["user"], condition=~Q(status="ENDED"), name="uq_subscriptions_open"),
        ]
        indexes = [
            models.Index(
                fields=["current_period_end"], name="idx_subscriptions_period_end", condition=~Q(status="ENDED")
            ),
        ]


class SubscriptionPaymentStatus(models.TextChoices):
    OPEN = "OPEN", "Open"
    PAID = "PAID", "Paid"
    FAILED = "FAILED", "Failed"
    REFUNDED = "REFUNDED", "Refunded"
    VOID = "VOID", "Void"


class SubscriptionPayment(models.Model):
    """subscription_payments — рахунки (Rechnungen) з ПДВ за законом Німеччини та результат оплати.
    Номер, дата, період, суми, ставка, reverse charge і реквізити покупця після створення не змінюються, рахунок не
    видаляється (тригер trg_subscription_payments_immutable); виправлення — сторно / кредит-нота (DB-16).
    ПДВ: vat_amount = ROUND(net × rate / 100, 2), gross = net + vat; reverse charge лише для покупця з ЄС ≠ DE з USt-IdNr.
    Дані карток і банківських рахунків не зберігаються — лише ідентифікатори провайдера."""

    Status = SubscriptionPaymentStatus

    subscription = models.ForeignKey(Subscription, on_delete=models.PROTECT, related_name="payments", db_index=False)
    invoice_number = models.CharField(max_length=30, unique=True)
    issued_at = models.DateTimeField(default=timezone.now, db_default=Now())
    period_start = models.DateTimeField()
    period_end = models.DateTimeField()
    amount_net_eur = models.DecimalField(max_digits=10, decimal_places=2)
    vat_rate_pct = models.DecimalField(max_digits=5, decimal_places=2)
    vat_amount_eur = models.DecimalField(max_digits=10, decimal_places=2)
    amount_gross_eur = models.DecimalField(max_digits=10, decimal_places=2)
    reverse_charge = models.BooleanField(default=False, db_default=False)
    buyer_name = models.CharField(max_length=200)
    buyer_street = models.CharField(max_length=200)
    buyer_postal_code = models.CharField(max_length=16)
    buyer_city = models.CharField(max_length=100)
    buyer_country = models.ForeignKey(Country, on_delete=models.PROTECT, related_name="+", db_column="buyer_country_code")
    buyer_vat_id = models.CharField(max_length=20, null=True, blank=True)
    payment_method = models.ForeignKey(
        PaymentMethod, on_delete=models.PROTECT, null=True, blank=True, related_name="payments",
        db_column="payment_method_code",
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.OPEN, db_default=Status.OPEN)
    paid_at = models.DateTimeField(null=True, blank=True)
    refunded_at = models.DateTimeField(null=True, blank=True)
    failure_code = models.CharField(max_length=100, null=True, blank=True)
    provider_invoice_id = models.CharField(max_length=100, null=True, blank=True)
    provider_payment_id = models.CharField(max_length=100, null=True, blank=True)
    created_at = created_at_field()
    updated_at = updated_at_field()

    class Meta:
        db_table = "subscription_payments"
        constraints = [
            models.UniqueConstraint(fields=["subscription", "period_start"], name="uq_subscription_payments_period"),
            models.UniqueConstraint(fields=["provider_invoice_id"], name="uq_subscription_payments_invoice"),
            models.CheckConstraint(
                condition=Q(invoice_number__regex=r"\S"), name="chk_subscription_payments_number"
            ),
            models.CheckConstraint(
                condition=Q(period_end__gt=F("period_start")), name="chk_subscription_payments_period"
            ),
            models.CheckConstraint(
                condition=Q(amount_net_eur__gte=0, vat_rate_pct__gte=0, vat_rate_pct__lt=100)
                & Q(vat_amount_eur=Func(F("amount_net_eur") * F("vat_rate_pct") / Value(100), Value(2), function="round"))
                & Q(amount_gross_eur=F("amount_net_eur") + F("vat_amount_eur")),
                name="chk_subscription_payments_amounts",
            ),
            models.CheckConstraint(
                condition=Q(reverse_charge=True, vat_rate_pct=0, buyer_vat_id__isnull=False)
                & ~Q(buyer_country="DE")
                | Q(reverse_charge=False, vat_rate_pct__gt=0),
                name="chk_subscription_payments_reverse_charge",
            ),
            models.CheckConstraint(
                condition=Q(status__in=SubscriptionPaymentStatus.values), name="chk_subscription_payments_status"
            ),
            models.CheckConstraint(
                condition=iff(Q(status__in=["PAID", "REFUNDED"]), Q(paid_at__isnull=False))
                & (~Q(status__in=["PAID", "REFUNDED"]) | Q(payment_method__isnull=False))
                & iff(Q(status="REFUNDED"), Q(refunded_at__isnull=False))
                & (~Q(status="FAILED") | Q(failure_code__isnull=False)),
                name="chk_subscription_payments_paid",
            ),
        ]
        indexes = [
            models.Index(
                fields=["paid_at"], name="idx_subscription_payments_paid", condition=Q(status__in=["PAID", "REFUNDED"])
            ),
        ]


# =====================================================================
# Системні таблиці
# =====================================================================


class EmailNotificationType(models.TextChoices):
    EMAIL_VERIFICATION = "email_verification", "E-mail verification"
    PASSWORD_RESET = "password_reset", "Password reset"
    DRAFT_READY = "draft_ready", "Draft ready"
    DRAFT_DELETION_REMINDER = "draft_deletion_reminder", "Draft deletion reminder"
    DIGEST = "digest", "Digest"
    DIGEST_EMPTY = "digest_empty", "Empty digest"
    INTRODUCTION_REQUEST = "introduction_request", "Introduction request (D)"
    INTRODUCTION = "introduction", "Introduction (E)"
    SURVEY_INVITE = "survey_invite", "Survey invite"


class EmailNotificationStatus(models.TextChoices):
    QUEUED = "QUEUED", "Queued"
    SENT = "SENT", "Sent"
    FAILED = "FAILED", "Failed"


class EmailNotification(models.Model):
    """email_notifications — журнал службових листів без тексту листа."""

    Type = EmailNotificationType
    Status = EmailNotificationStatus

    user = models.ForeignKey(User, on_delete=models.PROTECT, related_name="email_notifications", db_index=False)
    type = models.CharField(max_length=32, choices=Type.choices)
    language = models.CharField(max_length=2, choices=InterfaceLanguage.choices)
    introduction = models.ForeignKey(
        Introduction,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="email_notifications",
        db_index=False,
    )
    digest = models.ForeignKey(
        Digest, on_delete=models.PROTECT, null=True, blank=True, related_name="email_notifications"
    )
    startup_profile = models.ForeignKey(
        StartupProfile, on_delete=models.PROTECT, null=True, blank=True, related_name="email_notifications"
    )
    status = models.CharField(max_length=8, choices=Status.choices, default=Status.QUEUED, db_default=Status.QUEUED)
    provider_message_id = models.CharField(max_length=200, null=True, blank=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    error_code = models.CharField(max_length=100, null=True, blank=True)
    created_at = created_at_field()

    class Meta:
        db_table = "email_notifications"
        constraints = [
            models.CheckConstraint(condition=Q(type__in=EmailNotificationType.values), name="chk_email_type"),
            models.CheckConstraint(condition=Q(language__in=["de", "en", "uk"]), name="chk_email_language"),
            models.CheckConstraint(condition=Q(status__in=EmailNotificationStatus.values), name="chk_email_status"),
            models.CheckConstraint(
                condition=iff(Q(status="SENT"), Q(sent_at__isnull=False))
                & (~Q(status="FAILED") | Q(error_code__isnull=False)),
                name="chk_email_sent",
            ),
            models.CheckConstraint(
                condition=(~Q(type__in=["introduction_request", "introduction"]) | Q(introduction__isnull=False))
                & (~Q(type__in=["digest", "digest_empty"]) | Q(digest__isnull=False))
                & (~Q(type__in=["draft_ready", "draft_deletion_reminder"]) | Q(startup_profile__isnull=False)),
                name="chk_email_links",
            ),
        ]
        indexes = [
            models.Index(fields=["introduction"], name="idx_email_intro", condition=Q(introduction__isnull=False)),
            models.Index(fields=["status", "created_at"], name="idx_email_queue", condition=Q(status="QUEUED")),
            models.Index(fields=["user", "type", "created_at"], name="idx_email_user_type"),
            BrinIndex(fields=["created_at"], name="brin_email_created"),
        ]


class EventRole(models.TextChoices):
    STARTUP = "startup", "Startup"
    INVESTOR = "investor", "Investor"
    SYSTEM = "system", "System"


class Event(models.Model):
    """events — аналітичні події Tracking Plan (BA-TP); без персональних даних; user_id без FK.

    Секціонована таблиця (PARTITION BY RANGE (occurred_at), секція на місяць). Django не створює секціоновані
    таблиці, тому managed = False: таблицю, секції, індекси й обмеження створює міграція RunSQL зі
    startshare_schema_postgres.sql. Первинний ключ у БД — (id, occurred_at); id унікальний сам по собі (identity),
    тому ORM працює з ним як з первинним ключем. Записи лише додаються; оновлення й видалення — заборонені
    застосунку (видаляє тільки purge_expired_data()).
    """

    Role = EventRole

    id = models.BigAutoField(primary_key=True)
    event_name = models.CharField(max_length=64)
    occurred_at = models.DateTimeField(default=timezone.now, db_default=Now())
    user_id = models.BigIntegerField(null=True, blank=True)
    role = models.CharField(max_length=8, choices=Role.choices)
    entity_type = models.CharField(max_length=32, null=True, blank=True)
    entity_id = models.BigIntegerField(null=True, blank=True)
    properties = models.JSONField(default=dict, db_default=Value({}, output_field=models.JSONField()))

    class Meta:
        managed = False  # таблицю створює RunSQL (секціонування)
        db_table = "events"
        # Обмеження й індекси нижче існують у БД (створені RunSQL); тут — для валідації в Django і документації.
        constraints = [
            models.CheckConstraint(condition=Q(event_name__regex=r"^[a-z][a-z0-9_]*$"), name="chk_events_name"),
            models.CheckConstraint(condition=Q(role__in=EventRole.values), name="chk_events_role"),
            models.CheckConstraint(
                condition=iff(Q(entity_type__isnull=True), Q(entity_id__isnull=True)), name="chk_events_entity"
            ),
        ]
        indexes = [
            models.Index(fields=["user_id", "occurred_at"], name="idx_events_user_time"),
            BrinIndex(fields=["occurred_at"], name="brin_events_time"),
        ]


class PlatformParameter(models.Model):
    """platform_parameters — бізнес-параметри, які змінюються без релізу (BA-02, «Параметри»)."""

    key = models.CharField(max_length=64, primary_key=True)
    value = models.JSONField()
    description = models.CharField(max_length=300)
    updated_by_user = models.ForeignKey(User, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    updated_at = updated_at_field()

    class Meta:
        db_table = "platform_parameters"
        constraints = [
            models.CheckConstraint(condition=Q(key__regex=r"^[a-z][a-z0-9_]*$"), name="chk_platform_parameters_key")
        ]

    def __str__(self):
        return f"{self.key} = {self.value}"


class DataAccessLogActorType(models.TextChoices):
    STAFF = "staff", "Staff"
    SYSTEM = "system", "System"


class DataAccessLogAction(models.TextChoices):
    VIEW = "view", "View"
    EXPORT = "export", "Export"
    UPDATE = "update", "Update"
    DELETE = "delete", "Delete"


class DataAccessLog(models.Model):
    """data_access_log — доступ до персональних даних співробітників і системи (NFR-08, append-only)."""

    ActorType = DataAccessLogActorType
    Action = DataAccessLogAction

    actor_user = models.ForeignKey(
        User, on_delete=models.PROTECT, null=True, blank=True, related_name="+", db_index=False
    )
    actor_type = models.CharField(max_length=8, choices=ActorType.choices)
    action = models.CharField(max_length=8, choices=Action.choices)
    target_table = models.CharField(max_length=64)
    target_id = models.BigIntegerField()
    purpose = models.CharField(max_length=200)
    accessed_at = models.DateTimeField(default=timezone.now, db_default=Now())

    class Meta:
        db_table = "data_access_log"
        constraints = [
            models.CheckConstraint(
                condition=Q(actor_type__in=DataAccessLogActorType.values)
                & iff(Q(actor_type="staff"), Q(actor_user__isnull=False)),
                name="chk_access_actor",
            ),
            models.CheckConstraint(condition=Q(action__in=DataAccessLogAction.values), name="chk_access_action"),
        ]
        indexes = [
            models.Index(fields=["target_table", "target_id", "accessed_at"], name="idx_access_target"),
            models.Index(fields=["actor_user", "accessed_at"], name="idx_access_actor"),
            BrinIndex(fields=["accessed_at"], name="brin_access_time"),
        ]
