from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ("created_at", "name", "user", "properties")
    list_filter = ("name",)
    date_hierarchy = "created_at"

    # the log is append-only
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False
