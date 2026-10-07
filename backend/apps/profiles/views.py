import os
import re

from django.db import transaction
from django.http import FileResponse
from rest_framework import status, permissions
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import Sector, Stage, BusinessModel, Country, Region
from .permissions import IsVerifiedStartup

from ..analytics.services import can_replace_deck, start_teaser_job
from ..documents.models import Deck
from ..documents.serializers import DeckSerializer, DeckUploadSerializer
from ..startups.models import StartupProfile
from ..startups.serializers import StartupProfileSerializer

GROWTH_PERIODS = [
    {"code": "mom", "name": "MoM (Month over month)"},
    {"code": "qoq", "name": "QoQ (Quarter over quarter)"},
    {"code": "yoy", "name": "YoY (Year over year)"},
]

def get_profile(user):
    return StartupProfile.objects.get_or_create(user=user)[0]


def serialize_reference(queryset, lang: str = "de"):
    """Допоміжна функція: перетворює QuerySet ReferenceModel у список {code, name, is_other}."""
    name_field = "name_en" if lang.startswith("en") else "name_de"
    result = []
    for item in queryset:
        data = {
            "code": item.code,
            "name": getattr(item, name_field, item.name_de),
        }
        # Якщо в моделі є поле is_other (для Sector та BusinessModel)
        if hasattr(item, "is_other"):
            data["is_other"] = item.is_other
        result.append(data)
    return result


class DictionariesView(APIView):
    """Повертає всі довідники для стартапів та інвесторів в одному запиті."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "sectors": [
                {"code": s.code, "name": s.name_de}
                for s in Sector.objects.filter(is_active=True)
            ],
            "stages": [
                {"code": s.code, "name": s.name_de}
                for s in Stage.objects.filter(is_active=True)
            ],
            "business_models": [
                {"code": b.code, "name": b.name_de}
                for b in BusinessModel.objects.filter(is_active=True)
            ],
            "regions": [
                {"code": r.code, "name": r.name_de}
                for r in Region.objects.filter(is_active=True)
            ],
            "countries": [
                {"code": c.code, "name": c.name_de}
                for c in Country.objects.filter(is_active=True)
            ],
            "growth_periods": GROWTH_PERIODS,
        })



class ProfileView(RetrieveUpdateAPIView):
    """GET / PUT / PATCH: PUT is also partial, so the form can autosave a draft."""

    permission_classes = [IsVerifiedStartup]
    serializer_class = StartupProfileSerializer

    def get_object(self):
        return get_profile(self.request.user)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)



class DeckView(APIView):
    permission_classes = [IsVerifiedStartup]
    parser_classes = [MultiPartParser]
    
    def get(self, request):
        deck = getattr(get_profile(request.user), "deck", None)
        if deck is None:
            return Response({"detail": "no_deck"}, status=status.HTTP_404_NOT_FOUND)
        return Response(DeckSerializer(deck).data)
    
    def post(self, request):
        s = DeckUploadSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        upload = s.validated_data["file"]
        profile = get_profile(request.user)
        
        if not can_replace_deck(profile):  # затверждённый тизер каскадом не теряем
            return Response({"detail": "teaser_approved"}, status=status.HTTP_409_CONFLICT)
        
        with transaction.atomic():
            deck = getattr(profile, "deck", None) or Deck(profile=profile)
            old_name = deck.file.name if deck.pk and deck.file else None
            deck.file = upload
            deck.original_name = re.sub(r"[\x00-\x1f]", "", os.path.basename(upload.name))[:255]
            deck.size = upload.size
            deck.status = Deck.Status.OK  # TODO: PENDING until the ClamAV scan finishes
            deck.save()
            start_teaser_job(deck, request.user)  # новая задача обработки (при замене старая сбрасывается)
        if old_name and old_name != deck.file.name:
            deck.file.storage.delete(old_name)  # replacing: старый файл удаляем уже после коммита
        return Response(DeckSerializer(deck).data, status=status.HTTP_201_CREATED)
    
    def delete(self, request):
        profile = get_profile(request.user)
        deck = getattr(profile, "deck", None)
        if deck is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        if not can_replace_deck(profile):
            return Response({"detail": "teaser_approved"}, status=status.HTTP_409_CONFLICT)
        deck.delete()  # post_delete signal removes the file; TeaserJob и Teaser удаляются каскадом
        return Response(status=status.HTTP_204_NO_CONTENT)



class DeckDownloadView(APIView):
    """Owner-only download. Files are never exposed through a public URL."""

    permission_classes = [IsVerifiedStartup]

    def get(self, request):
        deck = getattr(get_profile(request.user), "deck", None)
        if deck is None:
            return Response({"detail": "no_deck"}, status=status.HTTP_404_NOT_FOUND)
        response = FileResponse(
            deck.file.open("rb"), as_attachment=True, filename=deck.original_name,
            content_type="application/pdf",
        )
        response["X-Content-Type-Options"] = "nosniff"
        return response
