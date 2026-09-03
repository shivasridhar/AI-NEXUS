import pytest
import uuid
import os
import sys
from datetime import datetime

sys.path.append(os.getcwd())
from app.services.parsers.factory import ParserFactory
from app.services.cloudtrail_parser import CloudTrailParser
from app.models.canonical_event import CanonicalEvent
from app.core.config import settings
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

def test_wazuh_parser():
    workspace_id = uuid.uuid4()
    wazuh_data = {
        "timestamp": "2023-10-27T10:00:00Z",
        "rule": {
            "level": 12,
            "description": "High severity wazuh alert"
        },
        "agent": {
            "id": "001",
            "name": "web-server-01",
            "ip": "192.168.1.100"
        }
    }
    parser = ParserFactory.get_parser("wazuh")
    events = parser.parse([wazuh_data], workspace_id)
    
    assert len(events) == 1
    event = events[0]
    assert event.source_tool == "wazuh"
    assert event.event_type == "High severity wazuh alert"
    assert event.severity_normalized == 80
    assert event.severity_raw == "12"
    assert event.actor_identifier == "web-server-01"
    assert event.asset_identifier == "001"
    assert event.timestamp_utc == datetime.fromisoformat("2023-10-27T10:00:00+00:00")
    assert event.workspace_id == workspace_id

def test_suricata_parser():
    workspace_id = uuid.uuid4()
    suricata_data = {
        "timestamp": "2023-10-27T10:05:00.123456+0000",
        "event_type": "alert",
        "src_ip": "10.0.0.5",
        "dest_ip": "10.0.0.10",
        "alert": {
            "severity": 2,
            "signature": "ET EXPLOIT Possible CVE-2023-XXXX"
        }
    }
    parser = ParserFactory.get_parser("suricata")
    events = parser.parse([suricata_data], workspace_id)
    
    assert len(events) == 1
    event = events[0]
    assert event.source_tool == "suricata"
    assert event.event_type == "ET EXPLOIT Possible CVE-2023-XXXX"
    assert event.severity_normalized == 60
    assert event.severity_raw == "2"
    assert event.actor_identifier == "10.0.0.5"
    assert event.asset_identifier == "10.0.0.10"

def test_openvas_parser():
    workspace_id = uuid.uuid4()
    openvas_data = {
        "creation_time": "2023-10-27T10:10:00Z",
        "name": "Outdated Apache Version",
        "threat": "High",
        "host": {
            "asset_id": "asset-123",
            "ip": "192.168.1.50"
        }
    }
    parser = ParserFactory.get_parser("openvas")
    events = parser.parse([openvas_data], workspace_id)
    
    assert len(events) == 1
    event = events[0]
    assert event.source_tool == "openvas"
    assert event.event_type == "Outdated Apache Version"
    assert event.severity_normalized == 80
    assert event.severity_raw == "High"
    assert event.actor_identifier is None
    assert event.asset_identifier == "asset-123"

def test_cloudtrail_backward_compatibility():
    cloudtrail_data = {
        "Records": [
            {
                "eventVersion": "1.08",
                "userIdentity": {
                    "type": "IAMUser",
                    "principalId": "AIDAXXXXXXXXXXXXX",
                    "arn": "arn:aws:iam::123456789012:user/Alice",
                    "accountId": "123456789012",
                    "invokedBy": None
                },
                "eventTime": "2023-10-27T10:15:00Z",
                "eventSource": "s3.amazonaws.com",
                "eventName": "GetObject",
                "awsRegion": "us-east-1",
                "sourceIPAddress": "203.0.113.5",
                "userAgent": "aws-cli/2.0.0 Python/3.8.2",
                "requestParameters": {
                    "bucketName": "my-secure-bucket"
                },
                "responseElements": None,
                "eventID": "abcd-1234",
                "eventType": "AwsApiCall",
                "recipientAccountId": "123456789012"
            }
        ]
    }
    events = CloudTrailParser.parse_log_file(cloudtrail_data)
    assert len(events) == 1
    
    access_log_data = CloudTrailParser.extract_access_log_data(events[0])
    assert access_log_data["event_id"] == "abcd-1234"
    assert access_log_data["identity_arn"] == "arn:aws:iam::123456789012:user/Alice"

@pytest.mark.pg
def test_canonical_event_db_insertion(postgres_db):
    db = postgres_db
    
    # We must insert a workspace first to respect the foreign key constraint
    from app.models.tenant import Workspace
    workspace_id = uuid.uuid4()
    org_id = uuid.uuid4()
    
    # Insert org and workspace to satisfy FKs (assuming Organization exists, or we might need it)
    from app.models.tenant import Organization
    test_org = Organization(id=org_id, name="Test Org Insert", slug=str(org_id))
    test_workspace = Workspace(id=workspace_id, organization_id=org_id, name="Test Workspace Insert")
    db.add(test_org)
    db.add(test_workspace)
    db.commit()
    
    wazuh_data = {
        "timestamp": "2023-10-27T10:00:00Z",
        "rule": {
            "level": 12,
            "description": "DB Insert Test"
        },
        "agent": {
            "id": "001",
            "name": "web-server-01",
            "ip": "192.168.1.100"
        }
    }
    
    parser = ParserFactory.get_parser("wazuh")
    events = parser.parse([wazuh_data], workspace_id)
    event_schema = events[0]
    
    # Insert CanonicalEvent to DB
    db_event = CanonicalEvent(**event_schema.model_dump())
    db.add(db_event)
    db.commit()
    db.refresh(db_event)
    
    # Read back
    retrieved = db.query(CanonicalEvent).filter(CanonicalEvent.id == db_event.id).first()
    assert retrieved is not None
    assert retrieved.event_type == "DB Insert Test"
    assert retrieved.workspace_id == workspace_id
    assert retrieved.severity_normalized == 80

