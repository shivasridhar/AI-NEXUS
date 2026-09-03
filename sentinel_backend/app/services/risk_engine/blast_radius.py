"""
Blast Radius Analyzer (Stage 4)

Calculates the blast radius of a compromised identity by traversing the
knowledge graph to determine how many assets, services, and downstream
identities could be affected.
"""

import logging
from typing import Dict, List, Optional
from neo4j import Session as GraphSession
from sqlalchemy.orm import Session as DBSession

logger = logging.getLogger(__name__)


# Cypher query to find all reachable nodes from an identity within N hops
BLAST_RADIUS_QUERY = """
MATCH (start:Identity {arn: $arn, workspace_id: $workspace_id})
OPTIONAL MATCH path = (start)-[*1..4]->(target {workspace_id: $workspace_id})
WHERE target <> start
WITH DISTINCT target, length(path) AS distance
RETURN
    labels(target) AS node_labels,
    target.arn AS arn,
    target.name AS name,
    target.ip AS ip,
    target.hostname AS hostname,
    distance
ORDER BY distance ASC
"""

# Query to count relationships by type
RELATIONSHIP_COUNT_QUERY = """
MATCH (start:Identity {arn: $arn, workspace_id: $workspace_id})-[r*1..4]->(target {workspace_id: $workspace_id})
WHERE target <> start
UNWIND r AS rel
RETURN type(rel) AS rel_type, count(DISTINCT rel) AS count
"""


class BlastRadiusResult:
    """Holds the calculated blast radius metrics."""

    def __init__(self):
        self.total_reachable_nodes: int = 0
        self.resources_affected: int = 0
        self.identities_affected: int = 0
        self.ip_addresses_affected: int = 0
        self.hosts_affected: int = 0
        self.max_depth: int = 0
        self.affected_assets: List[Dict] = []
        self.relationship_summary: Dict[str, int] = {}
        self.blast_score: int = 0  # 0-100

    def to_dict(self) -> Dict:
        return {
            "total_reachable_nodes": self.total_reachable_nodes,
            "resources_affected": self.resources_affected,
            "identities_affected": self.identities_affected,
            "ip_addresses_affected": self.ip_addresses_affected,
            "hosts_affected": self.hosts_affected,
            "max_depth": self.max_depth,
            "blast_score": self.blast_score,
            "affected_assets": self.affected_assets[:20],  # Cap for payload size
            "relationship_summary": self.relationship_summary,
        }


class BlastRadiusAnalyzer:
    """
    Analyzes the blast radius of a compromised identity using graph traversal.
    The blast radius measures how far an attacker could pivot from a compromised identity.
    """

    def __init__(self, graph: GraphSession):
        self.graph = graph

    def analyze(self, arn: str, workspace_id: str) -> BlastRadiusResult:
        """
        Performs blast radius analysis for a given identity ARN.
        Returns a BlastRadiusResult with metrics.
        """
        result = BlastRadiusResult()

        try:
            # Phase 1: Find all reachable nodes
            records = self.graph.run(
                BLAST_RADIUS_QUERY,
                arn=arn,
                workspace_id=workspace_id
            ).data()

            for record in records:
                labels = record.get("node_labels", [])
                distance = record.get("distance", 0)
                node_id = (
                    record.get("arn")
                    or record.get("name")
                    or record.get("ip")
                    or record.get("hostname")
                    or "unknown"
                )

                result.total_reachable_nodes += 1
                result.max_depth = max(result.max_depth, distance)

                asset_entry = {
                    "id": node_id,
                    "type": labels[0] if labels else "Unknown",
                    "distance": distance,
                }
                result.affected_assets.append(asset_entry)

                # Classify by node type
                if "Resource" in labels:
                    result.resources_affected += 1
                elif "Identity" in labels:
                    result.identities_affected += 1
                elif "IPAddress" in labels:
                    result.ip_addresses_affected += 1
                elif "Host" in labels:
                    result.hosts_affected += 1

            # Phase 2: Relationship summary
            rel_records = self.graph.run(
                RELATIONSHIP_COUNT_QUERY,
                arn=arn,
                workspace_id=workspace_id
            ).data()

            for record in rel_records:
                rel_type = record.get("rel_type", "UNKNOWN")
                count = record.get("count", 0)
                result.relationship_summary[rel_type] = count

            # Phase 3: Calculate blast score (0-100)
            result.blast_score = self._calculate_blast_score(result)

        except Exception as e:
            logger.error("Blast radius analysis failed for %s: %s", arn, e)
            # Return empty result rather than crashing

        return result

    def _calculate_blast_score(self, result: BlastRadiusResult) -> int:
        """
        Calculates a normalized blast score from 0-100 based on:
        - Number of reachable nodes (primary factor)
        - Depth of traversal (deeper = worse)
        - Number of identities affected (lateral movement potential)
        """
        score = 0.0

        # Reachable nodes: each node adds diminishing points
        node_score = min(result.total_reachable_nodes * 5, 40)
        score += node_score

        # Depth penalty: deeper paths = more serious
        depth_score = min(result.max_depth * 10, 20)
        score += depth_score

        # Lateral movement: other identities reachable
        lateral_score = min(result.identities_affected * 8, 25)
        score += lateral_score

        # Resource breadth: more resources = larger blast radius
        resource_score = min(result.resources_affected * 3, 15)
        score += resource_score

        return min(max(int(score), 0), 100)
