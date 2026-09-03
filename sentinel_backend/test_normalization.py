import sys
import uuid
import json
from datetime import datetime

# Adjust the path so we can import from the app directory
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.parsers.factory import ParserFactory
from app.services.cloudtrail_parser import CloudTrailParser

def run_tests():
    workspace_id = uuid.uuid4()
    print(f"Testing with workspace_id: {workspace_id}\n")

    # 1. Test Wazuh
    print("--- Testing Wazuh Parser ---")
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
    wazuh_parser = ParserFactory.get_parser("wazuh")
    wazuh_events = wazuh_parser.parse([wazuh_data], workspace_id)
    for event in wazuh_events:
        print(f"Wazuh Event: {event.event_type}")
        print(f"Severity Normalized: {event.severity_normalized} (from raw: {event.severity_raw})")
        print(f"Actor: {event.actor_identifier}, Asset: {event.asset_identifier}")
        print(f"Time: {event.timestamp_utc}")
    print("\n")

    # 2. Test Suricata
    print("--- Testing Suricata Parser ---")
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
    suricata_parser = ParserFactory.get_parser("suricata")
    suricata_events = suricata_parser.parse([suricata_data], workspace_id)
    for event in suricata_events:
        print(f"Suricata Event: {event.event_type}")
        print(f"Severity Normalized: {event.severity_normalized} (from raw: {event.severity_raw})")
        print(f"Actor: {event.actor_identifier}, Asset: {event.asset_identifier}")
        print(f"Time: {event.timestamp_utc}")
    print("\n")

    # 3. Test OpenVAS
    print("--- Testing OpenVAS Parser ---")
    openvas_data = {
        "creation_time": "2023-10-27T10:10:00Z",
        "name": "Outdated Apache Version",
        "threat": "High",
        "host": {
            "asset_id": "asset-123",
            "ip": "192.168.1.50"
        }
    }
    openvas_parser = ParserFactory.get_parser("openvas")
    openvas_events = openvas_parser.parse([openvas_data], workspace_id)
    for event in openvas_events:
        print(f"OpenVAS Event: {event.event_type}")
        print(f"Severity Normalized: {event.severity_normalized} (from raw: {event.severity_raw})")
        print(f"Actor: {event.actor_identifier}, Asset: {event.asset_identifier}")
        print(f"Time: {event.timestamp_utc}")
    print("\n")

    # 4. Test CloudTrail (ensure old logic still works with the new time_utils)
    print("--- Testing CloudTrail Parser (Old Logic with extracted time_utils) ---")
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
    try:
        events = CloudTrailParser.parse_log_file(cloudtrail_data)
        for e in events:
            access_log_data = CloudTrailParser.extract_access_log_data(e)
            print("CloudTrail Event parsed successfully.")
            print(f"Event ID: {access_log_data['event_id']}")
            print(f"Time: {access_log_data['event_time']}")
            print(f"Identity ARN: {access_log_data['identity_arn']}")
    except Exception as e:
        print(f"CloudTrail parsing failed: {e}")

if __name__ == "__main__":
    run_tests()
