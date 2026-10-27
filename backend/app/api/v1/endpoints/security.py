import json
import uuid
from datetime import datetime, timezone
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.dependencies import get_current_active_creator, get_current_tenant, get_current_user
from app.models.security import PiracyIncident, SecurityEvent
from app.models.tenant import Tenant
from app.models.user import User
from app.models.video import Video
from app.schemas.security import (
    ActiveSessionResponse,
    CreateIncidentRequest,
    PiracyIncidentResponse,
    RiskOverviewResponse,
    SecurityEventLogRequest,
    SecurityEventResponse,
    UpdateIncidentStatusRequest,
)
from app.services.playback.concurrency import session_manager
from app.services.security.evidence_generator import evidence_generator
from app.services.security.risk_engine import risk_engine

router = APIRouter()


@router.get("/events", response_model=List[SecurityEventResponse])
async def list_security_events(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
    severity: Optional[str] = Query(None),
    event_type: Optional[str] = Query(None),
    limit: int = Query(50, le=100),
):
    query = select(SecurityEvent).where(SecurityEvent.tenant_id == current_tenant.id)
    if severity:
        query = query.where(SecurityEvent.severity == severity.upper())
    if event_type:
        query = query.where(SecurityEvent.event_type == event_type)

    query = query.order_by(SecurityEvent.created_at.desc()).limit(limit)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("/events/log", response_model=SecurityEventResponse, status_code=status.HTTP_201_CREATED)
async def log_security_event(
    req: SecurityEventLogRequest,
    request: Request,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    client_ip = request.headers.get("X-Forwarded-For", request.client.host if request.client else "127.0.0.1")

    # Evaluate risk score
    is_tamper = "tamper" in req.event_type.lower()
    evaluation = risk_engine.evaluate(
        concurrent_streams=1,
        is_tamper_detected=is_tamper,
    )

    details_payload = req.details or {}
    details_payload["risk_triggers"] = evaluation.triggers
    details_payload["recommended_action"] = evaluation.action_recommended

    event = SecurityEvent(
        tenant_id=current_user.tenant_id,
        user_id=current_user.id,
        session_id=req.session_id,
        video_id=req.video_id,
        event_type=req.event_type,
        severity=req.severity,
        ip_address=client_ip,
        risk_score=evaluation.risk_score,
        details=json.dumps(details_payload),
    )
    db.add(event)
    await db.commit()
    await db.refresh(event)
    return event


@router.get("/sessions", response_model=List[ActiveSessionResponse])
async def list_active_sessions(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Lists currently active streaming sessions and their real-time risk scores."""
    active_sessions = []
    now = datetime.now(timezone.utc)

    for session_id, s in list(session_manager._sessions.items()):
        # Check tenant matching
        v_res = await db.execute(select(Video).where(Video.id == s.video_id))
        video = v_res.scalar_one_or_none()
        if not video or video.tenant_id != current_tenant.id:
            continue

        u_res = await db.execute(select(User).where(User.id == s.user_id))
        user = u_res.scalar_one_or_none()

        is_alive = await session_manager.is_session_active(session_id)

        # Concurrency count for user
        user_sessions = session_manager._user_to_sessions.get(s.user_id, [])
        user_concurrent = len(user_sessions)
        evaluation = risk_engine.evaluate(
            concurrent_streams=user_concurrent,
            max_allowed_streams=1,
        )

        started_dt = datetime.fromtimestamp(s.created_at, tz=timezone.utc)
        last_dt = datetime.fromtimestamp(s.last_ping, tz=timezone.utc)

        active_sessions.append(
            ActiveSessionResponse(
                session_id=session_id,
                user_id=s.user_id,
                user_email=user.email if user else "Viewer",
                video_id=video.id,
                video_title=video.title,
                ip_address=s.ip,
                risk_score=evaluation.risk_score,
                risk_level=evaluation.risk_level,
                started_at=started_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                last_heartbeat=last_dt.strftime("%Y-%m-%d %H:%M:%S UTC"),
                status="ACTIVE" if is_alive else s.status,
            )
        )
    return active_sessions


@router.post("/sessions/{session_id}/revoke")
async def revoke_session(
    session_id: str,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    current_user: Annotated[User, Depends(get_current_active_creator)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """Instantly revokes an active streaming session."""
    await session_manager.terminate_session(session_id, reason="FORCE_REVOKED_BY_ADMIN")

    # Record security audit event
    event = SecurityEvent(
        tenant_id=current_tenant.id,
        session_id=session_id,
        user_id=current_user.id,
        event_type="SESSION_FORCE_REVOKED",
        severity="HIGH",
        risk_score=85,
        details=json.dumps({"action": "Stream terminated manually by creator/admin"}),
    )
    db.add(event)
    await db.commit()

    return {"success": True, "message": f"Session {session_id} has been forcefully revoked."}


@router.get("/risk-overview", response_model=RiskOverviewResponse)
async def get_risk_overview(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    # Total events count
    events_count_res = await db.execute(
        select(func.count(SecurityEvent.id)).where(SecurityEvent.tenant_id == current_tenant.id)
    )
    total_events = events_count_res.scalar() or 0

    # Open incidents count
    incidents_count_res = await db.execute(
        select(func.count(PiracyIncident.id)).where(
            PiracyIncident.tenant_id == current_tenant.id,
            PiracyIncident.status.in_(["DETECTED", "UNDER_REVIEW", "CONFIRMED"]),
        )
    )
    open_incidents = incidents_count_res.scalar() or 0

    # Recent critical events
    crit_res = await db.execute(
        select(SecurityEvent)
        .where(SecurityEvent.tenant_id == current_tenant.id, SecurityEvent.severity.in_(["HIGH", "CRITICAL"]))
        .order_by(SecurityEvent.created_at.desc())
        .limit(5)
    )
    recent_critical = crit_res.scalars().all()

    # Active streams count
    active_count = sum(1 for s in session_manager._sessions.values() if s.status == "ACTIVE")
    revoked_count = sum(1 for s in session_manager._sessions.values() if s.status in ["TERMINATED", "EXPIRED"])

    avg_score = 15 if active_count == 0 else min(95, 20 + (open_incidents * 25))
    risk_level = "LOW" if avg_score < 40 else "MEDIUM" if avg_score < 70 else "HIGH"

    return RiskOverviewResponse(
        overall_risk_level=risk_level,
        average_risk_score=avg_score,
        active_streaming_sessions=active_count,
        revoked_sessions_count=revoked_count,
        total_security_events=total_events,
        open_piracy_incidents=open_incidents,
        recent_critical_events=recent_critical,
    )


@router.get("/incidents", response_model=List[PiracyIncidentResponse])
async def list_incidents(
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(PiracyIncident)
        .where(PiracyIncident.tenant_id == current_tenant.id)
        .order_by(PiracyIncident.created_at.desc())
    )
    incidents = result.scalars().all()
    # Populate video title
    response_list = []
    for inc in incidents:
        v_res = await db.execute(select(Video).where(Video.id == inc.video_id))
        video = v_res.scalar_one_or_none()
        item = PiracyIncidentResponse.model_validate(inc)
        item.video_title = video.title if video else "Protected Content"
        response_list.append(item)
    return response_list


@router.post("/incidents", response_model=PiracyIncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_piracy_incident(
    req: CreateIncidentRequest,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    current_user: Annotated[User, Depends(get_current_active_creator)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    v_res = await db.execute(
        select(Video).where(Video.id == req.video_id, Video.tenant_id == current_tenant.id)
    )
    video = v_res.scalar_one_or_none()
    if not video:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Video not found")

    incident_num = f"INC-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"

    # Generate initial evidence package
    evidence_package = evidence_generator.generate_package(
        incident_number=incident_num,
        video_id=video.id,
        video_title=video.title,
        source_url=req.source_url,
        similarity_score=req.similarity_score,
        suspected_session_id=req.suspected_session_id,
        watermark_data={"reported_by": current_user.email},
    )

    incident = PiracyIncident(
        tenant_id=current_tenant.id,
        video_id=video.id,
        incident_number=incident_num,
        status="DETECTED",
        similarity_score=req.similarity_score,
        source_url=req.source_url,
        suspected_user_id=req.suspected_user_id,
        suspected_session_id=req.suspected_session_id,
        evidence_data=json.dumps(evidence_package),
        notes=req.notes,
    )
    db.add(incident)
    await db.commit()
    await db.refresh(incident)

    res_item = PiracyIncidentResponse.model_validate(incident)
    res_item.video_title = video.title
    return res_item


@router.post("/incidents/{incident_id}/update-status", response_model=PiracyIncidentResponse)
async def update_incident_status(
    incident_id: str,
    req: UpdateIncidentStatusRequest,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    result = await db.execute(
        select(PiracyIncident).where(
            PiracyIncident.id == incident_id, PiracyIncident.tenant_id == current_tenant.id
        )
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    incident.status = req.status
    if req.notes:
        incident.notes = req.notes
    await db.commit()
    await db.refresh(incident)

    v_res = await db.execute(select(Video).where(Video.id == incident.video_id))
    video = v_res.scalar_one_or_none()
    res_item = PiracyIncidentResponse.model_validate(incident)
    res_item.video_title = video.title if video else "Protected Content"
    return res_item


@router.get("/incidents/{incident_id}/evidence")
async def download_incident_evidence(
    incident_id: str,
    current_tenant: Annotated[Tenant, Depends(get_current_tenant)],
    db: Annotated[AsyncSession, Depends(get_db)],
    format: str = Query("json", pattern="^(json|csv)$"),
):
    result = await db.execute(
        select(PiracyIncident).where(
            PiracyIncident.id == incident_id, PiracyIncident.tenant_id == current_tenant.id
        )
    )
    incident = result.scalar_one_or_none()
    if not incident:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Incident not found")

    evidence_pkg = json.loads(incident.evidence_data)

    if format == "csv":
        csv_data = evidence_generator.export_csv(evidence_pkg)
        return Response(
            content=csv_data,
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={incident.incident_number}_evidence.csv"},
        )

    return Response(
        content=json.dumps(evidence_pkg, indent=2),
        media_type="application/json",
        headers={"Content-Disposition": f"attachment; filename={incident.incident_number}_evidence.json"},
    )
