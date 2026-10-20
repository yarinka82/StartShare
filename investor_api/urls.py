from django.urls import path

from .views import (
    IntroductionDecisionView,
    CriterionSuggestionDecisionView,
)

urlpatterns = [
    path(
        "introductions/<str:public_id>/decision/",
        IntroductionDecisionView.as_view(),
        name="introduction-decision",
    ),   # endpoint для решения «Цікаво» или «Ні».
path(
        "criterion-suggestions/<int:pk>/decision/",
        CriterionSuggestionDecisionView.as_view(),
        name="criterion-suggestion-decision",
    ),   # endpoint для принятия или отклонения предложения изменить критерий.
]