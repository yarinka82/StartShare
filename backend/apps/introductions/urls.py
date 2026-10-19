from django.urls import path

from .views import (
    IntroductionAcceptView,
    IntroductionDeclineView,
    IntroductionFreigabeView,
    IntroductionInterestView,
    IntroductionNeinView,
    IntroductionStartupDeclineView,
    StartupIntroductionRequestDetailView,
    StartupIntroductionRequestListView,
)

urlpatterns = [
    path("introductions/<int:pk>/interest/", IntroductionInterestView.as_view(), name="intro-interest"),
    path("introductions/<int:pk>/decline/", IntroductionDeclineView.as_view(), name="intro-decline"),
    path("introductions/<int:pk>/accept/", IntroductionAcceptView.as_view(), name="intro-accept"),
    path("introductions/<int:pk>/freigabe/", IntroductionFreigabeView.as_view(), name="intro-freigabe"),
    path("introductions/<int:pk>/nein/", IntroductionNeinView.as_view(), name="intro-nein"),
    path("introductions/<int:pk>/startup-decline/", IntroductionStartupDeclineView.as_view(), name="intro-startup-decline"),
    path("introductions/requests/", StartupIntroductionRequestListView.as_view(), name="startup-intro-requests"),
    path("introductions/requests/<int:pk>/", StartupIntroductionRequestDetailView.as_view(), name="startup-intro-request-detail"),
]
