import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Annotated, Optional
import jwt
from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db
from app.core.dependencies import get_current_user
from app.core.security import ALGORITHM, decode_token
from app.models.tenant import Tenant
from app.models.user import User
from app.models.video import Video
from app.schemas.playback import (
    HeartbeatRequest,
    HeartbeatResponse,
    PlaybackSessionInfo,
    PlaybackTokenRequest,
    WatermarkData,
)
from app.services.playback.concurrency import session_manager
from app.services.storage.factory import get_storage_provider
from app.services.video.crypto import decrypt_key_cipher

router = APIRouter()


def _extract_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "127.0.0.1"


def _verify_playback_token(token: Optional[str]) -> dict:
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Playback authorization token required",
        )
    payload = decode_token(token)
    if not payload or payload.get("type") != "playback":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired playback token",
        )
    return payload


@router.post("/token", response_model=PlaybackSessionInfo)
async def generate_playback_token(
    req: PlaybackTokenRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Issues a short-lived, IP-bound playback token for an authorized viewer
    and enforces maximum concurrent stream limits.
    """
    # 1. Fetch Video with Tenant Quotas
    result = await db.execute(
        select(Video)
        .options(
            selectinload(Video.tenant).selectinload(Tenant.quota),
            selectinload(Video.tenant).selectinload(Tenant.usage),
        )
        .where(Video.id == req.video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if video.status != "READY":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video is not ready for playback (status: {video.status})",
        )

    # 2. Access control check
    if video.visibility == "PRIVATE" and video.tenant_id != current_user.tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access forbidden: this video is private to its creator organization",
        )

    # 3. Check Tenant Bandwidth Quota
    tenant = video.tenant
    if tenant and tenant.quota and tenant.usage:
        if tenant.usage.bandwidth_bytes_used >= tenant.quota.bandwidth_bytes_limit:
            raise HTTPException(
                status_code=status.HTTP_402_PAYMENT_REQUIRED,
                detail="Tenant monthly bandwidth quota exceeded",
            )

    client_ip = _extract_client_ip(request)
    max_concurrent = (
        tenant.quota.max_concurrent_streams if tenant and tenant.quota else 1
    )

    # 4. Register session in concurrency manager
    session_id = await session_manager.register_session(
        user_id=current_user.id,
        video_id=video.id,
        ip=client_ip,
        max_concurrent=max_concurrent,
    )

    # 5. Sign short-lived Playback Token
    expires_in = settings.PLAYBACK_TOKEN_EXPIRE_SECONDS
    expire_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in)

    payload = {
        "sub": current_user.id,
        "email": current_user.email,
        "video_id": video.id,
        "tenant_id": video.tenant_id,
        "key_id": video.encryption_key_id,
        "session_id": session_id,
        "ip": client_ip,
        "type": "playback",
        "exp": expire_time,
    }
    playback_token = jwt.encode(payload, settings.SECRET_KEY, algorithm=ALGORITHM)

    manifest_url = (
        f"{settings.API_V1_STR}/playback/manifest/{video.id}/master.m3u8?token={playback_token}"
    )

    now_iso = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    return PlaybackSessionInfo(
        session_id=session_id,
        video_id=video.id,
        manifest_url=manifest_url,
        playback_token=playback_token,
        expires_in_seconds=expires_in,
        watermark=WatermarkData(
            viewer_id=current_user.id[:8],
            viewer_email=current_user.email,
            viewer_ip=client_ip,
            timestamp=now_iso,
        ),
        heartbeat_interval_seconds=settings.HEARTBEAT_INTERVAL_SECONDS,
    )


@router.get("/key/{key_id}")
async def get_decryption_key(
    key_id: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Delivers raw 16-byte AES-128 decryption key only if the request carries
    a valid, unexpired playback token and active single-session credentials.
    """
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()

    payload = _verify_playback_token(raw_token)

    if payload.get("key_id") != key_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Key ID mismatch")

    # Verify session concurrency status
    session_id = payload.get("session_id")
    is_active = await session_manager.is_session_active(session_id)
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session revoked or terminated due to concurrent stream.",
        )

    # Fetch Video from DB
    result = await db.execute(select(Video).where(Video.encryption_key_id == key_id))
    video = result.scalar_one_or_none()
    if not video or not video.encryption_key_cipher:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Key cipher not found")

    try:
        raw_key, _ = decrypt_key_cipher(video.encryption_key_cipher)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Key decryption error",
        )

    return Response(
        content=raw_key,
        media_type="application/octet-stream",
        headers={
            "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
            "Pragma": "no-cache",
        },
    )


@router.get("/manifest/{video_id}/{path:path}")
async def get_manifest_or_segment(
    video_id: str,
    path: str,
    token: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
):
    """
    Securely serves HLS master/variant playlists and encrypted transport segments.
    Appends playback token to nested key queries to support standard HLS players.
    """
    raw_token = token
    if not raw_token and authorization and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()

    payload = _verify_playback_token(raw_token)
    if payload.get("video_id") != video_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Video ID mismatch")

    # Check session
    is_active = await session_manager.is_session_active(payload.get("session_id"))
    if not is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Session terminated: concurrent playback detected",
        )

    # Fetch Video
    result = await db.execute(
        select(Video)
        .options(selectinload(Video.tenant).selectinload(Tenant.usage))
        .where(Video.id == video_id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    remote_key = f"processed/{video.tenant_id}/{video.id}/hls/{path}"
    storage = get_storage_provider()

    exists = await storage.object_exists(remote_key)
    if not exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Asset {path} not found")

    # Determine Content Type
    if path.endswith(".m3u8"):
        content_type = "application/vnd.apple.mpegurl"
    elif path.endswith(".ts"):
        content_type = "video/mp2t"
    elif path.endswith(".jpg"):
        content_type = "image/jpeg"
    else:
        content_type = "application/octet-stream"

    # Local scratch retrieval
    temp_dir = Path("./scratch") / "playback"
    temp_dir.mkdir(parents=True, exist_ok=True)
    temp_file = temp_dir / f"{video.id}_{Path(path).name}"

    try:
        await storage.download_file(remote_key, str(temp_file))
        content = temp_file.read_bytes()

        # If it's an HLS playlist, rewrite relative key and segment URIs with token
        if path.endswith(".m3u8"):
            text = content.decode("utf-8")
            # Inject ?token into key URI
            text = re.sub(
                r'URI="([^"?]+)"',
                rf'URI="\1?token={raw_token}"',
                text,
            )
            # Inject ?token into variant sub-playlist references if needed
            content = text.encode("utf-8")

        # Track Bandwidth in Tenant Usage Ledger
        if video.tenant and video.tenant.usage:
            video.tenant.usage.bandwidth_bytes_used += len(content)
            await db.commit()

        return Response(
            content=content,
            media_type=content_type,
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0"
                if path.endswith(".m3u8")
                else "public, max-age=31536000",
            },
        )
    finally:
        if temp_file.exists():
            temp_file.unlink()


@router.post("/heartbeat", response_model=HeartbeatResponse)
async def session_heartbeat(req: HeartbeatRequest):
    """
    Heartbeat ping from active video player. Refreshes session activity
    or informs player if session was revoked due to another device connecting.
    """
    payload = decode_token(req.playback_token)
    if not payload:
        return HeartbeatResponse(status="EXPIRED", message="Token expired")

    is_valid, reason = await session_manager.validate_and_touch_session(req.session_id)
    if not is_valid:
        return HeartbeatResponse(status="TERMINATED", message=reason)

    return HeartbeatResponse(status="ACTIVE")
