
from rest_framework import serializers
from .models import PitchDeck

class PitchDeckSerializer(serializers.ModelSerializer):
    class Meta:
        model = PitchDeck
        fields = ["id", "file", "uploaded_at"]
        read_only_fields = ["id", "uploaded_at"]