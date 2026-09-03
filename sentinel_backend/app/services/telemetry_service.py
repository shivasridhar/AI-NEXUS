from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List
from uuid import UUID

from neo4j import Session as GraphSession
from sqlalchemy.orm import Session

from app.models.access_log import AccessLog
from app.models.integration import Integration
from app.models.machine_identity import MachineIdentity
from app.models.risk_finding import RiskFinding
from app.models.risk_score import RiskScore
from app.models.tenant import CloudAccount


class TelemetryService:
    @staticmethod
    def get_dashboard_summary(
        db: Session, graph: GraphSession, workspace_id: UUID
    ) -> dict:
        identities_count = (
            db.query(MachineIdentity)
            .filter(MachineIdentity.workspace_id == workspace_id)
            .count()
        )

        critical_risk_count = (
            db.query(RiskScore)
            .filter(
                RiskScore.workspace_id == workspace_id,
                RiskScore.severity.in_(["Critical", "High"]),
            )
            .count()
        )

        attack_path_count = 0
        try:
            res = graph.run(
                "MATCH ()-[r:ASSUMED_ROLE {workspace_id: $workspace_id}]->() RETURN count(r) as c",
                workspace_id=str(workspace_id),
            )
            single_res = res.single()
            if single_res:
                attack_path_count = single_res["c"]
        except Exception:
            pass

        total_findings_count = (
            db.query(RiskFinding)
            .filter(RiskFinding.workspace_id == workspace_id)
            .count()
        )
        cloud_accounts_count = (
            db.query(CloudAccount)
            .filter(CloudAccount.workspace_id == workspace_id)
            .count()
        )

        return {
            "identities_count": identities_count,
            "critical_risk_count": critical_risk_count,
            "attack_path_count": attack_path_count,
            "total_findings_count": total_findings_count,
            "cloud_accounts_count": cloud_accounts_count,
        }

    @staticmethod
    def get_recent_findings(db: Session, workspace_id: UUID, limit: int = 10) -> list:
        findings = (
            db.query(RiskFinding)
            .filter(RiskFinding.workspace_id == workspace_id)
            .order_by(RiskFinding.created_at.desc())
            .limit(limit)
            .all()
        )
        results = []
        for f in findings:
            results.append(
                {
                    "id": str(f.id),
                    "identity_arn": f.identity.arn if f.identity else "Unknown",
                    "finding_type": f.finding_type,
                    "severity": f.severity,
                    "description": f.description,
                    "created_at": f.created_at.isoformat() if f.created_at else None,
                }
            )
        return results

    @staticmethod
    def get_top_attack_paths(
        graph: GraphSession, workspace_id: UUID, limit: int = 3
    ) -> list:
        query = """
        MATCH p=shortestPath((i:Identity {workspace_id: $workspace_id})-[*1..4]->(d {workspace_id: $workspace_id}))
        WHERE any(label in labels(d) WHERE label IN ['DataStore', 'Resource'])
          AND length(p) > 0
        RETURN p
        LIMIT $limit
        """
        results = []
        try:
            res = graph.run(query, limit=limit, workspace_id=str(workspace_id))
            for record in res:
                path = record["p"]
                nodes_data = []
                for node in path.nodes:
                    labels = list(node.labels)
                    label = labels[0] if labels else "Unknown"
                    name = dict(node.items()).get("arn", "Unknown")
                    nodes_data.append({"label": label, "name": name})

                edges_data = []
                for rel in path.relationships:
                    edges_data.append(rel.type)

                if len(nodes_data) > 1:
                    results.append(
                        {
                            "nodes": nodes_data,
                            "edges": edges_data,
                            "severity": (
                                "Critical"
                                if "DataStore" in nodes_data[-1]["label"]
                                else "High"
                            ),
                        }
                    )
        except Exception:
            pass
        return results

    @staticmethod
    def get_recent_events(
        db: Session,
        workspace_id: UUID,
        limit: int = 50,
        format_for_ingestion: bool = False,
    ) -> list:
        events = (
            db.query(AccessLog)
            .filter(AccessLog.workspace_id == workspace_id)
            .order_by(AccessLog.event_time.desc())
            .limit(limit)
            .all()
        )
        results: List[Dict[str, Any]] = []
        for e in events:
            raw_json = e.raw_event_json or {}
            error_code = raw_json.get("errorCode") or ""
            error_msg = raw_json.get("errorMessage") or ""

            is_denied = "Denied" in str(error_code) or "Unauthorized" in str(error_msg)
            is_anomaly = is_denied or e.event_name in [
                "DeleteVpc",
                "ConsoleLogin",
                "DeleteBucket",
            ]
            status_label = "FAILED" if is_denied else "SUCCESS"
            severity_label = "HIGH" if is_anomaly else "INFO"

            if format_for_ingestion:
                # Matches frontend LiveEvent interface
                results.append(
                    {
                        "id": str(e.id),
                        "timestamp": e.event_time.isoformat(),
                        "connector": "AWS CloudTrail",  # We can infer from source if multiple exists
                        "eventType": e.event_name,
                        "severity": severity_label,
                        "status": status_label,
                        "message": f"{'Failed' if is_denied else 'Successful'} action by {e.identity_arn}",
                    }
                )
            else:
                # Matches frontend Dashboard events interface
                results.append(
                    {
                        "id": str(e.id),
                        "event": e.event_name,
                        "user": e.identity_arn,
                        "source": e.source_ip or e.event_source,
                        "status": "Denied" if is_denied else "Success",
                        "isAnomaly": is_anomaly,
                        "anomalyReason": (
                            "Destructive Action"
                            if e.event_name.startswith("Delete")
                            else (
                                "Unauthorized"
                                if is_denied
                                else ("Login" if "Login" in e.event_name else "")
                            )
                        ),
                        "event_time": e.event_time.isoformat(),
                    }
                )
        return results

    @staticmethod
    def get_ingestion_metrics(db: Session, workspace_id: UUID) -> dict:
        total_events = (
            db.query(AccessLog).filter(AccessLog.workspace_id == workspace_id).count()
        )

        # Calculate events per minute over the last 20 minutes
        now = datetime.now(timezone.utc)
        twenty_mins_ago = now - timedelta(minutes=20)

        recent_events = (
            db.query(AccessLog)
            .filter(
                AccessLog.workspace_id == workspace_id,
                AccessLog.event_time >= twenty_mins_ago,
            )
            .all()
        )

        events_per_minute = len(recent_events) / 20.0

        # We can dynamically group events by minute for chartData
        minute_buckets = {}
        for i in range(20):
            bucket_time = (now - timedelta(minutes=19 - i)).replace(
                second=0, microsecond=0
            )
            minute_buckets[bucket_time] = 0

        for e in recent_events:
            bucket_time = e.event_time.replace(second=0, microsecond=0)
            if bucket_time in minute_buckets:
                minute_buckets[bucket_time] += 1

        chart_data = []
        for b_time, count in sorted(minute_buckets.items()):
            chart_data.append(
                {
                    "time": b_time.isoformat(),
                    "events": count,
                    "validated": count,  # Assuming 100% validation success for DB-saved events
                }
            )

        active_connectors = (
            db.query(Integration)
            .filter(
                Integration.workspace_id == workspace_id, Integration.status != "error"
            )
            .count()
        )

        return {
            "totalEvents": total_events,
            "eventsPerMinute": round(events_per_minute, 1),
            "validationSuccessRate": 100.0 if total_events > 0 else 0.0,
            "activeConnectors": active_connectors,
            "chartData": chart_data,
        }

    @staticmethod
    def get_pipeline_config() -> dict:
        return {
            "stages": [
                {
                    "id": "1",
                    "name": "Connectors",
                    "status": "healthy",
                    "description": "Data ingestion from external sources",
                },
                {
                    "id": "2",
                    "name": "Validation",
                    "status": "healthy",
                    "description": "Schema enforcement & typing",
                },
                {
                    "id": "3",
                    "name": "Deduplication",
                    "status": "healthy",
                    "description": "Cache-based duplicate filtering",
                },
                {
                    "id": "4",
                    "name": "Enrichment",
                    "status": "healthy",
                    "description": "Metadata and threat intel tagging",
                },
                {
                    "id": "5",
                    "name": "Publisher",
                    "status": "healthy",
                    "description": "Event bus distribution",
                },
            ],
            "columns": [
                {"key": "timestamp", "label": "Time", "type": "date", "sortable": True},
                {
                    "key": "connector",
                    "label": "Source",
                    "type": "badge",
                    "sortable": True,
                },
                {
                    "key": "eventType",
                    "label": "Event Type",
                    "type": "string",
                    "sortable": False,
                },
                {
                    "key": "severity",
                    "label": "Severity",
                    "type": "severity",
                    "sortable": True,
                },
                {"key": "status", "label": "Status", "type": "badge", "sortable": True},
                {
                    "key": "message",
                    "label": "Message",
                    "type": "string",
                    "sortable": False,
                },
            ],
            "healthThresholds": {"latencyMs": 1500, "errorRatePercent": 5.0},
        }
