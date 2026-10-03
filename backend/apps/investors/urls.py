from django.urls import path

from . import views

urlpatterns = [
    path("", views.InvestorStateView.as_view()),
    path("confirm-status/", views.ConfirmStatusView.as_view()),
    path("mandate/", views.MandateView.as_view()),
]
