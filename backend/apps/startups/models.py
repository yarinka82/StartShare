from django.conf import settings
from django.db import models


class StartupProfile(models.Model):
    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        LIVE = "live", "Live"
        PAUSED = "paused", "Paused"
        REMOVED = "removed", "Removed"

    class Sector(models.TextChoices):
        FINTECH = "fintech", "Fintech"
        HEALTHTECH = "healthtech", "Healthtech"
        # ...

    class Stage(models.TextChoices):
        PRE_SEED = "pre_seed", "Pre-Seed"
        SEED = "seed", "Seed"
        SERIES_A = "series_a", "Series A"
        # ...

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.DRAFT)
    sector = models.CharField(max_length=30, choices=Sector.choices)
    stage = models.CharField(max_length=30, choices=Stage.choices)
    country = models.CharField(max_length=2)  # ISO-код, список стран фронт хранит сам
    amount_seeking = models.DecimalField(max_digits=12, decimal_places=2)
    mrr = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    growth_rate = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    team_size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)