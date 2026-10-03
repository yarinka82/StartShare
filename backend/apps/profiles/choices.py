"""Approved lists (BA document, confirmed by the PM). Single source of truth for the backend.

Sector and stage are HARD matching filters, business model is a SOFT criterion.
The value (code) is what is stored in the DB and sent by the API; it never changes.
The label is the German interface name; EN/UA labels live in the frontend locale files by code.

Changing a list = edit this file + `makemigrations` (no data script, nothing to seed).
Removing a value: write a data migration first, otherwise old rows keep a value that is no
longer valid (such a profile is reported as "not filled" until the startup picks a new one).
"""
from django.db import models


class Sector(models.TextChoices):
    FINTECH = "fintech", "FinTech"
    INSURTECH = "insurtech", "InsurTech"
    HEALTHTECH_MEDTECH = "healthtech-medtech", "HealthTech & MedTech"
    BIOTECH = "biotech", "BioTech"
    EDTECH = "edtech", "EdTech"
    PROPTECH_CONTECH = "proptech-contech", "PropTech & ConTech"
    CLIMATETECH_ENERGY = "climatetech-energy", "ClimateTech & Energie"
    MOBILITY_LOGISTICS = "mobility-logistics", "Mobilität & Logistik"
    FOODTECH_AGRITECH = "foodtech-agritech", "FoodTech & AgriTech"
    ECOMMERCE_RETAILTECH = "ecommerce-retailtech", "E-Commerce & RetailTech"
    HR_TECH = "hr-tech", "HR Tech"
    LEGALTECH_REGTECH = "legaltech-regtech", "LegalTech & RegTech"
    CYBERSECURITY = "cybersecurity", "Cybersecurity"
    AI_DATA = "ai-data", "KI & Daten"
    ENTERPRISE_SOFTWARE = "enterprise-software", "Enterprise Software"
    DEEPTECH_HARDWARE = "deeptech-hardware", "DeepTech & Hardware"
    INDUSTRIE_4_0 = "industrie-4-0", "Industrie 4.0"
    MEDIA_ENTERTAINMENT_GAMING = "media-entertainment-gaming", "Medien, Entertainment & Gaming"
    TRAVEL_HOSPITALITY = "travel-hospitality", "Reisen & Gastgewerbe"
    OTHER = "other", "Sonstiges"


class Stage(models.TextChoices):
    PRE_SEED = "pre-seed", "Pre-Seed"
    SEED = "seed", "Seed"
    SERIES_A = "series-a", "Series A"
    SERIES_B = "series-b", "Series B"
    SERIES_C_PLUS = "series-c-plus", "Series C und später"


class BusinessModel(models.TextChoices):
    SAAS_SUBSCRIPTION = "saas-subscription", "SaaS & Abo-Modell"
    MARKETPLACE_PLATFORM = "marketplace-platform", "Marktplatz & Plattform"
    ECOMMERCE_D2C = "ecommerce-d2c", "E-Commerce & D2C"
    HARDWARE_SALES = "hardware-sales", "Hardware-Verkauf"
    LICENSING = "licensing", "Lizenzmodell"
    SERVICES = "services", "Dienstleistung"
    TRANSACTION_FEE = "transaction-fee", "Transaktionsmodell"
    OTHER = "other", "Sonstiges"
