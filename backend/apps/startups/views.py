
from rest_framework import viewsets, permissions
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.profiles.models import StartupProfile
from .serializers import ProfileSerializer

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
        
        
class ChoicesMetaView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        # Допоміжна функція перетворення в [{code: "...", name: "..."}, ...] для фронтенду
        def to_options(choices_list):
            return [{"code": c[0], "name": str(c[1])} for c in (choices_list or [])]

        # 1. Отримуємо choices безпечно через _meta поля моделі
        def get_field_choices(field_name):
            try:
                field = StartupProfile._meta.get_field(field_name)
                return getattr(field, "choices", []) or []
            except Exception:
                return []

        # 2. Країни (якщо є модель Country, беремо з бази, інакше дефолтний список)
        countries = []
        try:
            from apps.startups.models import Country
            countries = [
                {"code": c.code, "name": c.name}
                for c in Country.objects.all().order_by("id")
            ]
        except Exception:
            pass

        if not countries:
            countries = [
                {"code": "DE", "name": "Germany (Deutschland)"},
                {"code": "AT", "name": "Austria (Österreich)"},
                {"code": "CH", "name": "Switzerland (Schweiz)"},
                {"code": "GB", "name": "United Kingdom"},
                {"code": "US", "name": "United States"},
                {"code": "EU", "name": "Other European Union"},
                {"code": "OTHER", "name": "Other Country"},
            ]

        # 3. Періоди росту (MoM, QoQ, YoY)
        growth_periods = get_field_choices("growth_period")
        if not growth_periods:
            growth_periods = [
                ("mom", "MoM (Month over month)"),
                ("qoq", "QoQ (Quarter over quarter)"),
                ("yoy", "YoY (Year over year)"),
            ]

        # Формуємо повну відповідь, яку очікує React-фронтенд
        return Response({
            "sectors": to_options(get_field_choices("sector")),
            "stages": to_options(get_field_choices("stage")),
            "business_models": to_options(get_field_choices("business_model")),
            "regions": to_options(get_field_choices("region")),
            "growth_periods": to_options(growth_periods),
            "countries": countries,
        })