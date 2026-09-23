from django.urls import path
from . import views

urlpatterns = [
    path('', views.MemberListView.as_view(), name='member-list'),
    path('add/', views.member_create, name='member-add'),
    path('<int:pk>/', views.MemberDetailView.as_view(), name='member-detail'),
    path('<int:pk>/edit/', views.member_edit, name='member-edit'),
]
