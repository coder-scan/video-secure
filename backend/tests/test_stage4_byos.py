import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.storage_integration import TenantStorageIntegration
from app.models.tenant import Tenant, TenantQuota
from app.services.storage.factory import get_storage_provider
from app.services.storage.google_drive import GoogleDriveStorageProvider
from app.services.video.crypto import decrypt_credential_cipher


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
    # 1. Register Tenant & Connect Google Drive
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "GDrive Creator Studio",
            "email": "user@gdrivecreator.com",
            "password": "Password123!",
        },
    )
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    headers = {"Authorization": f"Bearer {token}"}

    connect_res = await client.post(
        "/api/v1/integrations/storage/connect-oauth",
        json={
            "provider_type": "GOOGLE_DRIVE",
            "refresh_token": "1//mock_gdrive_refresh_token_555",
            "account_email": "user@gmail.com",
        },
        headers=headers,
    )
    assert connect_res.status_code == 201
    integration_id = connect_res.json()["id"]

    # Quota is expanded to 15 GB
    async with async_session_maker() as db:
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        assert q_res.scalar_one().storage_bytes_limit == 15 * 1024 * 1024 * 1024

    # 2. List Integrations
    list_res = await client.get("/api/v1/integrations/storage", headers=headers)
    assert list_res.status_code == 200
    assert len(list_res.json()) == 1
    assert list_res.json()[0]["provider_type"] == "GOOGLE_DRIVE"

    # 3. Disconnect Integration
    del_res = await client.delete(
        f"/api/v1/integrations/storage/{integration_id}",
        headers=headers,
    )
    assert del_res.status_code == 204

    # 4. Verify list is empty and quota reverted to 5 GB default
    list_after = await client.get("/api/v1/integrations/storage", headers=headers)
    assert len(list_after.json()) == 0

    async with async_session_maker() as db:
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        assert q_res.scalar_one().storage_bytes_limit == 5 * 1024 * 1024 * 1024
