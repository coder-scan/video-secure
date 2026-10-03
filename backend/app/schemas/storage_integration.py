from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ConnectCustomS3Request(BaseModel):
    bucket_name: str = Field(..., min_length=3, max_length=63)
    access_key_id: str = Field(..., min_length=4)
    secret_access_key: str = Field(..., min_length=8)
    endpoint_url: Optional[str] = None
    region_name: Optional[str] = "auto"


class ConnectOAuthStorageRequest(BaseModel):
    provider_type: str = Field(..., pattern="^(GOOGLE_DRIVE|ONEDRIVE)$")
    refresh_token: str = Field(..., min_length=8)
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

