
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



class LegalDocument(models.Model):
    Code = LegalDocumentCode

    code = models.CharField(max_length=8, choices=Code.choices)
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
