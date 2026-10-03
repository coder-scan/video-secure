import pytest
from httpx import AsyncClient
from app.core.config import settings


@pytest.mark.asyncio
async def test_root_superadmin_login(client: AsyncClient):
    # 1. Invalid credentials -> 401
    bad_res = await client.post(
        "/api/v1/auth/admin-login",
        json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": "WrongPassword!",
        },
    )
    assert bad_res.status_code == 401

    # 2. Valid credentials defined directly in .env -> 200
    res = await client.post(
        "/api/v1/auth/admin-login",
        json={
            "email": settings.SUPERADMIN_EMAIL,
            "password": settings.SUPERADMIN_PASSWORD,
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "OWNER"
    assert "access_token" in data
    assert "refresh_token" in data

    token = data["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 3. Verify access to Organization details with Enterprise unlimited quotas
    org_res = await client.get("/api/v1/tenants/my-organization", headers=headers)
    assert org_res.status_code == 200
    org_data = org_res.json()
    assert org_data["plan_tier"] == "ENTERPRISE"
    assert org_data["quota"]["storage_bytes_limit"] >= 100 * 1024 * 1024 * 1024 * 1024  # 100 TB
