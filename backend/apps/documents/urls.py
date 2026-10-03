
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import PitchDeckViewSet

router = DefaultRouter()
# Реєструємо ViewSet для маршруту /decks/
router.register(r"decks", PitchDeckViewSet, basename="deck")

urlpatterns = [
    path("", include(router.urls)),
]