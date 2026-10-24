from django.conf import settings
from django.core.mail import send_mail
from rest_framework import permissions, status
from rest_framework.generics import RetrieveUpdateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import ReportType, Sector, Stage, BusinessModel, Region, Country, InvestorType
from .models import StartupProfile, Report, ReportStatus
from .permissions import IsVerifiedStartup
from .serializers import StartupProfileSerializer


GROWTH_PERIODS = [
    {"code": "mom", "name": "MoM (Month over month)"},
    {"code": "qoq", "name": "QoQ (Quarter over quarter)"},
    {"code": "yoy", "name": "YoY (Year over year)"},
]

def get_profile(user):
    return StartupProfile.objects.get_or_create(user=user)[0]


def serialize_reference(queryset, lang: str = "de"):
    """Допоміжна функція: перетворює QuerySet ReferenceModel у список {code, name, is_other}."""
    name_field = "name_en" if lang.startswith("en") else "name_de"
    result = []
    for item in queryset:
        data = {
            "code": item.code,
            "name": getattr(item, name_field, item.name_de),
        }
        # Якщо в моделі є поле is_other (для Sector та BusinessModel)
        if hasattr(item, "is_other"):
            data["is_other"] = item.is_other
        result.append(data)
    return result



class DictionariesView(APIView):
    """Повертає всі довідники для стартапів та інвесторів в одному запиті."""

    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            "sectors": [
                {"code": s.code, "name": s.name_de}
                for s in Sector.objects.filter(is_active=True)
            ],
            "stages": [
                {"code": s.code, "name": s.name_de}
                for s in Stage.objects.filter(is_active=True)
            ],
            "business_models": [
                {"code": b.code, "name": b.name_de}
                for b in BusinessModel.objects.filter(is_active=True)
            ],
            "regions": [
                {"code": r.code, "name": r.name_de}
                for r in Region.objects.filter(is_active=True)
            ],
            "countries": [
                {"code": c.code, "name": c.name_de}
                for c in Country.objects.filter(is_active=True)
            ],
            "growth_periods": GROWTH_PERIODS,
            "investor_types": [
                {"code": t.code, "name": t.name_de}
                for t in InvestorType.objects.filter(is_active=True)
            ],
        })



class ProfileView(RetrieveUpdateAPIView):
    """GET / PUT / PATCH: PUT is also partial, so the form can autosave a draft."""

    permission_classes = [IsVerifiedStartup]
    serializer_class = StartupProfileSerializer

    def get_object(self):
        return get_profile(self.request.user)

    def put(self, request, *args, **kwargs):
        return self.partial_update(request, *args, **kwargs)
    
    

class SubmitReportView(APIView):
    """
    POST /api/startups/<public_id>/report/
    Фіксує скаргу інвестора на профіль за ст. 16 DSA.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, public_id):
        profile = None

        # 1. Пробуємо знайти напряму за ID чи public_id стартапу
        if str(public_id).isdigit():
            profile = StartupProfile.objects.filter(pk=int(public_id)).first()
        else:
            profile = StartupProfile.objects.filter(public_id=public_id).first()

        # 🚀 2. Якщо це UUID зі сліпої картки дайджесту — знаходимо через Introduction:
        if not profile:
            try:
                from apps.investors.models import Introduction
                intro = Introduction.objects.filter(public_id=public_id).select_related("startup_profile").first()
                if intro:
                    profile = intro.startup_profile
            except Exception:
                pass

        if not profile:
            return Response({"detail": "Startup not found."}, status=status.HTTP_404_NOT_FOUND)

        # Захист від повторної скарги від того самого юзера (UniqueConstraint)
        if Report.objects.filter(startup_profile=profile, reporter_user=request.user).exists():
            return Response(
                {"detail": "Ви вже надіслали скаргу на цей профіль. Вона перебуває на розгляді."},
                status=status.HTTP_409_CONFLICT,
            )

        # 3. Підтримуємо обидві назви полів (explanation / description та reason_category / report_type_code)
        description = (
            request.data.get("description")
            or request.data.get("explanation")
            or ""
        ).strip()

        type_code = (
            request.data.get("report_type_code")
            or request.data.get("reason_category")
            or "other"
        )

        good_faith = request.data.get("declaration_good_faith", False)
        if not good_faith:
            return Response(
                {"declaration_good_faith": "Підтвердження сумлінності є обов'язковим за ст. 16 DSA."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if len(description) < 10:
            return Response(
                {"explanation": "Будь ласка, вкажіть більш детальне обґрунтування (мінімум 10 символів)."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Знаходимо або створюємо тип скарги
        report_type = ReportType.objects.filter(code=type_code).first()
        if not report_type:
            report_type, _ = ReportType.objects.get_or_create(
                code=type_code,
                defaults={"code": type_code.capitalize()}
            )

        # 4. Створюємо скаргу
        report = Report.objects.create(
            startup_profile=profile,
            reporter_user=request.user,
            report_type=report_type,
            description=description,
            status=ReportStatus.OPEN,
        )

        # 5. Обов'язкове миттєве підтвердження на e-mail за ст. 16.5 DSA
        recipient_email = request.data.get("reporter_email") or request.user.email
        try:
            send_mail(
                subject="Start Share: Bestätigung Ihrer Meldung (Art. 16 DSA)",
                message=(
                    f"Guten Tag,\n\n"
                    f"wir haben Ihre Meldung bezüglich des Profils #{profile.public_id} erhalten "
                    f"und werden diese unverzüglich im Rahmen unserer gesetzlichen Pflichten nach dem Digital Services Act prüfen.\n\n"
                    f"Meldungs-ID: #{report.id}\n\n"
                    f"Mit freundlichen Grüßen,\nStart Share Compliance Team"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "compliance@startshare.de"),
                recipient_list=[recipient_email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({"status": "received", "report_id": report.id}, status=status.HTTP_201_CREATED)
