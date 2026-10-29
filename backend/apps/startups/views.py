from django.conf import settings
from django.core.mail import send_mail
from rest_framework import viewsets, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from common.models import ReportType
from .models import StartupProfile, Report, ReportStatus
from .serializers import ReportSubmitSerializer
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
        profile = StartupProfile.objects.filter(public_id=public_id).first()
        if not profile:
            return Response({"detail": "Startup not found."}, status=status.HTTP_404_NOT_FOUND)

        # Захист від повторної скарги від того ж юзера (UniqueConstraint)
        if Report.objects.filter(startup_profile=profile, reporter_user=request.user).exists():
            return Response(
                {"detail": "Ви вже надіслали скаргу на цей профіль. Вона перебуває на розгляді."},
                status=status.HTTP_409_CONFLICT,
            )

        serializer = ReportSubmitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        type_code = serializer.validated_data["report_type_code"]
        report_type = ReportType.objects.filter(code=type_code).first()
        if not report_type:
            report_type = ReportType.objects.first()  # або дефолтний тип

        report = Report.objects.create(
            startup_profile=profile,
            reporter_user=request.user,
            report_type=report_type,
            description=serializer.validated_data["description"],
            status=ReportStatus.OPEN,
        )

        # Обов'язкове миттєве підтвердження на e-mail за ст. 16.5 DSA
        try:
            send_mail(
                subject="Start Share: Bestätigung Ihrer Meldung (Art. 16 DSA)",
                message=(
                    f"Guten Tag,\n\n"
                    f"wir haben Ihre Meldung bezüglich des Profils #{profile.public_id} erhalten "
                    f"und werden diese unverzüglich prüfen.\n\n"
                    f"Meldungs-ID: #{report.id}\n\n"
                    f"Mit freundlichen Grüßen,\nStart Share Compliance Team"
                ),
                from_email=getattr(settings, "DEFAULT_FROM_EMAIL", "compliance@startshare.de"),
                recipient_list=[request.user.email],
                fail_silently=True,
            )
        except Exception:
            pass

        return Response({"status": "received", "report_id": report.id}, status=status.HTTP_201_CREATED)
        
