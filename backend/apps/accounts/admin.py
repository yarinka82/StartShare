from datetime import date

from django.contrib import admin
from django.contrib.admin import SimpleListFilter

from .models import Consent, User, VendorCompliance


class DpaUnsignedFilter(SimpleListFilter):
    title = "DPA not signed"
    parameter_name = "dpa_unsigned"

    def lookups(self, request, model_admin):
        return (("yes", "Not signed"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(dpa_signed=False)
        return queryset


class DpaExpiredFilter(SimpleListFilter):
    title = "DPA expired"
    parameter_name = "dpa_expired"

    def lookups(self, request, model_admin):
        return (("yes", "Expired"),)

    def queryset(self, request, queryset):
        if self.value() == "yes":
            return queryset.filter(dpa_signed=True, dpa_valid_until__lt=date.today())
        return queryset


@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ("email", "role", "email_verified_at", "is_active", "date_joined")
    list_filter = ("role", "is_active")
    search_fields = ("email",)
    exclude = ("password",)


@admin.register(Consent)
class ConsentAdmin(admin.ModelAdmin):
    list_display = ("user", "document_type", "document_version", "accepted_at")
    list_filter = ("document_type",)


@admin.register(VendorCompliance)
class VendorComplianceAdmin(admin.ModelAdmin):
    list_display = ("provider_name", "provider_type", "region", "dpa_signed", "dpa_valid_until", "no_model_training", "is_active")
    list_filter = ("provider_type", "region", "dpa_signed", "no_model_training", "is_active", DpaUnsignedFilter, DpaExpiredFilter)
    search_fields = ("provider_name", "name", "notes")
    readonly_fields = ("created_at", "updated_at")
