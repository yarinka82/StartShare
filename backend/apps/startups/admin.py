from django.contrib import admin
from django.utils import timezone

from apps.startups.models import Report, ReportStatus


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    # 🚀 ВИПРАВЛЕНО: точні поля з вашої моделі Report
    list_display = [
        "id",
        "startup_profile",
        "report_type",
        "get_reporter_email",
        "status",
        "decision",
        "created_at",
    ]
    list_filter = ["status", "decision", "report_type", "created_at"]
    search_fields = ["reporter_user__email", "description", "startup_profile__public_id"]
    readonly_fields = ["created_at", "updated_at"]

    @admin.display(description="Reporter Email")
    def get_reporter_email(self, obj):
        return obj.reporter_user.email if obj.reporter_user else "-"

    actions = ["action_hide_profile", "action_remove_profile"]

    @admin.action(description="Приховати стартап з матчингу (Profile Hidden)")
    def action_hide_profile(self, request, queryset):
        now = timezone.now()
        for report in queryset:
            report.status = ReportStatus.RESOLVED
            report.decision = "profile_hidden"
            report.decided_by_user = request.user
            report.decided_at = now
            report.save()

            sp = report.startup_profile
            sp.moderation_hidden_at = now
            sp.save(update_fields=["moderation_hidden_at"])
        self.message_user(request, "Профілі приховано з пошуку інвесторів.")

    @admin.action(description="Повністю видалити стартап (Profile Removed)")
    def action_remove_profile(self, request, queryset):
        now = timezone.now()
        for report in queryset:
            report.status = ReportStatus.RESOLVED
            report.decision = "profile_removed"
            report.decided_by_user = request.user
            report.decided_at = now
            report.save()

            sp = report.startup_profile
            sp.status = "REMOVED"
            sp.removed_at = now
            sp.removed_by = "staff"
            sp.save(update_fields=["status", "removed_at", "removed_by"])
        self.message_user(request, "Стартапи заблоковано та переведено в статус REMOVED.")