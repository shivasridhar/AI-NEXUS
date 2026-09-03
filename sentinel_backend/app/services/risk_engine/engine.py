from sqlalchemy.orm import Session as DBSession
from neo4j import Session as GraphSession
import logging

from app.models.machine_identity import MachineIdentity
from app.models.risk_score import RiskScore
from app.models.risk_finding import RiskFinding
from app.models.tenant import Workspace
from app.services.legacy.risk_factor_calculator import RiskFactorCalculator
from app.services.risk_engine.path_analyzer import PathAnalyzer
from app.services.risk_engine.vector_calculator import VectorCalculator
from app.services.risk_engine.mitre_mapper import MitreMapper
from app.services.risk_engine.blast_radius import BlastRadiusAnalyzer
from app.services.risk_engine.compliance_mapper import ComplianceMapper
from app.schemas.risk_evidence import RiskEvidence, IncidentDetail

from app.core.events.bus import event_bus
from app.core.events.contracts import RiskEvent
from app.core.events.event_types import ActorClassification, EventCategory, EventSeverity, EventStatus, ResourceClassification

logger = logging.getLogger(__name__)

class RiskEngine:
    def __init__(self, db: DBSession, graph: GraphSession):
        self.db = db
        self.graph = graph
        self.legacy_calculator = RiskFactorCalculator(db, graph)
        self.path_analyzer = PathAnalyzer(db, graph)
        self.vector_calculator = VectorCalculator()
        self.mitre_mapper = MitreMapper()
        self.blast_radius_analyzer = BlastRadiusAnalyzer(graph)
        self.compliance_mapper = ComplianceMapper()

    def _calculate_legacy_score(self, identity: MachineIdentity) -> int:
        total_score = 0
        
        score, _ = self.legacy_calculator.calc_privilege_escalation(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_sensitive_access(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_activity_volume(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_geographic_anomaly(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_dormant_then_active(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_failed_calls(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_no_mfa_console_login(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_cloudtrail_evasion(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_dangerous_policy(identity)
        total_score += score
        score, _ = self.legacy_calculator.calc_public_ingress(identity)
        total_score += score
        
        return min(max(total_score, 0), 100)

    def evaluate_identity(self, identity: MachineIdentity) -> RiskScore:
        # Calculate legacy score purely for comparison
        legacy_score = self._calculate_legacy_score(identity)
        
        # Phase 1: Attack Path Analysis
        attack_paths = self.path_analyzer.find_attack_paths(identity.arn, str(identity.workspace_id))
        
        # Phase 2: Vector Calculator Score
        score = self.vector_calculator.calculate_score(attack_paths)
        severity = self.vector_calculator.calculate_severity(score)
        
        # Phase 3: MITRE ATT&CK Mapping
        mitre_techniques = []
        try:
            from app.models.access_log import AccessLog
            recent_events = self.db.query(AccessLog).filter(
                AccessLog.identity_arn == identity.arn,
                AccessLog.workspace_id == identity.workspace_id
            ).order_by(AccessLog.event_time.desc()).limit(100).all()

            seen_techniques = set()
            for event in recent_events:
                mappings = self.mitre_mapper.map_event(
                    event.event_name or "",
                    vendor="aws",
                    metadata=event.raw_event if isinstance(event.raw_event, dict) else {}
                )
                for mapping in mappings:
                    tid = mapping["technique_id"]
                    if tid not in seen_techniques:
                        seen_techniques.add(tid)
                        mitre_techniques.append(mapping)
        except Exception as e:
            logger.warning("MITRE mapping failed for %s (non-fatal): %s", identity.arn, e)

        # Phase 4: Blast Radius Analysis
        blast_radius_data = None
        try:
            blast_result = self.blast_radius_analyzer.analyze(identity.arn, str(identity.workspace_id))
            blast_radius_data = blast_result.to_dict()
        except Exception as e:
            logger.warning("Blast radius analysis failed for %s (non-fatal): %s", identity.arn, e)

        # Phase 5: Compliance Mapping
        compliance_data = None
        try:
            if mitre_techniques:
                technique_ids = [t["technique_id"] for t in mitre_techniques]
                compliance_data = self.compliance_mapper.get_compliance_score(technique_ids)
        except Exception as e:
            logger.warning("Compliance mapping failed for %s (non-fatal): %s", identity.arn, e)

        # Generate incidents
        incidents = []
        if attack_paths:
            incidents.append(
                IncidentDetail(
                    finding_type="Attack Path Discovered",
                    description=f"Found {len(attack_paths)} potential attack paths.",
                    attack_paths=attack_paths
                )
            )
        if mitre_techniques:
            tactics = list({t["tactic"] for t in mitre_techniques})
            incidents.append(
                IncidentDetail(
                    finding_type="MITRE ATT&CK Techniques Detected",
                    description=f"Mapped {len(mitre_techniques)} MITRE techniques across tactics: {', '.join(tactics[:5])}.",
                    metadata={"techniques": mitre_techniques}
                )
            )
        if blast_radius_data and blast_radius_data.get("total_reachable_nodes", 0) > 0:
            incidents.append(
                IncidentDetail(
                    finding_type="Blast Radius Assessment",
                    description=f"Compromise could affect {blast_radius_data['total_reachable_nodes']} nodes including {blast_radius_data['resources_affected']} resources and {blast_radius_data['identities_affected']} identities.",
                    metadata={"blast_radius": blast_radius_data}
                )
            )

        evidence = RiskEvidence(
            score=score,
            severity=severity,
            incidents=incidents,
            mitre_techniques=mitre_techniques,
            blast_radius=blast_radius_data,
            compliance=compliance_data,
        )
        
        # Clear existing score and findings
        self.db.query(RiskScore).filter(RiskScore.identity_id == identity.id, RiskScore.workspace_id == identity.workspace_id).delete()
        self.db.query(RiskFinding).filter(RiskFinding.identity_id == identity.id, RiskFinding.workspace_id == identity.workspace_id).delete()
        
        # Create legacy-compatible reasons (for backward compatibility of the string array)
        legacy_reasons = [incident.description for incident in evidence.incidents]
        
        # Insert new Risk Findings with MITRE and blast radius data
        blast_score = blast_radius_data.get("blast_score") if blast_radius_data else None
        for incident in evidence.incidents:
            # Extract MITRE technique from incident metadata if available
            inc_mitre_id = None
            inc_mitre_tactic = None
            inc_compliance = None
            if incident.metadata:
                techniques = incident.metadata.get("techniques", [])
                if techniques:
                    inc_mitre_id = techniques[0].get("technique_id")
                    inc_mitre_tactic = techniques[0].get("tactic")
                    # Map to compliance
                    if inc_mitre_id:
                        inc_compliance = self.compliance_mapper.map_techniques([inc_mitre_id])

            finding = RiskFinding(
                workspace_id=identity.workspace_id,
                identity_id=identity.id,
                finding_type=incident.finding_type,
                severity=evidence.severity,
                description=incident.description,
                mitre_technique=inc_mitre_id,
                mitre_tactic=inc_mitre_tactic,
                blast_radius_score=blast_score,
                compliance_refs=inc_compliance,
            )
            self.db.add(finding)
        
        # Create new Risk Score record with evidence and legacy comparison
        risk_record = RiskScore(
            workspace_id=identity.workspace_id,
            identity_id=identity.id,
            score=evidence.score,
            severity=evidence.severity,
            reasons=legacy_reasons,
            legacy_comparison_score=legacy_score,
            risk_evidence=evidence.model_dump()
        )
        self.db.add(risk_record)
        
        # Update identity summary
        identity.risk_score = evidence.score
        self.db.flush()
        
        # Publish Event
        workspace = self.db.query(Workspace).filter(Workspace.id == identity.workspace_id).first()
        org_id = str(workspace.organization_id) if workspace else "SYSTEM"
        
        event_bus.publish(RiskEvent(
            workspace_id=str(identity.workspace_id),
            organization_id=org_id,
            actor="RiskEngineWorker",
            actor_type=ActorClassification.INTERNAL_ENGINE,
            module="RiskEngine",
            action="RISK_CALCULATED",
            category=EventCategory.RISK,
            severity=EventSeverity.CRITICAL if severity == "Critical" else EventSeverity.INFO,
            status=EventStatus.SUCCESS,
            resource_type=ResourceClassification.IDENTITY,
            resource_id=identity.arn,
            metadata={"score": score, "severity": severity, "legacy_score": legacy_score, "findings_count": len(incidents)}
        ))
        
        return risk_record

    def evaluate_new_identities(self, identity_arns: list, workspace_id: str) -> int:
        findings_count = 0
        for arn in identity_arns:
            ident = self.db.query(MachineIdentity).filter(MachineIdentity.arn == arn, MachineIdentity.workspace_id == workspace_id).first()
            if ident:
                risk_record = self.evaluate_identity(ident)
                # Parse risk_evidence to find number of incidents
                if risk_record.risk_evidence:
                    findings_count += len(risk_record.risk_evidence.get('incidents', []))
        self.db.commit()
        return findings_count
