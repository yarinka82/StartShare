from django.utils import timezone
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from apps.documents.models import TeaserField, Teaser, PitchDeck
from apps.startups.models import StartupProfile
from common.models import Country
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
    
    



class DictionaryAdmin(admin.ModelAdmin):
    list_display = ["code", "name_de", "name_en", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["code", "name_de", "name_en"]


admin.site.register(Country, DictionaryAdmin)


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "public_id",
        "status",
        "sector",
        "stage",
        "country",
        "round_amount_eur",
        "moderation_hidden_at",
        "created_at",
    ]
    list_filter = ["status", "sector", "stage", "country", "created_at"]
    search_fields = [
        "public_id",
        "private_details__company_name",
        "user__email",  # ← проверьте имя связи
    ]
    actions = ["hide_startups_from_matching", "unhide_startups_from_matching"]

    @admin.action(description="🚨 Приховати стартап з видачі (moderation_hidden_at)")
    def hide_startups_from_matching(self, request, queryset):
        now = timezone.now()
        updated = queryset.update(moderation_hidden_at=now)
        self.message_user(
            request,
            f"Успішно приховано {updated} стартап(ів) з видачі інвесторів.",
        )

    @admin.action(description="✅ Розблокувати стартап (повернути у видачу)")
    def unhide_startups_from_matching(self, request, queryset):
        updated = queryset.update(moderation_hidden_at=None)
        self.message_user(
            request,
            f"Розблоковано {updated} стартап(ів). Вони знову доступні в матчингу.",
        )



@admin.register(PitchDeck)
class PitchDeckAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "startup_profile",
        "original_name",
        "file_size_kb",
        "page_count",
        "processing_state",
        "ai_model",
        "ai_cost_eur",
        "keep_original",
        "uploaded_at",
        "deleted_at",
    )
    list_filter = (
        "processing_state",
        "keep_original",
        "ai_provider",
        "failure_reason",
        "deletion_reason",
    )
    search_fields = (
        "original_name",
        "startup_profile__public_id",
        "startup_profile__user__email",
    )
    readonly_fields = (
        "file",
        "uploaded_at",
        "processing_started_at",
        "processing_finished_at",
        "created_at",
        "deleted_at",
    )

    @admin.display(description="Size (KB)")
    def file_size_kb(self, obj):
        if obj.file_size_bytes:
            return f"{round(obj.file_size_bytes / 1024, 1)} KB"
        return "—"


class TeaserFieldInline(admin.TabularInline):
    model = TeaserField
    extra = 0
    fields = ("field_name", "language", "is_edited", "approved_at")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Teaser)
class TeaserAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "startup_profile",
        "version",
        "status",
        "is_current",
        "pitch_deck",
        "approved_at",
        "created_at",
    )
    list_filter = ("status", "is_current")
    search_fields = ("startup_profile__public_id", "startup_profile__user__email")
    readonly_fields = ("created_at", "updated_at", "approved_at")
    inlines = [TeaserFieldInline]


@admin.register(TeaserField)
class TeaserFieldAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "teaser",
        "field_name",
        "language",
        "is_edited",
        "approved_at",
    )
    list_filter = ("field_name", "language", "is_edited")
    search_fields = ("teaser__startup_profile__public_id", "final_text", "ai_text")
