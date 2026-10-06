from django.urls import path
from .teaser.views import DeckDraftView, TeaserApproveView, TeaserReviewView, TeaserView

urlpatterns = [
    # Опитування статусу ШІ (Polling у TeaserPage)
    path("decks/<int:pk>/draft/", DeckDraftView.as_view(), name="deck-draft"),

    # Отримання та редагування полів (GET, PATCH у TeaserEditor)
    path("decks/<int:pk>/teaser/", TeaserView.as_view(), name="teaser"),

    # Підтвердження окремого поля (POST у FieldCard)
    path("decks/<int:pk>/teaser/review/", TeaserReviewView.as_view(), name="teaser-review"),

    # Фінальне затвердження з Декларацією A (POST approve)
    path("decks/<int:pk>/teaser/approve/", TeaserApproveView.as_view(), name="teaser-approve"),
]