from __future__ import annotations

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import Storage
from django.core.exceptions import ImproperlyConfigured

from apps.accounts.compliance import ProviderBlocked, assert_provider_allowed


class AzureBlobPrivateStorage(Storage):
    """Private Azure Blob backend. No public URL is exposed to the user."""

    def __init__(self, container_name=None, account_name=None, account_key=None):
        self.container_name = container_name or getattr(settings, "AZURE_BLOB_CONTAINER_NAME", "startshare-private")
        self.account_name = account_name or getattr(settings, "AZURE_BLOB_ACCOUNT_NAME", "")
        self.account_key = account_key or getattr(settings, "AZURE_BLOB_ACCOUNT_KEY", "")
        self.endpoint_suffix = getattr(settings, "AZURE_BLOB_ENDPOINT_SUFFIX", "core.windows.net")

    @property
    def url(self):
        return None

    def _client(self):
        if not self.account_name or not self.account_key:
            raise ImproperlyConfigured("Azure Blob storage is not configured.")
        try:
            from azure.storage.blob import BlobServiceClient
        except ImportError as exc:
            raise ImproperlyConfigured("azure-storage-blob is required for Azure Blob storage.") from exc
        account_url = f"https://{self.account_name}.blob.{self.endpoint_suffix}"
        return BlobServiceClient(account_url=account_url, credential=self.account_key)

    def _container(self):
        client = self._client()
        container = client.get_container_client(self.container_name)
        if not container.exists():
            client.create_container(self.container_name)
        return container

    def _open(self, name, mode="rb"):
        if not name:
            raise FileNotFoundError(name)
        data = self._container().download_blob(name).readall()
        return ContentFile(data, name=name)

    def _save(self, name, content):
        assert_provider_allowed("azure_blob")
        blob = self._container().get_blob_client(name)
        blob.upload_blob(content, overwrite=True)
        return name

    def delete(self, name):
        if not name:
            return
        try:
            self._container().delete_blob(name, delete_snapshots='include')
        except Exception:
            pass

    def exists(self, name):
        if not name:
            return False
        try:
            return self._container().get_blob_client(name).exists()
        except Exception:
            return False

    def listdir(self, path):
        return [], []

    def size(self, name):
        if not name:
            return 0
        try:
            return self._container().get_blob_client(name).get_blob_properties().size
        except Exception:
            return 0


def get_storage_backend():
    if getattr(settings, "AZURE_BLOB_ACCOUNT_NAME", "") and getattr(settings, "AZURE_BLOB_ACCOUNT_KEY", ""):
        return AzureBlobPrivateStorage()
    from django.core.files.storage import FileSystemStorage
    return FileSystemStorage(location=getattr(settings, "PRIVATE_MEDIA_ROOT", settings.BASE_DIR / "private_media"))


def delete_deck(profile_id):
    from apps.profiles.models import Deck, StartupProfile

    if not StartupProfile.objects.filter(pk=profile_id).exists():
        return False

    deck = Deck.objects.filter(profile_id=profile_id).first()
    if deck:
        name = getattr(deck.file, "name", "") or ""
        if name:
            try:
                deck.file.storage.delete(name)
            except ProviderBlocked:
                raise
            except Exception:
                pass

    Deck.objects.filter(profile_id=profile_id).delete()
    return True
