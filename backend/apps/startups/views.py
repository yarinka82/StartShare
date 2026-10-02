
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import StartupProfile
from .serializers import StartupProfileSerializer

class StartupProfileViewSet(viewsets.ModelViewSet):
    serializer_class = StartupProfileSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch"]  # без delete — по ТЗ профиль паузится/removed, а не удаляется физически

    def get_queryset(self):
        return StartupProfile.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.role != "startup":
            raise permissions.PermissionDenied("Только пользователь с ролью startup может создать профиль.")
        serializer.save(user=self.request.user)
        
        
class ChoicesMetaView(APIView):
    def get(self, request):
        return Response({
            "sectors": StartupProfile.Sector.choices,
            "stages": StartupProfile.Stage.choices,
        })