from app.graph.session import neo4j_manager
import logging

logger = logging.getLogger(__name__)

class GraphProjection:
    def get_graph_summary(self, workspace_id: str) -> dict:
        summary = {
            "total_nodes": 0,
            "total_relationships": 0,
            "attack_paths": 0,
            "most_connected_identity": None
        }
        
        try:
            session = neo4j_manager.get_session()
            if not session:
                return summary
                
            # Nodes
            result = session.run("""
                MATCH (n) WHERE n.workspace_id = $workspace_id
                RETURN count(n) as count
            """, workspace_id=workspace_id)
            record = result.single()
            summary["total_nodes"] = record["count"] if record else 0
            
            # Relationships
            result = session.run("""
                MATCH (n)-[r]->(m) WHERE n.workspace_id = $workspace_id
                RETURN count(r) as count
            """, workspace_id=workspace_id)
            record = result.single()
            summary["total_relationships"] = record["count"] if record else 0
            
            # Attack Paths (Simulated count for now based on vulnerabilities)
            result = session.run("""
                MATCH p=(n:Identity)-[*1..3]->(m:Vulnerability) WHERE n.workspace_id = $workspace_id
                RETURN count(p) as count
            """, workspace_id=workspace_id)
            record = result.single()
            summary["attack_paths"] = record["count"] if record else 0
            
            # Most connected
            result = session.run("""
                MATCH (n:Identity)-[r]->() WHERE n.workspace_id = $workspace_id
                RETURN n.name as name, count(r) as count
                ORDER BY count DESC LIMIT 1
            """, workspace_id=workspace_id)
            record = result.single()
            if record:
                summary["most_connected_identity"] = record["name"]
                
            session.close()
        except Exception as e:
            logger.error("GraphProjection Error (Neo4j might be unavailable): %s", e)
            summary["graph_unavailable"] = True
            
        return summary
