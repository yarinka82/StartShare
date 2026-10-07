
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



from ..models import Teaser, TeaserJob, Deck
from .contract import FIELD_NAMES
from .editing import approval_blockers, refresh_phrases, risky_fields, validate_content
from .leak_check import terms_from_profile
from .serializers import TeaserDraftSerializer, TeaserSerializer


class Conflict(APIException):
    status_code = 409
    default_detail = "Conflict."
    default_code = "conflict"


def _teaser_for(request, pk) -> Teaser:
    deck = get_object_or_404(Deck.objects.filter(profile__user=request.user), pk=pk)
    job = TeaserJob.objects.filter(deck=deck).first()
    if job is None:
        raise NotFound("No teaser job for this deck.")
    if job.state != TeaserJob.State.DRAFT_READY:
        raise Conflict(f"Draft is not ready (state: {job.state}).", code="draft_not_ready")
    teaser, _ = Teaser.objects.get_or_create(
        job=job, defaults={"content": dict(job.draft["teaser"]), "risk_phrases": list(job.risk_phrases)})
    return teaser


def _locked(teaser_id) -> Teaser:
    teaser = Teaser.objects.select_for_update().select_related("job__deck__profile").get(pk=teaser_id)
    if teaser.status == Teaser.Status.APPROVED:
        raise Conflict("Teaser is already approved and locked.", code="already_approved")
    return teaser


def _respond(teaser: Teaser) -> Response:
    response = Response(TeaserSerializer(teaser).data)
    response["Cache-Control"] = "no-store"
    return response


def _field_list(request) -> list[str]:
    fields = request.data.get("fields")
    if not isinstance(fields, list) or not fields or not all(isinstance(f, str) for f in fields):
        raise ValidationError({"fields": "A non-empty list of field names is required."})
    unknown = [f for f in fields if f not in FIELD_NAMES]
    if unknown:
        raise ValidationError({"fields": f"Unknown fields: {', '.join(unknown)}."})
    return fields


class TeaserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        return _respond(_teaser_for(request, pk))

    def patch(self, request, pk):
        """Тело: {"fields": {"problem": "новый текст"}}. Правка снимает подтверждение с изменённого поля."""
        patch = request.data.get("fields")
        if not isinstance(patch, dict) or not patch:
            raise ValidationError({"fields": "An object {field: text} is required."})
        bad = {k: "Unknown field." for k in patch if k not in FIELD_NAMES}
        bad.update({k: "Must be a string." for k, v in patch.items() if k in FIELD_NAMES and not isinstance(v, str)})
        if bad:
            raise ValidationError({"fields": bad})

        teaser = _teaser_for(request, pk)
        with transaction.atomic():
            teaser = _locked(teaser.pk)
            new = {**teaser.content, **{k: v.strip() for k, v in patch.items()}}
            errors = validate_content(new)
            if errors:
                raise ValidationError({"fields": errors})
            changed = [k for k in patch if new[k] != teaser.content[k]]
            if changed:
                profile = teaser.job.deck.profile
                teaser.content = new
                teaser.edited = sorted(set(teaser.edited) | set(changed))
                teaser.reviewed = [f for f in teaser.reviewed if f not in changed]
                teaser.risk_phrases = refresh_phrases(new, teaser.risk_phrases, terms_from_profile(profile))
                teaser.save()
        for name in changed:
            track(EventName.FIELD_EDITED, user=request.user, field=name)  # только название поля, без текста
        return _respond(teaser)


class TeaserReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        """Тело: {"fields": ["headline", ...]}. Ручное подтверждение полей (REQ-14)."""
        fields = _field_list(request)
        teaser = _teaser_for(request, pk)
        with transaction.atomic():
            teaser = _locked(teaser.pk)
            risky = risky_fields(teaser.risk_phrases)
            errors = {}
            for f in fields:
                if not (teaser.content.get(f) or "").strip():
                    errors[f] = "empty_field"
                elif f in risky:
                    errors[f] = "risk_found"
            if errors:
                raise ValidationError({"fields": errors})
            teaser.reviewed = sorted(set(teaser.reviewed) | set(fields))
            teaser.save()
        return _respond(teaser)


class TeaserApproveView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request, pk):
        """Тело: {"declaration_a": true}. Идемпотентно: повтор после затверждения даёт 200 без нового события."""
        if request.data.get("declaration_a") is not True:
            raise ValidationError({"declaration_a": "Declaration A must be accepted."})
        
        teaser = _teaser_for(request, pk)
        if teaser.status == Teaser.Status.APPROVED:
            return _respond(teaser)
        
        with transaction.atomic():
            try:
                teaser = _locked(teaser.pk)
            except Conflict:  # параллельный запрос успел раньше
                return _respond(Teaser.objects.get(pk=teaser.pk))
            
            blockers = approval_blockers(teaser.content, teaser.reviewed, teaser.risk_phrases)
            if blockers:
                raise ValidationError({"detail": "Teaser is not ready for approval.", "blockers": blockers})
            
            now = timezone.now()
            teaser.status = Teaser.Status.APPROVED
            teaser.declaration_a_accepted_at = now
            teaser.approved_at = now
            teaser.save()
            
            # -------------------------------------------------------------
            # 1. ПЕРЕВОДИМО ПРОФІЛЬ СТАРТАПУ В СТАТУС LIVE (за ТЗ)
            # -------------------------------------------------------------
            profile = getattr(request.user, "startup_profile", getattr(request.user, "startupprofile", None))
            if profile and profile.status == "DRAFT":
                profile.status = "LIVE"
                profile.save(update_fields=["status"])
            
            # -------------------------------------------------------------
            # 2. ВИДАЛЯЄМО ОРИГІНАЛ PDF З ДИСКА (за ТЗ)
            # -------------------------------------------------------------
            deck = getattr(profile, "deck", None)
            if deck and deck.file and deck.file.name:
                file_name = deck.file.name
                storage = deck.file.storage
                deck.file = ""  # не None: поле NOT NULL
                deck.save(update_fields=["file"])
                # физически удаляем только после успешного коммита транзакции
                transaction.on_commit(lambda: storage.delete(file_name))
        
        # Трекінг аналітики
        track(EventName.TEASER_APPROVED, user=request.user)
        track(EventName.WENT_LIVE, user=request.user)
        
        return _respond(teaser)



class DeckDraftView(APIView):
    """GET /decks/{id}/draft/: статус и чернетка. Фронтенд опрашивает, пока state не станет DRAFT_READY или FAILED."""
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, pk):
        deck = get_object_or_404(Deck.objects.filter(profile__user=request.user), pk=pk)  # чужая дека: 404
        job = TeaserJob.objects.filter(deck=deck).first()
        if job is None:
            raise NotFound("No teaser job for this deck.")
        response = Response(TeaserDraftSerializer(job).data)
        response["Cache-Control"] = "no-store"  # внутри данные, по которым можно узнать компанию
        return response