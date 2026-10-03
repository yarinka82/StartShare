
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import ChoicesMetaView, StartupProfileViewSet

router = DefaultRouter()
# Реєструємо ViewSet для профілів
router.register(r"profiles", StartupProfileViewSet, basename="startup-profile")

urlpatterns = [
    # Ендпоінт для отримання довідників (сектори, стадії)
    path("choices/", ChoicesMetaView.as_view(), name="startup-choices"),
    
    # Роути для профілю (/api/startups/profiles/ та /api/startups/profiles/{id}/)
    path("", include(router.urls)),
]