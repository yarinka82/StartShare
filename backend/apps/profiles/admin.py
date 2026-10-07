from django.contrib import admin

from apps.documents.models import Deck
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


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("profile", "original_name", "size", "status", "uploaded_at")
    readonly_fields = ("file",)  # no download from admin on purpose
