from django.urls import path

from .views import SubmitReportView
from ..matching.intro_views import StartupIntrosListView, StartupIntroRespondView

urlpatterns = [
    path("intros/", StartupIntrosListView.as_view(), name="startup-intros-list"),

    # Відповідь стартапу (Freigabe або Nein)
    path("intros/<str:public_id>/respond/", StartupIntroRespondView.as_view(),
         name="startup-intro-respond"),
    path("<str:public_id>/report/", SubmitReportView.as_view(), name="startup-report"),
]