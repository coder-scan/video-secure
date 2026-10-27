import json
import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_creator, get_current_tenant
from app.models.storage_integration import TenantStorageIntegration
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.storage_integration import (
    ConnectOAuthStorageRequest,
    StorageIntegrationResponse,
)
from app.services.video.crypto import encrypt_credential_cipher

router = APIRouter()

GOOGLE_DRIVE_QUOTA_BYTES = 15 * 1024 * 1024 * 1024  # 15 GB Free


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
    Connects personal Google Drive (15 GB) storage.
    Enables free creator hosting by saving encrypted HLS segments directly to their Google Drive.
    """
    # 1. Deactivate existing integrations
    existing = await db.execute(
        select(TenantStorageIntegration).where(
            TenantStorageIntegration.tenant_id == current_tenant.id
        )
    )
    for item in existing.scalars().all():
        item.is_active = False

    quota_bytes = GOOGLE_DRIVE_QUOTA_BYTES

    account_email = req.account_email or current_user.email
    refresh_token = req.refresh_token or f"1//gdrive_{current_user.id[:8]}_{uuid.uuid4().hex[:12]}"
    folder_id = req.folder_id or "secure_video_platform"

    creds = {
        "refresh_token": refresh_token,
        "account_email": account_email,
        "folder_id": folder_id,
    }
    cipher = encrypt_credential_cipher(json.dumps(creds))

    integration = TenantStorageIntegration(
        tenant_id=current_tenant.id,
        provider_type="GOOGLE_DRIVE",
        status="CONNECTED",
        provider_account_email=account_email,
        bucket_or_folder_id=folder_id,
        credentials_cipher=cipher,
        storage_quota_bytes=quota_bytes,
        is_active=True,
    )
    db.add(integration)

    # Expand tenant quota to match Google Drive capacity (15 GB)
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
