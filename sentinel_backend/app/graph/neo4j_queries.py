MERGE_IDENTITY = """
MERGE (i:Identity {arn: $arn, workspace_id: $workspace_id})
SET i.account_id = $account_id,
    i.type = $identity_type,
    i:Actor
"""

MERGE_RESOURCE = """
MERGE (r:Resource {arn: $arn, workspace_id: $workspace_id})
"""

MERGE_IP = """
MERGE (ip:IPAddress {ip: $ip, workspace_id: $workspace_id})
"""

LINK_IDENTITY_RESOURCE = """
MATCH (i:Identity {arn: $identity_arn, workspace_id: $workspace_id})
MATCH (r:Resource {arn: $resource_arn, workspace_id: $workspace_id})
MERGE (i)-[rel:ACCESSED_RESOURCE]->(r)
ON CREATE SET rel.first_accessed = $event_time, rel.count = 1
ON MATCH SET rel.last_accessed = $event_time, rel.count = rel.count + 1
"""

LINK_IDENTITY_IP = """
MATCH (i:Identity {arn: $identity_arn, workspace_id: $workspace_id})
MATCH (ip:IPAddress {ip: $source_ip, workspace_id: $workspace_id})
MERGE (i)-[rel:ORIGINATED_FROM]->(ip)
ON CREATE SET rel.first_seen = $event_time, rel.count = 1
ON MATCH SET rel.last_seen = $event_time, rel.count = rel.count + 1
"""

LINK_ASSUME_ROLE = """
MATCH (i:Identity {arn: $source_arn, workspace_id: $workspace_id})
MATCH (target {arn: $target_arn, workspace_id: $workspace_id})
SET target:Identity
MERGE (i)-[rel:ASSUMED_ROLE]->(target)
ON CREATE SET rel.first_assumed = $event_time, rel.count = 1
ON MATCH SET rel.last_assumed = $event_time, rel.count = rel.count + 1
"""

GET_ATTACK_PATH = """
MATCH path = (start:Identity {arn: $arn, workspace_id: $workspace_id})-[*1..3]->(target)
RETURN path
"""

MERGE_HOST_ACTOR = """
MERGE (h:Host {hostname: $hostname, workspace_id: $workspace_id})
SET h:Actor
"""

MERGE_IP_ACTOR = """
MERGE (ip:IPAddress {ip: $ip, workspace_id: $workspace_id})
SET ip:Actor
"""

CREATE_EVENT = """
MATCH (actor {workspace_id: $workspace_id})
WHERE (actor:Identity AND actor.arn = $actor_id) OR (actor:Host AND actor.hostname = $actor_id) OR (actor:IPAddress AND actor.ip = $actor_id)

OPTIONAL MATCH (asset {workspace_id: $workspace_id})
WHERE (asset:Resource AND asset.arn = $asset_id) OR (asset:IPAddress AND asset.ip = $asset_id) OR (asset:Host AND asset.hostname = $asset_id)

CREATE (e:Event {
    id: $event_id,
    workspace_id: $workspace_id,
    timestamp: $timestamp,
    source_tool: $source_tool,
    severity: $severity,
    mitre_technique: $mitre_technique
})
MERGE (actor)-[:TRIGGERED]->(e)
WITH e, asset
WHERE asset IS NOT NULL
MERGE (e)-[:TARGETS]->(asset)
"""

CORRELATE_INCIDENT = """
MATCH (e:Event {id: $event_id, workspace_id: $workspace_id})
// Find existing events for same actor or asset within 5 mins
OPTIONAL MATCH (past_e:Event {workspace_id: $workspace_id})
WHERE past_e.id <> e.id 
  AND duration.inSeconds(datetime(past_e.timestamp), datetime(e.timestamp)).seconds >= 0
  AND duration.inSeconds(datetime(past_e.timestamp), datetime(e.timestamp)).seconds <= $time_window_seconds
  AND (
    (past_e)<-[:TRIGGERED]-()-[:TRIGGERED]->(e) OR
    (past_e)-[:TARGETS]->()<-[:TARGETS]-(e) OR
    (past_e)<-[:TRIGGERED]-()<-[:TARGETS]-(e) OR
    (past_e)-[:TARGETS]->()-[:TRIGGERED]->(e)
  )
WITH e, collect(past_e) as past_events

// Get existing incidents
OPTIONAL MATCH (pe)-[:PART_OF]->(existing_inc:Incident)
WHERE pe IN past_events
WITH e, collect(DISTINCT existing_inc) as existing_incs

// If no existing incident, create one. If there are, merge into the first one (simple heuristic)
FOREACH (ignoreMe IN CASE WHEN size(existing_incs) = 0 THEN [1] ELSE [] END |
    CREATE (new_inc:Incident {
        id: randomUUID(),
        workspace_id: e.workspace_id,
        created_at: e.timestamp
    })
    MERGE (e)-[:PART_OF]->(new_inc)
)
FOREACH (inc IN CASE WHEN size(existing_incs) > 0 THEN [existing_incs[0]] ELSE [] END |
    MERGE (e)-[:PART_OF]->(inc)
)
"""
