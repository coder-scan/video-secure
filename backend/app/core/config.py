import json
import urllib.parse
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="allow",
    )

    APP_NAME: str = "Secure Video Infrastructure & Anti-Piracy Platform"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_STR: str = "/api/v1"
    
    # Server & Port
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Cryptographic keys
    SECRET_KEY: str = "insecure-default-change-in-production-0123456789abcdef"
    MASTER_ENCRYPTION_KEY: str = "0123456789abcdef0123456789abcdef"  # 32 chars

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./platform.db"

    # Redis & Celery
    REDIS_URL: str = "redis://localhost:6379/0"
    CELERY_BROKER_URL: str = "redis://localhost:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/2"

    # Tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    PLAYBACK_TOKEN_EXPIRE_SECONDS: int = 120
    HEARTBEAT_INTERVAL_SECONDS: int = 45

    # Storage
    STORAGE_PROVIDER_TYPE: str = "LOCAL"  # LOCAL, S3, R2
    LOCAL_STORAGE_BASE_PATH: str = "./storage"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_REGION_NAME: str = "auto"
    S3_BUCKET_NAME: str = "secure-video-platform"

    # Quotas (Free Tier Defaults)
    FREE_TIER_STORAGE_BYTES_LIMIT: int = 5 * 1024 * 1024 * 1024  # 5 GB
    FREE_TIER_MAX_VIDEOS: int = 10
    FREE_TIER_PROCESSING_MINUTES_LIMIT: int = 120  # 2 hours
    FREE_TIER_BANDWIDTH_BYTES_LIMIT: int = 100 * 1024 * 1024 * 1024  # 100 GB
    FREE_TIER_MAX_CONCURRENT_STREAMS: int = 1
    FREE_TIER_MAX_DEVICES: int = 3

    # Superadmin Root Credentials
    SUPERADMIN_EMAIL: str = "admin@aetherstream.internal"
    SUPERADMIN_PASSWORD: str = "SuperSecretAdmin2026!"
    SUPERADMIN_ORG: str = "AetherStream Master Platform"

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def assemble_database_url(cls, v: str) -> str:
        """
        Normalizes database URL for async SQLAlchemy / asyncpg.
        Render and cloud providers often provide postgres:// or postgresql:// URLs,
        which must be converted to postgresql+asyncpg://.
        Also strips unsupported sslmode query parameters for asyncpg.
        """
        if not v:
            return "sqlite+aiosqlite:///./platform.db"
        
        # Replace postgres:// or postgresql:// without driver with postgresql+asyncpg://
        if v.startswith("postgres://"):
            v = v.replace("postgres://", "postgresql+asyncpg://", 1)
        elif v.startswith("postgresql://") and not v.startswith("postgresql+"):
            v = v.replace("postgresql://", "postgresql+asyncpg://", 1)

        # Remove sslmode query parameter if present since asyncpg handles SSL via connect_args
        if "asyncpg" in v and "sslmode" in v:
            parsed = urllib.parse.urlparse(v)
            query_dict = urllib.parse.parse_qs(parsed.query)
            query_dict.pop("sslmode", None)
            new_query = urllib.parse.urlencode(query_dict, doseq=True)
            v = urllib.parse.urlunparse(parsed._replace(query=new_query))

        return v

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        """Supports comma-separated strings or JSON string arrays for CORS_ORIGINS."""
        if isinstance(v, str):
            v_trimmed = v.strip()
            if v_trimmed.startswith("[") and v_trimmed.endswith("]"):
                try:
                    return json.loads(v_trimmed)
                except Exception:
                    pass
            return [origin.strip() for origin in v_trimmed.split(",") if origin.strip()]
        return v

    def model_post_init(self, __context):
        """Auto-populate Celery broker/backend if REDIS_URL is provided in cloud environments."""
        if self.REDIS_URL and self.REDIS_URL != "redis://localhost:6379/0":
            if self.CELERY_BROKER_URL == "redis://localhost:6379/1":
                self.CELERY_BROKER_URL = self.REDIS_URL
            if self.CELERY_RESULT_BACKEND == "redis://localhost:6379/2":
                self.CELERY_RESULT_BACKEND = self.REDIS_URL


settings = Settings()


