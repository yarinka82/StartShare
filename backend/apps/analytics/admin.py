import json
from django.contrib import admin

from .models import Event


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    # Если вы оставили ForeignKey на user, замените "user_id" обратно на "user"
    list_display = (
        "created_at",
        "name",
        "role",
        "user_id",
        "entity_type",
        "short_properties",
    )
    list_filter = ("role", "name")
    search_fields = ("name", "user_id", "entity_id")
    date_hierarchy = "created_at"
    ordering = ("-created_at",)

    # Строгий append-only журнал (запрет добавления, изменения и удаления)
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    @admin.display(description="Properties")
    def short_properties(self, obj):
        """Ограничивает длину JSON в списке, чтобы таблица оставалась читаемой."""
        if not obj.properties:
            return "-"
        raw = json.dumps(obj.properties, ensure_ascii=False)
        return (raw[:75] + "…") if len(raw) > 75 else raw
