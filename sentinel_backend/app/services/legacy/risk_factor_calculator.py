from sqlalchemy.orm import Session as DBSession
from sqlalchemy import func
from neo4j import Session as GraphSession
from typing import List, Tuple

from app.models.machine_identity import MachineIdentity
from app.models.access_log import AccessLog

class RiskFactorCalculator:
    def __init__(self, db: DBSession, graph: GraphSession):
        self.db = db
        self.graph = graph

    def calc_privilege_escalation(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        query = """
        MATCH (i:Identity {arn: $arn, workspace_id: $workspace_id})-[rel:ASSUMED_ROLE]->(target {workspace_id: $workspace_id})
        RETURN count(target) as role_count
        """
        result = self.graph.run(query, arn=identity.arn, workspace_id=str(identity.workspace_id)).single()
        role_count = result["role_count"] if result else 0
        
        if role_count > 0:
            score += min(role_count * 20, 40) # Max 40 points
            reasons.append(f"Identity assumes {role_count} other role(s), increasing privilege escalation risk.")
            
        return score, reasons

    def calc_sensitive_access(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        
        sensitive_services = ['kms.amazonaws.com', 'iam.amazonaws.com', 'secretsmanager.amazonaws.com']
        
        counts = self.db.query(AccessLog.event_source, func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_source.in_(sensitive_services))\
            .group_by(AccessLog.event_source).all()
            
        for service, count in counts:
            score += 15
            reasons.append(f"Accessed sensitive service {service} ({count} times).")
            
        s3_counts = self.db.query(func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_source == 's3.amazonaws.com')\
            .filter(AccessLog.event_name.in_(['DeleteBucket', 'DeleteObject', 'PutBucketAcl', 'PutBucketPolicy']))\
            .scalar()
            
        if s3_counts > 0:
            score += 15
            reasons.append(f"Performed {s3_counts} sensitive S3 management actions.")
            
        return min(score, 30), reasons

    def calc_activity_volume(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        if identity.total_events > 5000:
            score += 10
            reasons.append(f"High API activity volume ({identity.total_events} total events).")
        return score, reasons

    def calc_geographic_anomaly(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        query = """
        MATCH (i:Identity {arn: $arn, workspace_id: $workspace_id})-[rel:ORIGINATED_FROM]->(ip:IPAddress {workspace_id: $workspace_id})
        RETURN count(ip) as ip_count
        """
        result = self.graph.run(query, arn=identity.arn, workspace_id=str(identity.workspace_id)).single()
        ip_count = result["ip_count"] if result else 0
        
        if ip_count > 5:
            score += 10
            reasons.append(f"Activity originated from an unusually high number of distinct IPs ({ip_count}).")
            
        return score, reasons

    def calc_dormant_then_active(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        if identity.first_seen and identity.last_seen:
            days_active = (identity.last_seen - identity.first_seen).days
            # Heuristic: Activity after a long period of low usage (e.g. <10 events per day average)
            if days_active > 30 and (identity.total_events / days_active) < 5:
                score += 15
                reasons.append(f"Identity active after long period of low average activity.")
        return score, reasons

    def calc_failed_calls(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        
        failed_count = self.db.query(func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.raw_event_json.op('->>')('errorCode').in_(['AccessDenied', 'UnauthorizedOperation']))\
            .scalar()
            
        if failed_count > 0:
            score += min(failed_count * 5, 20) # Max 20 points
            reasons.append(f"Encountered {failed_count} 'AccessDenied' or 'UnauthorizedOperation' errors.")
            
        return score, reasons

    def calc_no_mfa_console_login(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        
        count = self.db.query(func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_name == 'ConsoleLogin')\
            .filter(AccessLog.raw_event_json.op('->')('additionalEventData').op('->>')('MFAUsed') == 'No')\
            .scalar()
            
        root_count = self.db.query(func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_name == 'ConsoleLogin')\
            .filter(AccessLog.raw_event_json.op('->')('additionalEventData').op('->>')('MFAUsed') == 'No')\
            .filter(AccessLog.raw_event_json.op('->')('userIdentity').op('->>')('type') == 'Root')\
            .scalar()

        if root_count > 0:
            score += 35
            reasons.append(f"Root user ConsoleLogin without MFA detected ({root_count} times).")
        elif count > 0:
            score += 35
            reasons.append(f"ConsoleLogin without MFA detected ({count} times).")
            
        return score, reasons

    def calc_cloudtrail_evasion(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        
        count = self.db.query(func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_source == 'cloudtrail.amazonaws.com')\
            .filter(AccessLog.event_name.in_(['StopLogging', 'DeleteTrail', 'UpdateTrail']))\
            .scalar()
            
        if count > 0:
            score += 40
            reasons.append(f"Performed {count} CloudTrail evasion actions (StopLogging, DeleteTrail, etc).")
            
        return score, reasons

    def calc_dangerous_policy(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        
        count = self.db.query(func.count(AccessLog.id))\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_name == 'AttachUserPolicy')\
            .filter(AccessLog.raw_event_json.op('->')('requestParameters').op('->>')('policyArn').like('%AdministratorAccess%'))\
            .scalar()
            
        if count > 0:
            score += 30
            reasons.append(f"Attached high-privilege policy AdministratorAccess {count} times.")
            
        return score, reasons

    def calc_public_ingress(self, identity: MachineIdentity) -> Tuple[int, List[str]]:
        score = 0
        reasons = []
        
        logs = self.db.query(AccessLog.raw_event_json)\
            .filter(AccessLog.identity_arn == identity.arn)\
            .filter(AccessLog.workspace_id == identity.workspace_id)\
            .filter(AccessLog.event_name == 'AuthorizeSecurityGroupIngress')\
            .all()
            
        trigger_count = 0
        for log in logs:
            try:
                event = log[0]
                req_params = event.get('requestParameters', {}) or {}
                ip_perms = req_params.get('ipPermissions', {}) or {}
                
                items = []
                if isinstance(ip_perms, dict):
                    items = ip_perms.get('items', [])
                elif isinstance(ip_perms, list):
                    items = ip_perms
                    
                for perm in items:
                    from_port = perm.get('fromPort')
                    if from_port in [22, 3389, '22', '3389']:
                        ip_ranges = perm.get('ipRanges', {}) or {}
                        ranges = []
                        if isinstance(ip_ranges, dict):
                            ranges = ip_ranges.get('items', [])
                        elif isinstance(ip_ranges, list):
                            ranges = ip_ranges
                        
                        if any(r.get('cidrIp') == '0.0.0.0/0' for r in ranges):
                            trigger_count += 1
                            break # Only count once per event
            except Exception:
                pass
                
        if trigger_count > 0:
            score += 25
            reasons.append(f"Authorized public ingress (0.0.0.0/0) on sensitive ports {trigger_count} times.")
            
        return score, reasons
