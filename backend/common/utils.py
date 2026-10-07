import uuid

from django.conf import settings
from django.contrib.postgres.functions import RandomUUID
from django.core.files.storage import FileSystemStorage
from django.db import models


def public_id_field():
    return models.UUIDField(default=uuid.uuid4, db_default=RandomUUID(), unique=True, editable=False)


def get_private_storage():
    """Deck files live outside MEDIA_ROOT and are never served directly."""
    return FileSystemStorage(location=settings.PRIVATE_MEDIA_ROOT)


def deck_upload_path(instance, filename):
    return f"decks/{uuid.uuid4().hex}.pdf"  # random name; original name stored in DB