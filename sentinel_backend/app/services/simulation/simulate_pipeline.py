import json
import time
import os
from datetime import datetime, timezone

from app.schemas.security_event import SecurityEvent
from app.services.ingestion_pipeline.validator import EventValidator
from app.services.ingestion_pipeline.duplicate_detector import InMemoryWindowedDeduplicationStrategy
from app.services.ingestion_pipeline.metadata_enrichment import MetadataEnricher
from app.services.ingestion_pipeline.event_pipeline import EventPipeline

# Mock payloads representing realistic inputs for all 5 connectors

WAZUH_HYDRA_ALERT = {
    "timestamp": "2026-07-14T22:00:00.000+0000",
    "rule": {
        "level": 10,
        "description": "sshd: repeated authentication failures from Hydra brute-force tool",
        "id": "5712",
        "groups": ["syslog", "sshd", "authentication_failed"]
    },
    "agent": {"id": "001", "name": "web-server-node"},
    "data": {
        "srcip": "192.168.1.15",
        "dstip": "10.0.0.5",
        "dstuser": "admin"
    },
    "id": "wazuh-alert-uuid-1234"
}

SURICATA_NMAP_ALERT = {
    "timestamp": "2026-07-14T22:01:00.123456+0000",
    "flow_id": 192837465,
    "event_type": "alert",
    "src_ip": "192.168.1.15",
    "src_port": 54321,
    "dest_ip": "10.0.0.5",
    "dest_port": 80,
    "proto": "TCP",
    "alert": {
        "action": "allowed",
        "gid": 1,
        "signature_id": 2001213,
        "rev": 1,
        "signature": "ET SCAN Nmap portscan detected",
        "category": "Attempted Information Leak",
        "severity": 2
    }
}

OPENVAS_GVM_REPORT = """<result id="openvas-result-uuid-5678">
    <name>Nmap (NASL wrapper)</name>
    <description>The remote host has port 80 open.</description>
    <threat>Medium</threat>
    <severity>5.0</severity>
    <host>10.0.0.5</host>
    <port>80/tcp</port>
    <nvt oid="1.3.6.1.4.1.25623.1.0.10330">
        <name>Nmap (NASL wrapper)</name>
        <cvss_base>5.0</cvss_base>
        <cve>NOCVE</cve>
    </nvt>
</result>"""

SECURITY_HUB_FINDING = {
    "SchemaVersion": "2018-10-08",
    "Id": "arn:aws:securityhub:us-east-1:123456789012:subscription/prowler/finding/hub-uuid-9999",
    "ProductArn": "arn:aws:securityhub:us-east-1::product/aws/securityhub",
    "GeneratorId": "prowler",
    "AwsAccountId": "123456789012",
    "Types": ["Software and Configuration Checks/Vulnerabilities/CVE"],
    "CreatedAt": "2026-07-14T22:02:00.000Z",
    "UpdatedAt": "2026-07-14T22:02:00.000Z",
    "Severity": {"Label": "HIGH", "Normalized": 70},
    "Title": "AWS Foundation CIS 1.1: Avoid Root User Usage",
    "Description": "IAM root user has been used to authenticate or configure resources.",
    "Resources": [{"Type": "AwsIamUser", "Id": "arn:aws:iam::123456789012:root"}],
    "RecordState": "ACTIVE"
}

AWS_IAM_CREDENTIAL_REPORT_LINE = {
    "arn": "arn:aws:iam::123456789012:user/admin-session",
    "user": "admin-session",
    "password_enabled": "true",
    "password_last_used": "2026-07-14T22:03:00.000Z",
    "mfa_active": "false",
    "access_key_1_active": "true",
    "access_key_1_last_used_date": "2026-07-14T22:03:00.000Z"
}


def run_pipeline_on_event(name: str, event: SecurityEvent):
    """Feeds simulated SecurityEvent through the pipeline and prints results."""
    print(f"\n==================================================")
    print(f" SIMULATING: {name}")
    print(f"==================================================")
    
    # Instantiate the processing pipeline
    validator = EventValidator()
    detector = InMemoryWindowedDeduplicationStrategy()
    enricher = MetadataEnricher(environment="simulation", node_id="sim-node")
    pipeline = EventPipeline(validator, detector, enricher)
    
    print("\n--- [1] Raw SecurityEvent fields ---")
    print(f"Event ID:  {event.event_id}")
    print(f"Vendor:    {event.vendor}")
    print(f"Source:    {event.source}")
    print(f"Type:      {event.event_type}")
    print(f"Timestamp: {event.timestamp.isoformat()}")
    print(f"Severity:  {event.severity}")
    print(f"Asset:     {event.asset}")
    print(f"Metadata:  {json.dumps(event.metadata, indent=2)}")
    
    # Process event
    print("\n--- [2] Processing pipeline invocation ---")
    processed = pipeline.process([event])
    
    if processed:
        enriched_event = processed[0]
        print("Result: [PASS] Event successfully processed and enriched.")
        print(f"Enrichment Metadata Namespace: {json.dumps(enriched_event.metadata.get('ingestion'), indent=2)}")
    else:
        print("Result: [FAIL] Event rejected or deduplicated by pipeline.")


def simulate_all():
    # Force loading of connectors for dynamic registration
    import app.services.connectors.wazuh_connector
    import app.services.connectors.suricata_connector
    import app.services.connectors.openvas_connector
    import app.services.connectors.aws_securityhub_connector
    import app.services.connectors.aws_iam_connector
    
    # 1. Wazuh Simulation Mapping
    # Using Wazuh parser/normalizer mapping rules
    wazuh_event = SecurityEvent(
        event_id=WAZUH_HYDRA_ALERT["id"],
        source="wazuh_alerts",
        vendor="wazuh",
        event_type="Authentication",
        timestamp=datetime.now(timezone.utc),
        severity="HIGH", # Derived from level 10
        asset=WAZUH_HYDRA_ALERT["data"]["srcip"],
        raw_payload=WAZUH_HYDRA_ALERT,
        metadata={"rule_id": WAZUH_HYDRA_ALERT["rule"]["id"]}
    )
    run_pipeline_on_event("Hydra brute-force -> Wazuh -> SecurityEvent", wazuh_event)

    # 2. Suricata Simulation Mapping
    suricata_event = SecurityEvent(
        event_id="suricata-event-uuid-4444",
        source="suricata_alerts",
        vendor="suricata",
        event_type="alert",
        timestamp=datetime.now(timezone.utc),
        severity="MEDIUM", # Derived from severity 2
        asset=SURICATA_NMAP_ALERT["src_ip"],
        raw_payload=SURICATA_NMAP_ALERT,
        metadata={"signature_id": SURICATA_NMAP_ALERT["alert"]["signature_id"]}
    )
    run_pipeline_on_event("Nmap scan -> Suricata -> SecurityEvent", suricata_event)

    # 3. OpenVAS Simulation Mapping
    openvas_event = SecurityEvent(
        event_id="openvas-result-uuid-5678",
        source="openvas_findings",
        vendor="openvas",
        event_type="vulnerability_finding",
        timestamp=datetime.now(timezone.utc),
        severity="MEDIUM", # Derived from GVM Medium
        asset="10.0.0.5",
        raw_payload={"xml_fragment": OPENVAS_GVM_REPORT},
        metadata={"cvss_base": 5.0, "nvt_name": "Nmap (NASL wrapper)"}
    )
    run_pipeline_on_event("OpenVAS scan -> SecurityEvent", openvas_event)

    # 4. AWS Security Hub Simulation Mapping
    sechub_event = SecurityEvent(
        event_id=SECURITY_HUB_FINDING["Id"],
        source="aws_securityhub_findings",
        vendor="aws_securityhub",
        event_type="finding",
        timestamp=datetime.now(timezone.utc),
        severity="HIGH",
        asset=SECURITY_HUB_FINDING["Resources"][0]["Id"],
        raw_payload=SECURITY_HUB_FINDING,
        metadata={"GeneratorId": SECURITY_HUB_FINDING["GeneratorId"]}
    )
    run_pipeline_on_event("AWS Security Hub finding -> SecurityEvent", sechub_event)

    # 5. AWS IAM Simulation Mapping
    iam_event = SecurityEvent(
        event_id="iam-report-line-uuid-7777",
        source="aws_iam_discovery",
        vendor="aws_iam",
        event_type="identity_discovery",
        timestamp=datetime.now(timezone.utc),
        severity="MEDIUM", # MFA disabled is Medium severity
        asset=AWS_IAM_CREDENTIAL_REPORT_LINE["arn"],
        raw_payload=AWS_IAM_CREDENTIAL_REPORT_LINE,
        metadata={"mfa_active": False}
    )
    run_pipeline_on_event("AWS IAM discovery -> SecurityEvent", iam_event)


if __name__ == "__main__":
    simulate_all()
