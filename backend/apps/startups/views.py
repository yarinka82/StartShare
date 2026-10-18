from django.conf import settings
from django.core.mail import send_mail
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import ReportType
from .models import StartupProfile, Report, ReportStatus
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
