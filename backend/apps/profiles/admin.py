from django.contrib import admin

from apps.documents.models import TeaserField, Teaser, PitchDeck
from apps.startups.models import StartupProfile
from common.models import Country


class DictionaryAdmin(admin.ModelAdmin):
    list_display = ["code", "name_de", "name_en", "sort_order", "is_active"]
    list_editable = ["sort_order", "is_active"]
    search_fields = ["code", "name_de", "name_en"]


admin.site.register(Country, DictionaryAdmin)


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = ["public_id", "get_company_name", "status", "user", "created_at"]

    @admin.display(description="Company Name")
    def get_company_name(self, obj):
        if hasattr(obj, "private_details") and obj.private_details:
            return obj.private_details.company_name
        return "—"


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
