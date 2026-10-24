from django.contrib import admin
from django.urls import include, path

from apps.documents.views import DeckDownloadView, DeckView
from apps.startups.views import DictionariesView, ProfileView


urlpatterns = [
    path("admin/", admin.site.urls),
    # Авторизація
    path("api/auth/", include("apps.accounts.urls")),
    # Довідники (сектори, стадії)
    path("api/dictionaries/", DictionariesView.as_view(), name="dictionaries"),
    # Профіль та завантаження деку (/api/profile/ та /api/profile/deck/)
    path("api/profile/deck/download/", DeckDownloadView.as_view(), name="profile-deck-download"),
    path("api/profile/deck/", DeckView.as_view(), name="profile-deck"),
    path("api/profile/", ProfileView.as_view(), name="profile"),
    
    path("api/startups/", include("apps.startups.urls")),
    # Інвестор
    path("api/investor/", include("apps.investors.urls")),
    # Тизери та ШІ (/api/decks/<id>/draft/ тощо)
    path("api/", include("apps.documents.urls")),
]