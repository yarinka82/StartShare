from django.contrib.auth.base_user import AbstractBaseUser, BaseUserManager
from django.contrib.auth.models import PermissionsMixin
from django.db import models
from django.utils import timezone


class Role(models.TextChoices):
    STARTUP = "startup", "Startup"
    INVESTOR = "investor", "Investor"


class UserManager(BaseUserManager):
    use_in_migrations = True

    def _create(self, email, password, **extra):
        if not email:
            raise ValueError("Email is required")
        user = self.model(email=email.strip().lower(), **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._create(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("role", Role.STARTUP)
        extra.setdefault("email_verified_at", timezone.now())
        return self._create(email, password, **extra)


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=Role.choices)
    email_verified_at = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    def __str__(self):
        return self.email

    @property
    def is_email_verified(self):
        return self.email_verified_at is not None


class Consent(models.Model):
    """Which legal document (and which version) the user accepted, and when."""

    class DocumentType(models.TextChoices):
        AGB = "agb", "AGB"
        DATENSCHUTZ = "datenschutz", "Datenschutz"
        INVESTOR_STATUS = "investor-status", "Investor status (text C)"

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="consents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_version = models.CharField(max_length=40)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "document_type"])]

    def __str__(self):
        return f"{self.user_id}:{self.document_type}@{self.document_version}"


class VendorCompliance(models.Model):
    """Tracks external vendors that receive user data and whether they are approved under AVV/DPA."""

    class VendorType(models.TextChoices):
        AI = "ai", "AI provider"
        EMAIL = "email", "Email provider"
        STORAGE = "storage", "File storage provider"
        ANALYTICS = "analytics", "Analytics provider"

    name = models.CharField(max_length=100, unique=True)
    provider_name = models.CharField(max_length=100, unique=True, blank=True, default="")
    vendor_type = models.CharField(max_length=20, choices=VendorType.choices)
    provider_type = models.CharField(max_length=20, choices=VendorType.choices, blank=True, default="")
    region = models.CharField(max_length=30, default="eu")
    dpa_signed = models.BooleanField(default=False)
    dpa_signed_at = models.DateTimeField(null=True, blank=True)
    dpa_valid_until = models.DateField(null=True, blank=True)
    no_model_training = models.BooleanField(default=False)
    contract_url = models.URLField(blank=True)
    subprocessor_list = models.TextField(blank=True)
    data_category = models.JSONField(default=list, blank=True)
    allowed_data_types = models.JSONField(default=list, blank=True)
    contact_email = models.EmailField(blank=True, default="")
    legal_contact = models.EmailField(blank=True, default="")
    notes = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def save(self, *args, **kwargs):
        if not self.provider_name:
            self.provider_name = self.name
        if not self.name:
            self.name = self.provider_name
        if not self.provider_type:
            self.provider_type = self.vendor_type
        if not self.vendor_type and self.provider_type:
            self.vendor_type = self.provider_type
        if not self.data_category and self.allowed_data_types:
            self.data_category = self.allowed_data_types
        elif self.data_category and not self.allowed_data_types:
            self.allowed_data_types = self.data_category
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.provider_name or self.name} ({self.provider_type or self.vendor_type})"
