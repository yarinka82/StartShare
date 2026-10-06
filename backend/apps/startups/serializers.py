
from rest_framework import serializers
from apps.profiles.models import StartupProfile


class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupProfile
        fields = [
            "company_name",
            "sector",
            "stage",
            "business_model",
            "country",
            "amount_sought",
            "mrr",
            "growth_percent",
            "growth_period",
            "team_size",
            "status",
            "is_complete",
            "missing_fields",
            "deck",
        ]
        read_only_fields = ["is_complete", "missing_fields", "deck"]