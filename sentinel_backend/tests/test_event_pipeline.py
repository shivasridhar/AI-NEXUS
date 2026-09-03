import pytest
import time
from datetime import datetime, timezone, timedelta
from app.schemas.security_event import SecurityEvent
from app.services.ingestion_pipeline.validator import EventValidator
from app.services.ingestion_pipeline.duplicate_detector import InMemoryWindowedDeduplicationStrategy
from app.services.ingestion_pipeline.metadata_enrichment import MetadataEnricher
from app.services.ingestion_pipeline.event_pipeline import EventPipeline

@pytest.fixture
def base_event() -> SecurityEvent:
    return SecurityEvent(
        event_id="test-event-uuid",
        source="wazuh_alerts",
        vendor="Wazuh",
        event_type="Authentication",
        timestamp=datetime.now(timezone.utc),
        severity="HIGH",
        asset="192.168.1.100",
        raw_payload={"auth_status": "failed", "user": "admin"}
    )

def test_pipeline_valid_flow(base_event):
    """Verify that a valid event passes validation, deduplication, and is enriched."""
    # Force import to register Wazuh connector
    import app.services.connectors.wazuh_connector

    validator = EventValidator()
    detector = InMemoryWindowedDeduplicationStrategy()
    enricher = MetadataEnricher(environment="staging", node_id="test-node-1")
    pipeline = EventPipeline(validator, detector, enricher)

    processed, _ = pipeline.process([base_event])
    assert len(processed) == 1
    
    event = processed[0]
    assert event.event_id == "test-event-uuid"
    assert "ingestion" in event.metadata
    
    ingestion_meta = event.metadata["ingestion"]
    assert ingestion_meta["connector"] == "wazuh_alerts"
    assert ingestion_meta["environment"] == "staging"
    assert ingestion_meta["node_id"] == "test-node-1"
    assert "ingested_at" in ingestion_meta
    assert "processing_duration_ms" in ingestion_meta

def test_pipeline_validation_rejections(base_event):
    """Verify that validation rejections drop the event from the pipeline."""
    # Force import to register Wazuh connector
    import app.services.connectors.wazuh_connector

    validator = EventValidator(max_age_days=1)
    detector = InMemoryWindowedDeduplicationStrategy()
    enricher = MetadataEnricher()
    pipeline = EventPipeline(validator, detector, enricher)

    # 1. Event too old
    base_event.timestamp = datetime.now(timezone.utc) - timedelta(days=2)
    processed, _ = pipeline.process([base_event])
    assert len(processed) == 0

    # 2. Event empty raw_payload
    base_event.timestamp = datetime.now(timezone.utc)
    base_event.raw_payload = {}
    processed, _ = pipeline.process([base_event])
    assert len(processed) == 0

    # 3. Invalid severity
    base_event.raw_payload = {"dummy": "data"}
    base_event.severity = "CRAP_SEVERITY"
    processed, _ = pipeline.process([base_event])
    assert len(processed) == 0

def test_pipeline_duplicate_filtering(base_event):
    """Verify that duplicate events are filtered out."""
    import app.services.connectors.wazuh_connector

    validator = EventValidator()
    detector = InMemoryWindowedDeduplicationStrategy(window_seconds=10)
    enricher = MetadataEnricher()
    pipeline = EventPipeline(validator, detector, enricher)

    # First event passes
    processed, _ = pipeline.process([base_event])
    assert len(processed) == 1

    # Identical event is skipped as duplicate
    processed_dup, _ = pipeline.process([base_event])
    assert len(processed_dup) == 0

def test_pipeline_hash_deduplication(base_event):
    """Verify that duplicate events are filtered via hash fallback if IDs differ but semantic fields match."""
    import app.services.connectors.wazuh_connector

    validator = EventValidator()
    detector = InMemoryWindowedDeduplicationStrategy(window_seconds=10)
    enricher = MetadataEnricher()
    pipeline = EventPipeline(validator, detector, enricher)

    # First event passes
    processed, _ = pipeline.process([base_event])
    assert len(processed) == 1

    # Second event has different ID, but identical semantic fields (vendor, source, type, timestamp, asset)
    dup_event = base_event.model_copy()
    dup_event.event_id = "completely-different-id"
    
    processed_dup, _ = pipeline.process([dup_event])
    assert len(processed_dup) == 0
