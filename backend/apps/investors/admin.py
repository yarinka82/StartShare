from django.contrib import admin

from .models import InvestorProfile, Mandate


class MandateInline(admin.TabularInline):
    """Отображение истории версий мандатов прямо в профиле инвестора."""

    model = Mandate
    extra = 0
    can_delete = False
    fields = (
        "version",
        "is_current",
        "check_min_eur",
        "check_max_eur",
        "sector_codes",
        "stage_codes",
        "country_codes",
        "source",
        "created_at",
    )
    readonly_fields = ("version", "created_at")
    show_change_link = True


@admin.register(InvestorProfile)
class InvestorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "organization_name",
        "user",
        "investor_type",
        "country",
        "contact_person_name",
        "contact_email",
        "created_at",
    )
    list_filter = ("investor_type", "country", "created_at")
    search_fields = (
        "organization_name",
        "contact_person_name",
        "contact_email",
        "user__email",
    )
    readonly_fields = ("created_at", "updated_at")
    inlines = [MandateInline]


@admin.register(Mandate)
class MandateAdmin(admin.ModelAdmin):
    list_display = (
        "investor_profile",
        "version",
        "is_current",
        "check_min_eur",
        "check_max_eur",
        "source",
        "created_at",
    )
    list_filter = ("is_current", "source", "created_at")
    search_fields = (
        "investor_profile__organization_name",
        "investor_profile__user__email",
    )
    readonly_fields = ("created_at",)
