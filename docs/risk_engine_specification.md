# SentinelAI Risk Engine Specification

## Overview

The Risk Engine computes contextual risk scores (0-100) for cloud machine identities by analyzing access patterns, generating security findings, mapping to MITRE ATT&CK techniques, and calculating blast radius scores. Findings are linked to identities via the `machine_identities` table and processed by a background risk worker.

## Architecture

```
Ingestion Pipeline
  |
  v
Access Logs (PostgreSQL)  --->  Risk Worker (background task)
  |                                    |
  v                                    v
Neo4j Graph Builder           Risk Score Calculation
  |                                    |
  v                                    v
Graph Evidence Engine         Risk Findings Generation
  |                                    |
  v                                    v
AI Analyst Service            MITRE ATT&CK Mapping
```

## Risk Score Model

### Score Range

| Score | Severity | Description |
|-------|----------|-------------|
| 0-25 | Low | Normal activity, minimal risk |
| 26-50 | Medium | Unusual patterns requiring attention |
| 51-75 | High | Significant risk indicators detected |
| 76-100 | Critical | Immediate investigation required |

**Database constraint**: `CHECK score >= 0 AND score <= 100`
**Severity constraint**: `CHECK severity IN ('Low', 'Medium', 'High', 'Critical')`

### Score Storage (`risk_scores` table)

```python
class RiskScore:
    id: UUID
    workspace_id: UUID          # Tenant isolation
    identity_id: UUID           # FK -> machine_identities
    score: int                  # 0-100
    severity: str               # Low/Medium/High/Critical
    reasons: List[str]          # Array of risk reasons
    legacy_comparison_score: int # Previous score for trend analysis
    risk_evidence: dict         # JSONB - full evidence payload
    calculated_at: datetime     # When score was computed
```

## Risk Findings

### Finding Model

Each finding represents a discrete security observation:

```python
class RiskFinding:
    id: UUID
    workspace_id: UUID
    identity_id: UUID           # FK -> machine_identities
    finding_type: str           # e.g., "privilege_escalation", "unusual_access"
    severity: str               # Low/Medium/High/Critical
    description: str            # Human-readable description
    event_reference: str        # Link to source event
    mitre_technique: str        # e.g., "T1078" (MITRE ATT&CK ID)
    mitre_tactic: str           # e.g., "Persistence"
    blast_radius_score: int     # Impact radius (nullable)
    compliance_refs: dict       # JSONB - compliance framework references
    created_at: datetime
```

### Finding Severity Classification

| Severity | Criteria |
|----------|----------|
| Critical | Privilege escalation, credential exposure, data exfiltration indicators |
| High | Unusual role assumptions, access to sensitive resources, new IP origins |
| Medium | Pattern deviations, increased activity volume, new resource access |
| Low | Normal operational patterns, routine access |

## MITRE ATT&CK Mapping

Findings include MITRE ATT&CK technique and tactic references:

- `mitre_technique`: ATT&CK technique ID (e.g., `T1078`, `T1548`)
- `mitre_tactic`: ATT&CK tactic name (e.g., `Persistence`, `Privilege Escalation`)

The MITRE endpoint (`/api/v1/mitre/*`) provides access to mapped techniques and coverage data.

## Attack Path Analysis

Attack paths are computed via Neo4j graph traversal:

```cypher
MATCH path = (start:Identity {arn: $arn, workspace_id: $workspace_id})-[*1..3]->(target)
RETURN path
```

This reveals:
- **Lateral movement**: Identity -> ASSUMED_ROLE -> Identity -> ACCESSED_RESOURCE -> Resource
- **Resource exposure**: Identity -> ACCESSED_RESOURCE -> Resource
- **IP origin tracking**: Identity -> ORIGINATED_FROM -> IPAddress

### Blast Radius Score

The `blast_radius_score` on findings estimates the downstream impact based on:
- Number of resources accessible from the compromised identity
- Depth of role assumption chains
- Criticality of accessed resources (from `criticality_configs`)

## Incident Correlation

The graph engine auto-correlates events into incidents:

1. A new event is synced to the graph
2. Past events within a 5-minute window sharing the same actor or target are found
3. Events are grouped into an `Incident` node via `PART_OF` relationships
4. If no existing incident matches, a new one is created

## Asset Criticality Configuration

Administrators can configure asset criticality via the `criticality_configs` table:

```python
class CriticalityConfig:
    workspace_id: UUID
    asset_id: str       # ARN or identifier
    criticality: int    # Criticality weight
```

This allows weighting risk scores based on business-critical asset importance.

## Risk Worker

**File**: `sentinel_backend/app/workers/risk_worker.py`

The risk worker runs as an `asyncio.create_task` during application lifespan. It processes ingestion jobs and generates risk findings.

**Known debt**: This is a temporary local-dev pattern. Production deployment should use a standalone worker process with heartbeat monitoring and orphaned job recovery.

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/v1/findings/` | GET | List risk findings (workspace-scoped) |
| `/api/v1/findings/{id}` | GET | Get specific finding details |
| `/api/v1/mitre/` | GET | MITRE ATT&CK mapping data |
| `/api/v1/identities/` | GET | List machine identities with risk scores |
| `/api/v1/ai/investigate` | POST | Trigger AI investigation for an identity |

## Evidence Collection

The evidence collector (`app/services/ai/evidence_collector.py`) gathers:
- Identity metadata from PostgreSQL
- Risk scores and findings
- Access log patterns
- Attack paths from Neo4j graph
- Graph relationships (role assumptions, resource access, IP origins)

This evidence bundle is then passed to the AI Analyst Service for investigation.
