from rest_framework import serializers

from .models import Introduction


class IntroductionSerializer(serializers.ModelSerializer):
    organization = serializers.SerializerMethodField()
    organization_type = serializers.SerializerMethodField()
    message = serializers.SerializerMethodField()

    class Meta:
        model = Introduction
        fields = [
            "id",
            "startup",
            "investor",
            "organization",
            "organization_type",
            "status",
            "investor_message",
            "message",
            "interested_at",
            "expires_at",
            "reminder_sent_at",
            "created_at",
        ]
        read_only_fields = fields

    def get_organization(self, obj):
        return obj.investor.organization_name or obj.investor.name or "Investor"

    def get_organization_type(self, obj):
        return obj.investor.organization_type or "Fund"

    def get_message(self, obj):
        return obj.investor_message
