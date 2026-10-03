
from django.db import transaction
from django.conf import settings
from django.db import transaction
from rest_framework import permissions, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.parsers import FormParser, MultiPartParser
from rest_framework.response import Response

from apps.analytics.models import EventName
from apps.analytics.services import track

from .models import PitchDeck, TeaserJob
from .serializers import PitchDeckSerializer
from .tasks import process_deck
from .teaser.serializers import TeaserDraftSerializer


class PitchDeckViewSet(viewsets.ModelViewSet):
    serializer_class = PitchDeckSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post"]  # замена файла — отдельный ТЗ, пока только upload

    def get_queryset(self):
        return PitchDeck.objects.filter(startup__user=self.request.user).select_related("job")
    
    def perform_create(self, serializer):
        # Шукаємо профіль стартапу безвідносно до назви зв'язку
        profile = getattr(
            self.request.user,
            "startup_profile",
            getattr(self.request.user, "startupprofile", None)
        )
        
        # Якщо через зв'язок не знайшло, шукаємо прямим запитом
        if profile is None:
            try:
                from apps.startups.models import StartupProfile
                profile = StartupProfile.objects.get(user=self.request.user)
            except Exception:
                raise PermissionDenied("Only startups can upload a pitch deck.")
        
        if PitchDeck.objects.filter(startup=profile).exists():
            raise ValidationError({"file": "Дек уже загружен. Замена файла пока не поддерживается."})
        
        deck = serializer.save(startup=profile)
        job = TeaserJob.objects.create(deck=deck)
        track(EventName.DECK_UPLOADED, user=self.request.user, file_size_bytes=deck.file.size)
        
        # Якщо це тести — запускаємо синхронно, інакше — через чергу Celery
        if getattr(settings, "CELERY_TASK_ALWAYS_EAGER", False):
            process_deck(job.id)
        else:
            transaction.on_commit(lambda: process_deck.delay(job.id))

    @action(detail=True, methods=["get"], url_path="draft")
    def draft(self, request, pk=None):
        """GET /decks/{id}/draft/: статус и чернетка. Фронтенд опрашивает, пока state не станет DRAFT_READY или FAILED."""
        deck = self.get_object()  # чужая дека даёт 404 через get_queryset
        job = TeaserJob.objects.filter(deck=deck).first()
        if job is None:
            raise NotFound("No teaser job for this deck.")
        response = Response(TeaserDraftSerializer(job).data)
        response["Cache-Control"] = "no-store"  # внутри данные, по которым можно узнать компанию
        return response