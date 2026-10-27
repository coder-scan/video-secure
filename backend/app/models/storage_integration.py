import uuid
from datetime import datetime, timezone
from sqlalchemy import BigInteger, Boolean, Column, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base, utc_now


class TenantStorageIntegration(Base):
    __tablename__ = "tenant_storage_integrations"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    tenant_id = Column(String(36), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, index=True)
    provider_type = Column(
        String(50),
        nullable=False,
    )  # GOOGLE_DRIVE, LOCAL
    status = Column(
        String(50),
        nullable=False,
        default="CONNECTED",
    )  # CONNECTED, DISCONNECTED, ERROR
    provider_account_email = Column(String(255), nullable=True)
    bucket_or_folder_id = Column(String(255), nullable=True)
    credentials_cipher = Column(Text, nullable=True)  # Authenticated cipher containing sensitive keys/tokens
    storage_quota_bytes = Column(BigInteger, nullable=True)  # 15GB for Google Drive
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=utc_now, nullable=False)
    updated_at = Column(
        DateTime,
        default=utc_now,
        onupdate=utc_now,
        nullable=False,
    )

    tenant = relationship("Tenant", back_populates="storage_integrations")
