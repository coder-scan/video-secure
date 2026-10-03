import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.storage_integration import TenantStorageIntegration
from app.models.tenant import Tenant, TenantQuota
from app.services.storage.factory import get_storage_provider
from app.services.storage.google_drive import GoogleDriveStorageProvider
from app.services.storage.onedrive import OneDriveStorageProvider
from app.services.storage.s3 import S3CompatibleStorageProvider
from app.services.video.crypto import decrypt_credential_cipher


@pytest.mark.asyncio
async def test_byos_custom_s3_connection(client: AsyncClient):
    # 1. Register Tenant
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "S3 Enterprise Studio",
            "email": "owner@s3studio.com",
            "password": "Password123!",
        },
    )
    assert res.status_code == 201
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Connect Custom S3 Bucket
    s3_payload = {
        "bucket_name": "my-private-video-vault",
        "access_key_id": "AKIAIOSFODNN7EXAMPLE",
        "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "endpoint_url": "https://s3.us-west-2.amazonaws.com",
        "region_name": "us-west-2",
    }
    connect_res = await client.post(
        "/api/v1/integrations/storage/connect-s3",
        json=s3_payload,
        headers=headers,
    )
    assert connect_res.status_code == 201
    data = connect_res.json()
    integration_id = data["id"]
    assert data["provider_type"] == "CUSTOM_S3"
    assert data["bucket_or_folder_id"] == "my-private-video-vault"
    assert data["is_active"] is True

    # 3. Verify Database State & Quota Expansion
    async with async_session_maker() as db:
        integ_res = await db.execute(
            select(TenantStorageIntegration).where(TenantStorageIntegration.id == integration_id)
        )
        integration = integ_res.scalar_one()
        assert integration.credentials_cipher is not None

        # Verify cryptographic decryption of stored credentials
        decrypted_str = decrypt_credential_cipher(integration.credentials_cipher)
        creds = json.loads(decrypted_str)
        assert creds["access_key_id"] == s3_payload["access_key_id"]
        assert creds["bucket_name"] == s3_payload["bucket_name"]

        # Verify tenant quota expanded to 1 TB BYOS limit
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        quota = q_res.scalar_one()
        assert quota.storage_bytes_limit == 1024 * 1024 * 1024 * 1024

        # 4. Verify Factory instantiates S3CompatibleStorageProvider with decrypted creds
        provider = get_storage_provider(integration)
        assert isinstance(provider, S3CompatibleStorageProvider)
        assert provider.bucket_name == "my-private-video-vault"
        assert provider.access_key_id == "AKIAIOSFODNN7EXAMPLE"


@pytest.mark.asyncio
async def test_byos_google_drive_connection(client: AsyncClient):
    # 1. Register Tenant
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "GDrive Academy",
            "email": "prof@gdriveacademy.edu",
            "password": "Password123!",
        },
    )
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Connect Google Drive (OAuth)
    gdrive_payload = {
        "provider_type": "GOOGLE_DRIVE",
        "refresh_token": "1//04mock_google_refresh_token_xyz987",
        "account_email": "prof@gmail.com",
        "folder_id": "gdrive_folder_abc123",
    }
    connect_res = await client.post(
        "/api/v1/integrations/storage/connect-oauth",
        json=gdrive_payload,
        headers=headers,
    )
    assert connect_res.status_code == 201
    data = connect_res.json()
    integration_id = data["id"]
    assert data["provider_type"] == "GOOGLE_DRIVE"
    assert data["provider_account_email"] == "prof@gmail.com"

    # 3. Verify Quota expanded to 15 GB (Google Drive free tier)
    async with async_session_maker() as db:
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        quota = q_res.scalar_one()
        assert quota.storage_bytes_limit == 15 * 1024 * 1024 * 1024

        integ_res = await db.execute(
            select(TenantStorageIntegration).where(TenantStorageIntegration.id == integration_id)
        )
        integration = integ_res.scalar_one()

        # 4. Verify Factory instantiates GoogleDriveStorageProvider
        provider = get_storage_provider(integration)
        assert isinstance(provider, GoogleDriveStorageProvider)
        assert provider.refresh_token == "1//04mock_google_refresh_token_xyz987"
        assert provider.root_folder_id == "gdrive_folder_abc123"

        # Verify presigned upload URL contains direct resumable upload parameter
        presigned = await provider.generate_presigned_upload_url(
            key="raw/test.mp4",
            content_type="video/mp4",
            max_size_bytes=1024 * 1024,
        )
        assert "uploadType=resumable" in presigned["upload_url"]
        assert presigned["method"] == "PUT"


@pytest.mark.asyncio
async def test_byos_disconnect_and_revert(client: AsyncClient):
    # 1. Register Tenant & Connect OneDrive
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "OneDrive Creator",
            "email": "user@onedrivecreator.com",
            "password": "Password123!",
        },
    )
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    headers = {"Authorization": f"Bearer {token}"}

    connect_res = await client.post(
        "/api/v1/integrations/storage/connect-oauth",
        json={
            "provider_type": "ONEDRIVE",
            "refresh_token": "mock_onedrive_refresh_token_555",
            "account_email": "user@outlook.com",
        },
        headers=headers,
    )
    assert connect_res.status_code == 201
    integration_id = connect_res.json()["id"]

    # Quota is 5 GB
    async with async_session_maker() as db:
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        assert q_res.scalar_one().storage_bytes_limit == 5 * 1024 * 1024 * 1024

    # 2. List Integrations
    list_res = await client.get("/api/v1/integrations/storage", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["provider_type"] == "ONEDRIVE"

    # 3. Disconnect Integration
    del_res = await client.delete(
        f"/api/v1/integrations/storage/{integration_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    # 4. Verify list is empty and quota reverted
    list_after = await client.get("/api/v1/integrations/storage", headers=headers)
    assert len(list_after.json()) == 0

    async with async_session_maker() as db:
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        assert q_res.scalar_one().storage_bytes_limit == 5 * 1024 * 1024 * 1024
