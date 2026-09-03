import os
import sys
import uuid
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

sys.path.append(os.getcwd())
from app.core.config import settings
from app.models.access_log import AccessLog
from app.services.ingestion import IngestionService
from app.services.cloudtrail_parser import CloudTrailParser

def run_tests():
    print("==================================================")
    print(" Running Ingestion Refinement Comprehensive Tests")
    print("==================================================")
    
    engine = create_engine(settings.SQLALCHEMY_DATABASE_URI)
    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()
    
    # Setup service
    ingestion_service = IngestionService(db)
    
    # Create test org and workspace
    from app.models.tenant import Organization, Workspace
    org_id = uuid.uuid4()
    workspace_id = uuid.uuid4()
    org = Organization(id=org_id, name="Test Org Idemp", slug=str(org_id))
    workspace = Workspace(id=workspace_id, organization_id=org_id, name="Test Workspace Idemp")
    db.add(org)
    db.add(workspace)
    db.commit()
    
    # 1. Standard CloudTrail Records format
    print("\nTest 1: Standard CloudTrail Records format...")
    rec_id_1 = f"rec-evt-{uuid.uuid4()}"
    rec_payload = {
        "Records": [
            {
                "eventVersion": "1.08",
                "userIdentity": {
                    "type": "IAMUser",
                    "principalId": "AIDA1",
                    "arn": "arn:aws:iam::123456789012:user/std-user-1",
                    "accountId": "123456789012"
                },
                "eventTime": "2026-07-01T11:00:00Z",
                "eventSource": "s3.amazonaws.com",
                "eventName": "GetObject",
                "awsRegion": "us-east-1",
                "sourceIPAddress": "192.168.1.1",
                "eventID": rec_id_1,
                "recipientAccountId": "123456789012"
            }
        ]
    }
    stats1 = ingestion_service.process_cloudtrail_json(rec_payload, job_id="job-1", filename="rec.json", workspace_id=workspace_id)
    print(f"Stats: {stats1}")
    assert stats1["inserted"] == 1
    assert stats1["duplicates"] == 0
    print("[PASS]")

    # 2. Single Event History JSON
    print("\nTest 2: Single Event History JSON format...")
    single_id = f"single-evt-{uuid.uuid4()}"
    single_payload = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "AIDA2",
            "arn": "arn:aws:iam::123456789012:user/std-user-2",
            "accountId": "123456789012"
        },
        "eventTime": "2026-07-01T11:05:00Z",
        "eventSource": "iam.amazonaws.com",
        "eventName": "CreateUser",
        "awsRegion": "us-east-1",
        "sourceIPAddress": "192.168.1.2",
        "eventID": single_id,
        "recipientAccountId": "123456789012"
    }
    stats2 = ingestion_service.process_cloudtrail_json(single_payload, job_id="job-2", filename="single.json", workspace_id=workspace_id)
    print(f"Stats: {stats2}")
    assert stats2["inserted"] == 1
    assert stats2["duplicates"] == 0
    print("[PASS]")

    # 3. Array of events
    print("\nTest 3: Array of events format...")
    arr_id_1 = f"arr-evt-{uuid.uuid4()}"
    arr_id_2 = f"arr-evt-{uuid.uuid4()}"
    arr_payload = [
        {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "AIDA3",
                "arn": "arn:aws:iam::123456789012:user/std-user-3",
                "accountId": "123456789012"
            },
            "eventTime": "2026-07-01T11:10:00Z",
            "eventSource": "ec2.amazonaws.com",
            "eventName": "RunInstances",
            "awsRegion": "us-east-1",
            "sourceIPAddress": "192.168.1.3",
            "eventID": arr_id_1,
            "recipientAccountId": "123456789012"
        },
        {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "AIDA3",
                "arn": "arn:aws:iam::123456789012:user/std-user-3",
                "accountId": "123456789012"
            },
            "eventTime": "2026-07-01T11:12:00Z",
            "eventSource": "ec2.amazonaws.com",
            "eventName": "DescribeInstances",
            "awsRegion": "us-east-1",
            "sourceIPAddress": "192.168.1.3",
            "eventID": arr_id_2,
            "recipientAccountId": "123456789012"
        }
    ]
    stats3 = ingestion_service.process_cloudtrail_json(arr_payload, job_id="job-3", filename="arr.json", workspace_id=workspace_id)
    print(f"Stats: {stats3}")
    assert stats3["inserted"] == 2
    assert stats3["duplicates"] == 0
    print("[PASS]")

    # 4. Duplicate uploads
    print("\nTest 4: Duplicate uploads...")
    stats4 = ingestion_service.process_cloudtrail_json(arr_payload, job_id="job-4", filename="arr.json", workspace_id=workspace_id)
    print(f"Stats: {stats4}")
    assert stats4["inserted"] == 0
    assert stats4["duplicates"] == 2
    print("[PASS]")

    # 5. Mixed new + duplicate uploads
    print("\nTest 5: Mixed new + duplicate uploads...")
    mixed_id = f"mixed-evt-{uuid.uuid4()}"
    mixed_payload = [
        arr_payload[0], # Duplicate
        {
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "AIDA4",
                "arn": "arn:aws:iam::123456789012:user/std-user-4",
                "accountId": "123456789012"
            },
            "eventTime": "2026-07-01T11:15:00Z",
            "eventSource": "s3.amazonaws.com",
            "eventName": "PutObject",
            "awsRegion": "us-east-1",
            "sourceIPAddress": "192.168.1.4",
            "eventID": mixed_id,
            "recipientAccountId": "123456789012"
        }
    ]
    stats5 = ingestion_service.process_cloudtrail_json(mixed_payload, job_id="job-5", filename="mixed.json", workspace_id=workspace_id)
    print(f"Stats: {stats5}")
    assert stats5["inserted"] == 1
    assert stats5["duplicates"] == 1
    print("[PASS]")

    # 6. Invalid JSON structure
    print("\nTest 6: Validation check on invalid root key...")
    try:
        CloudTrailParser.parse_log_file({"Invalid": []})
        assert False, "Expected ValueError on missing Records list"
    except ValueError as ve:
        print(f"Received expected error: {ve}")
        assert "Unsupported CloudTrail format" in str(ve)
    print("[PASS]")

    # 6a. Empty Records array
    print("\nTest 6a: Validation check on empty Records array...")
    empty_result = CloudTrailParser.parse_log_file({"Records": []})
    assert empty_result == [], f"Expected empty list, got {empty_result}"
    print("[PASS]")

    # 7. Missing eventID
    print("\nTest 7: Missing eventID check...")
    missing_id_payload = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "AIDA2",
            "arn": "arn:aws:iam::123456789012:user/std-user-2",
            "accountId": "123456789012"
        },
        "eventTime": "2026-07-01T11:05:00Z",
        "eventSource": "iam.amazonaws.com",
        "eventName": "CreateUser",
        "awsRegion": "us-east-1",
        "sourceIPAddress": "192.168.1.2",
        "recipientAccountId": "123456789012"
    }
    try:
        CloudTrailParser.parse_log_file(missing_id_payload)
        assert False, "Expected ValueError on missing eventID"
    except ValueError as ve:
        print(f"Received expected error: {ve}")
        assert "All records failed validation" in str(ve)
    print("[PASS]")

    # 8. Missing eventTime
    print("\nTest 8: Missing eventTime check...")
    missing_time_payload = {
        "eventVersion": "1.08",
        "userIdentity": {
            "type": "IAMUser",
            "principalId": "AIDA2",
            "arn": "arn:aws:iam::123456789012:user/std-user-2",
            "accountId": "123456789012"
        },
        "eventSource": "iam.amazonaws.com",
        "eventName": "CreateUser",
        "awsRegion": "us-east-1",
        "sourceIPAddress": "192.168.1.2",
        "eventID": "some-id",
        "recipientAccountId": "123456789012"
    }
    try:
        CloudTrailParser.parse_log_file(missing_time_payload)
        assert False, "Expected ValueError on missing eventTime"
    except ValueError as ve:
        print(f"Received expected error: {ve}")
        assert "All records failed validation" in str(ve)
    print("[PASS]")

    # 9. Large upload (1000+ events)
    print("\nTest 9: Large upload (1000+ events)...")
    large_records = []
    large_ids = []
    for idx in range(1050):
        evt_id = f"large-evt-{idx}-{uuid.uuid4()}"
        large_ids.append(evt_id)
        large_records.append({
            "eventVersion": "1.08",
            "userIdentity": {
                "type": "IAMUser",
                "principalId": "AIDA_LARGE",
                "arn": "arn:aws:iam::123456789012:user/large-user",
                "accountId": "123456789012"
            },
            "eventTime": "2026-07-01T12:00:00Z",
            "eventSource": "s3.amazonaws.com",
            "eventName": "GetObject",
            "awsRegion": "us-east-1",
            "sourceIPAddress": "192.168.1.10",
            "eventID": evt_id,
            "recipientAccountId": "123456789012"
        })
    large_payload = {"Records": large_records}
    stats9 = ingestion_service.process_cloudtrail_json(large_payload, job_id="job-large", filename="large.json", workspace_id=workspace_id)
    print(f"Inserted: {stats9['inserted']}, Duplicates: {stats9['duplicates']}")
    assert stats9["inserted"] == 1050
    assert stats9["total_events"] == 1050
    print("[PASS]")

    # Clean up test database records
    print("\nCleaning up test database records...")
    db.query(AccessLog).filter(AccessLog.event_id.in_([rec_id_1, single_id, arr_id_1, arr_id_2, mixed_id] + large_ids)).delete()
    db.delete(workspace)
    db.delete(org)
    db.commit()
    db.close()
    
    print("\n==================================================")
    print(" ALL TESTS PASSED SUCCESSFULLY! PASSED")
    print("==================================================")

if __name__ == "__main__":
    run_tests()
