
from rest_framework import viewsets, permissions
from rest_framework.parsers import MultiPartParser, FormParser
from .models import PitchDeck
from .serializers import PitchDeckSerializer

class PitchDeckViewSet(viewsets.ModelViewSet):
    serializer_class = PitchDeckSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]
    http_method_names = ["get", "post"]  # замена файла — отдельный ТЗ, пока только upload

    def get_queryset(self):
        return PitchDeck.objects.filter(startup__user=self.request.user)

    def perform_create(self, serializer):
        profile = self.request.user.startupprofile
        serializer.save(startup=profile)