import os
import pytest
from neo4j import GraphDatabase

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USER", "neo4j")
NEO4J_PASSWORD = os.getenv("NEO4J_PASSWORD", "12Asdf*#_")
TEST_WORKSPACE = "test-workspace-char"

@pytest.fixture(scope="module")
def graph_session():
    driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASSWORD))
    with driver.session() as session:
        yield session
    driver.close()

@pytest.fixture(scope="module", autouse=True)
def setup_test_data(graph_session):
    # Clean up before
    graph_session.run("MATCH (n {workspace_id: $workspace_id}) DETACH DELETE n", workspace_id=TEST_WORKSPACE)
    
    # Insert Privilege Escalation Baseline (1 ASSUMED_ROLE)
    graph_session.run("""
    MERGE (i1:Identity {arn: 'arn:aws:iam::111122223333:user/test-source', workspace_id: $workspace_id})
    MERGE (i2:Identity {arn: 'arn:aws:iam::111122223333:role/test-target', workspace_id: $workspace_id})
    MERGE (i1)-[:ASSUMED_ROLE]->(i2)
    """, workspace_id=TEST_WORKSPACE)
    
    # Insert Geographic Anomaly Baseline (2 ORIGINATED_FROM)
    graph_session.run("""
    MERGE (i:Identity {arn: 'arn:aws:iam::111122223333:user/geo-test', workspace_id: $workspace_id})
    MERGE (ip1:IPAddress {ip: '192.168.1.100', workspace_id: $workspace_id})
    MERGE (ip2:IPAddress {ip: '10.0.0.99', workspace_id: $workspace_id})
    MERGE (i)-[:ORIGINATED_FROM]->(ip1)
    MERGE (i)-[:ORIGINATED_FROM]->(ip2)
    """, workspace_id=TEST_WORKSPACE)
    
    yield
    
    # Clean up after
    graph_session.run("MATCH (n {workspace_id: $workspace_id}) DETACH DELETE n", workspace_id=TEST_WORKSPACE)

def test_privilege_escalation_baseline(graph_session):
    # Privilege escalation query isolated to test workspace
    query = "MATCH (i:Identity {workspace_id: $workspace_id})-[:ASSUMED_ROLE]->(target) RETURN count(target) as c"
    res = graph_session.run(query, workspace_id=TEST_WORKSPACE)
    c = res.single()["c"]
    assert c == 1, f"Expected 1 ASSUMED_ROLE relations, got {c}"

def test_geographic_anomaly_baseline(graph_session):
    # Geographic anomaly query isolated to test workspace
    query = "MATCH (i:Identity {workspace_id: $workspace_id})-[:ORIGINATED_FROM]->(ip:IPAddress) RETURN count(ip) as c"
    res = graph_session.run(query, workspace_id=TEST_WORKSPACE)
    c = res.single()["c"]
    assert c == 2, f"Expected 2 ORIGINATED_FROM relations, got {c}"
