from django.conf import settings
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core import signing
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode
from django.views.decorators.csrf import csrf_protect, ensure_csrf_cookie
from rest_framework import status
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
        try:
            uid = read_verify_token(s.validated_data["token"])
        except signing.BadSignature:  # includes SignatureExpired
            return Response({"detail": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        user = User.objects.filter(pk=uid).first()
        if user is None:
            return Response({"detail": "invalid_or_expired_token"}, status=status.HTTP_400_BAD_REQUEST)
        if user.email_verified_at is None:
            user.email_verified_at = timezone.now()
            user.save(update_fields=["email_verified_at"])
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
        user.save(update_fields=["password"])
        return Response({"detail": "password_changed"})
