from django.contrib import admin

from .models import Consent, User


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
