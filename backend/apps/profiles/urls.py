from django.urls import path
from .views import DeckView, ProfileView

urlpatterns = [
    # GET /api/profile/ та PATCH /api/profile/
    path("", ProfileView.as_view(), name="profile"),

    # GET, POST, DELETE /api/profile/deck/ (ОСЬ ВАШ DeckView)
    path("deck/", DeckView.as_view(), name="profile-deck"),
]
