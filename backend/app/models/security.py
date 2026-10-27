import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class SecurityEvent(Base):
    __tablename__ = "security_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    session_id = Column(String(64), nullable=True, index=True)
    user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(100), nullable=False, index=True)  # CONCURRENT_STREAM_DETECTED, DOM_TAMPER_DETECTED, GEO_HOPPING, KEY_DENIED
    severity = Column(String(20), nullable=False, default="INFO")  # INFO, LOW, MEDIUM, HIGH, CRITICAL
    ip_address = Column(String(64), nullable=True)
    risk_score = Column(Integer, nullable=False, default=0)
    details = Column(Text, nullable=False, default="{}")  # JSON encoded triggers and metadata
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False, index=True)

    tenant = relationship("Tenant")
    user = relationship("User")
    video = relationship("Video")


class PiracyIncident(Base):
    __tablename__ = "piracy_incidents"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    video_id = Column(String(36), ForeignKey("videos.id", ondelete="CASCADE"), nullable=False, index=True)
    incident_number = Column(String(50), nullable=False, unique=True, index=True)  # e.g. INC-2026-0042
    status = Column(
        String(50),
        nullable=False,
        default="DETECTED",  # DETECTED, UNDER_REVIEW, CONFIRMED, DISMISSED, RESOLVED
        index=True,
    )
    similarity_score = Column(Float, nullable=False, default=0.0)  # 0.0 to 1.0
    source_url = Column(String(1024), nullable=False)
    suspected_user_id = Column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    suspected_session_id = Column(String(64), nullable=True)
    evidence_data = Column(Text, nullable=False, default="{}")  # JSON encoded evidence details
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    tenant = relationship("Tenant")
    video = relationship("Video")
    suspected_user = relationship("User")
