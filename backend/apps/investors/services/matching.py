
from datetime import timedelta
from django.utils import timezone
from apps.startups.models import StartupProfile
from apps.documents.models import Teaser  # або apps.documents.teaser.models
from apps.investors.models import Introduction, Mandate


def find_matches_for_mandate(mandate: Mandate, limit: int = 5):
    """
    1. Відсікає за жорсткими фільтрами (SQL).
    2. Виключає стартапи, з якими інвестор уже має Introduction.
    3. Знаходить затверджений тизер для кожного стартапу.
    4. Рахує soft_match_count та profile_age_days.
    5. Сортує: -soft_match_count -> profile_age_days.
    """
    investor_profile = mandate.investor_profile
    now = timezone.now()

    # 1. Знаходимо стартапи, з якими інвестор уже контактував
    existing_intro_startup_ids = Introduction.objects.filter(
        investor_profile=investor_profile
    ).values_list("startup_profile_id", flat=True)
    
    # 2. ЖОРСТКІ ФІЛЬТРИ (SQL)
    candidates_qs = StartupProfile.objects.filter(
        status="LIVE",
        moderation_hidden_at__isnull=True,
        sector_id__in=mandate.sector_codes,
        stage_id__in=mandate.stage_codes,
        country_id__in=mandate.country_codes,
    ).exclude(
        id__in=existing_intro_startup_ids
    ).select_related("country", "sector", "stage", "business_model")
    
    # Жорсткий фільтр за сумою чека (round_amount_eur)
    if mandate.check_min_eur is not None:
        candidates_qs = candidates_qs.filter(round_amount_eur__gte=mandate.check_min_eur)
    if mandate.check_max_eur is not None:
        candidates_qs = candidates_qs.filter(round_amount_eur__lte=mandate.check_max_eur)
    
    scored_candidates = []
    
    # 3. М'ЯКІ КРИТЕРІЇ ТА СВІЖІСТЬ
    for startup in candidates_qs:
        # Шукаємо діючий затверджений сліпий тизер стартапу
        teaser = Teaser.objects.filter(
            startup_profile=startup,
            status=Teaser.Status.APPROVED,
            is_current=True,
        ).first()
        
        # Якщо тизер чомусь не знайдено або не затверджено — пропускаємо
        if not teaser:
            continue
        
        reason_codes = ["sector", "stage", "check_size", "region"]
        soft_count = 0
        
        # М'який критерій: бізнес-модель (+1 до soft_match_count)
        bm_code = startup.business_model_id or getattr(startup.business_model, "code", None)
        if mandate.business_model_codes and bm_code in mandate.business_model_codes:
            reason_codes.append("business_model")
            soft_count += 1
        
        # Розрахунок свіжості в днях
        age_days = (now - startup.created_at).days
        
        scored_candidates.append({
            "startup": startup,
            "teaser": teaser,  # обов'язково передаємо для Introduction!
            "match_reason_codes": reason_codes,
            "soft_match_count": soft_count,
            "profile_age_days": age_days,
        })
    
    # Сортуємо строго за ТЗ:
    # 1) За кількістю збігів м'яких критеріїв (більше -> вище)
    # 2) За свіжістю (менше днів -> вище)
    scored_candidates.sort(
        key=lambda x: (-x["soft_match_count"], x["profile_age_days"])
    )
    
    return scored_candidates[:limit]