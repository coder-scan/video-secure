import uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class Video(Base):
    __tablename__ = "videos"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    creator_id = Column(String(36), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    status = Column(
        String(50),
        nullable=False,
        default="UPLOADING",  # UPLOADING, UPLOADED, QUEUED, PROCESSING, READY, FAILED
        index=True,
    )
    duration_seconds = Column(Integer, default=0, nullable=False)
    raw_size_bytes = Column(BigInteger, default=0, nullable=False)
    raw_storage_key = Column(String(512), nullable=True)
    hls_master_path = Column(String(512), nullable=True)
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)
    codec_video = Column(String(32), nullable=True)
    codec_audio = Column(String(32), nullable=True)
    thumbnail_paths = Column(Text, nullable=True)
    processing_error = Column(Text, nullable=True)
    encryption_key_id = Column(String(36), default=lambda: str(uuid.uuid4()), nullable=False)
    encryption_key_cipher = Column(String(512), nullable=True)
    visibility = Column(String(50), nullable=False, default="PRIVATE")  # PUBLIC, UNLISTED, PRIVATE
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="videos")
    creator = relationship("User", back_populates="videos")
