from django.contrib import admin
from django.utils import timezone

from apps.startups.models import Report, ReportStatus


@admin.action(description="🚨 Заблокувати профіль стартапу (приховати з матчингу)")
def hide_startups_from_matching(modeladmin, request, queryset):
    now = timezone.now()
    updated = queryset.update(moderation_hidden_at=now)
    modeladmin.message_user(
        request,
        f"Успішно приховано {updated} стартапів з видачі інвесторів.",
    )


@admin.register(Report)
class StartupReportAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "startup_profile",
        "report_type",
        "reporter_email_display",
        "status",
        "created_at",
    ]
    list_filter = ["status", "report_type", "created_at"]
    search_fields = [
        "reporter_user__email",
        "description",
        "startup_profile__company_name",
    ]
    readonly_fields = ["created_at", "updated_at", "decided_at"]
    actions = ["mark_resolved_and_hide_profile"]

    @admin.display(description="Reporter email", ordering="reporter_user__email")
    def reporter_email_display(self, obj):
        return obj.reporter_user.email if obj.reporter_user_id else "—"

    @admin.action(description="Підтвердити порушення та приховати стартап")
    def mark_resolved_and_hide_profile(self, request, queryset):
        now = timezone.now()
        for report in queryset:
            report.status = ReportStatus.RESOLVED
            report.decided_at = now
            report.decided_by_user = request.user
            report.save(update_fields=["status", "decided_at", "decided_by_user"])

            # Приховуємо стартап з усіх алгоритмів матчингу
            sp = report.startup_profile
            sp.moderation_hidden_at = now
            sp.save(update_fields=["moderation_hidden_at"])

        self.message_user(
            request,
            "Скарги схвалено, відповідні стартапи вилучені з матчингу.",
        )