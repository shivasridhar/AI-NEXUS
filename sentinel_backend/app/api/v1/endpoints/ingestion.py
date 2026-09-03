import logging
import time
from typing import Any, Dict, List

import json
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from sqlalchemy.sql import func

from app.core.redis_client import get_redis_client

from app.api.dependencies import get_current_workspace, get_db
from app.core.events.bus import event_bus
from app.core.events.contracts import AuditEvent
from app.core.events.event_types import (
    ActorClassification,
    EventCategory,
    EventSeverity,
    EventStatus,
    ResourceClassification,
)
from app.models.ingestion_job import IngestionJob
from app.models.tenant import Workspace
from app.schemas.security_event import SecurityEvent
from app.services.connectors.connector_factory import ConnectorFactory
from app.services.ingestion import IngestionService
from app.services.ingestion_pipeline.duplicate_detector import (
    InMemoryWindowedDeduplicationStrategy,
)
from app.services.ingestion_pipeline.event_pipeline import EventPipeline
from app.services.ingestion_pipeline.metadata_enrichment import MetadataEnricher
from app.services.ingestion_pipeline.validator import EventValidator
from app.services.ingestion_sources.base import IngestionSource
from app.services.ingestion_sources.file_upload import FileUploadSource
from app.services.security_event_publisher import (
    SecurityEventPublisherFactory,
)

# Create a global deduplication strategy instance to persist state across requests
global_detector = InMemoryWindowedDeduplicationStrategy()
global_validator = EventValidator()
global_enricher = MetadataEnricher()
global_pipeline = EventPipeline(global_validator, global_detector, global_enricher)
global_publisher = SecurityEventPublisherFactory.create("in_memory")

router = APIRouter()
logger = logging.getLogger(__name__)

async def execute_ingestion_pipeline(source: IngestionSource, job_id: str, workspace_id: str = None) -> dict:
    """Background task to fetch events from the source, normalize, validate and update the job status."""
    from app.db.session import SessionLocal
    from app.graph.session import neo4j_manager
    from app.services.cloudtrail_parser import CloudTrailParser
    from app.services.graph_sync_service import GraphSyncService
    from app.services.risk_engine import RiskEngine

    start_time = time.time()
    db = SessionLocal()

    try:
        # Get metadata
        meta = source.get_source_metadata()
        identifier = meta.get("identifier", "unknown")
        source_type = meta.get("sourceType", "unknown")

        print("\n------------------------------------------------")
        print(f"Ingestion Started [{source_type}]")
        print(f"identifier={identifier}")
        print("------------------------------------------------")

        # Fetch raw JSON via the source
        json_data = source.fetch_events()

        # Normalization Info Logging
        if isinstance(json_data, list):
            format_name = "Array of Events"
            records_count = len(json_data)
        elif isinstance(json_data, dict):
            if "eventID" in json_data or "eventTime" in json_data:
                format_name = "Single Event"
                records_count = 1
            else:
                # Find standard wrappers
                keys_lower = [k.lower() for k in json_data.keys()]
                if "records" in keys_lower:
                    format_name = "Standard CloudTrail Log File"
                elif "events" in keys_lower:
                    format_name = "Events List"
                else:
                    format_name = "Custom Log Format"

                # Extract records count safely
                normalized_temp = CloudTrailParser.normalize_json(json_data)
                records_count = len(normalized_temp.get("Records", []))
        else:
            format_name = "Unknown Format"
            records_count = 0

        print("Normalization")
        print(f"Detected Format:\n{format_name}")
        print(f"Normalized:\n{records_count} Records")
        print("------------------------------------------------")

        # Validation Info Logging
        # parse_log_file will validate and throw descriptive ValueError if invalid
        CloudTrailParser.parse_log_file(json_data)
        print("Validation")
        print("Passed")
        print("------------------------------------------------")

        # Update job to running
        job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
        if job:
            job.status = "running"
            db.commit()

        ingestion_service = IngestionService(db)
        stats = ingestion_service.process_cloudtrail_json(
            json_data, job_id=job_id, filename=identifier, workspace_id=workspace_id
        )

        print("Ingestion")
        print(f"Inserted:\n{stats['inserted']}")
        print(f"Duplicates:\n{stats['duplicates']}")
        print(f"Failed:\n{stats['failed']}")
        print("------------------------------------------------")

        print("Identity Discovery")
        print(f"Created:\n{stats.get('identities_created_count', 0)}")
        print(f"Updated:\n{stats.get('identities_updated_count', 0)}")
        print("------------------------------------------------")

        # Sync Neo4j graph and evaluate risk scores ONLY for newly inserted events
        neo4j_session = None
        neo4j_stats = {"nodes_created": 0, "relationships_created": 0}
        findings_count = 0

        try:
            if stats["new_logs"]:
                neo4j_session = neo4j_manager.get_session()

                # Sync graph incrementally
                print(f"[{time.time()}] GRAPH_SYNC_START")
                graph_sync = GraphSyncService(db, neo4j_session)
                neo4j_stats = graph_sync.sync_new_events(stats["new_logs"], workspace_id=workspace_id)
                print(f"[{time.time()}] GRAPH_SYNC_END")
                
                # Instead of calculating synchronously, publish to Redis for background worker
                if stats["new_identity_arns"]:
                    print(f"[{time.time()}] REDIS_PUBLISH_START")
                    redis = await get_redis_client()
                    await redis.xadd(
                        "risk_evaluation_events",
                        {
                            "job_id": job_id,
                            "workspace_id": workspace_id,
                            "new_identity_arns": json.dumps(list(stats["new_identity_arns"]))
                        }
                    )
                    print(f"[{time.time()}] REDIS_PUBLISH_END")
                findings_count = 0 # Will be populated asynchronously by the worker
        finally:
            if neo4j_session:
                neo4j_session.close()

        print("Risk Engine")
        print(f"Processed:\n{len(stats['new_identity_arns'])}")
        print(f"Findings:\n{findings_count}")
        print("------------------------------------------------")

        print("Neo4j")
        print(f"Nodes:\n{neo4j_stats['nodes_created']}")
        print(f"Relationships:\n{neo4j_stats['relationships_created']}")
        print("------------------------------------------------")

        # Job stays running until risk worker completes it
        job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
        if job:
            job.events_processed = stats.get('total_events', 0)
            db.commit()

        duration = time.time() - start_time
        print("Completed")
        print(f"Duration:\n{duration:.2f} sec")
        print("------------------------------------------------\n")

        # Merge stats
        stats["risk_findings_generated"] = findings_count
        stats["neo4j_nodes_created"] = neo4j_stats["nodes_created"]
        stats["neo4j_relationships_created"] = neo4j_stats["relationships_created"]
        stats["processing_time_ms"] = int(duration * 1000)
        stats["status"] = "running"
        return stats

    except ValueError as ve:
        logger.error("Validation or format mismatch error: %s", str(ve))
        db.rollback()
        job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = func.now()
            db.commit()
        # Raise standard HTTPException with custom message matching requirements
        raise HTTPException(status_code=400, detail=str(ve)) from ve

    except Exception as e:
        logger.error("Background processing failed for job %s: %s", job_id, str(e))
        db.rollback()
        job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
        if job:
            job.status = "failed"
            job.completed_at = func.now()
            db.commit()
        raise HTTPException(status_code=500, detail=str(e)) from e
    finally:
        db.close()


@router.post("/upload", response_model=Dict[str, Any])
async def upload_cloudtrail_logs(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    workspace: Workspace = Depends(get_current_workspace),
):
    """
    Upload a JSON file containing AWS CloudTrail logs.
    The file will be processed synchronously for real-time UI updates.
    """
    if not file.filename.endswith(".json"):
        raise HTTPException(status_code=400, detail="Only JSON files are supported.")

    try:
        content = await file.read()
        print(f"DEBUG: file read length: {len(content)}")
        print(f"DEBUG: file content preview: {content[:100]}")
        # Create Ingestion Job record
        job = IngestionJob(
            workspace_id=workspace.id,
            s3_bucket_name="manual-upload",  # Fallback since we aren't pulling from S3 directly
            status="pending",
        )
        db.add(job)
        db.commit()
        db.refresh(job)

        # Initialize the file upload source
        source = FileUploadSource(content, file.filename)

        # Process the file asynchronously to write to graph then publish to Redis
        stats = await execute_ingestion_pipeline(source, str(job.job_id), str(workspace.id))

        event_bus.publish(
            AuditEvent(
                workspace_id=str(workspace.id),
                organization_id=str(workspace.organization_id),
                actor="SYSTEM",
                actor_type=ActorClassification.INTERNAL_ENGINE,
                module="Ingestion",
                action="UPLOAD_COMPLETED",
                category=EventCategory.INGESTION,
                severity=EventSeverity.INFO,
                status=EventStatus.SUCCESS,
                resource_type=ResourceClassification.SYSTEM,
                metadata={"filename": file.filename, "stats": stats},
            )
        )
        return {
            "message": "File uploaded and processed successfully. Risk evaluation is processing.",
            "job_id": str(job.job_id),
            "filename": file.filename,
            "status": "processing",
            "risk_findings_status": "processing",
            "total_events": stats.get("total_events", 0),
            "inserted": stats.get("inserted", 0),
            "duplicates": stats.get("duplicates", 0),
            "failed": stats.get("failed", 0),
            "identities_discovered": stats.get("identities_discovered", 0),
            "risk_findings_generated": stats.get("risk_findings_generated", 0),
            "neo4j_nodes_created": stats.get("neo4j_nodes_created", 0),
            "neo4j_relationships_created": stats.get("neo4j_relationships_created", 0),
            "processing_time_ms": stats.get("processing_time_ms", 0),
        }
    except HTTPException as he:
        raise he
    except Exception as e:
        event_bus.publish(
            AuditEvent(
                workspace_id=str(workspace.id),
                organization_id=str(workspace.organization_id),
                actor="SYSTEM",
                actor_type=ActorClassification.INTERNAL_ENGINE,
                module="Ingestion",
                action="UPLOAD_FAILED",
                category=EventCategory.INGESTION,
                severity=EventSeverity.HIGH,
                status=EventStatus.FAILED,
                resource_type=ResourceClassification.SYSTEM,
                metadata={"filename": file.filename, "error": str(e)},
            )
        )
        raise HTTPException(status_code=500, detail=str(e)) from e


class TriggerIngestionRequest(BaseModel):
    connector_name: str = Field(
        ...,
        description="Registered connector identifier (e.g. wazuh, suricata, openvas)",
    )
    config: Dict[str, Any] = Field(
        default_factory=dict,
        description="Injected configuration settings for this connection run",
    )


class TriggerIngestionResponse(BaseModel):
    connector: str
    status: str
    events_received: int
    events_validated: int
    events_deduplicated: int
    events_published: int
    failures: List[Dict[str, str]] = Field(default_factory=list)
    processing_time_ms: float


@router.post("/trigger", response_model=TriggerIngestionResponse)
async def trigger_connector_ingestion(
    request: TriggerIngestionRequest,
):
    """
    Triggers dynamic connector authentication, ingestion, validation/deduplication processing pipeline,
    and publishes events to the default transport sink.
    """
    start_time = time.time()
    failures: List[Dict[str, str]] = []

    # 1. Initialize connector via Factory
    try:
        connector = ConnectorFactory.create(request.connector_name, request.config)
    except ValueError as ve:
        logger.error("[IngestionAPI] Connector initialization failed: %s", ve)
        raise HTTPException(
            status_code=400, detail=f"Invalid connector configurations: {str(ve)}"
        ) from ve
    except Exception as e:
        logger.error("[IngestionAPI] Initialization failed: %s", e)
        raise HTTPException(
            status_code=500, detail=f"Failed to load connector: {str(e)}"
        ) from e

    # 2. Connection and Authentication
    try:
        connector.connect()
        authenticated = connector.authenticate()
        if not authenticated:
            raise HTTPException(
                status_code=401,
                detail=f"Authentication rejected by {request.connector_name}",
            )
    except HTTPException as he:
        raise he
    except PermissionError as pe:
        logger.error("[IngestionAPI] Authentication rejected: %s", pe)
        raise HTTPException(status_code=401, detail=f"Credentials rejected: {str(pe)}") from pe
    except (ConnectionError, ConnectionRefusedError) as ce:
        logger.error("[IngestionAPI] Connection failed: %s", ce)
        raise HTTPException(status_code=502, detail=f"Connection failed: {str(ce)}") from ce
    except Exception as e:
        logger.error("[IngestionAPI] Connect/Auth failed: %s", e)
        raise HTTPException(status_code=500, detail=f"Auth framework failure: {str(e)}") from e

    # 3. Ingestion (Fetch Events)
    raw_events: List[SecurityEvent] = []
    try:
        raw_events = connector.fetch_events()
    except Exception as e:
        logger.error("[IngestionAPI] Fetch failed for %s: %s", request.connector_name, e)
        # Clean up connection
        try:
            connector.disconnect()
        except Exception:
            pass
        raise HTTPException(status_code=502, detail=f"Remote fetch failure: {str(e)}") from e

    # Clean up connection
    try:
        connector.disconnect()
    except Exception as e:
        logger.warning(
            "[IngestionAPI] Disconnect warning for %s: %s", request.connector_name, e
        )

    # 4. Processing Pipeline Execution (Validate -> Dedupe -> Enrich)
    # Track statistics
    events_received = len(raw_events)

    processed_events, pipeline_failures = global_pipeline.process(raw_events)

    for f in pipeline_failures:
        # Convert to the API response format
        failures.append({"event_id": f["event_id"], "reason": f["reason"]})

    val_fails = len([f for f in pipeline_failures if f["type"] == "validation"])
    dup_fails = len([f for f in pipeline_failures if f["type"] == "duplicate"])

    events_validated_count = len(processed_events) + val_fails
    events_deduplicated_count = dup_fails

    # 5. Publisher
    publish_summary = global_publisher.publish(processed_events)

    # Gather failed publications
    for fail in publish_summary.failures:
        failures.append(
            {"event_id": fail.event_id, "reason": f"Publish failed: {fail.reason}"}
        )

    duration_ms = (time.time() - start_time) * 1000.0

    return TriggerIngestionResponse(
        connector=request.connector_name,
        status="completed" if not failures else "completed_with_errors",
        events_received=events_received,
        events_validated=events_validated_count,
        events_deduplicated=events_deduplicated_count,
        events_published=publish_summary.published_count,
        failures=failures,
        processing_time_ms=round(duration_ms, 3),
    )


class MetricsResponse(BaseModel):
    totalEvents: int
    eventsPerMinute: float
    validationSuccessRate: float
    activeConnectors: int
    chartData: List[Dict[str, Any]]


@router.get("/metrics", response_model=MetricsResponse)
async def get_ingestion_metrics(
    workspace: Workspace = Depends(get_current_workspace), db: Session = Depends(get_db)
):
    """Returns ingestion statistics for the current environment."""
    from app.services.telemetry_service import TelemetryService

    return TelemetryService.get_ingestion_metrics(db, workspace.id)


@router.get("/events", response_model=List[Dict[str, Any]])
async def get_ingestion_events(
    limit: int = 50,
    offset: int = 0,
    workspace: Workspace = Depends(get_current_workspace),
    db: Session = Depends(get_db),
):
    """Returns the latest successfully published security events."""
    from app.services.telemetry_service import TelemetryService

    events = TelemetryService.get_recent_events(
        db, workspace.id, limit=limit, format_for_ingestion=True
    )
    return events[offset:] if offset else events


@router.get("/config", response_model=Dict[str, Any])
async def get_ingestion_config():
    """Returns active connector configurations and settings."""
    from app.services.telemetry_service import TelemetryService

    return TelemetryService.get_pipeline_config()

@router.get("/jobs/{job_id}/status")
def get_job_status(job_id: str, db: Session = Depends(get_db)):
    job = db.query(IngestionJob).filter(IngestionJob.job_id == job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
        
    return {
        "job_id": str(job.job_id),
        "status": job.status,
        "events_processed": job.events_processed,
        "risk_findings_generated": job.risk_findings_generated,
        "error_message": job.error_message
    }
