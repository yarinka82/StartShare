"""
Seeds all reference dictionaries into the database (idempotent):
- Countries
- Sectors
- Stages
- Business Models
- Regions
"""

from django.core.management.base import BaseCommand
from common.models import Country, Sector, Stage, BusinessModel, Region

# ------------------ 1. COUNTRIES ------------------
COUNTRIES_INITIAL = [
    # (code, name_de, name_en, sort_order)
    ("de", "Deutschland", "Germany", 1),
    ("at", "Österreich", "Austria", 2),
    ("ch", "Schweiz", "Switzerland", 3),
    ("eu", "Andere EU-Länder", "Other EU Countries", 4),
    ("gb", "Großbritannien", "United Kingdom", 5),
    ("us", "Vereinigte Staaten", "United States", 6),
    ("ua", "Ukraine", "Ukraine", 7),
    ("other", "Sonstiges", "Other", 99),
]

# ------------------ 2. SECTORS ------------------
SECTORS_INITIAL = [
    # (code, name_de, name_en, sort_order, is_other)
    ("fintech", "FinTech", "FinTech", 1, False),
    ("insurtech", "InsurTech", "InsurTech", 2, False),
    ("healthtech-medtech", "HealthTech & MedTech", "HealthTech & MedTech", 3, False),
    ("biotech", "BioTech", "BioTech", 4, False),
    ("ai-data", "KI & Daten", "AI & Data", 5, False),
    ("cybersecurity", "Cybersecurity", "Cybersecurity", 6, False),
    ("enterprise-software", "Enterprise Software", "Enterprise Software", 7, False),
    ("deeptech-hardware", "DeepTech & Hardware", "DeepTech & Hardware", 8, False),
    ("industrie-4-0", "Industrie 4.0", "Industry 4.0", 9, False),
    ("climatetech-energy", "ClimateTech & Energie", "ClimateTech & Energy", 10, False),
    ("mobility-logistics", "Mobilität & Logistik", "Mobility & Logistics", 11, False),
    ("proptech-contech", "PropTech & ConTech", "PropTech & ConTech", 12, False),
    ("foodtech-agritech", "FoodTech & AgriTech", "FoodTech & AgriTech", 13, False),
    ("ecommerce-retailtech", "E-Commerce & RetailTech", "E-Commerce & RetailTech", 14, False),
    ("edtech", "EdTech", "EdTech", 15, False),
    ("hr-tech", "HR Tech", "HR Tech", 16, False),
    ("legaltech-regtech", "LegalTech & RegTech", "LegalTech & RegTech", 17, False),
    ("media-entertainment-gaming", "Medien, Entertainment & Gaming", "Media, Entertainment & Gaming", 18, False),
    ("travel-hospitality", "Reisen & Gastgewerbe", "Travel & Hospitality", 19, False),
    ("other", "Sonstiges", "Other", 99, True),
]

# ------------------ 3. STAGES ------------------
STAGES_INITIAL = [
    # (code, name_de, name_en, sort_order)
    ("pre-seed", "Pre-Seed", "Pre-Seed", 1),
    ("seed", "Seed", "Seed", 2),
    ("series-a", "Series A", "Series A", 3),
    ("series-b", "Series B", "Series B", 4),
    ("series-c-plus", "Series C und später", "Series C and later", 5),
]

# ------------------ 4. BUSINESS MODELS ------------------
BUSINESS_MODELS_INITIAL = [
    # (code, name_de, name_en, sort_order, is_other)
    ("saas-subscription", "SaaS & Abo-Modell", "SaaS & Subscription", 1, False),
    ("marketplace-platform", "Marktplatz & Plattform", "Marketplace & Platform", 2, False),
    ("ecommerce-d2c", "E-Commerce & D2C", "E-Commerce & D2C", 3, False),
    ("hardware-sales", "Hardware-Verkauf", "Hardware Sales", 4, False),
    ("licensing", "Lizenzmodell", "Licensing", 5, False),
    ("services", "Dienstleistung", "Professional Services", 6, False),
    ("transaction-fee", "Transaktionsmodell", "Transaction Fee", 7, False),
    ("other", "Sonstiges", "Other", 99, True),
]

# ------------------ 5. REGIONS (INVESTOR GEO SCOPE) ------------------
REGIONS_INITIAL = [
    # (code, name_de, name_en, sort_order)
    ("dach", "DACH (Deutschland, Österreich, Schweiz)", "DACH (Germany, Austria, Switzerland)", 1),
    ("eu", "Europäische Union (EU)", "European Union (EU)", 2),
    ("europe", "Europa (inkl. UK, Schweiz, Ukraine)", "Europe (incl. UK, Switzerland, Ukraine)", 3),
    ("worldwide", "Weltweit", "Worldwide", 4),
]


class Command(BaseCommand):
    help = "Seeds all reference dictionaries (idempotent)."

    def handle(self, *args, **options):
        # 1. Countries
        for code, name_de, name_en, sort_order in COUNTRIES_INITIAL:
            Country.objects.update_or_create(
                code=code,
                defaults={
                    "name_de": name_de,
                    "name_en": name_en,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Seeded {len(COUNTRIES_INITIAL)} Countries"))

        # 2. Sectors
        for code, name_de, name_en, sort_order, is_other in SECTORS_INITIAL:
            Sector.objects.update_or_create(
                code=code,
                defaults={
                    "name_de": name_de,
                    "name_en": name_en,
                    "sort_order": sort_order,
                    "is_other": is_other,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Seeded {len(SECTORS_INITIAL)} Sectors"))

        # 3. Stages
        for code, name_de, name_en, sort_order in STAGES_INITIAL:
            Stage.objects.update_or_create(
                code=code,
                defaults={
                    "name_de": name_de,
                    "name_en": name_en,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Seeded {len(STAGES_INITIAL)} Stages"))

        # 4. Business Models
        for code, name_de, name_en, sort_order, is_other in BUSINESS_MODELS_INITIAL:
            BusinessModel.objects.update_or_create(
                code=code,
                defaults={
                    "name_de": name_de,
                    "name_en": name_en,
                    "sort_order": sort_order,
                    "is_other": is_other,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Seeded {len(BUSINESS_MODELS_INITIAL)} Business Models"))

        # 5. Regions
        for code, name_de, name_en, sort_order in REGIONS_INITIAL:
            Region.objects.update_or_create(
                code=code,
                defaults={
                    "name_de": name_de,
                    "name_en": name_en,
                    "sort_order": sort_order,
                    "is_active": True,
                },
            )
        self.stdout.write(self.style.SUCCESS(f"✓ Seeded {len(REGIONS_INITIAL)} Regions"))

        self.stdout.write(self.style.SUCCESS("\nAll reference dictionaries successfully seeded! 🚀"))

## python manage.py seed_dictionaries