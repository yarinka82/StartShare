from django.urls import path

from . import views

urlpatterns = [
    path("dictionaries/", views.DictionariesView.as_view()),
    path("profile/", views.ProfileView.as_view()),
    path("profile/deck/", views.DeckView.as_view()),
    path("profile/deck/download/", views.DeckDownloadView.as_view()),
]
