from django.urls import path
from rest_framework.routers import DefaultRouter

from apps.documents.teaser.views import TeaserApproveView, TeaserReviewView, TeaserView
from .views import PitchDeckViewSet

router = DefaultRouter()
router.register("decks", PitchDeckViewSet, basename="deck")

urlpatterns = [
                  path("decks/<int:pk>/teaser/", TeaserView.as_view(), name="teaser"),
                  path("decks/<int:pk>/teaser/review/", TeaserReviewView.as_view(), name="teaser-review"),
                  path("decks/<int:pk>/teaser/approve/", TeaserApproveView.as_view(), name="teaser-approve"),
              ] + router.urls