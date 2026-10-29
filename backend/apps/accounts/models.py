from django.conf import settings
from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


def created_at_field():
    return models.DateTimeField(default=timezone.now, editable=False)


def updated_at_field():
    return models.DateTimeField(auto_now=True)


class InterfaceLanguage(models.TextChoices):
    DE = "de", "Deutsch"
    EN = "en", "English"
    UK = "uk", "Українська"


class Language(models.TextChoices):
    DE = "de", "Deutsch"
    EN = "en", "English"


class UserRole(models.TextChoices):
    STARTUP = "startup", "Startup"
    INVESTOR = "investor", "Investor"
    STAFF = "staff", "Staff"


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
        extra.setdefault("role", UserRole.STARTUP)
        return self._create_user(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.update(role=UserRole.STAFF, is_staff=True, is_superuser=True)
        return self._create_user(email, password, **extra)



class User(AbstractBaseUser, PermissionsMixin):
    Role = UserRole

    email = models.EmailField(max_length=254, unique=True)
    role = models.CharField(max_length=16, choices=Role.choices)
    preferred_language = models.CharField(
        max_length=2, choices=InterfaceLanguage.choices, default=InterfaceLanguage.DE
    )
    email_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_test = models.BooleanField(default=False)
    created_at = created_at_field()
    updated_at = updated_at_field()
    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = UserManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["role"]

    class Meta:
        db_table = "users"
        indexes = [models.Index(fields=["role", "created_at"], name="idx_users_role_created")]

    def __str__(self):
        return f"{self.email} ({self.role})"

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None



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
    IMPRESSUM = "IMPRESSUM", "Impressum"



class LegalDocument(models.Model):
    Code = LegalDocumentCode

    code = models.CharField(max_length=10, choices=Code.choices)
    language = models.CharField(max_length=2, choices=Language.choices)
    version = models.IntegerField(default=1)
    title = models.CharField(max_length=200)
    body = models.TextField()
    legal_approved_at = models.DateTimeField(null=True, blank=True)
    valid_from = models.DateTimeField(null=True, blank=True)
    valid_to = models.DateTimeField(null=True, blank=True)
    created_at = created_at_field()

    class Meta:
        db_table = "legal_documents"
        unique_together = [("code", "language", "version")]

    def __str__(self):
        return f"{self.code} {self.language} v{self.version}"



class UserConsentContext(models.TextChoices):
    REGISTRATION = "registration", "Registration (AGB, DSE)"
    TEASER_APPROVAL = "teaser_approval", "Teaser approval (A)"
    INVESTOR_STATUS = "investor_status", "Investor status (C)"



class UserConsent(models.Model):
    Context = UserConsentContext

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="consents")
    legal_document = models.ForeignKey(LegalDocument, on_delete=models.PROTECT, related_name="consents")
    context = models.CharField(max_length=24, choices=Context.choices)
    accepted_at = models.DateTimeField(default=timezone.now)

    @property
    def document_type(self):
        if not self.legal_document:
            return ""
        # Повертає "agb", "datenschutz", "investor-status"
        code = self.legal_document.code.lower()
        if code in ("dse", "datenschutz"):
            return "datenschutz"
        if code in ("c", "investor-status", "investor_status"):
            return "investor-status"
        return code

    @property
    def document_version(self):
        # Повертає версію з settings або версію документа
        legal_versions = getattr(settings, "LEGAL_DOCUMENT_VERSIONS", {})
        return legal_versions.get(self.document_type, str(self.legal_document.version if self.legal_document else "1"))

    class Meta:
        db_table = "user_consents"
        indexes = [models.Index(fields=["user", "context"], name="idx_user_consents_user")]

    def __str__(self):
        return f"{self.user_id}:{self.document_type}@{self.document_version}"



class PlatformConfig(models.Model):
    """Глобальні системні налаштування платформи (Singleton: завжди ID=1)."""
    
    # 1. ШІ та LLM
    ai_provider = models.CharField(max_length=32, default="gemini")
    ai_model = models.CharField(max_length=64, default="gemini-3.8-flash")
    ai_temperature = models.FloatField(default=0.2)
    
    # 2. Ліміти файлів та TTL
    max_deck_size_mb = models.PositiveIntegerField(default=20)
    deck_retention_hours = models.PositiveIntegerField(default=24)
    draft_expiry_days = models.PositiveIntegerField(default=30)
    
    # 3. Правила матчингу та тижневого дайджесту
    min_digest_cards = models.PositiveSmallIntegerField(default=3)
    max_digest_cards = models.PositiveSmallIntegerField(default=5)
    
    # 4. Параметри знайомства
    intro_request_expiry_days = models.PositiveSmallIntegerField(default=7,
                                                                 help_text="Q-01: термін на відповідь Freigabe (дні)")
    intro_reminder_days = models.PositiveSmallIntegerField(default=4,
                                                           help_text="Q-32: нагадування стартапу перед закінченням (дні)")
    card_active_days = models.PositiveSmallIntegerField(default=4,
                                                        help_text="Q-27: картка зникає з активного списку інвестора (дні)")
    
    # 5. Опитування цінності продукту (14 і 30 днів)
    surveys_enabled = models.BooleanField(default=False, help_text="Увімкнути автоматичні опитування")
    survey_day_first = models.PositiveSmallIntegerField(default=14)
    survey_day_second = models.PositiveSmallIntegerField(default=30)
    
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = "platform_config"
        verbose_name = "Platform Configuration"
    
    def save(self, *args, **kwargs):
        self.pk = 1
        super().save(*args, **kwargs)
    
    @classmethod
    def get_solo(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj
    
    def __str__(self):
        return f"Config (Model: {self.ai_model}, Intro TTL: {self.intro_request_expiry_days}d)"
