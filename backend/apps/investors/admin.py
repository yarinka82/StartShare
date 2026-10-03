from django.contrib import admin

from .models import InvestorMandate


@admin.register(InvestorMandate)
class InvestorMandateAdmin(admin.ModelAdmin):
    list_display = ("user", "ticket_min", "ticket_max", "updated_at")
    search_fields = ("user__email",)
