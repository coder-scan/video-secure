import asyncio
import json
import logging
import math
import shutil
import uuid
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import async_session_maker
from app.models.tenant import Tenant
from app.models.video import Video
from app.services.storage.factory import get_storage_provider
from app.services.video.crypto import encrypt_key_cipher, generate_aes128_key_and_iv
from app.services.video.inspector import MediaValidationError, inspect_media_file
from app.services.video.transcoder import transcode_to_encrypted_hls

logger = logging.getLogger(__name__)


async def process_video_task(video_id: str, tenant_id: str) -> dict:
    """
    Asynchronous task that validates untrusted uploaded media,
    verifies tenant processing quota, packages video into encrypted multi-variant HLS,
    generates thumbnails, and updates the database state.
    """
    logger.info(f"Starting transcode task for video {video_id} (tenant: {tenant_id})")
    return await _process_video_async(video_id, tenant_id)


async def _process_video_async(video_id: str, tenant_id: str) -> dict:
    async with async_session_maker() as db:
        # 1. Fetch Video and Tenant records
        v_res = await db.execute(
            select(Video).where(Video.id == video_id, Video.tenant_id == tenant_id)
        )
        video = v_res.scalar_one_or_none()
        if not video:
            logger.error(f"Video {video_id} not found in database")
            return {"success": False, "error": "Video not found"}

        # Idempotency check: if already READY, skip
        if video.status == "READY":
            logger.info(f"Video {video_id} is already READY. Skipping.")
            return {"success": True, "status": "ALREADY_READY"}

        t_res = await db.execute(
            select(Tenant)
            .options(
                selectinload(Tenant.quota),
                selectinload(Tenant.usage),
                selectinload(Tenant.storage_integrations),
            )
            .where(Tenant.id == tenant_id)
        )
        tenant = t_res.scalar_one_or_none()
        if not tenant:
            logger.error(f"Tenant {tenant_id} not found")
            return {"success": False, "error": "Tenant not found"}

        # 2. Transition status to PROCESSING
        video.status = "PROCESSING"
        video.processing_error = None
        await db.commit()

        # 3. Setup isolated scratch directory
        scratch_base = Path("./scratch")
        scratch_dir = scratch_base / f"job_{video_id}_{uuid.uuid4().hex[:8]}"
        scratch_dir.mkdir(parents=True, exist_ok=True)
        local_raw_path = scratch_dir / "source_media.tmp"
        hls_output_dir = scratch_dir / "hls_output"

        active_integ = (
            next((i for i in tenant.storage_integrations if i.is_active), None)
            if tenant.storage_integrations
            else None
        )
        storage = get_storage_provider(active_integ)

        try:
            # 4. Ingest raw media from object storage
            if not video.raw_storage_key:
                raise MediaValidationError("Missing raw storage key on video record")

            exists = await storage.object_exists(video.raw_storage_key)
            if not exists:
                raise MediaValidationError(f"Raw video object {video.raw_storage_key} not found in storage")

            await storage.download_file(video.raw_storage_key, str(local_raw_path))

            # 5. Inspect untrusted media
            metadata = inspect_media_file(local_raw_path)

            # 6. Pre-transcode Processing Quota Check
            quota = tenant.quota
            usage = tenant.usage
            media_minutes = math.ceil(metadata.duration_seconds / 60.0)

            if usage.processing_minutes_used + media_minutes > quota.processing_minutes_limit:
                error_msg = (
                    f"Processing quota exceeded: video requires {media_minutes} minutes, "
                    f"but only {quota.processing_minutes_limit - usage.processing_minutes_used} minutes remain."
                )
                logger.warning(f"Tenant {tenant_id} quota breach: {error_msg}")
                video.status = "FAILED"
                video.processing_error = error_msg
                await db.commit()
                return {"success": False, "error": error_msg}

            # 7. Generate random 16-byte AES-128 key and IV
            raw_key, iv = generate_aes128_key_and_iv()

            # Store encrypted key cipher in database
            video.encryption_key_cipher = encrypt_key_cipher(raw_key, iv)

            # Stage 3 key license delivery URL
            key_uri = f"/api/v1/playback/key/{video.encryption_key_id}"

            # 8. Transcode into multi-variant encrypted HLS
            package_info = transcode_to_encrypted_hls(
                source_file=local_raw_path,
                output_dir=hls_output_dir,
                key_uri=key_uri,
                raw_key=raw_key,
                iv=iv,
                metadata=metadata,
            )

            # 9. Upload all generated HLS assets & thumbnails to Storage
            remote_hls_prefix = f"processed/{tenant_id}/{video_id}/hls"
            uploaded_master_path = None

            for local_file in hls_output_dir.rglob("*"):
                if local_file.is_file():
                    rel_path = local_file.relative_to(hls_output_dir).as_posix()
                    remote_key = f"{remote_hls_prefix}/{rel_path}"

                    content_type = "application/octet-stream"
                    if rel_path.endswith(".m3u8"):
                        content_type = "application/vnd.apple.mpegurl"
                    elif rel_path.endswith(".ts"):
                        content_type = "video/mp2t"
                    elif rel_path.endswith(".jpg"):
                        content_type = "image/jpeg"

                    await storage.upload_file(str(local_file), remote_key, content_type=content_type)

                    if rel_path == "master.m3u8":
                        uploaded_master_path = remote_key

            # 10. Update Video State & Finalize Usage
            video.status = "READY"
            video.hls_master_path = uploaded_master_path
            video.duration_seconds = int(metadata.duration_seconds)
            video.width = metadata.width
            video.height = metadata.height
            video.codec_video = metadata.codec_video
            video.codec_audio = metadata.codec_audio
            video.thumbnail_paths = json.dumps(package_info.get("thumbnails", []))
            video.processing_error = None

            # Increment tenant processing usage
            usage.processing_minutes_used += media_minutes

            await db.commit()
            logger.info(f"Video {video_id} processing successfully completed -> READY")
            return {"success": True, "video_id": video_id, "status": "READY"}

        except MediaValidationError as mve:
            logger.error(f"Media validation error for video {video_id}: {str(mve)}")
            video.status = "FAILED"
            video.processing_error = f"Validation Error: {str(mve)}"
            await db.commit()
            return {"success": False, "error": str(mve)}

        except Exception as e:
            logger.exception(f"Unexpected transcoding error on video {video_id}: {str(e)}")
            video.status = "FAILED"
            video.processing_error = f"Processing failed: {str(e)[:300]}"
            await db.commit()
            return {"success": False, "error": str(e)}

        finally:
            # 11. Guarantee scratch directory cleanup
            if scratch_dir.exists():
                shutil.rmtree(scratch_dir, ignore_errors=True)
                logger.debug(f"Cleaned scratch directory {scratch_dir}")
