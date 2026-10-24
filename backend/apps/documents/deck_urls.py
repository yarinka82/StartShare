from django.urls import path

from apps.documents.views import DeckView, DeckDownloadView

urlpatterns = [
    # GET, POST, DELETE /api/profile/deck/
    path("", DeckView.as_view(), name="profile-deck"),
    path("download/", DeckDownloadView.as_view(), name="profile-deck-download"),
]