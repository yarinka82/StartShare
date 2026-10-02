from django.contrib import admin

from .models import BusinessModel, Country, Deck, Sector, Stage, StartupProfile


class DictionaryAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "sort_order", "is_active")
    list_editable = ("sort_order", "is_active")


admin.site.register(Sector, DictionaryAdmin)
admin.site.register(Stage, DictionaryAdmin)
admin.site.register(Country, DictionaryAdmin)
admin.site.register(BusinessModel, DictionaryAdmin)


@admin.register(StartupProfile)
class StartupProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "company_name", "sector", "stage", "country", "status")
    list_filter = ("status", "sector", "stage")


@admin.register(Deck)
class DeckAdmin(admin.ModelAdmin):
    list_display = ("profile", "original_name", "size", "status", "uploaded_at")
    readonly_fields = ("file",)  # no download from admin on purpose
