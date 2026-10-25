from django.utils import timezone
from django.db import transaction
from rest_framework import status
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError as DRFValidationError
from rest_framework.views import APIView
from decimal import Decimal

from apps.accounts.models import LegalDocument, LegalDocumentCode, UserConsent
from apps.analytics.events import track
from apps.analytics.models import EventName, Event
from apps.investors.services.intro_emails import send_intro_request_to_startup
from common.models import InvestorType, Country, DeclineReason
from .models import InvestorProfile, Mandate, MandateSource, Digest, DigestCard, Introduction
from .permissions import IsConfirmedInvestor, IsVerifiedInvestor, is_status_confirmed
from .serializers import ConfirmStatusSerializer, MandateOutSerializer, MandateSerializer, InvestorProfileSerializer
from .services.intro_state_machine import transition_introduction
from  apps.investors.tasks import build_first_digest
from .validators import validate_investor_message

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
    """Формирует текущее состояние инвестора: подтверждение Текста C, профиль и активный мандат."""
    # импорт внутри функции: сериализатор профиля может импортировать этот модуль
    from .serializers import InvestorProfileSerializer

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
        "profile": InvestorProfileSerializer(profile).data if profile else None,
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
    GET: Отримання діючого мандату (is_current=True).
    PUT: Збереження мандату з версіонуванням [B].
    """
    permission_classes = [IsConfirmedInvestor]
    
    def get(self, request):
        profile = getattr(request.user, "investor_profile", None)
        if not profile:
            return Response({"detail": "profile_required"}, status=status.HTTP_409_CONFLICT)
        current = Mandate.objects.filter(investor_profile=profile, is_current=True).first()
        if not current:
            return Response(None)
        return Response(MandateOutSerializer(current).data)
    
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
                # the first digest does not wait for Monday; a broker failure is logged, not a 500
                transaction.on_commit(lambda: build_first_digest.delay(profile.pk), robust=True)
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



class MandateHistoryView(APIView):
    """GET /api/investor/mandate/history/: список усіх версій мандату інвестора."""
    permission_classes = [IsConfirmedInvestor]
    
    def get(self, request):
        profile = request.user.investor_profile
        # Віддаємо історію від найновішої до найстарішої
        mandates = Mandate.objects.filter(investor_profile=profile).order_by("-version")
        
        data = [
            {
                "version": m.version,
                "is_current": m.is_current,
                "created_at": m.created_at,
                "check_min_eur": str(m.check_min_eur),
                "check_max_eur": str(m.check_max_eur),
                "sector_codes": m.sector_codes,
                "stage_codes": m.stage_codes,
                "country_codes": m.country_codes,
                "business_model_codes": m.business_model_codes,
            }
            for m in mandates
        ]
        return Response(data)



class InvestorFeedView(APIView):
    """Повертає картки поточного тижневого дайджесту для інвестора."""
    permission_classes = [IsConfirmedInvestor]

    def get(self, request):
        inv_profile = request.user.investor_profile
        # Беремо останній надісланий дайджест
        digest = Digest.objects.filter(investor_profile=inv_profile).order_by("-period_start").first()
        if not digest:
            return Response([])

        # Фіксуємо перше відкриття в кабінеті (для аналітики за ТЗ)
        if not digest.first_opened_at:
            digest.first_opened_at = timezone.now()
            digest.first_open_channel = Digest.Channel.CABINET
            digest.save(update_fields=["first_opened_at", "first_open_channel"])
        
        cards = (
            digest.cards.filter(introduction__status=Introduction.Status.SUGGESTED)
            .select_related("introduction__startup_profile", "introduction__teaser")
            .prefetch_related("introduction__teaser__fields")
            .order_by("position")
        )

        data = []
        for c in cards:
            sp = c.introduction.startup_profile
            teaser = c.introduction.teaser
            
            teaser_content = {
                field.field_name: field.final_text or field.ai_text or ""
                for field in teaser.fields.all()
            }
            data.append({
                "id": str(c.introduction.public_id),
                "card_id": c.id,
                "position": c.position,
                "sector": sp.sector.code if sp.sector else "",
                "stage": sp.stage.code if sp.stage else "",
                "region": getattr(sp.country, "name", "DACH"),
                "target_amount": int(sp.round_amount_eur or 0),
                "mrr": int(sp.mrr_eur or 0) if sp.mrr_eur else None,
                "team_size": sp.team_size,

                "headline": teaser_content.get("headline", ""),
                "problem_solution": f"{teaser_content.get('problem', '')} {teaser_content.get('solution', '')}",
                "team_summary": teaser_content.get("team", ""),
                
                "match_reasons": c.match_reason_codes,
                "action": c.introduction.status,
            })
        
        return Response(data)



class CardActionView(APIView):
    """
    POST /api/investor/cards/action/
    Фіксує рішення інвестора: INTERESTED або DECLINED.
    """
    permission_classes = [IsConfirmedInvestor]
    
    def post(self, request):
        card_id = request.data.get("card_id")
        action = request.data.get("action")
        confirm_notice = request.data.get("confirm_notice", True)
        
        if not confirm_notice and action == "interested":
            return Response(
                {"confirm_notice": "Необхідно підтвердити згоду на передачу даних стартапу."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        
        # Знаходимо картку (використовуємо .filter().first() для безпеки)
        card = DigestCard.objects.select_related("introduction", "digest").filter(
            id=card_id,
            digest__investor_profile__user=request.user,
        ).first()
        
        if not card:
            return Response({"detail": "Card not found."}, status=status.HTTP_404_NOT_FOUND)
        
        intro = card.introduction
        
        try:
            if action == "interested":
                # 1. Валідація повідомлення
                raw_message = request.data.get("investor_message", "")
                # Перехоплюємо можливу ValidationError, щоб не було 500
                try:
                    message = validate_investor_message(raw_message)
                except Exception as e:
                    raise DRFValidationError({"investor_message": str(e)})
                
                # 2. Зміна статусу через State Machine
                transition_introduction(
                    intro.id,
                    Introduction.Status.INTERESTED,
                    user=request.user,
                    message=message
                )
                
                # 3. Надсилання Тексту D (після успішного коміту в БД)
                transaction.on_commit(lambda: send_intro_request_to_startup(intro))
            
            elif action == "declined":
                reason_code = request.data.get("decline_reason", "other")
                
                # Знаходимо причину відмови
                decline_obj = None
                if reason_code:
                    decline_obj, _ = DeclineReason.objects.get_or_create(
                        code=reason_code,
                        defaults={"name": reason_code.capitalize()}
                    )
                
                transition_introduction(
                    intro.id,
                    Introduction.Status.DECLINED,
                    user=request.user,
                    declined_by=Introduction.DeclinedBy.INVESTOR,
                    decline_reason=decline_obj,
                )
            
            return Response({"status": "ok", "action": action}, status=status.HTTP_200_OK)
        
        except Exception as e:
            # Якщо виникла непередбачена помилка, Django виведе її в консоль
            import logging
            logging.getLogger(__name__).error(f"Error in CardActionView: {e}", exc_info=True)
            return Response({"detail": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    

    
class InvestorProfileView(APIView):
    permission_classes = [IsConfirmedInvestor]

    def get(self, request):
        profile = getattr(request.user, "investor_profile", None)
        return Response(InvestorProfileSerializer(profile).data if profile else None)

    def put(self, request):
        profile = getattr(request.user, "investor_profile", None)
        ser = InvestorProfileSerializer(profile, data=request.data, partial=profile is not None)
        ser.is_valid(raise_exception=True)
        ser.save(user=request.user)
        return Response(ser.data)
    