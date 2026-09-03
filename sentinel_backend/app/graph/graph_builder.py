from neo4j import Session
from app.graph import neo4j_queries as q

class GraphBuilder:
    def __init__(self, session: Session):
        self.session = session

    def sync_identity(self, arn: str, account_id: str, identity_type: str, workspace_id: str):
        self.session.run(q.MERGE_IDENTITY, arn=arn, account_id=account_id, identity_type=identity_type, workspace_id=workspace_id)

    def sync_resource(self, arn: str, workspace_id: str):
        if arn:
            self.session.run(q.MERGE_RESOURCE, arn=arn, workspace_id=workspace_id)

    def sync_ip(self, ip: str, workspace_id: str):
        if ip:
            self.session.run(q.MERGE_IP, ip=ip, workspace_id=workspace_id)

    def link_identity_resource(self, identity_arn: str, resource_arn: str, event_time: str, workspace_id: str):
        if identity_arn and resource_arn:
            self.session.run(q.LINK_IDENTITY_RESOURCE, identity_arn=identity_arn, resource_arn=resource_arn, event_time=event_time, workspace_id=workspace_id)

    def link_identity_ip(self, identity_arn: str, source_ip: str, event_time: str, workspace_id: str):
        if identity_arn and source_ip:
            self.session.run(q.LINK_IDENTITY_IP, identity_arn=identity_arn, source_ip=source_ip, event_time=event_time, workspace_id=workspace_id)

    def link_assume_role(self, source_arn: str, target_arn: str, event_time: str, workspace_id: str):
        if source_arn and target_arn:
            self.session.run(q.LINK_ASSUME_ROLE, source_arn=source_arn, target_arn=target_arn, event_time=event_time, workspace_id=workspace_id)

    def sync_host_actor(self, hostname: str, workspace_id: str):
        if hostname:
            self.session.run(q.MERGE_HOST_ACTOR, hostname=hostname, workspace_id=workspace_id)
            
    def sync_ip_actor(self, ip: str, workspace_id: str):
        if ip:
            self.session.run(q.MERGE_IP_ACTOR, ip=ip, workspace_id=workspace_id)

    def sync_event(self, event_id: str, workspace_id: str, timestamp: str, source_tool: str, severity: int, mitre_technique: str, actor_id: str, asset_id: str):
        self.session.run(
            q.CREATE_EVENT,
            event_id=event_id,
            workspace_id=workspace_id,
            timestamp=timestamp,
            source_tool=source_tool,
            severity=severity,
            mitre_technique=mitre_technique,
            actor_id=actor_id,
            asset_id=asset_id
        )

    def correlate_events_to_incident(self, event_id: str, workspace_id: str, time_window_seconds: int = 300):
        """
        Correlates a newly synced Event into an Incident based on common actors/assets within a time window.
        
        KNOWN LIMITATION (Deferred v2 item):
        When an event's time window overlaps multiple existing Incidents, it only joins the first 
        Incident it finds. It does NOT merge the underlying Incidents themselves together. True
        incident merging/consolidation will be addressed in a future version.
        KNOWN LIMITATION (Deferred v2 item - Stage 4):
        The risk_worker is currently started via asyncio.create_task in the FastAPI lifespan.
        This is a TEMPORARY local-dev pattern. Before cloud deployment, it must be replaced 
        with a standalone worker process/container with proper crash recovery (heartbeat + 
        handling for jobs orphaned in "running" state after a restart).
        """
        self.session.run(
            q.CORRELATE_INCIDENT,
            event_id=event_id,
            workspace_id=workspace_id,
            time_window_seconds=time_window_seconds
        )
