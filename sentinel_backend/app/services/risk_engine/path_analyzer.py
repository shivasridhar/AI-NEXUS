from neo4j import Session as GraphSession
from sqlalchemy.orm import Session as DBSession
from app.models.criticality_config import CriticalityConfig
from app.schemas.risk_evidence import AttackPath
import logging

logger = logging.getLogger(__name__)

class PathAnalyzer:
    def __init__(self, db: DBSession, graph: GraphSession):
        self.db = db
        self.graph = graph

    def find_attack_paths(self, arn: str, workspace_id: str) -> list[AttackPath]:
        # Cypher query to find paths from the identity up to 3 hops
        query = """
        MATCH path = (i:Identity {arn: $arn, workspace_id: $workspace_id})-[*1..3]->(target {workspace_id: $workspace_id})
        RETURN nodes(path) AS path_nodes
        """
        
        try:
            results = self.graph.run(query, arn=arn, workspace_id=workspace_id).data()
        except Exception as e:
            logger.error(f"Error executing Cypher query: {e}")
            return []
            
        attack_paths = []
        for row in results:
            path_nodes = row.get("path_nodes", [])
            if not path_nodes:
                continue
                
            # Extract ARN or name of the nodes in the path
            node_ids = []
            target_asset_id = None
            for node in path_nodes:
                # Some nodes might use 'arn', some might use 'name' or 'id'
                node_id = node.get("arn") or node.get("id") or node.get("name") or "unknown"
                node_ids.append(node_id)
                target_asset_id = node_id # Last one will be the target
                
            # Fetch criticality from DB
            criticality = None
            if target_asset_id and target_asset_id != "unknown":
                config = self.db.query(CriticalityConfig).filter(
                    CriticalityConfig.workspace_id == workspace_id,
                    CriticalityConfig.asset_id == target_asset_id
                ).first()
                if config and config.criticality is not None:
                    criticality = config.criticality
                    
            if criticality is None:
                # Fallback to depth/privilege weights: deeper paths or certain targets might imply higher criticality
                # A simple heuristic: 10 points minus 2 for every hop
                criticality = max(1, 10 - len(path_nodes) * 2)

            attack_paths.append(AttackPath(
                path_nodes=node_ids,
                criticality=criticality
            ))
            
        return attack_paths
