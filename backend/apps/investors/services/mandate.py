from decimal import Decimal

from django.db import transaction

from apps.analytics.models import Event, EventName
from apps.investors.models import Mandate, InvestorProfile


def save_or_update_mandate(investor_profile: InvestorProfile, data: dict, source="manual") -> tuple[Mandate, bool]:
    """
    Зберігає мандат з версіонуванням [B]:
    - Якщо мандату ще не було: створює v1 (is_current=True).
    - Якщо дані НЕ змінилися: повертає існуючий мандат (created=False).
    - Якщо дані змінилися: архівує старий (is_current=False) та створює v+1 (created=True).
    """
    with transaction.atomic():
        current = Mandate.objects.filter(investor_profile=investor_profile, is_current=True).first()

        # Підготовка та нормалізація нових даних
        check_min = Decimal(str(data["check_min_eur"]))
        check_max = Decimal(str(data["check_max_eur"]))
        sectors = sorted(list(dict.fromkeys(data.get("sector_codes") or [])))
        stages = sorted(list(dict.fromkeys(data.get("stage_codes") or [])))
        countries = sorted(list(dict.fromkeys(data.get("country_codes") or [])))
        regions = sorted(list(dict.fromkeys(data.get("region_codes") or [])))
        b_models = sorted(list(dict.fromkeys(data.get("business_model_codes") or [])))

        # 1. Перевірка: чи змінилися дані порівняно з поточною версією?
        if current:
            is_same = (
                current.check_min_eur == check_min
                and current.check_max_eur == check_max
                and sorted(current.sector_codes) == sectors
                and sorted(current.stage_codes) == stages
                and sorted(current.country_codes) == countries
                and sorted(current.region_codes or []) == regions
                and sorted(current.business_model_codes or []) == b_models
            )
            # Якщо нічого не змінилося — повертаємо поточний без створення нової версії
            if is_same:
                return current, False

            # Якщо змінилися — архівуємо попередній
            current.is_current = False
            current.save(update_fields=["is_current"])
            new_version = current.version + 1
        else:
            new_version = 1

        # 2. Створюємо нову версію мандату
        new_mandate = Mandate(
            investor_profile=investor_profile,
            version=new_version,
            is_current=True,
            source=source,
            check_min_eur=check_min,
            check_max_eur=check_max,
            sector_codes=sectors,
            stage_codes=stages,
            country_codes=countries,
            region_codes=regions,
            business_model_codes=b_models,
        )
        new_mandate.full_clean()
        new_mandate.save()

        # 3. Логування подій за ТЗ
        try:
            if new_version == 1:
                Event.objects.create(name=EventName.MANDATE_SAVED, user=investor_profile.user)
            else:
                Event.objects.create(name=EventName.MANDATE_CHANGED, user=investor_profile.user)
        except Exception:
            pass

        return new_mandate, True