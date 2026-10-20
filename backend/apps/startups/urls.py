
from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import StartupProfileViewSet, SubmitReportView
from ..matching.intro_views import StartupIntrosListView, StartupIntroRespondView
from ..profiles.views import DictionariesView

router = DefaultRouter()
router.register(r"profiles", StartupProfileViewSet, basename="startup-profile")

urlpatterns = [
    # Ендпоінт для отримання довідників (/api/startups/choices/ або /api/startups/dictionaries/)
    path("choices/", DictionariesView.as_view(), name="startup-choices"),
    path("dictionaries/", DictionariesView.as_view(), name="startup-dictionaries"),
    path("intros/", StartupIntrosListView.as_view(), name="startup-intros-list"),
    
    # Відповідь стартапу (Freigabe або Nein)
    path("intros/<str:public_id>/respond/", StartupIntroRespondView.as_view(),
         name="startup-intro-respond"),
    path("<str:public_id>/report/", SubmitReportView.as_view(), name="startup-report"),
    # Роути для профілю (/api/startups/profiles/ та /api/startups/profiles/{id}/)
    path("", include(router.urls)),
]