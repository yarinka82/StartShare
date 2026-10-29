from django.contrib import admin
from django.urls import include, path

from apps.startups.views import ChoicesMetaView


urlpatterns = [
    path("admin/", admin.site.urls),

    # Авторизация
    path("api/auth/", include("apps.accounts.urls")),

    # Стартапы
    path("api/startups/", include("apps.startups.urls")),

    # Профиль
    path("api/", include("apps.profiles.urls")),



    # Инвестор
    path("api/investors/", include("apps.investors.urls")),

    # Pitch decks
    path("api/", include("apps.documents.urls")),
]
