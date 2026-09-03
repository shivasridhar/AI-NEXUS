# Changelog

All notable changes to the SentinelAI project will be documented in this file.

## [Unreleased]

### Changed
- **Telemetry Endpoints Realized:** The backend telemetry endpoints (`/api/v1/ingestion/config`, `/api/v1/ingestion/metrics`, and `/api/v1/ingestion/events`) are now fully implemented using live PostgreSQL data via the unified `TelemetryService`. All frontend hardcoded `setTimeout` mocks have been successfully replaced with real API calls.
- **Connector Health Tracking:** The `/api/v1/health` endpoint now dynamically aggregates connector health by inspecting the `Integration` table and evaluating sync freshness.
- **Unified Telemetry:** Reconciled dashboard and ingestion statistics to prevent duplication, consolidating overlapping logic into `TelemetryService`.
