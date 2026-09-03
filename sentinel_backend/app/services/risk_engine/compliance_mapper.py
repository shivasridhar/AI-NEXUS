"""
Compliance Mapping Service (Stage 4)

Maps risk findings and MITRE techniques to compliance framework controls.
Supports NIST 800-53, SOC 2, CIS AWS Benchmark, and PCI DSS.
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Compliance Framework Definitions
# Maps MITRE technique IDs to compliance control references.
# ---------------------------------------------------------------------------

NIST_800_53_MAP: Dict[str, List[Dict[str, str]]] = {
    "T1078": [
        {"control_id": "AC-2", "control_name": "Account Management", "family": "Access Control"},
        {"control_id": "IA-2", "control_name": "Identification and Authentication", "family": "Identification and Authentication"},
    ],
    "T1078.004": [
        {"control_id": "AC-2(12)", "control_name": "Account Monitoring", "family": "Access Control"},
        {"control_id": "AC-6", "control_name": "Least Privilege", "family": "Access Control"},
    ],
    "T1136.003": [
        {"control_id": "AC-2", "control_name": "Account Management", "family": "Access Control"},
        {"control_id": "CM-5", "control_name": "Access Restrictions for Change", "family": "Configuration Management"},
    ],
    "T1098": [
        {"control_id": "AC-2", "control_name": "Account Management", "family": "Access Control"},
        {"control_id": "AC-3", "control_name": "Access Enforcement", "family": "Access Control"},
        {"control_id": "AC-6", "control_name": "Least Privilege", "family": "Access Control"},
    ],
    "T1098.001": [
        {"control_id": "AC-2", "control_name": "Account Management", "family": "Access Control"},
        {"control_id": "IA-5", "control_name": "Authenticator Management", "family": "Identification and Authentication"},
    ],
    "T1548": [
        {"control_id": "AC-6", "control_name": "Least Privilege", "family": "Access Control"},
        {"control_id": "AC-6(5)", "control_name": "Privileged Accounts", "family": "Access Control"},
    ],
    "T1562.008": [
        {"control_id": "AU-12", "control_name": "Audit Generation", "family": "Audit and Accountability"},
        {"control_id": "SI-4", "control_name": "System Monitoring", "family": "System and Information Integrity"},
    ],
    "T1562": [
        {"control_id": "SI-4", "control_name": "System Monitoring", "family": "System and Information Integrity"},
    ],
    "T1555": [
        {"control_id": "IA-5", "control_name": "Authenticator Management", "family": "Identification and Authentication"},
        {"control_id": "SC-28", "control_name": "Protection of Information at Rest", "family": "System and Communications Protection"},
    ],
    "T1552": [
        {"control_id": "IA-5(7)", "control_name": "No Embedded Unencrypted Static Authenticators", "family": "Identification and Authentication"},
    ],
    "T1580": [
        {"control_id": "RA-5", "control_name": "Vulnerability Scanning", "family": "Risk Assessment"},
    ],
    "T1087.004": [
        {"control_id": "AC-2", "control_name": "Account Management", "family": "Access Control"},
    ],
    "T1530": [
        {"control_id": "AC-3", "control_name": "Access Enforcement", "family": "Access Control"},
        {"control_id": "SC-28", "control_name": "Protection of Information at Rest", "family": "System and Communications Protection"},
    ],
    "T1537": [
        {"control_id": "AC-4", "control_name": "Information Flow Enforcement", "family": "Access Control"},
        {"control_id": "SC-7", "control_name": "Boundary Protection", "family": "System and Communications Protection"},
    ],
    "T1485": [
        {"control_id": "CP-9", "control_name": "System Backup", "family": "Contingency Planning"},
        {"control_id": "SI-7", "control_name": "Software, Firmware, and Information Integrity", "family": "System and Information Integrity"},
    ],
    "T1110": [
        {"control_id": "AC-7", "control_name": "Unsuccessful Logon Attempts", "family": "Access Control"},
        {"control_id": "IA-2(1)", "control_name": "Multi-Factor Authentication to Privileged Accounts", "family": "Identification and Authentication"},
    ],
    "T1190": [
        {"control_id": "SI-2", "control_name": "Flaw Remediation", "family": "System and Information Integrity"},
        {"control_id": "SC-7", "control_name": "Boundary Protection", "family": "System and Communications Protection"},
    ],
    "T1046": [
        {"control_id": "SC-7", "control_name": "Boundary Protection", "family": "System and Communications Protection"},
        {"control_id": "SI-4", "control_name": "System Monitoring", "family": "System and Information Integrity"},
    ],
    "T1021.004": [
        {"control_id": "AC-17", "control_name": "Remote Access", "family": "Access Control"},
    ],
}

SOC2_MAP: Dict[str, List[Dict[str, str]]] = {
    "T1078": [
        {"control_id": "CC6.1", "control_name": "Logical and Physical Access Controls", "category": "Common Criteria"},
    ],
    "T1098": [
        {"control_id": "CC6.1", "control_name": "Logical and Physical Access Controls", "category": "Common Criteria"},
        {"control_id": "CC6.3", "control_name": "Role-Based Access and Least Privilege", "category": "Common Criteria"},
    ],
    "T1562.008": [
        {"control_id": "CC7.2", "control_name": "Monitoring of System Components", "category": "Common Criteria"},
    ],
    "T1485": [
        {"control_id": "A1.2", "control_name": "Recovery of Data", "category": "Availability"},
    ],
    "T1530": [
        {"control_id": "CC6.1", "control_name": "Logical and Physical Access Controls", "category": "Common Criteria"},
        {"control_id": "C1.1", "control_name": "Confidentiality Commitments", "category": "Confidentiality"},
    ],
    "T1110": [
        {"control_id": "CC6.1", "control_name": "Logical and Physical Access Controls", "category": "Common Criteria"},
    ],
    "T1548": [
        {"control_id": "CC6.3", "control_name": "Role-Based Access and Least Privilege", "category": "Common Criteria"},
    ],
}

CIS_AWS_MAP: Dict[str, List[Dict[str, str]]] = {
    "T1078": [
        {"control_id": "CIS 1.10", "control_name": "Ensure MFA is enabled for the root account", "section": "Identity and Access Management"},
        {"control_id": "CIS 1.14", "control_name": "Ensure access keys are rotated every 90 days", "section": "Identity and Access Management"},
    ],
    "T1098.001": [
        {"control_id": "CIS 1.12", "control_name": "Ensure no root account access key exists", "section": "Identity and Access Management"},
    ],
    "T1562.008": [
        {"control_id": "CIS 3.1", "control_name": "Ensure CloudTrail is enabled in all regions", "section": "Logging"},
        {"control_id": "CIS 3.4", "control_name": "Ensure CloudTrail log file validation is enabled", "section": "Logging"},
    ],
    "T1530": [
        {"control_id": "CIS 2.1.1", "control_name": "Ensure S3 Bucket Policy is set to deny HTTP requests", "section": "Storage"},
    ],
    "T1537": [
        {"control_id": "CIS 2.1.2", "control_name": "Ensure S3 buckets are not publicly accessible", "section": "Storage"},
    ],
}


class ComplianceMapper:
    """
    Maps MITRE ATT&CK techniques to compliance framework controls.
    Provides a deterministic compliance posture assessment.
    """

    FRAMEWORK_MAPS = {
        "NIST 800-53": NIST_800_53_MAP,
        "SOC 2": SOC2_MAP,
        "CIS AWS Benchmark": CIS_AWS_MAP,
    }

    def map_techniques(self, technique_ids: List[str],
                       frameworks: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        Maps a list of MITRE technique IDs to compliance controls across frameworks.

        Args:
            technique_ids: List of MITRE technique IDs (e.g., ["T1078", "T1098"])
            frameworks: Optional list of frameworks to check. Default: all.

        Returns:
            Dict keyed by framework name, each containing a list of
            violated/relevant controls.
        """
        if frameworks is None:
            frameworks = list(self.FRAMEWORK_MAPS.keys())

        result: Dict[str, List[Dict]] = {}

        for framework_name in frameworks:
            framework_map = self.FRAMEWORK_MAPS.get(framework_name, {})
            controls = []
            seen_control_ids = set()

            for technique_id in technique_ids:
                mapped_controls = framework_map.get(technique_id, [])
                for control in mapped_controls:
                    control_id = control.get("control_id", "")
                    if control_id not in seen_control_ids:
                        seen_control_ids.add(control_id)
                        controls.append({
                            **control,
                            "triggered_by": technique_id,
                        })

            if controls:
                result[framework_name] = controls

        return result

    def get_compliance_score(self, technique_ids: List[str]) -> Dict[str, any]:
        """
        Calculates a simplified compliance posture score per framework.
        Score = 100 - (number_of_violated_controls * penalty)
        """
        all_mappings = self.map_techniques(technique_ids)
        scores = {}

        for framework, controls in all_mappings.items():
            total_controls = len(controls)
            # Penalty based on severity of control violations
            penalty = min(total_controls * 8, 80)
            score = max(100 - penalty, 10)
            scores[framework] = {
                "score": score,
                "violated_controls": total_controls,
                "controls": controls,
            }

        return scores
