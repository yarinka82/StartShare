
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import LegalDocument, User, UserConsent


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    # Відображення полів у списку користувачів
    list_display = [
        "email",
        "role",
        "is_active",
        "is_staff",
        "preferred_language",
        "is_test",
        "created_at",
    ]
    list_filter = ["role", "is_active", "is_staff", "is_test", "preferred_language"]
    search_fields = ["email"]
    ordering = ["-created_at"]

    # Налаштування форми перегляду / редагування
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Персональна інформація та роль",
            {"fields": ("role", "preferred_language", "email_verified_at", "is_test")},
        ),
        (
            "Права доступу",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Дати", {"fields": ("created_at", "updated_at", "deleted_at")}),
    )

    readonly_fields = ["created_at", "updated_at"]

    # Форма створення нового користувача в адмінці
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "role", "password1", "password2", "is_staff", "is_active"),
            },
        ),
    )


@admin.register(UserConsent)
class UserConsentAdmin(admin.ModelAdmin):
    list_display = ["user", "legal_document", "context", "accepted_at"]
    list_filter = ["context", "legal_document__code", "legal_document__language", "accepted_at"]
    search_fields = ["user__email", "legal_document__title", "legal_document__code"]
    readonly_fields = ["accepted_at"]
    ordering = ["-accepted_at"]


@admin.register(LegalDocument)
class LegalDocumentAdmin(admin.ModelAdmin):
    list_display = ["code", "language", "version", "title", "legal_approved_at", "valid_from", "valid_to"]
    list_filter = ["code", "language", "version"]
    search_fields = ["title", "body"]
    ordering = ["code", "language", "-version"]
