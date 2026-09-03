"""
MITRE ATT&CK Mapping Service (Stage 3/4)

Maps CloudTrail API actions and security events to MITRE ATT&CK techniques.
This provides the deterministic MITRE mapping required by the SentinelAI architecture
before AI analysis begins.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# MITRE ATT&CK Technique Registry
# Maps CloudTrail event names / patterns to MITRE technique IDs and names.
# Reference: https://attack.mitre.org/techniques/enterprise/
# ---------------------------------------------------------------------------

MITRE_TECHNIQUE_MAP: Dict[str, Dict[str, str]] = {
    # Initial Access (TA0001)
    "ConsoleLogin": {
        "technique_id": "T1078",
        "technique_name": "Valid Accounts",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
    },
    "GetFederationToken": {
        "technique_id": "T1078.004",
        "technique_name": "Valid Accounts: Cloud Accounts",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
    },

    # Execution (TA0002)
    "Invoke": {
        "technique_id": "T1059",
        "technique_name": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "tactic_id": "TA0002",
    },
    "InvokeFunction": {
        "technique_id": "T1648",
        "technique_name": "Serverless Execution",
        "tactic": "Execution",
        "tactic_id": "TA0002",
    },
    "StartInstances": {
        "technique_id": "T1204",
        "technique_name": "User Execution",
        "tactic": "Execution",
        "tactic_id": "TA0002",
    },
    "RunInstances": {
        "technique_id": "T1204",
        "technique_name": "User Execution",
        "tactic": "Execution",
        "tactic_id": "TA0002",
    },

    # Persistence (TA0003)
    "CreateUser": {
        "technique_id": "T1136.003",
        "technique_name": "Create Account: Cloud Account",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "CreateAccessKey": {
        "technique_id": "T1098.001",
        "technique_name": "Account Manipulation: Additional Cloud Credentials",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "CreateLoginProfile": {
        "technique_id": "T1098",
        "technique_name": "Account Manipulation",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "AttachUserPolicy": {
        "technique_id": "T1098",
        "technique_name": "Account Manipulation",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "AttachRolePolicy": {
        "technique_id": "T1098",
        "technique_name": "Account Manipulation",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "PutUserPolicy": {
        "technique_id": "T1098",
        "technique_name": "Account Manipulation",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "PutRolePolicy": {
        "technique_id": "T1098",
        "technique_name": "Account Manipulation",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },
    "CreateRole": {
        "technique_id": "T1136.003",
        "technique_name": "Create Account: Cloud Account",
        "tactic": "Persistence",
        "tactic_id": "TA0003",
    },

    # Privilege Escalation (TA0004)
    "AssumeRole": {
        "technique_id": "T1548",
        "technique_name": "Abuse Elevation Control Mechanism",
        "tactic": "Privilege Escalation",
        "tactic_id": "TA0004",
    },
    "AssumeRoleWithSAML": {
        "technique_id": "T1548",
        "technique_name": "Abuse Elevation Control Mechanism",
        "tactic": "Privilege Escalation",
        "tactic_id": "TA0004",
    },
    "AssumeRoleWithWebIdentity": {
        "technique_id": "T1548",
        "technique_name": "Abuse Elevation Control Mechanism",
        "tactic": "Privilege Escalation",
        "tactic_id": "TA0004",
    },

    # Defense Evasion (TA0005)
    "StopLogging": {
        "technique_id": "T1562.008",
        "technique_name": "Impair Defenses: Disable Cloud Logs",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },
    "DeleteTrail": {
        "technique_id": "T1562.008",
        "technique_name": "Impair Defenses: Disable Cloud Logs",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },
    "UpdateTrail": {
        "technique_id": "T1562.008",
        "technique_name": "Impair Defenses: Disable Cloud Logs",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },
    "PutEventSelectors": {
        "technique_id": "T1562.008",
        "technique_name": "Impair Defenses: Disable Cloud Logs",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },
    "DeleteFlowLogs": {
        "technique_id": "T1562.008",
        "technique_name": "Impair Defenses: Disable Cloud Logs",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },
    "DisableAlarmActions": {
        "technique_id": "T1562",
        "technique_name": "Impair Defenses",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },

    # Credential Access (TA0006)
    "GetSecretValue": {
        "technique_id": "T1555",
        "technique_name": "Credentials from Password Stores",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
    },
    "GetParametersByPath": {
        "technique_id": "T1555",
        "technique_name": "Credentials from Password Stores",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
    },
    "Decrypt": {
        "technique_id": "T1552",
        "technique_name": "Unsecured Credentials",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
    },

    # Discovery (TA0007)
    "DescribeInstances": {
        "technique_id": "T1580",
        "technique_name": "Cloud Infrastructure Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "ListBuckets": {
        "technique_id": "T1580",
        "technique_name": "Cloud Infrastructure Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "ListUsers": {
        "technique_id": "T1087.004",
        "technique_name": "Account Discovery: Cloud Account",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "ListRoles": {
        "technique_id": "T1087.004",
        "technique_name": "Account Discovery: Cloud Account",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "GetCallerIdentity": {
        "technique_id": "T1087.004",
        "technique_name": "Account Discovery: Cloud Account",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "DescribeSecurityGroups": {
        "technique_id": "T1580",
        "technique_name": "Cloud Infrastructure Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "ListAccessKeys": {
        "technique_id": "T1087.004",
        "technique_name": "Account Discovery: Cloud Account",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },

    # Lateral Movement (TA0008)
    "SwitchRole": {
        "technique_id": "T1550.001",
        "technique_name": "Use Alternate Authentication Material: Application Access Token",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
    },

    # Collection (TA0009)
    "GetObject": {
        "technique_id": "T1530",
        "technique_name": "Data from Cloud Storage",
        "tactic": "Collection",
        "tactic_id": "TA0009",
    },
    "CopyObject": {
        "technique_id": "T1530",
        "technique_name": "Data from Cloud Storage",
        "tactic": "Collection",
        "tactic_id": "TA0009",
    },

    # Exfiltration (TA0010)
    "PutBucketPolicy": {
        "technique_id": "T1537",
        "technique_name": "Transfer Data to Cloud Account",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
    },
    "PutBucketAcl": {
        "technique_id": "T1537",
        "technique_name": "Transfer Data to Cloud Account",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
    },
    "CreateSnapshot": {
        "technique_id": "T1537",
        "technique_name": "Transfer Data to Cloud Account",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
    },
    "ModifySnapshotAttribute": {
        "technique_id": "T1537",
        "technique_name": "Transfer Data to Cloud Account",
        "tactic": "Exfiltration",
        "tactic_id": "TA0010",
    },

    # Impact (TA0040)
    "DeleteBucket": {
        "technique_id": "T1485",
        "technique_name": "Data Destruction",
        "tactic": "Impact",
        "tactic_id": "TA0040",
    },
    "TerminateInstances": {
        "technique_id": "T1485",
        "technique_name": "Data Destruction",
        "tactic": "Impact",
        "tactic_id": "TA0040",
    },
    "DeleteDBInstance": {
        "technique_id": "T1485",
        "technique_name": "Data Destruction",
        "tactic": "Impact",
        "tactic_id": "TA0040",
    },
    "StopInstances": {
        "technique_id": "T1489",
        "technique_name": "Service Stop",
        "tactic": "Impact",
        "tactic_id": "TA0040",
    },
}

# Wazuh rule group → MITRE mappings
WAZUH_GROUP_MITRE_MAP: Dict[str, Dict[str, str]] = {
    "authentication_success": {
        "technique_id": "T1078",
        "technique_name": "Valid Accounts",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
    },
    "authentication_failed": {
        "technique_id": "T1110",
        "technique_name": "Brute Force",
        "tactic": "Credential Access",
        "tactic_id": "TA0006",
    },
    "sshd": {
        "technique_id": "T1021.004",
        "technique_name": "Remote Services: SSH",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
    },
    "web-scan": {
        "technique_id": "T1595",
        "technique_name": "Active Scanning",
        "tactic": "Reconnaissance",
        "tactic_id": "TA0043",
    },
    "exploit_attempt": {
        "technique_id": "T1190",
        "technique_name": "Exploit Public-Facing Application",
        "tactic": "Initial Access",
        "tactic_id": "TA0001",
    },
    "rootcheck": {
        "technique_id": "T1014",
        "technique_name": "Rootkit",
        "tactic": "Defense Evasion",
        "tactic_id": "TA0005",
    },
    "syscheck": {
        "technique_id": "T1565",
        "technique_name": "Data Manipulation",
        "tactic": "Impact",
        "tactic_id": "TA0040",
    },
}

# Suricata event type → MITRE mappings
SURICATA_MITRE_MAP: Dict[str, Dict[str, str]] = {
    "Alert": {
        "technique_id": "T1046",
        "technique_name": "Network Service Discovery",
        "tactic": "Discovery",
        "tactic_id": "TA0007",
    },
    "DNS": {
        "technique_id": "T1071.004",
        "technique_name": "Application Layer Protocol: DNS",
        "tactic": "Command and Control",
        "tactic_id": "TA0011",
    },
    "SSH": {
        "technique_id": "T1021.004",
        "technique_name": "Remote Services: SSH",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
    },
    "HTTP": {
        "technique_id": "T1071.001",
        "technique_name": "Application Layer Protocol: Web Protocols",
        "tactic": "Command and Control",
        "tactic_id": "TA0011",
    },
    "SMB": {
        "technique_id": "T1021.002",
        "technique_name": "Remote Services: SMB/Windows Admin Shares",
        "tactic": "Lateral Movement",
        "tactic_id": "TA0008",
    },
}


class MitreMapper:
    """
    Deterministic MITRE ATT&CK mapper.
    Maps security events to MITRE techniques based on event source and type.
    """

    def map_event(self, event_name: str, vendor: str = "aws",
                  metadata: Optional[Dict] = None) -> List[Dict[str, str]]:
        """
        Maps a single event to zero or more MITRE techniques.

        Returns a list of dicts, each with:
          - technique_id (e.g., "T1078")
          - technique_name
          - tactic (e.g., "Initial Access")
          - tactic_id (e.g., "TA0001")
        """
        techniques = []

        if vendor.lower() in ("aws", "cloudtrail"):
            mapping = MITRE_TECHNIQUE_MAP.get(event_name)
            if mapping:
                techniques.append(mapping)

        elif vendor.lower() == "wazuh":
            # Check groups from metadata
            groups = (metadata or {}).get("rule_groups", [])
            for group in groups:
                mapping = WAZUH_GROUP_MITRE_MAP.get(group)
                if mapping and mapping not in techniques:
                    techniques.append(mapping)
            # Also try event_name directly
            if not techniques:
                mapping = WAZUH_GROUP_MITRE_MAP.get(event_name)
                if mapping:
                    techniques.append(mapping)

        elif vendor.lower() == "suricata":
            mapping = SURICATA_MITRE_MAP.get(event_name)
            if mapping:
                techniques.append(mapping)

        elif vendor.lower() == "openvas":
            # All OpenVAS findings map to vulnerability exploitation
            techniques.append({
                "technique_id": "T1190",
                "technique_name": "Exploit Public-Facing Application",
                "tactic": "Initial Access",
                "tactic_id": "TA0001",
            })

        return techniques

    def map_events_bulk(self, events: List[Dict]) -> Dict[str, List[Dict[str, str]]]:
        """
        Maps a list of event dicts to their MITRE techniques.
        Returns a dict keyed by event_name.
        """
        result = {}
        for event in events:
            event_name = event.get("event_name", "")
            vendor = event.get("vendor", "aws")
            metadata = event.get("metadata", {})
            mappings = self.map_event(event_name, vendor, metadata)
            if mappings:
                result[event_name] = mappings
        return result

    def get_attack_chain(self, technique_ids: List[str]) -> List[Dict[str, str]]:
        """
        Given a list of technique IDs observed, returns them ordered by
        the ATT&CK kill chain (tactic order).
        """
        tactic_order = [
            "TA0043",  # Reconnaissance
            "TA0042",  # Resource Development
            "TA0001",  # Initial Access
            "TA0002",  # Execution
            "TA0003",  # Persistence
            "TA0004",  # Privilege Escalation
            "TA0005",  # Defense Evasion
            "TA0006",  # Credential Access
            "TA0007",  # Discovery
            "TA0008",  # Lateral Movement
            "TA0009",  # Collection
            "TA0011",  # Command and Control
            "TA0010",  # Exfiltration
            "TA0040",  # Impact
        ]

        # Collect all unique techniques from all maps
        all_techniques = {}
        for tech_map in [MITRE_TECHNIQUE_MAP, WAZUH_GROUP_MITRE_MAP, SURICATA_MITRE_MAP]:
            for mapping in tech_map.values():
                all_techniques[mapping["technique_id"]] = mapping

        matched = [all_techniques[tid] for tid in technique_ids if tid in all_techniques]

        # Sort by tactic order
        def tactic_sort_key(t: Dict) -> int:
            try:
                return tactic_order.index(t["tactic_id"])
            except ValueError:
                return 999

        matched.sort(key=tactic_sort_key)
        return matched
