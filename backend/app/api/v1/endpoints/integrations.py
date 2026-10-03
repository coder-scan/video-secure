import json
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_active_creator, get_current_tenant
from app.models.storage_integration import TenantStorageIntegration
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.storage_integration import (
    ConnectCustomS3Request,
    ConnectOAuthStorageRequest,
    StorageIntegrationResponse,
)
from app.services.video.crypto import encrypt_credential_cipher

router = APIRouter()

GOOGLE_DRIVE_QUOTA_BYTES = 15 * 1024 * 1024 * 1024  # 15 GB Free
ONEDRIVE_QUOTA_BYTES = 5 * 1024 * 1024 * 1024        # 5 GB Free
CUSTOM_S3_QUOTA_BYTES = 1024 * 1024 * 1024 * 1024    # 1 TB BYOS Quota


@router.get("/storage", response_model=List[StorageIntegrationResponse])
async def list_storage_integrations(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists all configured Bring-Your-Own-Storage (BYOS) accounts for this tenant."""
    result = await db.execute(
        select(TenantStorageIntegration)
        .where(TenantStorageIntegration.tenant_id == current_tenant.id)
        .order_by(TenantStorageIntegration.created_at.desc())
    )
    return result.scalars().all()


@router.post(
    "/storage/connect-s3",
    response_model=StorageIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_custom_s3(
    req: ConnectCustomS3Request,
    current_user: Annotated[User, Depends(get_current_active_creator)],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Connects a creator-owned AWS S3 or Cloudflare R2 bucket.
    Encrypts credentials with authenticated master key cipher.
    """
    # 1. Deactivate existing integrations
    existing = await db.execute(
        select(TenantStorageIntegration).where(
            TenantStorageIntegration.tenant_id == current_tenant.id
        )
    )
    for item in existing.scalars().all():
        item.is_active = False

    # 2. Encrypt credentials
    creds = {
        "bucket_name": req.bucket_name,
        "access_key_id": req.access_key_id,
        "secret_access_key": req.secret_access_key,
        "endpoint_url": req.endpoint_url,
        "region_name": req.region_name or "auto",
    }
    cipher = encrypt_credential_cipher(json.dumps(creds))

    # 3. Create integration record
    integration = TenantStorageIntegration(
        tenant_id=current_tenant.id,
        provider_type="CUSTOM_S3",
        status="CONNECTED",
        bucket_or_folder_id=req.bucket_name,
        credentials_cipher=cipher,
        storage_quota_bytes=CUSTOM_S3_QUOTA_BYTES,
        is_active=True,
    )
    db.add(integration)

    # 4. Expand tenant storage quota limit
    if current_tenant.quota:
        current_tenant.quota.storage_bytes_limit = CUSTOM_S3_QUOTA_BYTES

    await db.commit()
    await db.refresh(integration)
    return integration


@router.post(
    "/storage/connect-oauth",
    response_model=StorageIntegrationResponse,
    status_code=status.HTTP_201_CREATED,
)
async def connect_oauth_storage(
    req: ConnectOAuthStorageRequest,
    current_user: Annotated[User, Depends(get_current_active_creator)],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Connects Google Drive (15 GB) or Microsoft OneDrive (5 GB) storage.
    Enables free creator hosting by saving encrypted HLS segments directly to their drive.
    """
    # 1. Deactivate existing integrations
    existing = await db.execute(
        select(TenantStorageIntegration).where(
            TenantStorageIntegration.tenant_id == current_tenant.id
        )
    )
    for item in existing.scalars().all():
        item.is_active = False

    # 2. Determine quota
    quota_bytes = (
        GOOGLE_DRIVE_QUOTA_BYTES
        if req.provider_type == "GOOGLE_DRIVE"
        else ONEDRIVE_QUOTA_BYTES
    )

    creds = {
        "refresh_token": req.refresh_token,
        "account_email": req.account_email,
        "folder_id": req.folder_id or "secure_video_platform",
    }
    cipher = encrypt_credential_cipher(json.dumps(creds))

    integration = TenantStorageIntegration(
        tenant_id=current_tenant.id,
        provider_type=req.provider_type,
        status="CONNECTED",
        provider_account_email=req.account_email,
        bucket_or_folder_id=req.folder_id or "secure_video_platform",
        credentials_cipher=cipher,
        storage_quota_bytes=quota_bytes,
        is_active=True,
    )
    db.add(integration)

    # Expand tenant quota to match provider capacity
    if current_tenant.quota:
        current_tenant.quota.storage_bytes_limit = quota_bytes

    await db.commit()
    await db.refresh(integration)
    return integration


@router.delete("/storage/{integration_id}", status_code=status.HTTP_204_NO_CONTENT)
async def disconnect_storage_integration(
    integration_id: str,
    current_user: Annotated[User, Depends(get_current_active_creator)],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Disconnects BYOS integration and resets tenant quota to default platform free tier."""
    res = await db.execute(
        select(TenantStorageIntegration).where(
            TenantStorageIntegration.id == integration_id,
            TenantStorageIntegration.tenant_id == current_tenant.id,
        )
    )
    integration = res.scalar_one_or_none()
    if not integration:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Storage integration not found"
        )

    await db.delete(integration)

    # Reset quota to default 5 GB
    if current_tenant.quota:
        current_tenant.quota.storage_bytes_limit = 5 * 1024 * 1024 * 1024

    await db.commit()
    return None
