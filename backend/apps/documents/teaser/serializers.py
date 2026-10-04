
"""Ответ API для чернетки тизера. Наружу не отдаём стоимость, попытки, время и тексты ошибок."""
from rest_framework import serializers

from ..models import TeaserJob

# Коды, которые фронтенд умеет показывать. Всё остальное для клиента — "unexpected".
KNOWN_ERROR_CODES = {
    "deck_deleted", "encrypted", "corrupted", "too_many_pages", "empty",
    "no_text", "invalid_response", "llm_error", "timeout",
}


def error_code_for(job: TeaserJob) -> "str | None":
    if job.state != TeaserJob.State.FAILED:
        return None
    code = (job.error or "").split(":", 1)[0].strip()
    return code if code in KNOWN_ERROR_CODES else "unexpected"


class TeaserDraftSerializer(serializers.ModelSerializer):
    draft = serializers.SerializerMethodField()
    risk_phrases = serializers.SerializerMethodField()
    error_code = serializers.SerializerMethodField()

    class Meta:
        model = TeaserJob
        fields = ["state", "draft", "risk_phrases", "error_code", "created_at", "ready_at"]
        read_only_fields = fields

    def get_draft(self, job):
        return job.draft if job.state == TeaserJob.State.DRAFT_READY else None

    def get_risk_phrases(self, job):
        return job.risk_phrases if job.state == TeaserJob.State.DRAFT_READY else []

    def get_error_code(self, job):
        return error_code_for(job)


class TeaserSerializer(serializers.Serializer):
    """Рабочий тизер для редактирования. Стоимость, время и исходный вывод ШІ не отдаём."""

    status = serializers.CharField()
    content = serializers.JSONField()
    reviewed = serializers.JSONField()
    risk_phrases = serializers.JSONField()
    approval_blockers = serializers.SerializerMethodField()
    declaration_a_accepted_at = serializers.DateTimeField()
    approved_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()

    def get_approval_blockers(self, teaser):
        from .editing import approval_blockers
        return approval_blockers(teaser.content, teaser.reviewed, teaser.risk_phrases)