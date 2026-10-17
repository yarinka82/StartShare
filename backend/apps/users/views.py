from django.contrib.auth import  get_user_model
from django.contrib.auth import authenticate, login, logout, update_session_auth_hash
from django.middleware.csrf import get_token

from rest_framework import viewsets
from rest_framework.permissions import IsAdminUser
from rest_framework.exceptions import ValidationError
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .serializers import UserSerializer, UserCreateSerializer, UserUpdateSerializer
from .serializers import ChangePasswordSerializer


User = get_user_model()

# ---- Auth: login / logout / current user ----

class LoginView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        # Заменяет @ensure_csrf_cookie: выдает свежий CSRF-токен в куки
        get_token(request)

        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': "Вкажіть ім'я користувача та пароль."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = authenticate(request, username=username, password=password)
        if user is None:
            return Response(
                {'detail': "Невірне ім'я користувача або пароль."},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        login(request, user)
        return Response({
            'id': user.id,
            'username': user.username,
            'is_staff': user.is_staff,
        })


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)


class MeView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        # Принудительно генерирует и отправляет csrf-токен в куки
        get_token(request)

        if not request.user.is_authenticated:
            return Response({'id': None, 'username': None, 'is_staff': False})

        return Response({
            'id': request.user.id,
            'username': request.user.username,
            'is_staff': request.user.is_staff,
        })


# ---- Self-service password change (any authenticated user) ----

class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()

        # Сохраняем сессию активной после смены хеша пароля
        update_session_auth_hash(request, user)

        return Response({'detail': 'Пароль оновлено.'})


# ---- User management (staff only) ----

class UserViewSet(viewsets.ModelViewSet):
    """
    List, create, update, and deactivate users. Restricted to staff
    accounts — an ordinary member should not be able to see or manage
    the user list.
    """
    queryset = User.objects.all().order_by('username')
    permission_classes = [IsAdminUser]

    def get_serializer_class(self):
        if self.action == 'create':
            return UserCreateSerializer
        if self.action in ('update', 'partial_update'):
            return UserUpdateSerializer
        return UserSerializer

    def perform_update(self, serializer):
        instance = serializer.instance
        # Prevent an admin from demoting or deactivating their own account —
        # otherwise a single click could lock everyone out of user management.
        if instance.pk == self.request.user.pk:
            new_is_staff = serializer.validated_data.get('is_staff', instance.is_staff)
            new_is_active = serializer.validated_data.get('is_active', instance.is_active)
            if not new_is_staff or not new_is_active:
                raise ValidationError(
                    "Ви не можете зняти з себе права адміністратора "
                    "або деактивувати власний обліковий запис."
                )
        serializer.save()
    
    def perform_destroy(self, instance):
        # Prevent an admin from deleting their own account.
        if instance.pk == self.request.user.pk:
            raise ValidationError('Ви не можете видалити власний обліковий запис.')
        instance.delete()