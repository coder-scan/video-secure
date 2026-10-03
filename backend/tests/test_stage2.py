import json
import pytest
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.tenant import Tenant, TenantQuota, TenantUsage
from app.models.video import Video
from app.services.storage.factory import get_storage_provider
from app.services.video.crypto import decrypt_key_cipher, encrypt_key_cipher, generate_aes128_key_and_iv
from app.services.video.inspector import MediaValidationError, inspect_media_file
from app.services.video.transcoder import select_target_variants
from app.workers.transcode_tasks import _process_video_async


@pytest.mark.asyncio
async def test_crypto_key_and_cipher():
    raw_key, iv = generate_aes128_key_and_iv()
    assert len(raw_key) == 16
    assert len(iv) == 16
    assert raw_key != iv

    # Encrypt
    cipher_str = encrypt_key_cipher(raw_key, iv)
    assert isinstance(cipher_str, str)
    assert len(cipher_str) > 32

    # Decrypt and verify round-trip
    dec_key, dec_iv = decrypt_key_cipher(cipher_str)
    assert dec_key == raw_key
    assert dec_iv == iv


@pytest.mark.asyncio
async def test_variant_resolution_picker():
    # 720p source must NOT generate 1080p
    variants_720 = select_target_variants(720)
    names_720 = [v.name for v in variants_720]
    assert "360p" in names_720
    assert "720p" in names_720
    assert "1080p" not in names_720

    # 1080p source must generate all 3
    variants_1080 = select_target_variants(1080)
    names_1080 = [v.name for v in variants_1080]
    assert names_1080 == ["360p", "720p", "1080p"]

    # 480p source must only generate 360p
    variants_480 = select_target_variants(480)
    names_480 = [v.name for v in variants_480]
    assert names_480 == ["360p"]


@pytest.mark.asyncio
async def test_media_inspector_untrusted_input(tmp_path: Path):
    # 1. Non-existent file
    with pytest.raises(MediaValidationError, match="does not exist"):
        inspect_media_file(tmp_path / "missing.mp4")

    # 2. Empty file
    empty_file = tmp_path / "empty.mp4"
    empty_file.touch()
    with pytest.raises(MediaValidationError, match="empty"):
        inspect_media_file(empty_file)

    # 3. Invalid container / fake file
    fake_file = tmp_path / "fake.mp4"
    fake_file.write_text("THIS IS NOT A REAL VIDEO FILE")
    with pytest.raises(MediaValidationError, match="Unsupported file signature or container"):
        inspect_media_file(fake_file)


@pytest.mark.asyncio
async def test_end_to_end_transcode_pipeline(client: AsyncClient):
    # 1. Register Tenant and Creator
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Stream Lab",
            "email": "producer@streamlab.tv",
            "password": "Password123!",
        },
    )
    assert reg_res.status_code == 201
    auth_data = reg_res.json()
    token = auth_data["access_token"]
    tenant_id = auth_data["tenant_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Upload Intent
    intent_res = await client.post(
        "/api/v1/videos/upload-intent",
        json={
            "title": "Quantum Computing 101",
            "filename": "quantum.mp4",
            "file_size_bytes": 1024 * 50,
            "content_type": "video/mp4",
        },
        headers=headers,
    )
    assert intent_res.status_code == 201
    video_id = intent_res.json()["video_id"]
    storage_key = intent_res.json()["storage_key"]

    # 3. Write mock MP4 file to test storage
    test_storage_dir = Path("./storage_test")
    file_path = test_storage_dir / storage_key.lstrip("/\\")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        # Write valid MP4 ftyp container box signature
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 4096)

    # 4. Complete upload -> status becomes QUEUED
    comp_res = await client.post(f"/api/v1/videos/{video_id}/complete-upload", headers=headers)
    assert comp_res.status_code == 200
    assert comp_res.json()["status"] == "QUEUED"

    # 5. Execute worker processing
    worker_res = await _process_video_async(video_id, tenant_id)
    assert worker_res["success"] is True
    assert worker_res["status"] == "READY"

    # 6. Verify database state
    async with async_session_maker() as db:
        v_res = await db.execute(select(Video).where(Video.id == video_id))
        video = v_res.scalar_one()
        assert video.status == "READY"
        assert video.hls_master_path is not None
        assert video.duration_seconds > 0
        assert video.width == 1280
        assert video.height == 720
        assert video.encryption_key_cipher is not None
        assert video.processing_error is None

        # Verify thumbnails exist
        thumbs = json.loads(video.thumbnail_paths)
        assert len(thumbs) == 3

        # Verify tenant processing usage was updated
        t_res = await db.execute(select(TenantUsage).where(TenantUsage.tenant_id == tenant_id))
        usage = t_res.scalar_one()
        assert usage.processing_minutes_used > 0

    # 7. Verify generated HLS assets in storage
    storage = get_storage_provider()
    assert await storage.object_exists(video.hls_master_path) is True

    # 8. Idempotency test: reprocessing a READY video does not re-run or double-charge
    idempotent_res = await _process_video_async(video_id, tenant_id)
    assert idempotent_res["success"] is True
    assert idempotent_res["status"] == "ALREADY_READY"

    # Clean up test file
    if file_path.exists():
        file_path.unlink()


@pytest.mark.asyncio
async def test_security_negative_quota_breach(client: AsyncClient):
    # Register Tenant
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Zero Quota Org",
            "email": "admin@zeroquota.org",
            "password": "Password123!",
        },
    )
    token = reg_res.json()["access_token"]
    tenant_id = reg_res.json()["tenant_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # Set processing limit to 0
    async with async_session_maker() as db:
        q_res = await db.execute(select(TenantQuota).where(TenantQuota.tenant_id == tenant_id))
        quota = q_res.scalar_one()
        quota.processing_minutes_limit = 0
        await db.commit()

    # Upload video
    intent_res = await client.post(
        "/api/v1/videos/upload-intent",
        json={"title": "Exceed Quota Video", "filename": "test.mp4", "file_size_bytes": 1024},
        headers=headers,
    )
    video_id = intent_res.json()["video_id"]
    storage_key = intent_res.json()["storage_key"]

    file_path = Path("./storage_test") / storage_key.lstrip("/\\")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(b"\x00\x00\x00\x18ftypmp42\x00\x00\x00\x00mp42isom" + b"\x00" * 1024)

    await client.post(f"/api/v1/videos/{video_id}/complete-upload", headers=headers)

    # Worker processing should fail cleanly on quota breach
    worker_res = await _process_video_async(video_id, tenant_id)
    assert worker_res["success"] is False
    assert "Processing quota exceeded" in worker_res["error"]

    # Verify status is FAILED
    async with async_session_maker() as db:
        v_res = await db.execute(select(Video).where(Video.id == video_id))
        video = v_res.scalar_one()
        assert video.status == "FAILED"
        assert "quota exceeded" in video.processing_error.lower()

    if file_path.exists():
        file_path.unlink()
