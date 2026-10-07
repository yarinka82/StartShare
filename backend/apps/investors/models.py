from django.conf import settings
from django.db import models



class InvestorMandate(models.Model):
    """What the investor is looking for. The values come from the SAME lists as the startup profile
    (apps/profiles/choices.py), so matching can compare codes exactly.

    List fields hold arrays of codes; they are validated against the choices in the serializer and stored
    in the canonical (list) order, so two mandates with the same selection are always equal.
    """

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="investor_mandate"
    )
    # HARD filters (at least one value each)
    sectors = models.JSONField(default=list)
    stages = models.JSONField(default=list)
    regions = models.JSONField(default=list)
    ticket_min = models.DecimalField(max_digits=14, decimal_places=2)  # EUR
    ticket_max = models.DecimalField(max_digits=14, decimal_places=2)  # EUR
    # SOFT criterion (may be empty: then it does not influence the order)
    business_models = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Mandate of {self.user_id}"
