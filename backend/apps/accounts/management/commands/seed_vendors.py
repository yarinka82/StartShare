from django.core.management.base import BaseCommand

from apps.accounts.models import VendorCompliance


class Command(BaseCommand):
    help = "Seed default approved vendor registry entries for EU processing providers."

    def handle(self, *args, **options):
        defaults = [
            {
                "provider_name": "azure_openai",
                "name": "azure_openai",
                "vendor_type": "ai",
                "provider_type": "ai",
                "region": "sweden-central",
                "dpa_signed": False,
                "no_model_training": False,
                "allowed_data_types": ["ai_prompt", "startup_profile", "investor_profile", "pitch_deck"],
                "notes": "Azure OpenAI EU processing placeholder. DPA/AVV not yet signed.",
                "is_active": True,
            },
            {
                "provider_name": "azure_blob",
                "name": "azure_blob",
                "vendor_type": "storage",
                "provider_type": "storage",
                "region": "sweden-central",
                "dpa_signed": False,
                "no_model_training": True,
                "allowed_data_types": ["pitch_deck", "document_upload", "startup_profile"],
                "notes": "Azure Blob EU storage placeholder. DPA/AVV not yet signed.",
                "is_active": True,
            },
            {
                "provider_name": "brevo",
                "name": "brevo",
                "vendor_type": "email",
                "provider_type": "email",
                "region": "eu",
                "dpa_signed": False,
                "no_model_training": True,
                "allowed_data_types": ["email_address", "user_id", "notification_type"],
                "notes": "Brevo EU email placeholder. DPA/AVV not yet signed.",
                "is_active": True,
            },
        ]

        for item in defaults:
            obj, created = VendorCompliance.objects.get_or_create(
                provider_name=item["provider_name"],
                defaults={
                    **item,
                    "provider_name": item["provider_name"],
                    "name": item["name"],
                },
            )
            if not created:
                changed = False
                for key, value in item.items():
                    if key in {"provider_name", "name"}:
                        continue
                    current = getattr(obj, key)
                    if isinstance(current, bool):
                        if current is True:
                            continue
                    elif isinstance(current, (list, tuple)):
                        if current:
                            continue
                    elif isinstance(current, str):
                        if current and key != "notes":
                            continue
                        if key == "notes" and current and current != "":
                            continue
                    setattr(obj, key, value)
                    changed = True
                if changed:
                    obj.save()

            if created:
                self.stdout.write(self.style.SUCCESS(f"Created vendor registry: {obj.provider_name}"))
            else:
                self.stdout.write(self.style.WARNING(f"Vendor already exists, preserved manual values: {obj.provider_name}"))
