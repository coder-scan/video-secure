import json
import logging
from typing import Optional

from app.core.config import settings
from app.models.storage_integration import TenantStorageIntegration
from app.services.storage.base import StorageProvider
from app.services.storage.google_drive import GoogleDriveStorageProvider
from app.services.storage.local import LocalStorageProvider
from app.services.storage.onedrive import OneDriveStorageProvider
from app.services.storage.s3 import S3CompatibleStorageProvider
from app.services.video.crypto import decrypt_credential_cipher

logger = logging.getLogger(__name__)

_default_provider_instance = None


def get_storage_provider(
    integration: Optional[TenantStorageIntegration] = None,
) -> StorageProvider:
    """
    Returns the appropriate storage provider instance.
    If a TenantStorageIntegration is passed and active (BYOS), instantiates the custom
    Google Drive, OneDrive, or AWS S3/R2 provider using decrypted credentials.
    Otherwise, returns the platform's default storage provider.
    """
    global _default_provider_instance

    if integration and integration.is_active and integration.credentials_cipher:
        try:
            creds_str = decrypt_credential_cipher(integration.credentials_cipher)
            creds = json.loads(creds_str)

            if integration.provider_type == "CUSTOM_S3":
                return S3CompatibleStorageProvider(
                    endpoint_url=creds.get("endpoint_url"),
                    access_key_id=creds.get("access_key_id"),
                    secret_access_key=creds.get("secret_access_key"),
                    region_name=creds.get("region_name", "auto"),
                    bucket_name=creds.get("bucket_name"),
                )
            elif integration.provider_type == "GOOGLE_DRIVE":
                return GoogleDriveStorageProvider(
                    refresh_token=creds.get("refresh_token"),
                    client_id=creds.get("client_id"),
                    client_secret=creds.get("client_secret"),
                    root_folder_id=integration.bucket_or_folder_id,
                )
            elif integration.provider_type == "ONEDRIVE":
                return OneDriveStorageProvider(
                    refresh_token=creds.get("refresh_token"),
                    client_id=creds.get("client_id"),
                    client_secret=creds.get("client_secret"),
                    root_folder_id=integration.bucket_or_folder_id,
                )
        except Exception as e:
            logger.error(
                f"Failed to load BYOS provider for integration {integration.id}: {e}. Falling back to default."
            )

    # Fallback to platform default provider
    if _default_provider_instance is None:
        if settings.STORAGE_PROVIDER_TYPE.upper() in ["S3", "R2"]:
            _default_provider_instance = S3CompatibleStorageProvider()
        else:
            _default_provider_instance = LocalStorageProvider()

    return _default_provider_instance
