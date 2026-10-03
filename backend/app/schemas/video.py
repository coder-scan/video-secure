from datetime import datetime
from typing import Any, Dict, Optional
from pydantic import BaseModel, ConfigDict, Field


class UploadIntentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    filename: str = Field(..., min_length=1, max_length=255)
    file_size_bytes: int = Field(..., gt=0)
    content_type: str = Field(default="video/mp4")
    description: Optional[str] = None


class UploadIntentResponse(BaseModel):
    video_id: str
    storage_key: str
    upload_url: str
    method: str = "PUT"
    upload_fields: Optional[Dict[str, Any]] = None
    expires_in_seconds: int = 3600


class CompleteUploadRequest(BaseModel):
    video_id: str


class VideoResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    creator_id: str
    title: str
    description: Optional[str]
    status: str
    duration_seconds: int
    raw_size_bytes: int
    visibility: str
    width: Optional[int] = None
    height: Optional[int] = None
    codec_video: Optional[str] = None
    codec_audio: Optional[str] = None
    thumbnail_paths: Optional[str] = None
    hls_master_path: Optional[str] = None
    processing_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime
