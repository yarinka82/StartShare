from django.contrib import admin

from .models import Country, Deck, StartupProfile


class DictionaryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


admin.site.register(Country, DictionaryAdmin)


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "sector", "stage", "country", "status")
    list_filter = ("status", "sector", "stage")


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("profile", "original_name", "size", "status", "uploaded_at")
    readonly_fields = ("file",)  # no download from admin on purpose
