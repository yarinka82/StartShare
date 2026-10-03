"""Seeds the only list that still lives in the DB: countries.

Sectors, stages and business models are code (apps/profiles/choices.py), they need no seeding.
The country list is NOT part of the approved BA lists yet; this is a placeholder (idempotent).
"""
from django.core.management.base import BaseCommand

from apps.profiles.models import Country

COUNTRIES = [("de", "Germany"), ("at", "Austria"), ("ch", "Switzerland"), ("nl", "Netherlands"),
             ("fr", "France"), ("pl", "Poland"), ("ua", "Ukraine"), ("other", "Other")]


class Command(BaseCommand):
    help = "Seed the country list (idempotent). Further edits via Django admin."

    def handle(self, *args, **options):
        for order, (code, name) in enumerate(COUNTRIES, start=1):
            Country.objects.update_or_create(
                code=code, defaults={"name": name, "sort_order": order, "is_active": True}
            )
        self.stdout.write(self.style.SUCCESS("Countries seeded"))
