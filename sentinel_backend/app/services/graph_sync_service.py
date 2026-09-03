from sqlalchemy.orm import Session as DBSession
from neo4j import Session as GraphSession
from app.models.machine_identity import MachineIdentity
from app.models.access_log import AccessLog
from app.models.tenant import Workspace
from app.graph.graph_builder import GraphBuilder
from app.services.ingestion_adapter import IngestionAdapter
import logging

from app.core.events.bus import event_bus
from app.core.events.contracts import GraphEvent
from app.core.events.event_types import ActorClassification, EventCategory, EventSeverity, EventStatus, ResourceClassification


logger = logging.getLogger(__name__)

class GraphSyncService:
    def __init__(self, db: DBSession, graph: GraphSession):
        self.db = db
        self.graph = graph
        self.builder = GraphBuilder(graph)

    def sync_all(self):
        logger.info("Starting graph synchronization...")
        
        # 1. Sync Identities
        identities = self.db.query(MachineIdentity).all()
        for ident in identities:
            self.builder.sync_identity(ident.arn, ident.account_id, ident.identity_type, str(ident.workspace_id))
            
        # 2. Sync Access Logs
        logs = self.db.query(AccessLog).all()
        for log in logs:
            if log.identity_arn == "unknown":
                continue
                
            event_time_str = log.event_time.isoformat()
                
            if log.source_ip:
                self.builder.sync_ip(log.source_ip, str(log.workspace_id))
                self.builder.link_identity_ip(log.identity_arn, log.source_ip, event_time_str, str(log.workspace_id))
                
            if log.resource_arn:
                self.builder.sync_resource(log.resource_arn, str(log.workspace_id))
                self.builder.link_identity_resource(log.identity_arn, log.resource_arn, event_time_str, str(log.workspace_id))
                
            if log.event_name == "AssumeRole" and log.resource_arn:
                self.builder.link_assume_role(log.identity_arn, log.resource_arn, event_time_str, str(log.workspace_id))
                
        logger.info("Graph synchronization complete.")

    def sync_new_events(self, events: list, workspace_id: str) -> dict:
        """
        Synchronizes newly inserted logs or events to the Neo4j graph using the unified ingestion adapter.
        """
        logger.info(f"Syncing {len(events)} new events to Neo4j...")
        
        relationships_created = 0
        nodes_created = 0
        
        for record in events:
            # 1. Normalize the record using IngestionAdapter
            if hasattr(record, "identity_arn"): # It's an AccessLog
                unified_event = IngestionAdapter.from_access_log(record)
                # Ensure AWS distinct graph paths stay exactly as-is for AccessLogs
                if record.identity_arn and record.identity_arn != "unknown":
                    ident = self.db.query(MachineIdentity).filter(MachineIdentity.arn == record.identity_arn, MachineIdentity.workspace_id == workspace_id).first()
                    if ident:
                        self.builder.sync_identity(ident.arn, ident.account_id, ident.identity_type, workspace_id)
                        nodes_created += 1
                        
                    event_time_str = record.event_time.isoformat()
                    
                    if record.source_ip:
                        self.builder.sync_ip_actor(record.source_ip, workspace_id) # Uses IP actor query just in case, but sync_ip works too
                        self.builder.link_identity_ip(record.identity_arn, record.source_ip, event_time_str, workspace_id)
                        relationships_created += 1
                        
                    if record.resource_arn:
                        self.builder.sync_resource(record.resource_arn, workspace_id)
                        self.builder.link_identity_resource(record.identity_arn, record.resource_arn, event_time_str, workspace_id)
                        relationships_created += 1
                        
                    if record.event_name == "AssumeRole" and record.resource_arn:
                        self.builder.link_assume_role(record.identity_arn, record.resource_arn, event_time_str, workspace_id)
                        relationships_created += 1
            else: # It's a CanonicalEvent
                unified_event = IngestionAdapter.from_canonical_event(record)
                
            # 2. Push Unified Event to graph
            if not unified_event:
                continue
                
            # Sync Actor node properly labeled
            if unified_event.actor_type == "Identity":
                # Will be synced by AccessLog logic above if AWS, but just in case
                self.builder.sync_identity(unified_event.actor_id, "unknown", "Unknown", workspace_id)
            elif unified_event.actor_type == "Host":
                self.builder.sync_host_actor(unified_event.actor_id, workspace_id)
            elif unified_event.actor_type == "IPAddress":
                self.builder.sync_ip_actor(unified_event.actor_id, workspace_id)
            nodes_created += 1
                
            # Sync Asset node
            if unified_event.asset_id:
                if unified_event.asset_type == "Resource":
                    self.builder.sync_resource(unified_event.asset_id, workspace_id)
                elif unified_event.asset_type == "Host":
                    self.builder.sync_host_actor(unified_event.asset_id, workspace_id) # Using actor merge sets both, safe fallback
                elif unified_event.asset_type == "IPAddress":
                    self.builder.sync_ip_actor(unified_event.asset_id, workspace_id)
                nodes_created += 1
            
            # Sync Event and Targets
            self.builder.sync_event(
                event_id=unified_event.event_id,
                workspace_id=workspace_id,
                timestamp=unified_event.timestamp,
                source_tool=unified_event.source_tool,
                severity=unified_event.severity,
                mitre_technique=unified_event.mitre_technique,
                actor_id=unified_event.actor_id,
                asset_id=unified_event.asset_id
            )
            nodes_created += 1 # Event node
            relationships_created += 2 # TRIGGERED, TARGETS (max)
            
            # 3. Correlate to Incident
            self.builder.correlate_events_to_incident(
                event_id=unified_event.event_id,
                workspace_id=workspace_id
            )
            relationships_created += 1 # PART_OF

        logger.info("Neo4j sync complete. Nodes affected: %s, Relationships affected: %s", nodes_created, relationships_created)
        
        workspace = self.db.query(Workspace).filter(Workspace.id == workspace_id).first()
        org_id = str(workspace.organization_id) if workspace else "SYSTEM"
        
        event_bus.publish(GraphEvent(
            workspace_id=workspace_id,
            organization_id=org_id,
            actor="GraphSyncEngine",
            actor_type=ActorClassification.INTERNAL_ENGINE,
            module="GraphSync",
            action="GRAPH_BUILD_COMPLETED",
            category=EventCategory.GRAPH,
            severity=EventSeverity.INFO,
            status=EventStatus.SUCCESS,
            resource_type=ResourceClassification.SYSTEM,
            metadata={"nodes_created": nodes_created, "relationships_created": relationships_created}
        ))
        
        return {
            "nodes_created": nodes_created,
            "relationships_created": relationships_created
        }
