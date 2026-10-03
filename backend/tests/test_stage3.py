import json
import pytest
from pathlib import Path
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.tenant import Tenant, TenantQuota, TenantUsage
from app.models.video import Video
from app.services.playback.concurrency import session_manager
from app.services.video.crypto import decrypt_key_cipher, encrypt_key_cipher, generate_aes128_key_and_iv


@pytest.mark.asyncio
async def test_stage3_playback_token_and_security(client: AsyncClient):
    # 1. Register Tenant A & Creator A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Cinema Org",
            "email": "director@cinema.org",
            "password": "Password123!",
        },
    )
    assert res_a.status_code == 201
    token_a = res_a.json()["access_token"]
    tenant_a_id = res_a.json()["tenant_id"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Tenant B & User B (Attacker / Outsider)
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Competitor Org",
            "email": "spy@competitor.org",
            "password": "Password123!",
        },
    )
    assert res_b.status_code == 201
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Create a READY video manually in database with encrypted AES-128 key
    raw_key, iv = generate_aes128_key_and_iv()
    cipher = encrypt_key_cipher(raw_key, iv)
    video_id = "test-video-uuid-1234"
    key_id = "test-key-uuid-5678"

    async with async_session_maker() as db:
        video = Video(
            id=video_id,
            tenant_id=tenant_a_id,
            creator_id=res_a.json()["user_id"],
            title="Confidential Masterpiece",
            status="READY",
            visibility="PRIVATE",
            encryption_key_id=key_id,
            encryption_key_cipher=cipher,
            hls_master_path=f"processed/{tenant_a_id}/{video_id}/hls/master.m3u8",
        )
        db.add(video)
        await db.commit()

    # 4. Attempt unauthenticated token generation -> 401
    unauth_res = await client.post(
        "/api/v1/playback/token",
        json={"video_id": video_id},
    )
    assert unauth_res.status_code == 401

    # 5. Attempt unauthorized tenant access (User B accessing Tenant A's private video) -> 403
    forbidden_res = await client.post(
        "/api/v1/playback/token",
        json={"video_id": video_id},
        headers=headers_b,
    )
    assert forbidden_res.status_code == 403
    assert "private" in forbidden_res.json()["detail"].lower()

    # 6. Authorized Viewer (User A) requests playback token -> 200
    auth_res = await client.post(
        "/api/v1/playback/token",
        json={"video_id": video_id},
        headers=headers_a,
    )
    assert auth_res.status_code == 200
    play_data = auth_res.json()
    playback_token = play_data["playback_token"]
    session_id = play_data["session_id"]
    manifest_url = play_data["manifest_url"]

    # Verify dynamic watermark payload
    assert play_data["watermark"]["viewer_email"] == "director@cinema.org"
    assert "viewer_ip" in play_data["watermark"]
    assert "timestamp" in play_data["watermark"]

    # 7. Key License Delivery: Direct access with NO token -> 401
    raw_key_no_token = await client.get(f"/api/v1/playback/key/{key_id}")
    assert raw_key_no_token.status_code == 401

    # 8. Key License Delivery: Tampered token -> 401
    bad_key_res = await client.get(
        f"/api/v1/playback/key/{key_id}",
        params={"token": "invalid.jwt.token"},
    )
    assert bad_key_res.status_code == 401

    # 9. Key License Delivery: Authorized token via Query Param -> 200
    key_res = await client.get(
        f"/api/v1/playback/key/{key_id}",
        params={"token": playback_token},
    )
    assert key_res.status_code == 200
    assert key_res.headers["content-type"] == "application/octet-stream"
    assert key_res.headers["cache-control"] == "no-store, no-cache, must-revalidate, max-age=0"
    # Cryptographic proof: Delivered raw bytes match original raw key
    assert key_res.content == raw_key
    assert len(key_res.content) == 16


@pytest.mark.asyncio
async def test_session_concurrency_single_device_enforcement(client: AsyncClient):
    """
    Verifies that when a second device starts streaming on the same account,
    the first stream session is evicted and subsequent key/heartbeat calls fail.
    """
    # 1. Register User
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Solo Streamer Org",
            "email": "user@solostream.com",
            "password": "Password123!",
        },
    )
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    user_id = res.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Video
    raw_key, iv = generate_aes128_key_and_iv()
    cipher = encrypt_key_cipher(raw_key, iv)
    video_id = "concurrency-video-001"
    key_id = "concurrency-key-001"

    async with async_session_maker() as db:
        video = Video(
            id=video_id,
            tenant_id=tenant_id,
            creator_id=user_id,
            title="Concurrency Test Video",
            status="READY",
            visibility="PRIVATE",
            encryption_key_id=key_id,
            encryption_key_cipher=cipher,
            hls_master_path=f"processed/{tenant_id}/{video_id}/hls/master.m3u8",
        )
        db.add(video)
        await db.commit()

    # 3. Device 1 connects
    res_dev1 = await client.post(
        "/api/v1/playback/token",
        json={"video_id": video_id},
        headers=headers,
    )
    assert res_dev1.status_code == 200
    token1 = res_dev1.json()["playback_token"]
    session1 = res_dev1.json()["session_id"]

    # Device 1 key fetch succeeds
    key_dev1 = await client.get(f"/api/v1/playback/key/{key_id}", params={"token": token1})
    assert key_dev1.status_code == 200

    # Device 1 heartbeat succeeds
    hb1 = await client.post(
        "/api/v1/playback/heartbeat",
        json={"session_id": session1, "playback_token": token1},
    )
    assert hb1.status_code == 200
    assert hb1.json()["status"] == "ACTIVE"

    # 4. Device 2 connects on same account (exceeds max_concurrent=1)
    res_dev2 = await client.post(
        "/api/v1/playback/token",
        json={"video_id": video_id},
        headers=headers,
    )
    assert res_dev2.status_code == 200
    token2 = res_dev2.json()["playback_token"]
    session2 = res_dev2.json()["session_id"]
    assert session1 != session2

    # 5. Device 1 tries heartbeat or key request -> Evicted!
    hb1_evicted = await client.post(
        "/api/v1/playback/heartbeat",
        json={"session_id": session1, "playback_token": token1},
    )
    assert hb1_evicted.status_code == 200
    assert hb1_evicted.json()["status"] == "TERMINATED"
    assert "CONCURRENT_STREAM_DETECTED" in hb1_evicted.json()["message"]

    key_dev1_revoked = await client.get(f"/api/v1/playback/key/{key_id}", params={"token": token1})
    assert key_dev1_revoked.status_code == 403
    assert "concurrent" in key_dev1_revoked.json()["detail"].lower()

    # 6. Device 2 succeeds
    key_dev2 = await client.get(f"/api/v1/playback/key/{key_id}", params={"token": token2})
    assert key_dev2.status_code == 200
    assert key_dev2.content == raw_key
