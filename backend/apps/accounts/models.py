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

    user = models.ForeignKey("accounts.User", on_delete=models.CASCADE, related_name="consents")
    document_type = models.CharField(max_length=20, choices=DocumentType.choices)
    document_version = models.CharField(max_length=40)
    accepted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=["user", "document_type"])]

    def __str__(self):
        return f"{self.user_id}:{self.document_type}@{self.document_version}"
