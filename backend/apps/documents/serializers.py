from rest_framework import serializers

from apps.analytics.services import processing_status
from apps.profiles.models import Deck


class DeckSerializer(serializers.ModelSerializer):
    processing_status = serializers.SerializerMethodField()

    class Meta:
        model = Deck
        fields = ("id", "original_name", "size", "status", "uploaded_at", "processing_status")
        read_only_fields = fields

    def get_processing_status(self, obj):
        return processing_status(obj)


class DeckUploadSerializer(serializers.Serializer):  # заглушка вашего: только проверка PDF
    file = serializers.FileField()

    def validate_file(self, f):
        head = f.read(5)
        f.seek(0)
        if head != b"%PDF-":
            raise serializers.ValidationError("Only PDF files are allowed.")
        return f