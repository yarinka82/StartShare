
from rest_framework import viewsets, permissions


from .models import StartupProfile
from ..profiles.serializers import ProfileSerializer


class StartupProfileViewSet(viewsets.ModelViewSet):
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch"]  # без delete — по ТЗ профиль паузится/removed, а не удаляется физически

    def get_queryset(self):
        return StartupProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != "startup":
            raise permissions.PermissionDenied("Только пользователь с ролью startup может создать профиль.")
        serializer.save(user=self.request.user)
        
        
