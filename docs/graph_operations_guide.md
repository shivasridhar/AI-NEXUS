# SentinelAI Graph Operations Guide (Neo4j)

## Overview

SentinelAI uses **Neo4j 5.12** as its graph database for modeling relationships between cloud identities, resources, IP addresses, and security events. The graph enables attack path analysis, incident correlation, and blast radius assessment.

## Architecture

```
FastAPI App
  |
  +-- Neo4jSessionManager (singleton)
  |     |-- connect() -> GraphDatabase.driver()
  |     |-- get_session() -> driver.session(database=...)
  |     |-- close() -> driver.close()
  |
  +-- GraphBuilder (per-request)
  |     |-- sync_identity()
  |     |-- sync_resource()
  |     |-- sync_ip()
  |     |-- link_identity_resource()
  |     |-- link_identity_ip()
  |     |-- link_assume_role()
  |     |-- sync_event()
  |     |-- correlate_events_to_incident()
  |
  +-- neo4j_queries.py (Cypher query definitions)
```

## Connection Management

**File**: `sentinel_backend/app/graph/session.py`

```python
neo4j_manager = Neo4jSessionManager()  # Singleton

# Startup (in app lifespan):
neo4j_manager.connect()  # Best-effort: app starts even if Neo4j is down

# Dependency injection:
def get_neo4j_session() -> Generator:
    session = neo4j_manager.get_session()
    yield session
    session.close()
```

**Configuration**:
| Variable | Default | Description |
|----------|---------|-------------|
| `NEO4J_URI` | `bolt://localhost:7687` | Neo4j connection URI |
| `NEO4J_USER` | `neo4j` | Username |
| `NEO4J_PASSWORD` | (required) | Password |
| `NEO4J_DATABASE` | `neo4j` | Database name |

---

## Graph Schema

### Node Types

| Label | Properties | Description |
|-------|-----------|-------------|
| `Identity` + `Actor` | `arn`, `account_id`, `type`, `workspace_id` | Cloud IAM identities |
| `Resource` | `arn`, `workspace_id` | Cloud resources (S3, EC2, etc.) |
| `IPAddress` + `Actor` | `ip`, `workspace_id` | Source IP addresses |
| `Host` + `Actor` | `hostname`, `workspace_id` | Host machines |
| `Event` | `id`, `workspace_id`, `timestamp`, `source_tool`, `severity`, `mitre_technique` | Security events |
| `Incident` | `id`, `workspace_id`, `created_at` | Correlated incident groups |

### Relationship Types

| Relationship | From | To | Properties |
|-------------|------|-----|-----------|
| `ACCESSED_RESOURCE` | Identity | Resource | `first_accessed`, `last_accessed`, `count` |
| `ORIGINATED_FROM` | Identity | IPAddress | `first_seen`, `last_seen`, `count` |
| `ASSUMED_ROLE` | Identity | Identity | `first_assumed`, `last_assumed`, `count` |
| `TRIGGERED` | Actor | Event | (none) |
| `TARGETS` | Event | Resource/Host/IP | (none) |
| `PART_OF` | Event | Incident | (none) |

### Graph Visual

```
[IPAddress] <--ORIGINATED_FROM-- [Identity/Actor]
                                      |
                              ACCESSED_RESOURCE
                                      |
                                      v
                                 [Resource]

[Identity] --ASSUMED_ROLE--> [Identity]

[Actor] --TRIGGERED--> [Event] --TARGETS--> [Resource]
                          |
                       PART_OF
                          |
                          v
                      [Incident]
```

---

## Cypher Queries

### MERGE_IDENTITY
Creates or updates an identity node with the Actor label:
```cypher
MERGE (i:Identity {arn: $arn, workspace_id: $workspace_id})
SET i.account_id = $account_id, i.type = $identity_type, i:Actor
```

### MERGE_RESOURCE
Creates or updates a resource node:
```cypher
MERGE (r:Resource {arn: $arn, workspace_id: $workspace_id})
```

### MERGE_IP
Creates or updates an IP address node:
```cypher
MERGE (ip:IPAddress {ip: $ip, workspace_id: $workspace_id})
```

### LINK_IDENTITY_RESOURCE
Links an identity to a resource it accessed, tracking frequency:
```cypher
MATCH (i:Identity {arn: $identity_arn, workspace_id: $workspace_id})
MATCH (r:Resource {arn: $resource_arn, workspace_id: $workspace_id})
MERGE (i)-[rel:ACCESSED_RESOURCE]->(r)
ON CREATE SET rel.first_accessed = $event_time, rel.count = 1
ON MATCH SET rel.last_accessed = $event_time, rel.count = rel.count + 1
```

### LINK_ASSUME_ROLE
Tracks role assumption chains:
```cypher
MATCH (i:Identity {arn: $source_arn, workspace_id: $workspace_id})
MATCH (target {arn: $target_arn, workspace_id: $workspace_id})
SET target:Identity
MERGE (i)-[rel:ASSUMED_ROLE]->(target)
ON CREATE SET rel.first_assumed = $event_time, rel.count = 1
ON MATCH SET rel.last_assumed = $event_time, rel.count = rel.count + 1
```

### GET_ATTACK_PATH
Traverses up to 3 hops from a starting identity:
```cypher
MATCH path = (start:Identity {arn: $arn, workspace_id: $workspace_id})-[*1..3]->(target)
RETURN path
```

### CREATE_EVENT
Creates an event node and links it to its triggering actor and target asset:
```cypher
MATCH (actor {workspace_id: $workspace_id})
WHERE (actor:Identity AND actor.arn = $actor_id) 
   OR (actor:Host AND actor.hostname = $actor_id) 
   OR (actor:IPAddress AND actor.ip = $actor_id)

OPTIONAL MATCH (asset {workspace_id: $workspace_id})
WHERE (asset:Resource AND asset.arn = $asset_id) 
   OR (asset:IPAddress AND asset.ip = $asset_id) 
   OR (asset:Host AND asset.hostname = $asset_id)

CREATE (e:Event { ... })
MERGE (actor)-[:TRIGGERED]->(e)
WITH e, asset WHERE asset IS NOT NULL
MERGE (e)-[:TARGETS]->(asset)
```

### CORRELATE_INCIDENT
Automatically groups events into incidents based on shared actors/assets within a time window:
```cypher
MATCH (e:Event {id: $event_id, workspace_id: $workspace_id})
// Find events for same actor/asset within time window
OPTIONAL MATCH (past_e:Event {workspace_id: $workspace_id})
WHERE past_e.id <> e.id 
  AND duration.inSeconds(...) <= $time_window_seconds
  AND (shared actor OR shared target)
// Join existing incident or create new one
```

**Default time window**: 300 seconds (5 minutes)

**Known limitation**: When an event overlaps multiple incidents, it joins only the first one found. Incident merging is deferred to v2.

---

## GraphBuilder API

**File**: `sentinel_backend/app/graph/graph_builder.py`

| Method | Description |
|--------|-------------|
| `sync_identity(arn, account_id, identity_type, workspace_id)` | Create/update identity node |
| `sync_resource(arn, workspace_id)` | Create/update resource node |
| `sync_ip(ip, workspace_id)` | Create/update IP node |
| `link_identity_resource(identity_arn, resource_arn, event_time, workspace_id)` | Track resource access |
| `link_identity_ip(identity_arn, source_ip, event_time, workspace_id)` | Track IP origins |
| `link_assume_role(source_arn, target_arn, event_time, workspace_id)` | Track role chains |
| `sync_host_actor(hostname, workspace_id)` | Create host actor node |
| `sync_ip_actor(ip, workspace_id)` | Create IP actor node |
| `sync_event(event_id, workspace_id, ...)` | Create event and link to actor/target |
| `correlate_events_to_incident(event_id, workspace_id, time_window)` | Auto-correlate into incidents |

## Multi-Tenancy in Graph

All nodes include a `workspace_id` property. All queries filter by `workspace_id` to ensure tenant isolation at the graph layer.

## Docker Setup

```yaml
neo4j:
  image: neo4j:5.12.0
  ports:
    - "7474:7474"  # HTTP browser interface
    - "7687:7687"  # Bolt protocol
  volumes:
    - neo4j_data:/data
```

Access Neo4j Browser at `http://localhost:7474` for visual graph exploration.
