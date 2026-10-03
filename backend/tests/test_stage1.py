import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    response = await client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"


@pytest.mark.asyncio
async def test_auth_registration_and_login(client: AsyncClient):
    # 1. Register organization and creator
    register_payload = {
        "organization_name": "Apex EdTech",
        "email": "creator@apex.edu",
        "password": "SecurePassword123!",
        "full_name": "Dr. Sarah Connor",
    }
    reg_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert reg_res.status_code == 201
    reg_data = reg_res.json()
    assert "access_token" in reg_data
    assert reg_data["role"] == "OWNER"
    tenant_id = reg_data["tenant_id"]

    # 2. Check duplicate registration rejection
    dup_res = await client.post("/api/v1/auth/register", json=register_payload)
    assert dup_res.status_code == 400

    # 3. Test Login
    login_payload = {
        "email": "creator@apex.edu",
        "password": "SecurePassword123!",
    }
    login_res = await client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    token = login_res.json()["access_token"]

    # 4. Test Protected /me endpoint
    headers = {"Authorization": f"Bearer {token}"}
    me_res = await client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    me_data = me_res.json()
    assert me_data["email"] == "creator@apex.edu"
    assert me_data["tenant_id"] == tenant_id


@pytest.mark.asyncio
async def test_tenant_quota_and_usage(client: AsyncClient):
    # Register creator
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Code Academy",
            "email": "admin@codeacademy.org",
            "password": "Password456!",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Query organization details
    org_res = await client.get("/api/v1/tenants/my-organization", headers=headers)
    assert org_res.status_code == 200
    org_data = org_res.json()
    assert org_data["name"] == "Code Academy"
    assert org_data["plan_tier"] == "FREE"
    assert org_data["quota"]["storage_bytes_limit"] == 5 * 1024 * 1024 * 1024
    assert org_data["quota"]["max_videos"] == 10
    assert org_data["usage"]["storage_bytes_used"] == 0
    assert org_data["usage"]["video_count"] == 0


@pytest.mark.asyncio
async def test_video_upload_intent_and_quota_enforcement(client: AsyncClient):
    # Register creator
    reg_res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Film Studio",
            "email": "director@filmstudio.io",
            "password": "Password789!",
        },
    )
    token = reg_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Normal upload intent (100 MB)
    upload_intent_payload = {
        "title": "Module 1: Introduction to Cyber Defense",
        "filename": "intro-lecture.mp4",
        "file_size_bytes": 100 * 1024 * 1024,
        "content_type": "video/mp4",
        "description": "Foundational security concepts.",
    }
    intent_res = await client.post("/api/v1/videos/upload-intent", json=upload_intent_payload, headers=headers)
    assert intent_res.status_code == 201
    intent_data = intent_res.json()
    assert "upload_url" in intent_data
    video_id = intent_data["video_id"]
    storage_key = intent_data["storage_key"]

    # 2. Quota rejection test: Request an upload larger than 5GB free limit (6 GB)
    giant_payload = {
        "title": "Raw 8K Uncompressed",
        "filename": "giant.mp4",
        "file_size_bytes": 6 * 1024 * 1024 * 1024,
        "content_type": "video/mp4",
    }
    quota_res = await client.post("/api/v1/videos/upload-intent", json=giant_payload, headers=headers)
    assert quota_res.status_code == 402  # Quota exceeded error

    # 3. Simulate file upload completion
    # In local storage, simulate the file existing
    from pathlib import Path
    test_storage_dir = Path("./storage_test")
    file_path = test_storage_dir / storage_key.lstrip("/\\")
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        f.write(b"MOCK_MP4_BINARY_DATA_TESTING")

    complete_res = await client.post(f"/api/v1/videos/{video_id}/complete-upload", headers=headers)
    assert complete_res.status_code == 200
    complete_data = complete_res.json()
    assert complete_data["status"] == "QUEUED"
    assert complete_data["raw_size_bytes"] > 0

    # 4. Verify tenant usage was updated
    org_res = await client.get("/api/v1/tenants/my-organization", headers=headers)
    org_data = org_res.json()
    assert org_data["usage"]["video_count"] == 1
    assert org_data["usage"]["storage_bytes_used"] > 0

    # Clean up test files
    if file_path.exists():
        file_path.unlink()


@pytest.mark.asyncio
async def test_multi_tenant_idor_isolation(client: AsyncClient):
    # 1. Register Tenant A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": "Org A", "email": "admin@orga.com", "password": "Password123!"},
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Tenant B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={"organization_name": "Org B", "email": "admin@orgb.com", "password": "Password123!"},
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Tenant A creates upload intent
    intent_res = await client.post(
        "/api/v1/videos/upload-intent",
        json={"title": "Private Org A Video", "filename": "private.mp4", "file_size_bytes": 1024 * 1024},
        headers=headers_a,
    )
    video_id_a = intent_res.json()["video_id"]

    # 4. Tenant B attempts to fetch Tenant A's video (must be 404/denied)
    idor_get = await client.get(f"/api/v1/videos/{video_id_a}", headers=headers_b)
    assert idor_get.status_code == 404

    # 5. Tenant B attempts to complete upload on Tenant A's video (must be 404/denied)
    idor_complete = await client.post(f"/api/v1/videos/{video_id_a}/complete-upload", headers=headers_b)
    assert idor_complete.status_code == 404

