import json
import pytest
from httpx import AsyncClient
from sqlalchemy import select

from app.core.database import async_session_maker
from app.models.security import PiracyIncident, SecurityEvent
from app.models.video import Video
from app.services.playback.concurrency import session_manager
from app.services.security.risk_engine import risk_engine


@pytest.mark.asyncio
async def test_risk_engine_evaluation():
    # 1. Normal single stream
    normal = risk_engine.evaluate(concurrent_streams=1, max_allowed_streams=1)
    assert normal.risk_score == 0
    assert normal.risk_level == "LOW"
    assert normal.action_recommended == "ALLOW"
    assert len(normal.triggers) == 0

    # 2. Concurrency anomaly (3 streams when 1 allowed)
    concurrency_anomaly = risk_engine.evaluate(concurrent_streams=3, max_allowed_streams=1)
    assert concurrency_anomaly.risk_score >= 50
    assert concurrency_anomaly.risk_level in ["MEDIUM", "HIGH"]
    assert any("concurrent" in t.lower() for t in concurrency_anomaly.triggers)

    # 3. DOM / Watermark Tampering
    tamper = risk_engine.evaluate(is_tamper_detected=True)
    assert tamper.risk_score >= 45
    assert tamper.risk_level == "MEDIUM"
    assert any("tamper" in t.lower() for t in tamper.triggers)

    # 4. Critical compound threat
    critical = risk_engine.evaluate(
        concurrent_streams=3,
        max_allowed_streams=1,
        is_tamper_detected=True,
        is_ip_anomaly=True,
    )
    assert critical.risk_score >= 90
    assert critical.risk_level == "VERY_HIGH"
    assert critical.action_recommended == "RESTRICT_SESSION"


@pytest.mark.asyncio
async def test_security_event_logging_and_filtering(client: AsyncClient):
    # 1. Register Tenant A
    res_a = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Security Test Studio A",
            "email": "sec_a@studio.com",
            "password": "Password123!",
        },
    )
    token_a = res_a.json()["access_token"]
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 2. Register Tenant B
    res_b = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Security Test Studio B",
            "email": "sec_b@studio.com",
            "password": "Password123!",
        },
    )
    token_b = res_b.json()["access_token"]
    headers_b = {"Authorization": f"Bearer {token_b}"}

    # 3. Log security event for Tenant A
    log_res = await client.post(
        "/api/v1/security/events/log",
        json={
            "event_type": "DOM_TAMPER_DETECTED",
            "severity": "HIGH",
            "details": {"element": "watermark_canvas", "action": "opacity_suppression"},
        },
        headers=headers_a,
    )
    assert log_res.status_code == 201
    event_data = log_res.json()
    assert event_data["event_type"] == "DOM_TAMPER_DETECTED"
    assert event_data["severity"] == "HIGH"
    assert event_data["risk_score"] > 0

    # 4. Tenant A lists events -> should see the event
    list_a = await client.get("/api/v1/security/events", headers=headers_a)
    assert list_a.status_code == 200
    assert len(list_a.json()) >= 1
    assert list_a.json()[0]["id"] == event_data["id"]

    # 5. Tenant B lists events -> isolation: must see 0 events
    list_b = await client.get("/api/v1/security/events", headers=headers_b)
    assert list_b.status_code == 200
    assert len(list_b.json()) == 0


@pytest.mark.asyncio
async def test_active_sessions_and_force_revocation(client: AsyncClient):
    # 1. Register Tenant
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Live Session Org",
            "email": "streamer@liveorg.com",
            "password": "Password123!",
        },
    )
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    user_id = res.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Video in DB
    video_id = "test-session-vid-99"
    async with async_session_maker() as db:
        video = Video(
            id=video_id,
            tenant_id=tenant_id,
            creator_id=user_id,
            title="Active Stream Video",
            status="READY",
            visibility="PRIVATE",
            encryption_key_id="k-99",
            encryption_key_cipher="dummy_cipher",
        )
        db.add(video)
        await db.commit()

    # 3. Register an active session in session_manager
    session_id = await session_manager.register_session(
        user_id=user_id,
        video_id=video_id,
        ip="198.51.100.42",
        max_concurrent=1,
    )

    # 4. Query active sessions API
    sessions_res = await client.get("/api/v1/security/sessions", headers=headers)
    assert sessions_res.status_code == 200
    sess_list = sessions_res.json()
    assert any(s["session_id"] == session_id for s in sess_list)

    # 5. Force revoke session via API
    revoke_res = await client.post(f"/api/v1/security/sessions/{session_id}/revoke", headers=headers)
    assert revoke_res.status_code == 200
    assert revoke_res.json()["success"] is True

    # 6. Verify session is no longer active
    is_active = await session_manager.is_session_active(session_id)
    assert is_active is False

    # 7. Verify security event was logged
    events_res = await client.get("/api/v1/security/events?event_type=SESSION_FORCE_REVOKED", headers=headers)
    assert events_res.status_code == 200
    assert len(events_res.json()) >= 1


@pytest.mark.asyncio
async def test_piracy_incident_lifecycle_and_evidence_export(client: AsyncClient):
    # 1. Register Creator
    res = await client.post(
        "/api/v1/auth/register",
        json={
            "organization_name": "Anti-Piracy Unit",
            "email": "investigator@autopiracy.org",
            "password": "Password123!",
        },
    )
    token = res.json()["access_token"]
    tenant_id = res.json()["tenant_id"]
    user_id = res.json()["user_id"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Create Video in DB
    video_id = "leaked-course-vid-01"
    async with async_session_maker() as db:
        video = Video(
            id=video_id,
            tenant_id=tenant_id,
            creator_id=user_id,
            title="Premium Cyber Masterclass",
            status="READY",
            visibility="PRIVATE",
            encryption_key_id="k-leak-01",
            encryption_key_cipher="dummy_cipher",
        )
        db.add(video)
        await db.commit()

    # 3. Create Piracy Incident
    create_payload = {
        "video_id": video_id,
        "source_url": "https://suspicious-file-sharing.com/leak/cyber-masterclass.mp4",
        "similarity_score": 0.94,
        "suspected_session_id": "sess_89a3f2",
        "notes": "Recovered visual watermark matches student enrollment batch 4.",
    }
    inc_res = await client.post("/api/v1/security/incidents", json=create_payload, headers=headers)
    assert inc_res.status_code == 201
    incident_data = inc_res.json()
    incident_id = incident_data["id"]
    assert incident_data["status"] == "DETECTED"
    assert incident_data["similarity_score"] == 0.94
    assert "INC-" in incident_data["incident_number"]
    assert incident_data["video_title"] == "Premium Cyber Masterclass"

    # 4. Update Incident Status to CONFIRMED
    update_res = await client.post(
        f"/api/v1/security/incidents/{incident_id}/update-status",
        json={"status": "CONFIRMED", "notes": "Fingerprint verified with >90% frame match."},
        headers=headers,
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "CONFIRMED"

    # 5. Download Evidence Package as JSON
    evidence_json_res = await client.get(
        f"/api/v1/security/incidents/{incident_id}/evidence?format=json",
        headers=headers,
    )
    assert evidence_json_res.status_code == 200
    assert evidence_json_res.headers["content-type"] == "application/json"
    evidence_pkg = evidence_json_res.json()
    assert evidence_pkg["incident_number"] == incident_data["incident_number"]
    assert "package_sha256_checksum" in evidence_pkg
    assert evidence_pkg["leak_detection"]["similarity_score_pct"] == 94.0

    # 6. Download Evidence Package as CSV
    evidence_csv_res = await client.get(
        f"/api/v1/security/incidents/{incident_id}/evidence?format=csv",
        headers=headers,
    )
    assert evidence_csv_res.status_code == 200
    assert "text/csv" in evidence_csv_res.headers["content-type"]
    csv_text = evidence_csv_res.text
    assert "Incident Number" in csv_text
    assert incident_data["incident_number"] in csv_text
    assert "package_sha256_checksum" in csv_text or "Cryptographic Checksum" in csv_text

    # 7. Verify Risk Overview reflects open incident
    overview_res = await client.get("/api/v1/security/risk-overview", headers=headers)
    assert overview_res.status_code == 200
    overview = overview_res.json()
    assert overview["open_piracy_incidents"] >= 1
