import uuid
from typing import Annotated, List
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.dependencies import get_current_active_creator, get_current_tenant
from app.models.tenant import Tenant
from app.models.user import User
from app.models.video import Video
from app.schemas.video import CompleteUploadRequest, UploadIntentRequest, UploadIntentResponse, VideoResponse
from app.services.storage.factory import get_storage_provider

router = APIRouter()


@router.post("/upload-intent", response_model=UploadIntentResponse, status_code=status.HTTP_201_CREATED)
async def create_upload_intent(
    request: UploadIntentRequest,
    current_user: Annotated[User, Depends(get_current_active_creator)],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    quota = current_tenant.quota
    usage = current_tenant.usage

    # 1. Enforce Storage Quota
    new_storage_usage = usage.storage_bytes_used + request.file_size_bytes
    if new_storage_usage > quota.storage_bytes_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "STORAGE_QUOTA_EXCEEDED",
                "message": "Storage limit reached. Please upgrade your plan or free up storage.",
                "used_bytes": usage.storage_bytes_used,
                "limit_bytes": quota.storage_bytes_limit,
                "requested_bytes": request.file_size_bytes,
            },
        )

    # 2. Enforce Video Count Quota
    if usage.video_count + 1 > quota.max_videos:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail={
                "code": "VIDEO_COUNT_QUOTA_EXCEEDED",
                "message": "Maximum video count reached for your plan.",
                "used_videos": usage.video_count,
                "max_videos": quota.max_videos,
            },
        )

    # 3. Generate Secure Storage Key
    video_id = str(uuid.uuid4())
    sanitized_filename = "".join(c for c in request.filename if c.isalnum() or c in "._-")
    storage_key = f"raw/{current_tenant.id}/{video_id}/{sanitized_filename}"

    # 4. Generate Presigned Direct Upload URL via StorageProvider
    storage = get_storage_provider()
    presigned = await storage.generate_presigned_upload_url(
        key=storage_key,
        content_type=request.content_type,
        max_size_bytes=request.file_size_bytes,
    )

    # 5. Create Video Ingestion Record
    video = Video(
        id=video_id,
        tenant_id=current_tenant.id,
        creator_id=current_user.id,
        title=request.title,
        description=request.description,
        status="UPLOADING",
        raw_size_bytes=request.file_size_bytes,
        raw_storage_key=storage_key,
        visibility="PRIVATE",
    )
    db.add(video)
    await db.commit()

    return UploadIntentResponse(
        video_id=video_id,
        storage_key=storage_key,
        upload_url=presigned["upload_url"],
        method=presigned["method"],
        upload_fields=presigned.get("fields"),
        expires_in_seconds=presigned.get("expires_in", 3600),
    )


@router.post("/{video_id}/complete-upload", response_model=VideoResponse)
async def complete_upload(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_active_creator)],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.tenant_id == current_tenant.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if video.status != "UPLOADING":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video cannot be completed because current status is '{video.status}'",
        )

    # Verify that file was actually received in Object Storage
    storage = get_storage_provider()
    exists = await storage.object_exists(video.raw_storage_key)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File has not been received in object storage. Upload might have failed or not completed.",
        )

    # Retrieve confirmed file size
    meta = await storage.get_object_metadata(video.raw_storage_key)
    actual_size = meta.get("content_length", video.raw_size_bytes)
    video.raw_size_bytes = actual_size
    video.status = "QUEUED"
    video.processing_error = None

    # Update Tenant Usage Ledger (storage bytes & count)
    usage = current_tenant.usage
    usage.storage_bytes_used += actual_size
    usage.video_count += 1

    await db.commit()
    await db.refresh(video)

    # Dispatch asynchronous transcoding task
    try:
        from app.workers.transcode_tasks import process_video_task
        process_video_task.apply_async(args=[video.id, current_tenant.id], retry=False)
    except Exception as e:
        # If celery broker is offline, task remains QUEUED for worker sweep
        pass

    return video


@router.post("/{video_id}/retry-process", response_model=VideoResponse)
async def retry_process(
    video_id: str,
    current_user: Annotated[User, Depends(get_current_active_creator)],
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.tenant_id == current_tenant.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    if video.status not in ["FAILED", "QUEUED"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Video cannot be retried because current status is '{video.status}'",
        )

    video.status = "QUEUED"
    video.processing_error = None
    await db.commit()
    await db.refresh(video)

    try:
        from app.workers.transcode_tasks import process_video_task
        process_video_task.delay(video.id, current_tenant.id)
    except Exception:
        pass

    return video


@router.get("", response_model=List[VideoResponse])
async def list_videos(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Video).where(Video.tenant_id == current_tenant.id).order_by(Video.created_at.desc())
    )
    videos = result.scalars().all()
    return videos


@router.get("/{video_id}", response_model=VideoResponse)
async def get_video(
    video_id: str,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(Video).where(Video.id == video_id, Video.tenant_id == current_tenant.id)
    )
    video = result.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")
    return video


# Local simulation upload endpoint (used when storage provider is LOCAL)
@router.put("/local-upload")
async def local_upload_handler(
    request: Request,
    storage_key: str = Query(...),
):
    from pathlib import Path
    from app.core.config import settings
    
    base = Path(settings.LOCAL_STORAGE_BASE_PATH)
    dest = base / storage_key.lstrip("/\\")
    dest.parent.mkdir(parents=True, exist_ok=True)
    
    total_size = 0
    with open(dest, "wb") as f:
        async for chunk in request.stream():
            f.write(chunk)
            total_size += len(chunk)
        
    return {"success": True, "size": total_size, "storage_key": storage_key}
