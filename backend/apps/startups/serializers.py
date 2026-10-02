
from rest_framework import serializers
from .models import StartupProfile

class StartupProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = StartupProfile
        fields = [
            "id", "status", "sector", "stage", "country",
            "amount_seeking", "mrr", "growth_rate", "team_size", "created_at",
        ]
        read_only_fields = ["id", "status", "created_at"]