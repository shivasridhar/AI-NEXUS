# SentinelAI Database Schema & Relationships

## Overview

SentinelAI uses **PostgreSQL 15** as its primary relational database, managed via **SQLAlchemy ORM** with **Alembic** for migrations. The schema follows a multi-tenant architecture where most tables include a `workspace_id` foreign key for data isolation.

## Architecture

- **ORM**: SQLAlchemy (declarative base with auto-generated table names)
- **Migrations**: Alembic (18 migration versions)
- **Connection**: `pool_pre_ping=True` for connection health checks
- **Session**: `autocommit=False`, `autoflush=False`

---

## Entity Relationship Diagram (ASCII)

```
organizations (1)
  |
  |--- (1:N) ---> users
  |--- (1:N) ---> workspaces (1)
                    |
                    |--- (1:N) ---> cloud_accounts
                    |--- (1:N) ---> access_logs
                    |--- (1:N) ---> canonical_events
                    |--- (1:N) ---> machine_identities (1)
                    |                  |
                    |                  |--- (1:N) ---> risk_scores
                    |                  |--- (1:N) ---> risk_findings
                    |
                    |--- (1:N) ---> ingestion_jobs
                    |--- (1:N) ---> integrations
                    |--- (1:N) ---> notifications
                    |--- (1:N) ---> audit_logs
                    |--- (1:N) ---> reports (1)
                    |                  |--- (1:N) ---> report_history
                    |--- (1:N) ---> scheduled_reports
                    |--- (1:N) ---> criticality_configs
```

---

## Table Definitions

### 1. `organizations`

Tenant root entity. Each organization is an isolated tenant.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, indexed |
| `name` | VARCHAR(255) | NOT NULL |
| `slug` | VARCHAR(100) | UNIQUE, indexed, NOT NULL |
| `is_active` | BOOLEAN | DEFAULT true |
| `created_at` | TIMESTAMPTZ | server default now() |
| `updated_at` | TIMESTAMPTZ | server default now(), auto-update |

**Relationships**: `users` (1:N), `workspaces` (1:N)

---

### 2. `users`

User accounts within an organization.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, indexed |
| `organization_id` | UUID | FK -> organizations.id, NOT NULL |
| `full_name` | VARCHAR(255) | NOT NULL |
| `email` | VARCHAR(255) | UNIQUE, indexed, NOT NULL |
| `password_hash` | VARCHAR(255) | NOT NULL |
| `google_id` | VARCHAR(255) | UNIQUE, indexed, nullable |
| `provider` | VARCHAR(50) | DEFAULT "LOCAL" |
| `profile_picture` | VARCHAR(1024) | nullable |
| `role` | VARCHAR(50) | DEFAULT "user" |
| `is_active` | BOOLEAN | DEFAULT true |
| `created_at` | TIMESTAMPTZ | server default now() |
| `updated_at` | TIMESTAMPTZ | server default now(), auto-update |

**Roles**: `admin`, `analyst`, `viewer`, `user`

---

### 3. `workspaces`

Logical environment within an organization (e.g., Production, Staging).

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, indexed |
| `organization_id` | UUID | FK -> organizations.id, NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `environment` | VARCHAR(50) | DEFAULT "Production" |
| `created_at` | TIMESTAMPTZ | server default now() |

**Relationships**: `cloud_accounts` (1:N, cascade delete)

---

### 4. `cloud_accounts`

Connected cloud provider accounts.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, indexed |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), NOT NULL |
| `provider` | VARCHAR(50) | NOT NULL |
| `name` | VARCHAR(100) | NOT NULL |
| `status` | VARCHAR(50) | DEFAULT "Connected" |
| `created_at` | TIMESTAMPTZ | server default now() |

---

### 5. `access_logs`

Raw CloudTrail/cloud access events.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `event_id` | VARCHAR(255) | indexed |
| `event_time` | TIMESTAMPTZ | indexed |
| `event_name` | VARCHAR(255) | indexed |
| `event_source` | VARCHAR(255) | indexed |
| `aws_region` | VARCHAR(50) | |
| `source_ip` | VARCHAR(50) | nullable |
| `identity_arn` | VARCHAR(512) | indexed |
| `resource_arn` | VARCHAR(512) | nullable, indexed |
| `account_id` | VARCHAR(12) | |
| `raw_event_json` | JSONB | |
| `created_at` | TIMESTAMPTZ | server default now() |

**Indexes**: `idx_access_log_time_arn` (event_time, identity_arn)
**Constraints**: `uq_event_workspace` UNIQUE(event_id, workspace_id)

---

### 6. `canonical_events`

Normalized security events from any source tool.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `source_tool` | VARCHAR(100) | indexed (e.g., wazuh, suricata, openvas) |
| `event_type` | VARCHAR(100) | indexed |
| `severity_raw` | VARCHAR(50) | nullable |
| `severity_normalized` | INTEGER | nullable (0-100 scale) |
| `timestamp_utc` | TIMESTAMPTZ | indexed |
| `actor_identifier` | VARCHAR(512) | nullable, indexed |
| `asset_identifier` | VARCHAR(512) | nullable, indexed |
| `raw_event_json` | JSONB | |
| `linked_access_log_id` | UUID | nullable, indexed |
| `created_at` | TIMESTAMPTZ | server default now() |

**Indexes**: `idx_canonical_event_time_actor` (timestamp_utc, actor_identifier)

---

### 7. `machine_identities`

Discovered cloud identities (IAM roles, users, services).

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `arn` | VARCHAR(512) | indexed |
| `identity_type` | VARCHAR(50) | CHECK: AssumedRole, AWSService, IAMUser |
| `account_id` | VARCHAR(12) | indexed |
| `first_seen` | TIMESTAMPTZ | nullable |
| `last_seen` | TIMESTAMPTZ | nullable |
| `total_events` | BIGINT | DEFAULT 0 |
| `created_at` | TIMESTAMPTZ | server default now() |

**Constraints**: `uq_arn_workspace` UNIQUE(arn, workspace_id)
**Relationships**: `risk_scores` (1:N, cascade delete), `risk_findings` (1:N, cascade delete)

---

### 8. `risk_scores`

Computed risk scores per identity.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `identity_id` | UUID | FK -> machine_identities.id (CASCADE), indexed |
| `score` | INTEGER | CHECK: 0-100 |
| `severity` | VARCHAR(50) | CHECK: Low, Medium, High, Critical; indexed |
| `reasons` | STRING[] | PostgreSQL ARRAY |
| `legacy_comparison_score` | INTEGER | nullable |
| `risk_evidence` | JSONB | nullable |
| `calculated_at` | TIMESTAMPTZ | default now() |

---

### 9. `risk_findings`

Individual security findings linked to identities.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `identity_id` | UUID | FK -> machine_identities.id (CASCADE), indexed |
| `finding_type` | VARCHAR(100) | indexed |
| `severity` | VARCHAR(50) | CHECK: Low, Medium, High, Critical; indexed |
| `description` | TEXT | |
| `event_reference` | VARCHAR(255) | nullable |
| `mitre_technique` | VARCHAR(20) | nullable, indexed |
| `mitre_tactic` | VARCHAR(50) | nullable |
| `blast_radius_score` | INTEGER | nullable |
| `compliance_refs` | JSONB | nullable |
| `created_at` | TIMESTAMPTZ | server default now() |

---

### 10. `ingestion_jobs`

Tracks data ingestion job status.

| Column | Type | Constraints |
|--------|------|-------------|
| `job_id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `s3_bucket_name` | VARCHAR(255) | NOT NULL |
| `status` | VARCHAR(50) | CHECK: pending, running, completed, failed |
| `events_processed` | BIGINT | DEFAULT 0 |
| `started_at` | TIMESTAMPTZ | server default now() |
| `completed_at` | TIMESTAMPTZ | nullable |
| `error_message` | VARCHAR(1024) | nullable |
| `risk_findings_generated` | BIGINT | DEFAULT 0 |

---

### 11. `integrations`

External provider integrations with encrypted credentials.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK, indexed |
| `workspace_id` | UUID | FK -> workspaces.id, indexed |
| `provider` | VARCHAR | indexed (e.g., 'aws') |
| `config` | JSON | DEFAULT {} |
| `encrypted_credentials` | VARCHAR | nullable |
| `status` | VARCHAR | DEFAULT "configured" |
| `last_sync_time` | TIMESTAMPTZ | nullable |
| `events_retrieved` | INTEGER | DEFAULT 0 |
| `error_message` | VARCHAR | nullable |
| `created_at` | TIMESTAMPTZ | |
| `updated_at` | TIMESTAMPTZ | auto-update |

---

### 12. `audit_logs`

Enterprise audit trail for all system actions.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `event_id` | VARCHAR(255) | UNIQUE, indexed |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE) |
| `organization_id` | UUID | FK -> organizations.id (CASCADE) |
| `timestamp` | TIMESTAMPTZ | indexed |
| `actor` | VARCHAR(255) | indexed |
| `actor_type` | VARCHAR(50) | |
| `module` | VARCHAR(100) | |
| `action` | VARCHAR(255) | indexed |
| `category` | VARCHAR(100) | indexed |
| `severity` | VARCHAR(50) | indexed |
| `status` | VARCHAR(50) | indexed |
| `resource_type` | VARCHAR(100) | |
| `resource_id` | VARCHAR(255) | nullable |
| `metadata_json` | JSON | nullable |
| `correlation_id` | VARCHAR(255) | nullable, indexed |
| `parent_event_id` | VARCHAR(255) | nullable |
| `root_event_id` | VARCHAR(255) | nullable |
| `duration_ms` | INTEGER | nullable |

**Indexes**: `ix_audit_logs_workspace_timestamp`, `ix_audit_logs_workspace_category`

---

### 13. `notifications`

User-facing notifications.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `type` | VARCHAR | NOT NULL (e.g., "CRITICAL", "PATH") |
| `title` | VARCHAR | NOT NULL |
| `description` | VARCHAR | NOT NULL |
| `is_read` | BOOLEAN | DEFAULT false |
| `created_at` | TIMESTAMPTZ | |

**Indexes**: `ix_notifications_workspace_created` (workspace_id, created_at)

---

### 14. `reports`

Generated security reports.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE) |
| `organization_id` | UUID | FK -> organizations.id (CASCADE) |
| `name` | VARCHAR(255) | NOT NULL |
| `type` | VARCHAR(100) | NOT NULL |
| `status` | VARCHAR(50) | DEFAULT "DRAFT" |
| `file_url` | TEXT | nullable (S3/local PDF path) |
| `csv_url` | TEXT | nullable (S3/local CSV ZIP path) |
| `metadata_json` | JSON | nullable |
| `report_size_bytes` | VARCHAR(50) | nullable |
| `version_number` | VARCHAR(20) | DEFAULT "1.0.0" |
| `generator_version` | VARCHAR(20) | DEFAULT "1.0.0" |
| `created_at` | TIMESTAMPTZ | |

**Status values**: DRAFT, QUEUED, GENERATING, VALIDATING, RENDERING, UPLOADING, COMPLETED, FAILED, RETRYING, CANCELLED

---

### 15. `report_history`

Tracks report generation lifecycle events.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `report_id` | UUID | FK -> reports.id (CASCADE) |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE) |
| `user_id` | UUID | FK -> users.id (SET NULL), nullable |
| `status` | VARCHAR(50) | |
| `stage` | VARCHAR(50) | nullable |
| `error_message` | TEXT | nullable |
| `duration_ms` | VARCHAR(50) | nullable |
| `timestamp` | TIMESTAMPTZ | |

---

### 16. `scheduled_reports`

Cron-based scheduled report configurations.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE) |
| `organization_id` | UUID | FK -> organizations.id (CASCADE) |
| `name` | VARCHAR(255) | NOT NULL |
| `type` | VARCHAR(100) | NOT NULL |
| `cron_schedule` | VARCHAR(100) | NOT NULL |
| `next_run` | TIMESTAMPTZ | nullable |
| `filters_json` | JSON | nullable |
| `created_at` | TIMESTAMPTZ | |

---

### 17. `criticality_configs`

Asset criticality overrides per workspace.

| Column | Type | Constraints |
|--------|------|-------------|
| `id` | UUID | PK |
| `workspace_id` | UUID | FK -> workspaces.id (CASCADE), indexed |
| `asset_id` | VARCHAR(512) | indexed |
| `criticality` | INTEGER | nullable |

**Constraints**: `uq_workspace_asset` UNIQUE(workspace_id, asset_id)

---

## Multi-Tenancy Strategy

All data tables include a `workspace_id` column that references `workspaces.id` with `CASCADE` delete. The hierarchy is:

```
Organization -> Workspace -> All Data
```

- **Workspace isolation**: Queries are always filtered by `workspace_id`
- **Organization isolation**: Workspace access is verified against `current_user.organization_id`
- **Header-based routing**: Frontend sends `X-Workspace-ID` header with every request

## Migration Strategy (Alembic)

Migrations are in `sentinel_backend/alembic/versions/`. Key migrations:

1. `759ce696f877` - Initial schema
2. `ad311fab1128` - Auth foundation (organizations, users, workspaces)
3. `062e7b7c3a52` - CanonicalEvent model
4. `919a8ef47f8c` - AuditLog and Report models
5. `3ec7378a997d` - ReportHistory
6. `676d81168d66` - Notification model
7. `78928ff61f82` - Integrations table
8. `58fc0fe94c1d` - Cloud accounts
9. `b8017f7e72ff` - workspace_id to models
10. `52ceb5be9bc4` - Workspace-scoped unique constraints
11. `651dd7f0e3d5` - Enterprise audit schema
12. `c4f359d476fa` - Stage 4 updates
13. `a1b2c3d4e5f6` - Google auth fields

**Running migrations**:
```bash
cd sentinel_backend
alembic upgrade head       # Apply all
alembic downgrade -1       # Rollback one
alembic revision --autogenerate -m "description"  # Create new
```

## Indexing Strategy

- **Primary keys**: All tables use UUID PKs
- **Foreign keys**: All FKs are indexed
- **Composite indexes**: Time + identity combinations for query performance
- **Unique constraints**: Deduplication (event_id + workspace_id, arn + workspace_id)
- **Check constraints**: Enum validation at DB level (severity, status, identity_type)
