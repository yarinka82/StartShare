"""Approved dictionaries (BA proposal, to be confirmed by the PM).

Sectors and stages are HARD matching filters, business models are a SOFT criterion.
`name` is the German interface name; EN/UA labels live in the frontend locale files by `code`.
The command is idempotent. Values that are not in the approved lists any more are
deactivated (not deleted: profiles may still reference them).
"""
from django.core.management.base import BaseCommand

from apps.profiles.models import BusinessModel, Country, Sector, Stage

# (code, DE name)
SECTORS = [
    ("fintech", "FinTech"),
    ("insurtech", "InsurTech"),
    ("healthtech-medtech", "HealthTech & MedTech"),
    ("biotech", "BioTech"),
    ("edtech", "EdTech"),
    ("proptech-contech", "PropTech & ConTech"),
    ("climatetech-energy", "ClimateTech & Energie"),
    ("mobility-logistics", "Mobilität & Logistik"),
    ("foodtech-agritech", "FoodTech & AgriTech"),
    ("ecommerce-retailtech", "E-Commerce & RetailTech"),
    ("hr-tech", "HR Tech"),
    ("legaltech-regtech", "LegalTech & RegTech"),
    ("cybersecurity", "Cybersecurity"),
    ("ai-data", "KI & Daten"),
    ("enterprise-software", "Enterprise Software"),
    ("deeptech-hardware", "DeepTech & Hardware"),
    ("industrie-4-0", "Industrie 4.0"),
    ("media-entertainment-gaming", "Medien, Entertainment & Gaming"),
    ("travel-hospitality", "Reisen & Gastgewerbe"),
    ("other", "Sonstiges"),
]
STAGES = [
    ("pre-seed", "Pre-Seed"),
    ("seed", "Seed"),
    ("series-a", "Series A"),
    ("series-b", "Series B"),
    ("series-c-plus", "Series C und später"),
]
BUSINESS_MODELS = [
    ("saas-subscription", "SaaS & Abo-Modell"),
    ("marketplace-platform", "Marktplatz & Plattform"),
    ("ecommerce-d2c", "E-Commerce & D2C"),
    ("hardware-sales", "Hardware-Verkauf"),
    ("licensing", "Lizenzmodell"),
    ("services", "Dienstleistung"),
    ("transaction-fee", "Transaktionsmodell"),
    ("other", "Sonstiges"),
]
# Not part of the BA document: unchanged placeholder list.
COUNTRIES = [("de", "Germany"), ("at", "Austria"), ("ch", "Switzerland"), ("nl", "Netherlands"),
             ("fr", "France"), ("pl", "Poland"), ("ua", "Ukraine"), ("other", "Other")]


def sync(model, rows, deactivate_missing=True):
    for order, (code, name) in enumerate(rows, start=1):
        model.objects.update_or_create(
            code=code, defaults={"name": name, "sort_order": order, "is_active": True}
        )
    if deactivate_missing:
        model.objects.exclude(code__in=[c for c, _ in rows]).update(is_active=False)


class Command(BaseCommand):
    help = "Sync approved dictionary values (idempotent). Further edits via Django admin."

    def handle(self, *args, **options):
        sync(Sector, SECTORS)
        sync(Stage, STAGES)
        sync(BusinessModel, BUSINESS_MODELS)
        sync(Country, COUNTRIES, deactivate_missing=False)
        self.stdout.write(self.style.SUCCESS("Dictionaries synced"))
