import os
import json
import pytest
from uuid import uuid4
from sqlalchemy.orm import Session
from datetime import datetime, timezone

from app.services.cloudtrail_parser import CloudTrailParser
from app.services.ingestion import IngestionService
from app.models.tenant import Workspace, Organization
from app.services.ingestion_pipeline.event_pipeline import EventPipeline
from app.services.ingestion_pipeline.validator import EventValidator
from app.services.ingestion_pipeline.duplicate_detector import InMemoryWindowedDeduplicationStrategy
from app.services.ingestion_pipeline.metadata_enrichment import MetadataEnricher
from app.schemas.security_event import SecurityEvent
from app.core.events.event_types import EventSeverity
from app.services.connectors.connector_registry import ConnectorRegistry
from app.services.connectors.base_connector import BaseConnector

FIXTURE_PATH = os.path.join(os.path.dirname(__file__), "fixtures", "cloudtrail_golden.json")

def load_golden_fixture():
    with open(FIXTURE_PATH, "r") as f:
        return json.load(f)
        
def load_expected_fixture(filename):
    path = os.path.join(os.path.dirname(__file__), "fixtures", filename)
    with open(path, "r") as f:
        return json.load(f)

def test_cloudtrail_parsing_regression():
    """
    Ensure CloudTrailParser continues to parse standard AWS CloudTrail JSON correctly.
    """
    json_data = load_golden_fixture()
    
    # Compare parsed events full dict against expected golden dict
    expected_parsed = load_expected_fixture("cloudtrail_golden_parsed_expected.json")
    events = CloudTrailParser.parse_log_file(json_data)
    
    parsed_dicts = [e.model_dump(mode='json') for e in events]
    assert parsed_dicts == expected_parsed


def test_cloudtrail_identity_extraction_regression():
    """
    Ensure CloudTrailParser extracts proper AccessLog ARNs to not break Risk Engine.
    """
    json_data = load_golden_fixture()
    events = CloudTrailParser.parse_log_file(json_data)
    
    # Compare access logs against expected golden access logs
    expected_access_logs = load_expected_fixture("cloudtrail_golden_access_logs_expected.json")
    
    def serialize_access_log(log):
        # Convert datetime to ISO string for proper JSON comparison
        if "event_time" in log and isinstance(log["event_time"], datetime):
            log["event_time"] = log["event_time"].isoformat()
        return log
        
    actual_access_logs = [serialize_access_log(CloudTrailParser.extract_access_log_data(e)) for e in events]
    assert actual_access_logs == expected_access_logs


def test_cloudtrail_compatibility_with_connector_pipeline():
    """
    Verify that if a CloudTrail event is passed to the shared Connector EventPipeline,
    the pipeline's validator and deduplicator do not crash on the payload.
    """
    json_data = load_golden_fixture()
    cloudtrail_events = CloudTrailParser.parse_log_file(json_data)
    
    # Convert CloudTrailEvent to Connector SecurityEvent to test pipeline compatibility
    # This simulates what a CloudTrail Connector would do.
    # Temporarily register AWS vendor to bypass validator check
    class MockAWSConnector(BaseConnector):
        def initialize(self): pass
        def ingest(self, workspace_id, start_time, end_time, publisher): pass
        def close(self): pass
        
    ConnectorRegistry._registry["AWS"] = MockAWSConnector
    
    security_events = []
    for ct in cloudtrail_events:
        se = SecurityEvent(
            event_id=ct.eventID,
            timestamp=datetime.now(timezone.utc),  # use current time to pass max_age check
            vendor="AWS",
            source="CloudTrail",
            event_type=ct.eventName,
            severity=EventSeverity.INFO,
            raw_payload=ct.model_dump(mode='json')
        )
        security_events.append(se)

    pipeline = EventPipeline(
        validator=EventValidator(),
        duplicate_detector=InMemoryWindowedDeduplicationStrategy(),
        enricher=MetadataEnricher()
    )

    processed, failures = pipeline.process(security_events)
    
    # Both events should pass validation and enrichment
    assert len(processed) == 2
    assert len(failures) == 0


@pytest.mark.pg
@pytest.mark.asyncio
async def test_existing_ingestion_service_regression(postgres_db: Session):
    """
    Verify the existing `IngestionService.process_cloudtrail_json` works end-to-end
    with the golden fixture inside a real database.
    """
    # Setup Tenant
    org = Organization(name="Test Org", slug="test-org")
    postgres_db.add(org)
    postgres_db.commit()

    ws = Workspace(name="Test WS", organization_id=org.id)
    postgres_db.add(ws)
    postgres_db.commit()
    
    # Process CloudTrail
    json_data = load_golden_fixture()
    service = IngestionService(postgres_db)
    
    stats = service.process_cloudtrail_json(
        json_data=json_data,
        job_id=str(uuid4()),
        filename="regression_test.json",
        workspace_id=str(ws.id)
    )
    
    # Assert stats
    assert stats["total_events"] == 2
    assert stats["inserted"] == 2
    assert stats["duplicates"] == 0
    assert stats["failed"] == 0
    assert stats["identities_created_count"] == 2  # Alice, TestRole/test-session

    # Deduplication check
    stats_dup = service.process_cloudtrail_json(
        json_data=json_data,
        job_id=str(uuid4()),
        filename="regression_test_dup.json",
        workspace_id=str(ws.id)
    )
    
    assert stats_dup["inserted"] == 0
    assert stats_dup["duplicates"] == 2
