from django.contrib import admin
from django.urls import include, path
from apps.startups.views import ChoicesMetaView

urlpatterns = [
    path("admin/", admin.site.urls),

    # Авторизація
    path("api/auth/", include("apps.accounts.urls")),

    # Довідники (сектори, стадії)
    path("api/dictionaries/", ChoicesMetaView.as_view(), name="dictionaries"),

    # Профіль та завантаження деку (/api/profile/ та /api/profile/deck/)
    path("api/profile/", include("apps.profiles.urls")),
    path("api/startups/", include("apps.startups.urls")),

    # Інвестор
    path("api/investor/", include("apps.investors.urls")),

    # Тизери та ШІ (/api/decks/<id>/draft/ тощо)
    path("api/", include("apps.documents.urls")),
]