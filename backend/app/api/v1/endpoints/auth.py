import re
from datetime import datetime, timezone
from typing import Annotated
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db, utc_now
from app.core.dependencies import get_current_user
from app.core.security import create_access_token, create_refresh_token, get_password_hash, verify_password
from app.models.tenant import Tenant, TenantQuota, TenantUsage
from app.models.user import User
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse
from app.schemas.user import UserResponse

router = APIRouter()


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r"[^\w\s-]", "", text)
    return re.sub(r"[-\s]+", "-", text)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    request: RegisterRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Check if user already exists
    existing_user_query = await db.execute(select(User).where(User.email == request.email))
    if existing_user_query.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists",
        )

    # Generate unique slug for tenant
    base_slug = slugify(request.organization_name)
    slug = base_slug
    counter = 1
    while True:
        existing_slug = await db.execute(select(Tenant).where(Tenant.slug == slug))
        if not existing_slug.scalar_one_or_none():
            break
        slug = f"{base_slug}-{counter}"
        counter += 1

    # 1. Create Tenant
    tenant = Tenant(
        name=request.organization_name,
        slug=slug,
        plan_tier="FREE",
        status="ACTIVE",
    )
    db.add(tenant)
    await db.flush()

    # 2. Initialize Free Tier Quotas
    quota = TenantQuota(
        tenant_id=tenant.id,
        storage_bytes_limit=settings.FREE_TIER_STORAGE_BYTES_LIMIT,
        max_videos=settings.FREE_TIER_MAX_VIDEOS,
        processing_minutes_limit=settings.FREE_TIER_PROCESSING_MINUTES_LIMIT,
        bandwidth_bytes_limit=settings.FREE_TIER_BANDWIDTH_BYTES_LIMIT,
        max_concurrent_streams=settings.FREE_TIER_MAX_CONCURRENT_STREAMS,
        max_devices_per_user=settings.FREE_TIER_MAX_DEVICES,
    )
    db.add(quota)

    # 3. Initialize Usage Ledger
    now = utc_now()
    # 30-day billing cycle for usage ledger
    from datetime import timedelta
    usage = TenantUsage(
        tenant_id=tenant.id,
        storage_bytes_used=0,
        video_count=0,
        processing_minutes_used=0,
        bandwidth_bytes_used=0,
        period_start=now,
        period_end=now + timedelta(days=30),
    )
    db.add(usage)

    # 4. Create Owner User
    hashed_pwd = get_password_hash(request.password)
    user = User(
        tenant_id=tenant.id,
        email=request.email,
        password_hash=hashed_pwd,
        full_name=request.full_name,
        role="OWNER",
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Generate tokens
    access_token = create_access_token(subject=user.id, tenant_id=tenant.id, role=user.role)
    refresh_token = create_refresh_token()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        tenant_id=tenant.id,
        role=user.role,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Check if logging in as root superadmin defined in .env
    if (
        request.email.lower() == settings.SUPERADMIN_EMAIL.lower()
        and request.password == settings.SUPERADMIN_PASSWORD
    ):
        return await admin_login(request, db)

    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Account is disabled"
        )

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role)
    refresh_token = create_refresh_token()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )


@router.post("/admin-login", response_model=TokenResponse)
async def admin_login(
    request: LoginRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Dedicated Root Administrator login endpoint.
    Validates superadmin credentials defined in .env and ensures
    master organization and superadmin account are initialized with full privileges.
    """
    # 1. Check against root .env superadmin credentials
    is_superadmin = (
        request.email.lower() == settings.SUPERADMIN_EMAIL.lower()
        and request.password == settings.SUPERADMIN_PASSWORD
    )

    if is_superadmin:
        # Check if master superadmin user already exists in DB
        result = await db.execute(select(User).where(User.email == settings.SUPERADMIN_EMAIL))
        user = result.scalar_one_or_none()

        if not user:
            # Initialize Root Master Tenant with Enterprise/Unlimited Quotas
            master_slug = "aetherstream-root-master"
            tenant_res = await db.execute(select(Tenant).where(Tenant.slug == master_slug))
            tenant = tenant_res.scalar_one_or_none()
            if not tenant:
                tenant = Tenant(
                    name=settings.SUPERADMIN_ORG,
                    slug=master_slug,
                    plan_tier="ENTERPRISE",
                    status="ACTIVE",
                )
                db.add(tenant)
                await db.flush()

                # Enterprise Quotas (100 TB Storage, 10,000 Videos, 100,000 Transcode Minutes)
                quota = TenantQuota(
                    tenant_id=tenant.id,
                    storage_bytes_limit=100 * 1024 * 1024 * 1024 * 1024,  # 100 TB
                    max_videos=10000,
                    processing_minutes_limit=100000,
                    bandwidth_bytes_limit=1000 * 1024 * 1024 * 1024 * 1024,  # 1 PB
                    max_concurrent_streams=10,
                    max_devices_per_user=10,
                )
                db.add(quota)

                from datetime import timedelta
                usage = TenantUsage(
                    tenant_id=tenant.id,
                    storage_bytes_used=0,
                    video_count=0,
                    processing_minutes_used=0,
                    bandwidth_bytes_used=0,
                    period_start=utc_now(),
                    period_end=utc_now() + timedelta(days=3650),
                )
                db.add(usage)

            # Create Superadmin user
            user = User(
                tenant_id=tenant.id,
                email=settings.SUPERADMIN_EMAIL,
                password_hash=get_password_hash(settings.SUPERADMIN_PASSWORD),
                full_name="Root Super Administrator",
                role="OWNER",
                is_active=True,
                is_verified=True,
            )
            db.add(user)
            await db.commit()
            await db.refresh(user)

        access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role="OWNER")
        refresh_token = create_refresh_token()
        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            user_id=user.id,
            tenant_id=user.tenant_id,
            role="OWNER",
        )

    # 2. Check if it's an existing database Admin / Owner user
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if user.role not in ["OWNER", "ADMIN"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied: administrative privileges required",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Administrator account is disabled"
        )

    access_token = create_access_token(subject=user.id, tenant_id=user.tenant_id, role=user.role)
    refresh_token = create_refresh_token()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        user_id=user.id,
        tenant_id=user.tenant_id,
        role=user.role,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: Annotated[User, Depends(get_current_user)]):
    return current_user

