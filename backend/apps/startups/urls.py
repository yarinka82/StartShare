
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StartupProfileViewSet, SubmitReportView
from ..profiles.views import DictionariesView

router = DefaultRouter()
# Реєструємо ViewSet для профілів (/api/startups/profiles/)
router.register(r"profiles", StartupProfileViewSet, basename="startup-profile")

urlpatterns = [
    # Ендпоінт для отримання довідників (/api/startups/choices/ або /api/startups/dictionaries/)
    path("choices/", DictionariesView.as_view(), name="startup-choices"),
    path("dictionaries/", DictionariesView.as_view(), name="startup-dictionaries"),
    path("<uuid:public_id>/report/", SubmitReportView.as_view(), name="startup-report"),
    # Роути для профілю (/api/startups/profiles/ та /api/startups/profiles/{id}/)
    path("", include(router.urls)),
]