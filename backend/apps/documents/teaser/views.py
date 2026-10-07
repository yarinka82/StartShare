
"""Редактирование и утверждение тизера. Отдельные APIView, как отдельные эндпоинты поверх profiles.Deck."""
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import permissions
from rest_framework.exceptions import APIException, NotFound, ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.models import EventName
from apps.analytics.services import track

from ..models import Teaser, TeaserStatus, PitchDeckProcessingState, PitchDeck, TeaserFieldFieldName, TeaserField
from .editing import risky_fields
from .serializers import TeaserDraftSerializer, TeaserSerializer
from ...accounts.models import Language, UserConsent, LegalDocument

VALID_TEASER_FIELDS = set(TeaserFieldFieldName.values)

class Conflict(APIException):
    status_code = 409
    default_detail = "Conflict."
    default_code = "conflict"


def _teaser_for(request, pk) -> Teaser:
    """Получает готовый тизер для PitchDeck."""
    pitch_deck = get_object_or_404(
        PitchDeck.objects.filter(
            startup_profile__user=request.user,
            deleted_at__isnull=True,
        ),
        pk=pk,
    )
    if pitch_deck.processing_state != PitchDeckProcessingState.DRAFT_READY:
        raise Conflict(
            f"Draft is not ready (state: {pitch_deck.processing_state}).",
            code="draft_not_ready",
        )
    
    teaser = getattr(pitch_deck, "teaser", None) or Teaser.objects.filter(pitch_deck=pitch_deck).first()
    if teaser is None:
        raise NotFound("No teaser generated for this deck.")
    return teaser


def _locked(teaser_id: int) -> Teaser:
    """Блокирует тизер для редактирования."""
    teaser = (
        Teaser.objects.select_for_update()
        .select_related("startup_profile")
        .get(pk=teaser_id)
    )
    if teaser.status == TeaserStatus.APPROVED:
        raise Conflict("Teaser is already approved and locked.", code="already_approved")
    return teaser


def _respond(teaser: Teaser) -> Response:
    response = Response(TeaserSerializer(teaser).data)
    response["Cache-Control"] = "no-store"
    return response


class Conflict(APIException):
    status_code = 409
    default_detail = "Conflict."
    default_code = "conflict"


def _teaser_for(request, pk) -> Teaser:
    pitch_deck = get_object_or_404(
        PitchDeck.objects.filter(
            startup_profile__user=request.user,
            deleted_at__isnull=True,
        ),
        pk=pk,
    )
    if pitch_deck.processing_state != PitchDeckProcessingState.DRAFT_READY:
        raise Conflict(f"Draft is not ready (state: {pitch_deck.processing_state}).", code="draft_not_ready")
    
    teaser = getattr(pitch_deck, "teaser", None) or Teaser.objects.filter(pitch_deck=pitch_deck).first()
    if teaser is None:
        raise NotFound("No teaser generated for this deck.")
    return teaser


def _locked(teaser_id: int) -> Teaser:
    teaser = Teaser.objects.select_for_update().select_related("startup_profile").get(pk=teaser_id)
    if teaser.status == TeaserStatus.APPROVED:
        raise Conflict("Teaser is already approved and locked.", code="already_approved")
    return teaser


def _respond(teaser: Teaser) -> Response:
    response = Response(TeaserSerializer(teaser).data)
    response["Cache-Control"] = "no-store"
    return response



class TeaserView(APIView):
    """GET и PATCH для работы с полями тизера (/api/decks/{id}/teaser/)."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        teaser = _teaser_for(request, pk)
        return _respond(teaser)

    def patch(self, request, pk):
        teaser_obj = _teaser_for(request, pk)
        import logging
        logging.getLogger(__name__).warning(
            "TEASER PATCH data=%r valid=%r", request.data, VALID_TEASER_FIELDS
        )
        # Собираем обновления полей. Поддерживаем три формата:
        updates = {}
        
        # 1) {"content": {"solution": "..."}} или {"fields": {"solution": "..."}}
        for container_key in ("content", "fields"):
            container = request.data.get(container_key)
            if isinstance(container, dict):
                updates.update(container)
        
        # 2) {"field_name": "solution", "text": "..."}
        if "field_name" in request.data and "text" in request.data:
            updates[request.data["field_name"]] = request.data["text"]
        
        # 3) плоский формат: {"solution": "..."}
        for key in VALID_TEASER_FIELDS:
            if key in request.data:
                updates[key] = request.data[key]

        reviewed_fields = request.data.get("reviewed") or []
        if not isinstance(reviewed_fields, list):
            raise ValidationError({"reviewed": "Must be a list of field names."})

        if not updates and not reviewed_fields:
            raise ValidationError(
                "Expected {field: text}, 'content': {...} or 'field_name' + 'text'."
            )

        unknown = [k for k in updates if k not in VALID_TEASER_FIELDS]
        if unknown:
            raise ValidationError({"content": f"Unknown fields: {unknown}"})
        if any(not isinstance(v, str) for v in updates.values()):
            raise ValidationError({"content": "Field text must be a string."})

        with transaction.atomic():
            teaser = _locked(teaser_obj.pk)

            for field_name, new_text in updates.items():
                # ищем существующее поле независимо от языка, чтобы не плодить дубли
                tf = (
                    TeaserField.objects.filter(teaser=teaser, field_name=field_name)
                    .order_by("pk")
                    .first()
                ) or TeaserField(teaser=teaser, field_name=field_name, language=Language.DE)

                tf.final_text = new_text
                tf.is_edited = True

                # Если пользователь убрал рисковую цитату, очищаем этот риск
                if isinstance(tf.risk_phrases, list):
                    low = new_text.lower()
                    kept = []
                    for rp in tf.risk_phrases:
                        if not isinstance(rp, dict):
                            continue
                        quote = (rp.get("quote") or rp.get("fragment") or "").lower()
                        if not quote or quote in low:
                            kept.append(rp)
                    tf.risk_phrases = kept

                tf.save()

            if reviewed_fields:
                TeaserField.objects.filter(
                    teaser=teaser, field_name__in=reviewed_fields
                ).update(approved_at=timezone.now())

            teaser.updated_at = timezone.now()
            teaser.save(update_fields=["updated_at"])

        return _respond(teaser)



class TeaserReviewView(APIView):
    """POST /api/decks/{id}/teaser/review/ — подтверждение отдельного поля (REQ-14)."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        teaser_obj = _teaser_for(request, pk)
        field_name = request.data.get("field") or request.data.get("field_name")
        
        with transaction.atomic():
            teaser = _locked(teaser_obj.pk)
            now = timezone.now()
            
            if field_name:
                TeaserField.objects.filter(teaser=teaser, field_name=field_name).update(approved_at=now)
            elif "fields" in request.data:
                for f in request.data["fields"]:
                    TeaserField.objects.filter(teaser=teaser, field_name=f).update(approved_at=now)
            
            teaser.updated_at = now
            teaser.save(update_fields=["updated_at"])
        
        return _respond(teaser)


class TeaserApproveView(APIView):
    """POST /api/decks/{id}/teaser/approve/ — утверждение всего тизера (Declaration A)."""
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        teaser_obj = _teaser_for(request, pk)
        now = timezone.now()
        
        with transaction.atomic():
            teaser = _locked(teaser_obj.pk)
            user = request.user
            
            legal_doc = LegalDocument.objects.filter(code="A").order_by("-version").first()
            consent = UserConsent.objects.create(
                user=user,
                legal_document=legal_doc,
                accepted_at=now,
            )
            
            teaser.fields.filter(approved_at__isnull=True).update(approved_at=now)
            
            teaser.status = TeaserStatus.APPROVED
            teaser.approved_at = now
            teaser.declaration_consent = consent
            teaser.is_current = True
            teaser.save(update_fields=["status", "approved_at", "declaration_consent", "is_current", "updated_at"])
            
            profile = teaser.startup_profile
            if profile.status == "DRAFT":
                profile.went_live_at = now
                profile.status = "LIVE"
                profile.save(update_fields=["went_live_at", "status", "updated_at"])
            
            track(EventName.TEASER_APPROVED, user=user, teaser_id=teaser.pk, version=teaser.version)
        
        return _respond(teaser)



class DeckDraftView(APIView):
    """
    GET /api/decks/{id}/draft/ (или /api/profile/deck/draft/)
    Статус и черновик тизера. Фронтенд опрашивает этот эндпоинт, пока
    state не станет DRAFT_READY или FAILED.
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        # Чужой или удалённый дек вернёт 404
        pitch_deck = get_object_or_404(
            PitchDeck.objects.select_related("startup_profile")
            .prefetch_related("teaser__fields")
            .filter(
                startup_profile__user=request.user,
                deleted_at__isnull=True,
            ),
            pk=pk,
        )

        response = Response(TeaserDraftSerializer(pitch_deck).data)
        # Запрещаем кэширование (содержит конфиденциальные данные стартапа)
        response["Cache-Control"] = "no-store"
        return response