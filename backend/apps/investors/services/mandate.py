from django.db import transaction
from apps.investors.models import Mandate


def save_investor_mandate(investor_profile, data: dict, source="manual") -> Mandate:
    with transaction.atomic():
        current_mandate = Mandate.objects.filter(investor_profile=investor_profile, is_current=True).first()
        
        new_version = (current_mandate.version + 1) if current_mandate else 1
        
        # 1. Попередній мандат стає архівним
        if current_mandate:
            current_mandate.is_current = False
            current_mandate.save(update_fields=["is_current"])
        
        # 2. Створюємо нову версію
        new_mandate = Mandate(
            investor_profile=investor_profile,
            version=new_version,
            is_current=True,
            source=source,
            check_min_eur=data["check_min_eur"],
            check_max_eur=data["check_max_eur"],
            sector_codes=data["sector_codes"],
            stage_codes=data["stage_codes"],
            country_codes=data["country_codes"],
            region_codes=data.get("region_codes", []),
            business_model_codes=data.get("business_model_codes", []),
        )
        new_mandate.full_clean()
        new_mandate.save()
        
        return new_mandate