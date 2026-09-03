# Stage 1 API Reference

## 1. Trigger Ingestion Connector

Triggers a dynamic connector authentication, ingestion, validation, deduplication pipeline, and publishes events to the default transport sink.

**Endpoint:** `POST /api/v1/ingestion/trigger`

### Request Schema (`TriggerIngestionRequest`)

```json
{
  "connector_name": "string (Required. e.g., 'wazuh', 'suricata', 'openvas', 'aws_iam')",
  "config": {
    "key": "value (Optional. Configuration settings specific to the connector)"
  }
}
```

### Response Schema (`TriggerIngestionResponse`)

```json
{
  "connector": "string",
  "status": "completed | completed_with_errors",
  "events_received": "integer",
  "events_validated": "integer",
  "events_deduplicated": "integer",
  "events_published": "integer",
  "failures": [
    {
      "event_id": "string",
      "reason": "string"
    }
  ],
  "processing_time_ms": "float"
}
```

### Example Request (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/trigger" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <token>" \
     -d '{
           "connector_name": "wazuh",
           "config": {
             "endpoint": "https://wazuh.local",
             "username": "admin",
             "password": "secretpassword"
           }
         }'
```

---

## 2. Manual Log Upload (CloudTrail)

Uploads a raw JSON file for ingestion. The file will be processed synchronously for real-time UI updates.

**Endpoint:** `POST /api/v1/ingestion/upload`

### Request (Multipart Form Data)
- `file`: `UploadFile` (Required. Only `.json` supported)

### Response Schema

```json
{
  "message": "File uploaded and processed successfully.",
  "job_id": "string (uuid)",
  "filename": "string",
  "status": "completed",
  "total_events": "integer",
  "inserted": "integer",
  "duplicates": "integer",
  "failed": "integer",
  "identities_discovered": "integer",
  "risk_findings_generated": "integer",
  "neo4j_nodes_created": "integer",
  "neo4j_relationships_created": "integer",
  "processing_time_ms": "integer"
}
```

### Example Request (cURL)
```bash
curl -X POST "http://localhost:8000/api/v1/ingestion/upload" \
     -H "Authorization: Bearer <token>" \
     -F "file=@cloudtrail_logs.json"
```

---

## Error Responses

Both endpoints return standardized HTTP exceptions:

- **400 Bad Request:** Missing parameters, unsupported file type, invalid connector configs.
- **401 Unauthorized:** Credentials rejected by the remote connector (e.g., incorrect OpenVAS password).
- **500 Internal Server Error:** Unexpected processing failure.
- **502 Bad Gateway:** Remote connector could not be reached (network error).

---

## 3. Ingestion Config

Retrieves the pipeline configuration describing the processing topology.

**Endpoint:** `GET /api/v1/ingestion/config`

### Response Schema
```json
{
  "stages": [
    {
      "id": "string",
      "name": "string",
      "status": "string",
      "description": "string"
    }
  ],
  "columns": [
    {
      "key": "string",
      "label": "string",
      "type": "string",
      "sortable": boolean
    }
  ],
  "healthThresholds": {
    "latencyMs": integer,
    "errorRatePercent": float
  }
}
```

---

## 4. Ingestion Metrics

Retrieves telemetry statistics describing the throughput of the ingestion pipeline.

**Endpoint:** `GET /api/v1/ingestion/metrics`

### Response Schema
```json
{
  "totalEvents": integer,
  "eventsPerMinute": float,
  "validationSuccessRate": float,
  "activeConnectors": integer,
  "chartData": [
    {
      "time": "string (ISO Date)",
      "events": integer,
      "validated": integer
    }
  ]
}
```

---

## 5. Live Events Feed

Retrieves the raw stream of recently processed events.

**Endpoint:** `GET /api/v1/ingestion/events`

### Query Parameters
- `limit` (integer, optional, default: 50): Number of events to fetch.
- `offset` (integer, optional, default: 0): Pagination offset.

### Response Schema (List of objects)
```json
[
  {
    "id": "string",
    "timestamp": "string (ISO Date)",
    "connector": "string",
    "eventType": "string",
    "severity": "string",
    "status": "string",
    "message": "string"
  }
]
```

---

## 6. Health Checks

Retrieves global backend health, Neo4j status, and per-connector sync freshness.

**Endpoint:** `GET /api/v1/health`

### Response Schema
```json
{
  "status": "ok | degraded | error",
  "database": "ok",
  "neo4j": "ok",
  "connectors": {
    "aws": "ok | stale | error | pending",
    "wazuh": "ok | stale | error | pending"
  }
}
```
