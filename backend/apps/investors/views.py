from decimal import Decimal
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.accounts.models import LegalDocument, LegalDocumentCode, UserConsent
from apps.analytics.events import track
from apps.analytics.models import EventName
from common.models import InvestorType, Country

# Импортируйте новые модели
from .models import InvestorProfile, Mandate, MandateSource
from .permissions import IsConfirmedInvestor, IsVerifiedInvestor, is_status_confirmed
from .serializers import ConfirmStatusSerializer, MandateOutSerializer, MandateSerializer

# Актуальный список полей новой модели
MANDATE_FIELDS = (
    "sector_codes",
    "stage_codes",
    "country_codes",
    "region_codes",
    "business_model_codes",
    "check_min_eur",
    "check_max_eur",
)


def snapshot(data_or_instance) -> dict:
    """
    Приводит параметры мандата (из модели или словаря) к каноническому виду для сравнения.
    Списки сортируются, Decimal форматируются в строки с 2 знаками.
    """
    out = {}
    is_model = isinstance(data_or_instance, Mandate)

    for field in MANDATE_FIELDS:
        val = getattr(data_or_instance, field) if is_model else data_or_instance.get(field)

        if field.startswith("check_"):
            # Приводим к строке вида '10000.00'
            out[field] = f"{Decimal(str(val)):.2f}" if val is not None else "0.00"
        else:
            # Сортируем списки кодов, чтобы сравнение ['AI', 'B2B'] == ['B2B', 'AI'] было равным
            out[field] = sorted(list(val)) if val else []

    return out


def build_state(user) -> dict:
    """Формирует текущее состояние инвестора: подтверждение Текста C и активный мандат."""
    consent = (
        UserConsent.objects.filter(
            user=user,
            context=UserConsent.Context.INVESTOR_STATUS,
        )
        .order_by("accepted_at")
        .first()
    )

    # Ищем профиль и его текущий активный мандат
    profile = getattr(user, "investor_profile", None)
    mandate = (
        Mandate.objects.filter(investor_profile=profile, is_current=True).first()
        if profile
        else None
    )

    return {
        "status_confirmed": consent is not None,
        "status_confirmed_at": consent.accepted_at if consent else None,
        "mandate": MandateOutSerializer(mandate).data if mandate else None,
    }


class InvestorStateView(APIView):
    """Кабинет инвестора: подтвержден ли статус и параметры активного мандата."""

    permission_classes = [IsVerifiedInvestor]

    def get(self, request):
        return Response(build_state(request.user))


class ConfirmStatusView(APIView):
    """Подтверждение статуса инвестора (Текст C)."""

    permission_classes = [IsVerifiedInvestor]

    def post(self, request):
        s = ConfirmStatusSerializer(data=request.data)
        s.is_valid(raise_exception=True)

        if not is_status_confirmed(request.user):
            with transaction.atomic():
                doc_c, _ = LegalDocument.objects.get_or_create(
                    code=getattr(LegalDocumentCode, "C", getattr(LegalDocumentCode, "INVESTOR_STATUS", "c")),
                    language="de",
                    defaults={"version": 1, "title": "Text C", "body": "Investor Status Text"},
                )
                consent = UserConsent.objects.create(
                    user=request.user,
                    legal_document=doc_c,
                    context=UserConsent.Context.INVESTOR_STATUS,
                )

                # Если в профиле есть поле status_consent, привязываем его
                profile = getattr(request.user, "investor_profile", None)
                if profile and hasattr(profile, "status_consent"):
                    profile.status_consent = consent
                    profile.save(update_fields=["status_consent"])

                track(EventName.STATUS_CONFIRMED, request.user)

        return Response(build_state(request.user))


class MandateView(APIView):
    """
    PUT: Сохранение мандата.
    Первое сохранение -> создание version=1 и событие MANDATE_SAVED.
    Последующие изменения -> создание новой версии (version+1) и событие MANDATE_CHANGED.
    """

    permission_classes = [IsConfirmedInvestor]

    def put(self, request):
        serializer = MandateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        profile, _ = InvestorProfile.objects.get_or_create(
            user=request.user,
            defaults={
                "organization_name": getattr(request.user, "first_name", "") or "Individual Investor",
                "investor_type": InvestorType.objects.first(),
                "country": Country.objects.first(),
                "contact_person_name": getattr(request.user, "first_name", "") or request.user.email,
                "contact_email": request.user.email,
            },
        )
        # -------------------------------------------------------------

        with transaction.atomic():
            current_mandate = (
                Mandate.objects.select_for_update()
                .filter(investor_profile=profile, is_current=True)
                .first()
            )

            after = snapshot(data)

            # 1. ПЕРВОЕ СОЗДАНИЕ (версия 1)
            if current_mandate is None:
                mandate = Mandate.objects.create(
                    investor_profile=profile,
                    version=1,
                    is_current=True,
                    source=MandateSource.MANUAL,
                    **data,
                )
                track(EventName.MANDATE_SAVED, request.user, **after)
                return Response(MandateOutSerializer(mandate).data, status=status.HTTP_201_CREATED)

            # 2. ПРОВЕРКА ИЗМЕНЕНИЙ
            before = snapshot(current_mandate)

            # Если данные не изменились — не плодим версии, просто отдаем текущий мандат
            if before == after:
                return Response(MandateOutSerializer(current_mandate).data)

            # 3. ДАННЫЕ ИЗМЕНИЛИСЬ — СОЗДАЕМ НОВУЮ ВЕРСИЮ
            # Архивация предыдущего мандата
            current_mandate.is_current = False
            current_mandate.save(update_fields=["is_current"])

            # Создание новой версии
            new_mandate = Mandate.objects.create(
                investor_profile=profile,
                version=current_mandate.version + 1,
                is_current=True,
                source=MandateSource.MANUAL,
                **data,
            )

            changed = [f for f in MANDATE_FIELDS if before[f] != after[f]]
            track(EventName.MANDATE_CHANGED, request.user, source="self", changed=changed, **after)

        return Response(MandateOutSerializer(new_mandate).data)
