import uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class Tenant(Base):
    __tablename__ = "tenants"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    plan_tier = Column(String(50), nullable=False, default="FREE")  # FREE, CREATOR, PRO, ENTERPRISE
    status = Column(String(50), nullable=False, default="ACTIVE")   # ACTIVE, SUSPENDED
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    # Relationships
    users = relationship("User", back_populates="tenant", cascade="all, delete-orphan")
    videos = relationship("Video", back_populates="tenant", cascade="all, delete-orphan")
    quota = relationship("TenantQuota", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    usage = relationship("TenantUsage", back_populates="tenant", uselist=False, cascade="all, delete-orphan")
    storage_integrations = relationship(
        "TenantStorageIntegration", back_populates="tenant", cascade="all, delete-orphan"
    )


class TenantQuota(Base):
    __tablename__ = "tenant_quotas"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    storage_bytes_limit = Column(BigInteger, nullable=False, default=5 * 1024 * 1024 * 1024)  # 5 GB
    max_videos = Column(Integer, nullable=False, default=10)
    processing_minutes_limit = Column(Integer, nullable=False, default=120)  # 2 hours
    bandwidth_bytes_limit = Column(BigInteger, nullable=False, default=100 * 1024 * 1024 * 1024)  # 100 GB
    max_concurrent_streams = Column(Integer, nullable=False, default=1)
    max_devices_per_user = Column(Integer, nullable=False, default=3)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="quota")


class TenantUsage(Base):
    __tablename__ = "tenant_usage"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    storage_bytes_used = Column(BigInteger, nullable=False, default=0)
    video_count = Column(Integer, nullable=False, default=0)
    processing_minutes_used = Column(Integer, nullable=False, default=0)
    bandwidth_bytes_used = Column(BigInteger, nullable=False, default=0)
    period_start = Column(DateTime, default=utc_now, nullable=False)
    period_end = Column(DateTime, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="usage")
