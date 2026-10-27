from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ConnectOAuthStorageRequest(BaseModel):
    provider_type: str = Field(default="GOOGLE_DRIVE", pattern="^(GOOGLE_DRIVE)$")
    refresh_token: Optional[str] = None
    account_email: Optional[str] = None
    folder_id: Optional[str] = None


class StorageIntegrationResponse(BaseModel):
    id: str
    provider_type: str
    status: str
    provider_account_email: Optional[str] = None
    bucket_or_folder_id: Optional[str] = None
    storage_quota_bytes: Optional[int] = None
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)
