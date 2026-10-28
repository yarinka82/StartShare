from django.urls import path

from . import views
from .staff_views import (StaffReportsListView, StaffReportDecisionView, StaffUsersListView,
                          StaffToggleUserActiveView, StaffConsentsListView, StaffEventsListView,
                          StaffPlatformConfigView, StaffPublishLegalDocView, StaffLegalDocumentsListView)
    

urlpatterns = [
    path("csrf/", views.CsrfView.as_view()),
    path("register/", views.RegisterView.as_view()),
    path("verify-email/", views.VerifyEmailView.as_view()),
    path("resend-verification/", views.ResendVerificationView.as_view()),
    path("login/", views.LoginView.as_view()),
    path("logout/", views.LogoutView.as_view()),
    path("me/", views.MeView.as_view()),
    path("password-reset/", views.PasswordResetRequestView.as_view()),
    path("password-reset/confirm/", views.PasswordResetConfirmView.as_view()),
    path("legal-documents/", views.ActiveLegalDocumentsView.as_view(), name="legal-documents-active"),
    path("export-data/", views.ExportUserDataView.as_view(), name="auth-export-data"),
    path("delete-account/", views.DeleteAccountView.as_view(), name="auth-delete-account"),
    path("staff/reports/", StaffReportsListView.as_view(), name="staff-reports-list"),
    path("staff/reports/<int:pk>/decide/", StaffReportDecisionView.as_view(), name="staff-report-decide"),
    path("staff/users/", StaffUsersListView.as_view(), name="staff-users"),
    path("staff/users/<int:pk>/toggle-active/", StaffToggleUserActiveView.as_view(),
         name="staff-toggle-user"),
    path("staff/consents/", StaffConsentsListView.as_view(), name="staff-consents"),
    path("staff/events/", StaffEventsListView.as_view(), name="staff-events"),
    path("staff/config/", StaffPlatformConfigView.as_view(), name="staff-config"),
    path("staff/legal-documents/publish/", StaffPublishLegalDocView.as_view(),
         name="staff-publish-legal-doc"),
    path("staff/legal-documents/", StaffLegalDocumentsListView.as_view(),
         name="staff-legal-docs-manage"),
]
