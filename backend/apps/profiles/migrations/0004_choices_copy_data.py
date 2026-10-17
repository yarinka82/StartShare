from django.db import migrations

VALID = {
    "sector": ['ai-data', 'biotech', 'climatetech-energy', 'cybersecurity', 'deeptech-hardware', 'ecommerce-retailtech', 'edtech', 'enterprise-software', 'fintech', 'foodtech-agritech', 'healthtech-medtech', 'hr-tech', 'industrie-4-0', 'insurtech', 'legaltech-regtech', 'media-entertainment-gaming', 'mobility-logistics', 'other', 'proptech-contech', 'travel-hospitality'],
    "stage": ['pre-seed', 'seed', 'series-a', 'series-b', 'series-c-plus'],
    "business_model": ['ecommerce-d2c', 'hardware-sales', 'licensing', 'marketplace-platform', 'other', 'saas-subscription', 'services', 'transaction-fee'],
}


def copy_codes(apps, schema_editor):
    """Old rows pointed at dictionary rows; keep the code if it is still in the approved list.
    Retired values (e.g. the old 'saas' sector) become empty = the startup must choose again."""
    Profile = apps.get_model("profiles", "StartupProfile")
    for p in Profile.objects.select_related("sector", "stage", "business_model"):
        for field in ("sector", "stage", "business_model"):
            old = getattr(p, field)
            code = old.code if old is not None and old.code in VALID[field] else ""
            setattr(p, field + "_code", code)
        p.save(update_fields=["sector_code", "stage_code", "business_model_code"])


class Migration(migrations.Migration):
    """Step 2/3: data only (kept separate from schema changes: PostgreSQL cannot mix them safely)."""

    dependencies = [("profiles", "0003_choices_add_fields")]
    operations = [migrations.RunPython(copy_codes, migrations.RunPython.noop)]
