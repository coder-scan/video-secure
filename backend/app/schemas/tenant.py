from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict


class TenantQuotaResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    storage_bytes_limit: int
    max_videos: int
    processing_minutes_limit: int
    bandwidth_bytes_limit: int
    max_concurrent_streams: int
    max_devices_per_user: int


class TenantUsageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    storage_bytes_used: int
    video_count: int
    processing_minutes_used: int
    bandwidth_bytes_used: int
    period_start: datetime
    period_end: datetime


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    slug: str
    plan_tier: str
    status: str
    created_at: datetime
    quota: Optional[TenantQuotaResponse] = None
    usage: Optional[TenantUsageResponse] = None
