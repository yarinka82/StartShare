from django.utils import timezone
from rest_framework import permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.serializers import PlatformConfigSerializer
from apps.accounts.models import User, UserConsent, UserRole, LegalDocument, PlatformConfig
from apps.analytics.models import Event
from apps.investors.models import Mandate
from apps.startups.models import Report, ReportDecision, ReportStatus



class IsStaff(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated and (request.user.is_staff or request.user.role == "staff"))



class StaffReportsListView(APIView):
    """GET /api/staff/reports/ — список усіх скарг для модератора."""
    permission_classes = [IsStaff]
    
    def get(self, request):
        status_filter = request.query_params.get("status", "OPEN")
        reports = Report.objects.select_related("startup_profile", "reporter_user", "report_type").order_by(
            "-created_at")
        
        if status_filter != "ALL":
            reports = reports.filter(status=status_filter)
        
        data = []
        for r in reports:
            data.append({
                "id": r.id,
                "startup_public_id": str(r.startup_profile.public_id),
                "startup_sector": str(r.startup_profile.sector_id),
                "startup_stage": str(r.startup_profile.stage_id),
                "startup_status": r.startup_profile.status,
                "moderation_hidden": bool(r.startup_profile.moderation_hidden_at),
                "reporter_email": r.reporter_user.email if r.reporter_user else "Anonymous",
                "report_type": r.report_type.name if hasattr(r.report_type, "name") else str(r.report_type_id),
                "description": r.description,
                "status": r.status,
                "decision": r.decision,
                "created_at": r.created_at.isoformat(),
            })
        return Response(data)



class StaffReportDecisionView(APIView):
    """
    POST /api/staff/reports/<int:pk>/decide/
    Прийняття рішення модератором: 'no_action' | 'profile_hidden' | 'profile_removed'
    """
    permission_classes = [IsStaff]
    
    def post(self, request, pk):
        report = Report.objects.filter(pk=pk).first()
        if not report:
            return Response({"detail": "Report not found."}, status=status.HTTP_404_NOT_FOUND)
        
        decision = request.data.get("decision")  # "no_action", "profile_hidden", "profile_removed"
        note = (request.data.get("decision_note") or "").strip()
        
        if decision not in ReportDecision.values:
            return Response({"detail": "Invalid decision."}, status=status.HTTP_400_BAD_REQUEST)
        
        now = timezone.now()
        report.status = ReportStatus.RESOLVED
        report.decision = decision
        report.decision_note = note
        report.decided_by_user = request.user
        report.decided_at = now
        report.reporter_notified_at = now  # DSA Art. 16.6
        report.save()
        
        sp = report.startup_profile
        if decision == ReportDecision.PROFILE_HIDDEN:
            sp.moderation_hidden_at = now
            sp.save(update_fields=["moderation_hidden_at"])
        elif decision == ReportDecision.PROFILE_REMOVED:
            sp.status = "REMOVED"
            sp.removed_at = now
            sp.removed_by = "staff"
            sp.save(update_fields=["status", "removed_at", "removed_by"])
        
        return Response({"status": "resolved", "decision": decision})
    
    
# ТАБ: КОРИСТУВАЧІ ТА ІНВЕСТОРИ
class StaffUsersListView(APIView):
    """GET /api/staff/users/ — список користувачів, їхні ролі, статус та мандати."""
    permission_classes = [IsStaff]

    def get(self, request):
        role_filter = request.query_params.get("role")
        users = User.objects.all().order_by("-created_at")
        if role_filter:
            users = users.filter(role=role_filter)

        data = []
        for u in users:
            item = {
                "id": u.id,
                "email": u.email,
                "role": u.role,
                "is_active": u.is_active,
                "is_test": u.is_test,
                "preferred_language": u.preferred_language,
                "created_at": u.created_at.isoformat() if hasattr(u, "created_at") else None,
                "email_verified": bool(u.email_verified_at),
            }
            # Якщо це інвестор, додаємо інфо про профіль та діючий мандат
            inv_profile = getattr(u, "investor_profile", None)
            if inv_profile:
                item["organization_name"] = inv_profile.organization_name
                current_mandate = Mandate.objects.filter(investor_profile=inv_profile, is_current=True).first()
                if current_mandate:
                    item["mandate"] = {
                        "version": current_mandate.version,
                        "check_range": f"€{int(current_mandate.check_min_eur):,} – €{int(current_mandate.check_max_eur):,}",
                        "sectors": current_mandate.sector_codes,
                        "stages": current_mandate.stage_codes,
                    }
            data.append(item)
        return Response(data)



class StaffToggleUserActiveView(APIView):
    """
    POST /api/staff/users/<id>/toggle-active/
    Дозволяє staff блокувати/розблоковувати інвесторів та стартапи.
    Суворо забороняє блокувати себе або інших співробітників/адміністраторів платформи.
    """
    permission_classes = [IsStaff]

    def post(self, request, pk):
        target_user = User.objects.filter(pk=pk).first()
        if not target_user:
            return Response({"detail": "User not found."}, status=status.HTTP_404_NOT_FOUND)

        # 1. ЗАХИСТ ВІД САМОБЛОКУВАННЯ
        if target_user.id == request.user.id:
            return Response(
                {"detail": "Ви не можете заблокувати власний обліковий запис."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 2. ЗАХИСТ КОЛЕГ-СПІВРОБІТНИКІВ ТА СУПЕРКОРИСТУВАЧІВ
        is_target_staff = (
            target_user.is_staff
            or getattr(target_user, "role", None) == UserRole.STAFF
            or target_user.is_superuser
        )
        if is_target_staff:
            return Response(
                {"detail": "Заборонено блокувати співробітників платформи або адміністраторів."},
                status=status.HTTP_403_FORBIDDEN,
            )

        # 3. ПЕРЕМИКАННЯ АКТИВНОСТІ (Тільки для інвесторів та стартапів)
        target_user.is_active = not target_user.is_active
        target_user.save(update_fields=["is_active"])

        return Response({
            "id": target_user.id,
            "email": target_user.email,
            "is_active": target_user.is_active,
            "status": "active" if target_user.is_active else "blocked",
        })


# ТАБ: ЖУРНАЛ АУДИТУ ЗГОД (Art. 7 DSGVO)
class StaffConsentsListView(APIView):
    """GET /api/staff/consents/ — журнал прийняття AGB, DSE та декларацій A і C."""
    permission_classes = [IsStaff]

    def get(self, request):
        consents = UserConsent.objects.select_related("user", "legal_document").order_by("-accepted_at")[:100]
        data = [
            {
                "id": c.id,
                "user_email": c.user.email,
                "document_code": c.legal_document.code,
                "document_version": c.legal_document.version,
                "context": c.context,
                "accepted_at": c.accepted_at.isoformat(),
            }
            for c in consents
        ]
        return Response(data)


# 3. ТАБ: ЖУРНАЛ ПОДІЙ (Append-Only Event Stream)
class StaffEventsListView(APIView):
    """GET /api/staff/events/ — стрічка подій аналітики (хто завантажив дек, затвердив тизер тощо)."""
    permission_classes = [IsStaff]

    def get(self, request):
        events = Event.objects.all().order_by("-created_at")[:100]
        data = [
            {
                "id": e.id,
                "name": e.name,
                "role": getattr(e, "role", "-"),
                "user_id": str(e.user_id) if hasattr(e, "user_id") else "-",
                "properties": e.properties if hasattr(e, "properties") else {},
                "created_at": e.created_at.isoformat() if hasattr(e, "created_at") else None,
            }
            for e in events
        ]
        return Response(data)



class StaffPlatformConfigView(APIView):
    """
    GET /api/staff/config/ — віддає налаштування та каталог провайдерів.
    PATCH /api/staff/config/ — валідує і зберігає через PlatformConfigSerializer.
    """
    permission_classes = [IsStaff]

    def get(self, request):
        cfg = PlatformConfig.get_solo()
        serializer = PlatformConfigSerializer(cfg)
        return Response(serializer.data)

    def patch(self, request):
        cfg = PlatformConfig.get_solo()
        serializer = PlatformConfigSerializer(cfg, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)



class StaffPublishLegalDocView(APIView):
    """
    POST /api/staff/legal-documents/publish/
    Публікація нової версії тексту (A-G, AGB, DSE) без перезапуску сайту.
    """
    permission_classes = [IsStaff]

    def post(self, request):
        code = request.data.get("code")
        language = request.data.get("language", "de")
        title = request.data.get("title", "")
        body = request.data.get("body", "").strip()

        if not code or not body:
            return Response({"detail": "Код документа та текст є обов'язковими."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        # 1. Знаходимо останню версію і архівуємо її
        current = LegalDocument.objects.filter(code=code, language=language, valid_to__isnull=True).order_by("-version").first()
        new_version = 1
        if current:
            current.valid_to = now
            current.save(update_fields=["valid_to"])
            new_version = current.version + 1

        # 2. Створюємо нову чинну версію (v+1)
        new_doc = LegalDocument.objects.create(
            code=code,
            language=language,
            version=new_version,
            title=title or current.title if current else f"Doc {code}",
            body=body,
            legal_approved_at=now,
            valid_from=now,
        )

        return Response({
            "status": "published",
            "code": new_doc.code,
            "version": new_doc.version,
            "valid_from": new_doc.valid_from.isoformat()
        }, status=status.HTTP_201_CREATED)
    

    
class StaffLegalDocumentsListView(APIView):
    """
    GET /api/auth/staff/legal-documents/ — список усіх версій текстів.
    POST /api/auth/staff/legal-documents/ — публікація нової версії (v+1).
    """
    permission_classes = [IsStaff]

    def get(self, request):
        docs = LegalDocument.objects.all().order_by("code", "language", "-version")
        data = [
            {
                "id": d.id,
                "code": d.code,
                "code_display": d.get_code_display() if hasattr(d, "get_code_display") else d.code,
                "language": d.language,
                "version": d.version,
                "title": d.title,
                "body": d.body,
                "is_current": d.valid_to is None and d.valid_from is not None,
                "valid_from": d.valid_from.isoformat() if d.valid_from else None,
                "valid_to": d.valid_to.isoformat() if d.valid_to else None,
                "created_at": d.created_at.isoformat() if hasattr(d, "created_at") else None,
            }
            for d in docs
        ]
        return Response(data)

    def post(self, request):
        code = request.data.get("code")
        language = request.data.get("language", "de")
        title = (request.data.get("title") or "").strip()
        body = (request.data.get("body") or "").strip()

        if not code or not body:
            return Response(
                {"detail": "Код документа та текст є обов'язковими."},
                status=status.HTTP_400_BAD_REQUEST
            )

        now = timezone.now()

        # 1. Знаходимо поточну версію і архівуємо її (закриваємо valid_to)
        current = (
            LegalDocument.objects.filter(code=code, language=language, valid_to__isnull=True)
            .order_by("-version")
            .first()
        )
        new_version = 1
        if current:
            current.valid_to = now
            current.save(update_fields=["valid_to"])
            new_version = current.version + 1

        # 2. Створюємо нову чинну версію
        new_doc = LegalDocument.objects.create(
            code=code,
            language=language,
            version=new_version,
            title=title or (current.title if current else f"Dokument {code}"),
            body=body,
            legal_approved_at=now,
            valid_from=now,
        )

        return Response({
            "status": "published",
            "id": new_doc.id,
            "code": new_doc.code,
            "version": new_doc.version,
            "language": new_doc.language,
        }, status=status.HTTP_201_CREATED)
    
    
    