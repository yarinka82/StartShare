from django.urls import path

from .teaser.views import DeckDraftView, TeaserApproveView, TeaserReviewView, TeaserView

urlpatterns = [
    path("decks/<int:pk>/draft/", DeckDraftView.as_view(), name="deck-draft"),
    path("decks/<int:pk>/teaser/", TeaserView.as_view(), name="teaser"),
    path("decks/<int:pk>/teaser/review/", TeaserReviewView.as_view(), name="teaser-review"),
    path("decks/<int:pk>/teaser/approve/", TeaserApproveView.as_view(), name="teaser-approve"),
]