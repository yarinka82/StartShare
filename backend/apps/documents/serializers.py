from rest_framework import serializers

from apps.analytics.services import processing_status
from apps.profiles.models import Deck
from apps.profiles.validators import validate_deck_file


class DeckSerializer(serializers.ModelSerializer):
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ("id", "original_name", "size", "status", "uploaded_at", "processing_status")
        read_only_fields = fields

    def get_processing_status(self, obj):
        return processing_status(obj)


class DeckUploadSerializer(serializers.Serializer):
    file = serializers.FileField(allow_empty_file=True)

    def validate_file(self, f):
        if f.size == 0:
            raise serializers.ValidationError("deck_empty")
        return validate_deck_file(f)