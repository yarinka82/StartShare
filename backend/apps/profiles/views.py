import os
import re

from django.db import transaction
from django.http import FileResponse
from rest_framework import status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BusinessModel, Country, Deck, Sector, Stage, StartupProfile
from .permissions import IsVerifiedStartup
from .serializers import (
    DeckSerializer,
    DeckUploadSerializer,
    DictionaryItemSerializer,
    StartupProfileSerializer,
)


def get_profile(user):
    return StartupProfile.objects.get_or_create(user=user)[0]


class DictionariesView(APIView):
    """All list values for the profile form in one request."""

    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        def items(model):
            return DictionaryItemSerializer(model.objects.filter(is_active=True), many=True).data

        return Response(
            {
                "sectors": items(Sector),
                "stages": items(Stage),
                "business_models": items(BusinessModel),
                "countries": items(Country),
                "growth_periods": [{"code": c, "name": n} for c, n in StartupProfile.GrowthPeriod.choices],
            }
        )


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

        with transaction.atomic():
            deck = getattr(profile, "deck", None) or Deck(profile=profile)
            old_name = deck.file.name if deck.pk and deck.file else None
            deck.file = upload
            deck.original_name = re.sub(r"[\x00-\x1f]", "", os.path.basename(upload.name))[:255]
            deck.size = upload.size
            deck.status = Deck.Status.OK  # TODO: PENDING until the ClamAV scan finishes
            deck.save()
            if old_name and old_name != deck.file.name:
                deck.file.storage.delete(old_name)  # replacing: remove the previous file
        return Response(DeckSerializer(deck).data, status=status.HTTP_201_CREATED)

    def delete(self, request):
        deck = getattr(get_profile(request.user), "deck", None)
        if deck is None:
            return Response(status=status.HTTP_404_NOT_FOUND)
        deck.delete()  # post_delete signal removes the file
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
