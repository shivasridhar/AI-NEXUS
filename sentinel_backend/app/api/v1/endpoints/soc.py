import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_, String

from app.api.dependencies import get_current_workspace, get_db
from app.models.tenant import Workspace
from app.models.canonical_event import CanonicalEvent
from app.models.incident import Incident
from app.schemas.security_event import SecurityEvent
from app.services.correlation.incident_correlator import IncidentCorrelator

# Reuse the existing ingestion pipeline (Phase 10 & 11)
from app.api.v1.endpoints.ingestion import global_pipeline

router = APIRouter()
logger = logging.getLogger(__name__)
correlator = IncidentCorrelator()

@router.post("/events", response_model=Dict[str, Any])
async def receive_soc_event(
    request: Request,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """
    Phase 2: Generic SOC Receiver Endpoint
    Accepts arbitrary JSON payloads from any security connector.
    """
    try:
        payload = await request.json()
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    # Map dynamic payload to canonical SecurityEvent (Phase 3)
    event_id = payload.get("id", str(uuid.uuid4()))
    source = payload.get("source", "unknown_connector")
    
    sec_event = SecurityEvent(
        event_id=event_id,
        source=source,
        vendor=payload.get("vendor", "unknown_vendor"),
        event_type=payload.get("type", "unknown_type"),
        timestamp=datetime.now(timezone.utc),
        severity=payload.get("severity", "INFO"),
        asset=payload.get("asset") or payload.get("target_ip"),
        identity=payload.get("identity") or payload.get("actor"),
        raw_payload=payload,
        metadata=payload.get("metadata", {})
    )

    # Phase 10: Validation and Enrichment via existing pipeline
    processed_events, failures = global_pipeline.process([sec_event])
    if failures:
        logger.warning(f"SOC Event rejected: {failures}")
        raise HTTPException(status_code=422, detail=failures)

    valid_event = processed_events[0]

    # Phase 4: Persist as CanonicalEvent using existing models
    canonical_event = CanonicalEvent(
        id=uuid.uuid4(),
        workspace_id=workspace.id,
        source_tool=valid_event.source,
        event_type=valid_event.event_type,
        severity_raw=valid_event.severity,
        severity_normalized=None,
        timestamp_utc=valid_event.timestamp,
        actor_identifier=valid_event.identity,
        asset_identifier=valid_event.asset,
        raw_event_json=valid_event.model_dump()
    )
    db.add(canonical_event)
    db.commit()
    db.refresh(canonical_event)

    # Phase 6 & 7: Dynamic Correlation & Incident Generation
    # We fetch recent canonical events to run correlation
    recent_events = db.query(CanonicalEvent).filter(
        CanonicalEvent.workspace_id == workspace.id,
        CanonicalEvent.timestamp_utc >= datetime.now(timezone.utc) - correlator.time_window
    ).all()
    
    event_dicts = [e.raw_event_json for e in recent_events]
    incidents = correlator.correlate(event_dicts)
    
    generated_incidents = []
    for inc in incidents:
        # Check if an incident with this description exists recently to avoid duplicates
        existing = db.query(Incident).filter(
            Incident.workspace_id == workspace.id,
            Incident.description == inc.description,
            Incident.created_at >= datetime.now(timezone.utc) - correlator.time_window
        ).first()
        
        if not existing:
            new_incident = Incident(
                workspace_id=workspace.id,
                title=f"Incident: {inc.description[:50]}...",
                description=inc.description,
                severity=inc.severity,
                affected_assets=list(inc.assets),
                contributing_sources=list(inc.sources),
                mitre_techniques=inc.mitre_techniques,
                start_time=inc.start_time,
                end_time=inc.end_time
            )
            # Link events
            linked_ids = [e.get("event_id") for e in inc.events if "event_id" in e]
            new_incident.events = db.query(CanonicalEvent).filter(
                func.jsonb_extract_path_text(CanonicalEvent.raw_event_json, 'event_id').in_(linked_ids)
            ).all()
            
            db.add(new_incident)
            db.commit()
            generated_incidents.append(new_incident.id)
            
            # Phase 8: Emit WebSocket Event for Incident
            from app.api.v1.websockets.updates import manager
            await manager.broadcast_to_workspace(str(workspace.id), {
                "type": "NEW_INCIDENT",
                "incident_id": str(new_incident.id),
                "severity": inc.severity,
                "description": inc.description
            })
            
            # Also publish to event bus for audit
            from app.core.events.bus import event_bus
            from app.core.events.contracts import AuditEvent
            from app.core.events.event_types import ActorClassification, EventCategory, EventSeverity, EventStatus, ResourceClassification
            
            event_bus.publish(AuditEvent(
                workspace_id=str(workspace.id),
                organization_id=str(workspace.organization_id),
                actor="SOC_ENGINE",
                actor_type=ActorClassification.INTERNAL_ENGINE,
                module="Correlation",
                action="INCIDENT_CREATED",
                category=EventCategory.SECURITY,
                severity=EventSeverity.HIGH,
                status=EventStatus.SUCCESS,
                resource_type=ResourceClassification.SYSTEM,
                metadata={"incident_id": str(new_incident.id), "description": inc.description}
            ))

    return {
        "status": "success",
        "canonical_event_id": str(canonical_event.id),
        "incidents_generated": len(generated_incidents)
    }

@router.get("/events")
def get_soc_events(
    source: Optional[str] = None,
    severity: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = Query(50, le=500),
    offset: int = 0,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Phase 5: Dashboard Data API for Events"""
    query = db.query(CanonicalEvent).filter(CanonicalEvent.workspace_id == workspace.id)
    
    if source:
        query = query.filter(CanonicalEvent.source_tool == source)
    if severity:
        query = query.filter(CanonicalEvent.severity_raw == severity)
    if search:
        query = query.filter(CanonicalEvent.raw_event_json.cast(String).ilike(f"%{search}%"))
        
    total = query.count()
    events = query.order_by(desc(CanonicalEvent.timestamp_utc)).offset(offset).limit(limit).all()
    
    return {
        "total": total,
        "events": events
    }

@router.get("/incidents")
def get_soc_incidents(
    status: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Phase 5: Dashboard Data API for Incidents"""
    query = db.query(Incident).filter(Incident.workspace_id == workspace.id)
    if status:
        query = query.filter(Incident.status == status)
        
    total = query.count()
    incidents = query.order_by(desc(Incident.created_at)).offset(offset).limit(limit).all()
    return {"total": total, "incidents": incidents}

@router.get("/stats")
def get_soc_stats(
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db)
):
    """Phase 5: Dynamic Summary Statistics"""
    total_events = db.query(func.count(CanonicalEvent.id)).filter(CanonicalEvent.workspace_id == workspace.id).scalar()
    total_incidents = db.query(func.count(Incident.id)).filter(Incident.workspace_id == workspace.id).scalar()
    
    sources = db.query(CanonicalEvent.source_tool, func.count(CanonicalEvent.id)).filter(
        CanonicalEvent.workspace_id == workspace.id
    ).group_by(CanonicalEvent.source_tool).all()
    
    return {
        "total_events": total_events,
        "total_incidents": total_incidents,
        "events_by_source": {s[0]: s[1] for s in sources}
    }
