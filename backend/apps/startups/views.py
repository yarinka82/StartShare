
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
        def to_options(choices_list):
            return [{"code": c[0], "name": str(c[1])} for c in (choices_list or [])]

        def get_field_choices(field_name):
            try:
                field = StartupProfile._meta.get_field(field_name)
                return getattr(field, "choices", []) or []
            except Exception:
                return []

        # 1. Регіони: імпортуємо клас Region (який очікують тести інвестора)
        regions_list = []
        try:
            from apps.investors.models import Region
            regions_list = Region.choices
        except Exception:
            try:
                from apps.startups.models import Region
                regions_list = Region.choices
            except Exception:
                regions_list = [
                    ("dach", "DACH"),
                    ("eu", "EU"),
                    ("europe", "Europe"),
                    ("worldwide", "Worldwide"),
                ]

        # 2. Країни (з бази або дефолтні у нижньому регістрі)
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
                {"code": "de", "name": "Germany (Deutschland)"},
                {"code": "at", "name": "Austria (Österreich)"},
                {"code": "ch", "name": "Switzerland (Schweiz)"},
                {"code": "gb", "name": "United Kingdom"},
                {"code": "us", "name": "United States"},
                {"code": "eu", "name": "Other European Union"},
                {"code": "other", "name": "Other"},
            ]

        # 3. Періоди росту (MoM, QoQ, YoY)
        growth_periods = get_field_choices("growth_period")
        if not growth_periods:
            growth_periods = [
                ("mom", "MoM (Month over month)"),
                ("qoq", "QoQ (Quarter over quarter)"),
                ("yoy", "YoY (Year over year)"),
            ]

        return Response({
            "sectors": to_options(get_field_choices("sector")),
            "stages": to_options(get_field_choices("stage")),
            "business_models": to_options(get_field_choices("business_model")),
            "regions": to_options(regions_list),  # <-- ТЕПЕР ПОВЕРТАЄ ['dach', 'eu', 'europe', 'worldwide']
            "growth_periods": to_options(growth_periods),
            "countries": countries,
        })