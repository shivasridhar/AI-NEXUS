import logging
from typing import Dict, Any, List
from neo4j import Session as GraphSession

logger = logging.getLogger(__name__)

class GraphReasoner:
    def __init__(self, graph: GraphSession, max_hops: int = 4, timeout_ms: int = 5000):
        self.graph = graph
        self.max_hops = max_hops
        self.timeout_ms = timeout_ms

    def analyze_identity_context(self, identity_id: str, workspace_id: str) -> Dict[str, Any]:
        """
        Executes read-only cypher queries to gather graph metrics safely.
        Uses limits to prevent query timeouts on massive graphs.
        """
        metrics = {
            "shortest_path_hops": None,
            "connected_components": 0,
            "reachable_critical_assets": 0,
            "cycle_detected": False
        }
        
        try:
            # 1. Reachable Critical Assets — standard Cypher, no APOC required.
            # LIMIT 1 is not applicable here (we need COUNT); path length bound
            # [*1..max_hops] prevents runaway traversals on large graphs.
            query_assets = f"""
            MATCH (i:Identity {{id: $id, workspace_id: $wid}})-[*1..{self.max_hops}]->(a:Resource)
            WHERE a.is_critical = true
            RETURN count(DISTINCT a) AS count
            """
            res_assets = self.graph.run(query_assets, id=identity_id, wid=workspace_id).data()
            if res_assets:
                metrics["reachable_critical_assets"] = res_assets[0].get("count", 0)

            # 2. Cycle Detection — standard Cypher, no APOC required.
            # LIMIT 1 short-circuits after finding the first cycle.
            query_cycles = f"""
            MATCH p=(n)-[*1..{self.max_hops}]->(n)
            WHERE n.id = $id AND n.workspace_id = $wid
            RETURN count(p) > 0 AS has_cycle
            LIMIT 1
            """
            res_cycles = self.graph.run(query_cycles, id=identity_id, wid=workspace_id).data()
            if res_cycles:
                metrics["cycle_detected"] = res_cycles[0].get("has_cycle", False)

        except Exception as e:
            logger.warning("Graph reasoning partial failure (timeout or error): %s", str(e))

        return metrics
