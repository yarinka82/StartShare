import os

from django.conf import settings
from pypdf import PdfReader

from rest_framework import serializers

# Messages are stable error codes; the frontend translates them.
ALLOWED_CONTENT_TYPES = {"application/pdf", "application/x-pdf", "application/octet-stream"}


def validate_deck_file(f):
    if f.size == 0:
        raise serializers.ValidationError("deck_empty")
    if f.size > settings.DECK_MAX_BYTES:
        raise serializers.ValidationError("deck_too_large")

    ext = os.path.splitext(f.name or "")[1].lower()
    ctype = (getattr(f, "content_type", "") or "").split(";")[0].strip().lower()
    if ext != ".pdf" or (ctype and ctype not in ALLOWED_CONTENT_TYPES):
        raise serializers.ValidationError("deck_not_pdf")

    f.seek(0)
    head = f.read(5)
    f.seek(0)
    if head != b"%PDF-":  # magic bytes: the real check, names and MIME can be faked
        raise serializers.ValidationError("deck_not_pdf")

    try:
        reader = PdfReader(f)
        if reader.is_encrypted and reader.decrypt("") == 0:  # 0 = NOT_DECRYPTED
            raise serializers.ValidationError("deck_password_protected")
        if len(reader.pages) < 1:
            raise serializers.ValidationError("deck_corrupted")
    except serializers.ValidationError:
        raise
    except Exception:
        raise serializers.ValidationError("deck_corrupted")
    finally:
        f.seek(0)
    return f
