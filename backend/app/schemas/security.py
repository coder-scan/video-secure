from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class SecurityEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    session_id: Optional[str] = None
    user_id: Optional[str] = None
    video_id: Optional[str] = None
    event_type: str
    severity: str
    ip_address: Optional[str] = None
    risk_score: int
    details: str
    created_at: datetime


class SecurityEventLogRequest(BaseModel):
    session_id: Optional[str] = None
    video_id: Optional[str] = None
    event_type: str
    severity: str = "MEDIUM"
    details: Dict[str, Any] = Field(default_factory=dict)


class ActiveSessionResponse(BaseModel):
    session_id: str
    user_id: str
    user_email: Optional[str] = None
    video_id: str
    video_title: Optional[str] = None
    ip_address: str
    risk_score: int
    risk_level: str
    started_at: str
    last_heartbeat: str
    status: str


class RiskOverviewResponse(BaseModel):
    overall_risk_level: str
    average_risk_score: int
    active_streaming_sessions: int
    revoked_sessions_count: int
    total_security_events: int
    open_piracy_incidents: int
    recent_critical_events: List[SecurityEventResponse] = Field(default_factory=list)


class PiracyIncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    tenant_id: str
    video_id: str
    video_title: Optional[str] = None
    incident_number: str
    status: str
    similarity_score: float
    source_url: str
    suspected_user_id: Optional[str] = None
    suspected_session_id: Optional[str] = None
    evidence_data: str
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class CreateIncidentRequest(BaseModel):
    video_id: str
    source_url: str
    similarity_score: float = Field(..., ge=0.0, le=1.0)
    suspected_user_id: Optional[str] = None
    suspected_session_id: Optional[str] = None
    notes: Optional[str] = None


class UpdateIncidentStatusRequest(BaseModel):
    status: str = Field(..., pattern="^(DETECTED|UNDER_REVIEW|CONFIRMED|DISMISSED|RESOLVED)$")
    notes: Optional[str] = None
