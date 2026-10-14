from django.urls import path

from . import views

urlpatterns = [
    path("", views.InvestorStateView.as_view(), name="investor-state"),
    path("confirm-status/", views.ConfirmStatusView.as_view(), name="confirm-status"),
    path("mandate/", views.MandateView.as_view(), name="mandate"),
    path("mandate/history/", views.MandateHistoryView.as_view(), name="mandate-history"),
    path("feed/", views.InvestorFeedView.as_view(), name="investor-feed"),
    path("cards/action/", views.CardActionView.as_view(), name="card-action"),
]
