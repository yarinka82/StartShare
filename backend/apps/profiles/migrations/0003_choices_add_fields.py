from django.db import migrations, models

SECTOR_CHOICES = [('fintech', 'FinTech'),
 ('insurtech', 'InsurTech'),
 ('healthtech-medtech', 'HealthTech & MedTech'),
 ('biotech', 'BioTech'),
 ('edtech', 'EdTech'),
 ('proptech-contech', 'PropTech & ConTech'),
 ('climatetech-energy', 'ClimateTech & Energie'),
 ('mobility-logistics', 'Mobilität & Logistik'),
 ('foodtech-agritech', 'FoodTech & AgriTech'),
 ('ecommerce-retailtech', 'E-Commerce & RetailTech'),
 ('hr-tech', 'HR Tech'),
 ('legaltech-regtech', 'LegalTech & RegTech'),
 ('cybersecurity', 'Cybersecurity'),
 ('ai-data', 'KI & Daten'),
 ('enterprise-software', 'Enterprise Software'),
 ('deeptech-hardware', 'DeepTech & Hardware'),
 ('industrie-4-0', 'Industrie 4.0'),
 ('media-entertainment-gaming', 'Medien, Entertainment & Gaming'),
 ('travel-hospitality', 'Reisen & Gastgewerbe'),
 ('other', 'Sonstiges')]
STAGE_CHOICES = [('pre-seed', 'Pre-Seed'),
 ('seed', 'Seed'),
 ('series-a', 'Series A'),
 ('series-b', 'Series B'),
 ('series-c-plus', 'Series C und später')]
BUSINESS_MODEL_CHOICES = [('saas-subscription', 'SaaS & Abo-Modell'),
 ('marketplace-platform', 'Marktplatz & Plattform'),
 ('ecommerce-d2c', 'E-Commerce & D2C'),
 ('hardware-sales', 'Hardware-Verkauf'),
 ('licensing', 'Lizenzmodell'),
 ('services', 'Dienstleistung'),
 ('transaction-fee', 'Transaktionsmodell'),
 ('other', 'Sonstiges')]


class Migration(migrations.Migration):
    """Step 1/3: sector, stage and business_model become model choices (plain text codes).
    New columns first, old FK columns are copied and removed in the next two steps."""

    dependencies = [("profiles", "0002_businessmodel_startupprofile_business_model")]

    operations = [
        migrations.AddField(
            model_name="startupprofile", name="sector_code",
            field=models.CharField(blank=True, choices=SECTOR_CHOICES, default="", max_length=40),
        ),
        migrations.AddField(
            model_name="startupprofile", name="stage_code",
            field=models.CharField(blank=True, choices=STAGE_CHOICES, default="", max_length=20),
        ),
        migrations.AddField(
            model_name="startupprofile", name="business_model_code",
            field=models.CharField(blank=True, choices=BUSINESS_MODEL_CHOICES, default="", max_length=30),
        ),
    ]
