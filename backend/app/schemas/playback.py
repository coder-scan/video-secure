from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class PlaybackTokenRequest(BaseModel):
    video_id: str
    client_fingerprint: Optional[str] = None


class WatermarkData(BaseModel):
    viewer_id: str
    viewer_email: str
    viewer_ip: str
    timestamp: str


class PlaybackSessionInfo(BaseModel):
    session_id: str
    video_id: str
    manifest_url: str
    playback_token: str
    expires_in_seconds: int
    watermark: WatermarkData
    heartbeat_interval_seconds: int = 30


class HeartbeatRequest(BaseModel):
    session_id: str
    playback_token: str
    current_time_seconds: float = 0.0


class HeartbeatResponse(BaseModel):
    status: str  # ACTIVE, TERMINATED, EXPIRED
    message: Optional[str] = None
