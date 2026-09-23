from django.urls import path, include
from rest_framework.routers import SimpleRouter
from . import views
from .views import LoginView, LogoutView, MeView, ChangePasswordView

router = SimpleRouter()
router.register(r'', views.UserViewSet, basename='user')

urlpatterns = [
    # auth
    path('auth/login/', LoginView.as_view(), name='login'),
    path('auth/logout/', LogoutView.as_view(), name='logout'),
    path('auth/me/', MeView.as_view(), name='me'),
    path('auth/change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # user management (staff only)
    path('users/', include(router.urls)),
]