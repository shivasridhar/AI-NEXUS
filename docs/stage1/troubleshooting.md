# Stage 1 Troubleshooting & Limitations Runbook

This document describes known limitations of the Stage 1 implementation and common failure modes during deployment or demos.

## Known Limitations

1. **Retry Behavior under Backend Outage**
   - If the core FastAPI backend dies during a sync, the Ingestion Pipeline does not currently feature persistent queueing (e.g., Kafka/RabbitMQ) for retry. The `SecurityEventPublisher` relies on a synchronous in-memory handoff. Events mid-flight may be lost if the server crashes.

## Common Demo Failures

### 1. "Authentication rejected by [Connector]"
- **Symptom:** You try to trigger Wazuh or OpenVAS in the UI and receive a 401 error.
- **Cause:** The mocked or injected credentials in the backend are stale or the external service rotated tokens.
- **Fix:** Go to `/integrations`, click Configure on the failing connector, and re-enter the valid username/password. Ensure the external sandbox is actually awake.

### 2. "Backend Connection Error" Banner Appears
- **Symptom:** A red error banner appears on the `/ingestion` page.
- **Cause:** The frontend React Query hooks failed to hit the mocked or real API layer 3 consecutive times. The FastAPI server is likely down.
- **Fix:** Check the terminal running `fastapi dev`. If it crashed due to a syntax error or missing package, restart it.

### 3. Events arriving with Timestamp "1970" or missing fields
- **Symptom:** Downstream systems (Stage 2) complain about corrupted data.
- **Cause:** A connector mapped a raw event improperly, or bypassed the `EventValidator`.
- **Fix:** Ensure the connector returns `SecurityEvent` objects and is not trying to bypass the `EventPipeline` by writing directly to the Publisher. The Validator enforces ISO 8601 timestamps.
