import json

from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.analytics.events import track
from apps.analytics.models import EventName

from .emails import read_verify_token, send_password_reset_email, send_verification_email
from .models import  UserConsent, LegalDocumentCode, LegalDocument
from .serializers import (
    LoginSerializer,
    MeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegisterSerializer,
    ResendVerificationSerializer,
    VerifyEmailSerializer,
)
from ..startups.models import StartupProfileRemovedBy

User = get_user_model()


@method_decorator(csrf_protect, name="dispatch")
class PublicPostView(APIView):
    """Unauthenticated POST endpoint, CSRF-protected (token from /api/auth/csrf/)."""

    authentication_classes = []
    permission_classes = [AllowAny]


@method_decorator(ensure_csrf_cookie, name="dispatch")
class CsrfView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({"detail": "ok"})



class LoginView(PublicPostView):
    throttle_scope = "login"

    def post(self, request):
        s = LoginSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = authenticate(
            request, username=s.validated_data["email"], password=s.validated_data["password"]
        )
        if user is None:
            return Response({"detail": "invalid_credentials"}, status=status.HTTP_400_BAD_REQUEST)
        if not user.is_email_verified:
            return Response({"detail": "email_not_verified"}, status=status.HTTP_403_FORBIDDEN)
        login(request, user)
        return Response(MeSerializer(user).data)



class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        logout(request)
        return Response(status=status.HTTP_204_NO_CONTENT)



class MeView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(MeSerializer(request.user).data)


class RegisterView(PublicPostView):
    throttle_scope = "register"

    def post(self, request):
        # 1. Валідуємо дані та передаємо context запиту для мультиязичності
        s = RegisterSerializer(data=request.data, context={"request": request})
        s.is_valid(raise_exception=True)
        data = s.validated_data

        # Захист від перебору акаунтів (Anti Account Enumeration)
        if not User.objects.filter(email__iexact=data["email"]).exists():
            with transaction.atomic():
                # 2. Створюємо користувача
                user = User.objects.create_user(
                    email=data["email"],
                    password=data["password"],
                    role=data["role"]
                )

                # 3. Знаходимо чинні редакції AGB та Datenschutzerklärung (DSE)
                # Використовуємо get_or_create, щоб у тестах і на старті документи завжди існували
                agb_doc, _ = LegalDocument.objects.get_or_create(
                    code=LegalDocumentCode.AGB,
                    language="de",
                    defaults={
                        "version": 1,
                        "title": "Allgemeine Geschäftsbedingungen",
                        "body": "AGB Text..."
                    }
                )

                dse_doc, _ = LegalDocument.objects.get_or_create(
                    code=getattr(LegalDocumentCode, "DATENSCHUTZ", getattr(LegalDocumentCode, "DSE", "datenschutz")),
                    language="de",
                    defaults={
                        "version": 1,
                        "title": "Datenschutzerklärung",
                        "body": "Datenschutz Text..."
                    }
                )

                # 4. Записуємо юридичну згоду у версіоновану таблицю user_consents
                UserConsent.objects.bulk_create([
                    UserConsent(user=user, legal_document=agb_doc, context=UserConsent.Context.REGISTRATION),
                    UserConsent(user=user, legal_document=dse_doc, context=UserConsent.Context.REGISTRATION),
                ])

            # 5. Аналітика та лист підтвердження (DOI)
            track(EventName.REGISTERED, user, role=user.role)
            send_verification_email(user)

        return Response({"detail": "check_email"}, status=status.HTTP_201_CREATED)



class VerifyEmailView(PublicPostView):
    throttle_scope = "verify"

    def post(self, request):
        s = VerifyEmailSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        payload = read_verify_token(s.validated_data["token"])
        if payload is None:
            return Response({"detail": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)

        # the e-mail is part of the token: a link issued for an old address no longer works
        user = User.objects.filter(
            pk=payload["uid"], email__iexact=payload["email"], is_active=True
        ).first()
        if user is None:
            return Response({"detail": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
            # first confirmation: the person has just registered, so continue in a session right away
            login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return Response({"detail": "verified"})



class ResendVerificationView(PublicPostView):
    throttle_scope = "resend"

    def post(self, request):
        s = ResendVerificationSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=s.validated_data["email"], is_active=True, email_verified_at__isnull=True
        ).first()
        if user:
            send_verification_email(user)
        return Response({"detail": "check_email"})  # same answer in every case



class PasswordResetRequestView(PublicPostView):
    throttle_scope = "password_reset"

    def post(self, request):
        s = PasswordResetRequestSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        user = User.objects.filter(email__iexact=s.validated_data["email"], is_active=True).first()
        if user:
            send_password_reset_email(user)
        return Response({"detail": "check_email"})



class PasswordResetConfirmView(PublicPostView):
    throttle_scope = "password_reset"

    def post(self, request):
        s = PasswordResetConfirmSerializer(data=request.data)
        s.is_valid(raise_exception=True)
        d = s.validated_data
        try:
            user = User.objects.get(pk=force_str(urlsafe_base64_decode(d["uid"])))
        except (User.DoesNotExist, ValueError, TypeError, OverflowError):
            user = None
        if user is None or not default_token_generator.check_token(user, d["token"]):
            return Response({"detail": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(d["new_password"], user=user)
        except DjangoValidationError as e:
            return Response({"new_password": list(e.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(d["new_password"])
        fields = ["password"]
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
            fields.append("email_verified_at")
        user.save(update_fields=fields)
        return Response({"detail": "password_changed"})
    
    
    
class ActiveLegalDocumentsView(APIView):
    """Повертає найсвіжіші діючі тексти документів A-G, AGB, DSE."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        lang = request.query_params.get("lang", "de")
        # Беремо чинні документи (де valid_to порожній)
        docs = LegalDocument.objects.filter(language=lang, valid_to__isnull=True).order_by("code", "-version")

        result = {}
        for d in docs:
            code_key = d.code.upper()
            if code_key not in result:
                result[code_key] = {
                    "code": d.code,
                    "version": d.version,
                    "title": d.title,
                    "body": d.body,
                    "language": d.language,
                }
        return Response(result)



class ExportUserDataView(APIView):
    """
    GET /api/auth/export-data/
    Вивантаження всіх персональних даних користувача в JSON (Art. 20 DSGVO).
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user

        # 1. Загальні дані акаунта
        export_data = {
            "account": {
                "id": str(user.id),
                "email": user.email,
                "role": user.role,
                "preferred_language": user.preferred_language,
                "created_at": user.created_at.isoformat() if hasattr(user, "created_at") else None,
                "email_verified_at": user.email_verified_at.isoformat() if user.email_verified_at else None,
            },
            # 2. Журнал юридичних згод (AGB, DSE, декларації)
            "legal_consents": [
                {
                    "document_code": c.legal_document.code,
                    "document_title": c.legal_document.title,
                    "version": c.legal_document.version,
                    "context": c.context,
                    "accepted_at": c.accepted_at.isoformat(),
                }
                for c in UserConsent.objects.filter(user=user).select_related("legal_document")
            ],
        }

        # 3. Дані в залежності від ролі:
        if user.role == "startup":
            profile = getattr(user, "startup_profile", getattr(user, "startupprofile", None))
            if profile:
                export_data["startup_profile"] = {
                    "public_id": str(profile.public_id),
                    "status": profile.status,
                    "sector": str(profile.sector_id),
                    "stage": str(profile.stage_id),
                    "country": str(profile.country_id),
                    "business_model": str(profile.business_model_id),
                    "round_amount_eur": str(profile.round_amount_eur),
                    "mrr_eur": str(profile.mrr_eur) if profile.mrr_eur else None,
                    "team_size": profile.team_size,
                    "created_at": profile.created_at.isoformat(),
                }

        elif user.role == "investor":
            inv_profile = getattr(user, "investor_profile", None)
            if inv_profile:
                from apps.investors.models import Mandate
                mandates = Mandate.objects.filter(investor_profile=inv_profile).order_by("-version")
                export_data["investor_mandates_history"] = [
                    {
                        "version": m.version,
                        "is_current": m.is_current,
                        "check_min_eur": str(m.check_min_eur),
                        "check_max_eur": str(m.check_max_eur),
                        "sector_codes": m.sector_codes,
                        "stage_codes": m.stage_codes,
                        "country_codes": m.country_codes,
                        "created_at": m.created_at.isoformat(),
                    }
                    for m in mandates
                ]

        # Формуємо JSON-файл для завантаження
        response = HttpResponse(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            content_type="application/json; charset=utf-8",
        )
        response["Content-Disposition"] = f'attachment; filename="startshare_data_export_{user.id}.json"'
        return response
    

    
class DeleteAccountView(APIView):
    """
    POST /api/auth/delete-account/
    Повне видалення акаунта та анонімізація за Art. 17 DSGVO.
    Вимагає передачі поточного пароля {"password": "..."}.
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get("password")
        if not password:
            return Response({"password": "Для видалення акаунта необхідно підтвердити пароль."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if not user.check_password(password):
            return Response({"password": "Невірний пароль."}, status=status.HTTP_400_BAD_REQUEST)

        now = timezone.now()

        with transaction.atomic():
            # 1. Якщо це стартап — очищаємо приватні дані, стираємо деки та переводимо в REMOVED
            profile = getattr(user, "startup_profile", getattr(user, "startupprofile", None))
            if profile:
                profile.status = "REMOVED"
                profile.removed_at = now
                profile.removed_by = StartupProfileRemovedBy.STARTUP
                profile.save()

                # Стираємо конфіденційні назви компанії
                if hasattr(profile, "private_details"):
                    profile.private_details.delete()

                # Фізично видаляємо завантажені файли презентацій з диска
                for deck in profile.pitch_decks.all():
                    if deck.file:
                        deck.file.delete(save=False)
                    deck.deleted_at = now
                    deck.save(update_fields=["file", "deleted_at"])

            # 2. Якщо це інвестор — архівуємо мандати
            inv_profile = getattr(user, "investor_profile", None)
            if inv_profile:
                inv_profile.mandates.all().update(is_current=False)

            # 3. Анонімізуємо самого користувача (Art. 17 DSGVO)
            # Замінюємо реальний e-mail на знеособлений хеш, вимикаємо вхід
            user.email = f"deleted_{user.id}_{int(now.timestamp())}@anonymized.invalid"
            user.is_active = False
            user.deleted_at = now
            user.set_unusable_password()
            user.save(update_fields=["email", "is_active", "deleted_at", "password"])

            # 4. Завершуємо сесію
            logout(request)

        return Response({"status": "deleted", "detail": "Account successfully erased."}, status=status.HTTP_200_OK)