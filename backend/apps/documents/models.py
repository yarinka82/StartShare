from django.db import models

from common.validators import validate_deck_file


class PitchDeck(models.Model):
    startup = models.OneToOneField("startups.StartupProfile", on_delete=models.CASCADE)
    file = models.FileField(upload_to="decks/%Y/%m/", validators=[validate_deck_file])
    uploaded_at = models.DateTimeField(auto_now_add=True)
    deleted_at = models.DateTimeField(null=True, blank=True)  # по ТЗ оригинал удаляется после тизера