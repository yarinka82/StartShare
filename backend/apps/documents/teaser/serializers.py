
"""Ответ API для чернетки тизера. Наружу не отдаём стоимость, попытки, время и тексты ошибок."""
from rest_framework import serializers

from ..models import PitchDeckProcessingState, PitchDeck, PitchDeckFailureReason, Teaser

# Коды, которые фронтенд умеет красиво показывать пользователю
KNOWN_ERROR_CODES = {
    "deck_deleted",
    "encrypted",
    "corrupted",
    "too_many_pages",
    "empty",
    "no_text",
    "invalid_response",
    "llm_error",
    "timeout",
    "pdf_unreadable",
    "provider_unavailable",
}


def error_code_for(pitch_deck: PitchDeck) -> "str | None":
    """
    Возвращает стандартизированный код ошибки для фронтенда, если генерация упала.
    Если ошибка неизвестная — возвращает 'unexpected'.
    """
    if pitch_deck.processing_state != PitchDeckProcessingState.FAILED:
        return None

    # Берём failure_reason из модели PitchDeck
    code = (pitch_deck.failure_reason or "").split(":", 1)[0].strip()

    if code in KNOWN_ERROR_CODES:
        return code

    # Fallback, если в базе сохранён системный enum (например, OTHER)
    if pitch_deck.failure_reason == PitchDeckFailureReason.OTHER:
        return "unexpected"

    return code if code in KNOWN_ERROR_CODES else "unexpected"



class TeaserDraftSerializer(serializers.ModelSerializer):
    """Сериализатор опроса черновика тизера."""

    state = serializers.CharField(source="processing_state", read_only=True)
    ready_at = serializers.DateTimeField(source="processing_finished_at", read_only=True)
    error_code = serializers.SerializerMethodField()
    draft = serializers.SerializerMethodField()
    risk_phrases = serializers.SerializerMethodField()

    class Meta:
        model = PitchDeck
        fields = [
            "state",
            "draft",
            "risk_phrases",
            "error_code",
            "created_at",
            "ready_at",
        ]
        read_only_fields = fields

    def get_error_code(self, pitch_deck: PitchDeck) -> "str | None":
        if pitch_deck.processing_state == PitchDeckProcessingState.FAILED:
            return pitch_deck.failure_reason or "processing_failed"
        return None

    def get_draft(self, pitch_deck: PitchDeck) -> "dict | None":
        if pitch_deck.processing_state != PitchDeckProcessingState.DRAFT_READY:
            return None

        teaser = getattr(pitch_deck, "teaser", None)
        if not teaser:
            return None

        # Собираем текстовые поля тизера
        fields_dict = {
            f.field_name: f.final_text or f.ai_text or ""
            for f in teaser.fields.all()
        }

        return {
            "teaser": fields_dict,
            "language": "de",
            "review": {"image_slides": [], "blanked_fields": []},
            "version": teaser.version,
            "teaser_id": teaser.id,
            "status": teaser.status,
        }

    def get_risk_phrases(self, pitch_deck: PitchDeck) -> list:
        if pitch_deck.processing_state != PitchDeckProcessingState.DRAFT_READY:
            return []

        teaser = getattr(pitch_deck, "teaser", None)
        if not teaser:
            return []

        all_risks = []
        for field in teaser.fields.all():
            if field.risk_phrases and isinstance(field.risk_phrases, list):
                all_risks.extend(field.risk_phrases)

        return all_risks



class TeaserSerializer(serializers.ModelSerializer):
    """
    Сериализатор полного тизера для страницы предпросмотра и редактирования.
    Собирает данные из нормализованных моделей Teaser и TeaserField.
    """
    content = serializers.SerializerMethodField()
    risk_phrases = serializers.SerializerMethodField()
    edited = serializers.SerializerMethodField()
    reviewed = serializers.SerializerMethodField()
    declaration_a_accepted_at = serializers.DateTimeField(source="approved_at", read_only=True)

    class Meta:
        model = Teaser
        fields = [
            "id",
            "version",
            "status",
            "is_current",
            "content",
            "risk_phrases",
            "reviewed",
            "edited",
            "declaration_a_accepted_at",
            "approved_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_content(self, obj: Teaser) -> dict:
        """Собирает текст всех полей тизера: {field_name: text}."""
        return {
            field.field_name: field.final_text or field.ai_text or ""
            for field in obj.fields.all()
        }

    def get_risk_phrases(self, obj: Teaser) -> list:
        """Собирает все рисковые фразы по всем полям тизера."""
        risks = []
        for field in obj.fields.all():
            if field.risk_phrases and isinstance(field.risk_phrases, list):
                risks.extend(field.risk_phrases)
        return risks

    def get_edited(self, obj: Teaser) -> list[str]:
        """Возвращает список полей, которые пользователь редактировал вручную."""
        return list(
            obj.fields.filter(is_edited=True).values_list("field_name", flat=True)
        )

    def get_reviewed(self, obj: Teaser) -> list[str]:
        """Возвращает список подтверждённых полей тизера."""
        return list(
            obj.fields.filter(approved_at__isnull=False).values_list("field_name", flat=True)
        )