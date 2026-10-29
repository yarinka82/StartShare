from rest_framework import serializers

from common.models import Country
from ..documents.serializers import DeckSerializer
from ..startups.models import StartupProfile




class DictionaryItemSerializer(serializers.Serializer):
    code = serializers.CharField()
    name = serializers.CharField()




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



