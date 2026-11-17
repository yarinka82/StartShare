from django.db.models import Exists, OuterRef
from django.utils import timezone
from apps.startups.models import StartupProfile
from apps.documents.models import Teaser  # або apps.documents.teaser.models
from apps.investors.models import Introduction, Mandate


def find_matches_for_mandate(mandate: Mandate, limit: int = 5):
    """
    1. Відсікає за жорсткими фільтрами (SQL): сектор, стадія, країна, чек.
    2. Виключає стартапи, з якими інвестор уже має Introduction.
    3. Залишає лише стартапи із затвердженим актуальним тизером.
    4. Рахує soft_match_count та profile_age_days.
    5. Сортує: -soft_match_count -> profile_age_days.
    """
    investor_profile = mandate.investor_profile
    now = timezone.now()

    # Без обраних країн жорсткий фільтр не має сенсу
    if not mandate.country_codes:
        return []

    # 1. Стартапи, з якими інвестор уже контактував
    existing_intro_startup_ids = Introduction.objects.filter(
        investor_profile=investor_profile
    ).values("startup_profile_id")

    # 2. Затверджений актуальний сліпий тизер (перевірка прямо в SQL)
    approved_teasers = Teaser.objects.filter(
        startup_profile=OuterRef("pk"),
        status=Teaser.Status.APPROVED,
        is_current=True,
    )

    # 3. ЖОРСТКІ ФІЛЬТРИ (SQL)
    candidates_qs = (
        StartupProfile.objects.filter(
            status="LIVE",
            moderation_hidden_at__isnull=True,
            sector_id__in=mandate.sector_codes,
            stage_id__in=mandate.stage_codes,
            country_id__in=mandate.country_codes,
        )
        .filter(Exists(approved_teasers))
        .exclude(id__in=existing_intro_startup_ids)
        .select_related("country", "sector", "stage", "business_model")
    )

    # Жорсткий фільтр за сумою чека (round_amount_eur)
    if mandate.check_min_eur is not None:
        candidates_qs = candidates_qs.filter(round_amount_eur__gte=mandate.check_min_eur)
    if mandate.check_max_eur is not None:
        candidates_qs = candidates_qs.filter(round_amount_eur__lte=mandate.check_max_eur)

    startups = list(candidates_qs)
    if not startups:
        return []

    # Тизери всіх кандидатів одним запитом (замість запиту на кожен стартап)
    teasers_by_startup = {}
    for teaser in Teaser.objects.filter(
        startup_profile_id__in=[s.id for s in startups],
        status=Teaser.Status.APPROVED,
        is_current=True,
    ).order_by("startup_profile_id", "-id"):
        teasers_by_startup.setdefault(teaser.startup_profile_id, teaser)

    scored_candidates = []

    # 4. М'ЯКІ КРИТЕРІЇ ТА СВІЖІСТЬ
    for startup in startups:
        teaser = teasers_by_startup.get(startup.id)
        if not teaser:  # страховка на випадок гонки між запитами
            continue

        # Жорсткі критерії пройдені, тому вони завжди є причинами збігу
        reason_codes = ["sector", "stage", "check_size", "country"]
        soft_count = 0

        # М'який критерій: бізнес-модель (+1 до soft_match_count)
        if mandate.business_model_codes and startup.business_model_id in mandate.business_model_codes:
            reason_codes.append("business_model")
            soft_count += 1

        # Свіжість профілю в днях
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