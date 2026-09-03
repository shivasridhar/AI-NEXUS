# Stage 1 Demo Guide

This guide outlines the exact sequence to run a live demonstration of the SentinelAI Stage 1 Ingestion Engine. Follow these steps precisely to ensure a flawless presentation.

## Setup Before Demo

1. Ensure both the backend (`fastapi dev`) and frontend (`npm run dev`) are running.
2. Open two browser tabs:
   - **Tab 1:** `/integrations` (Connector Management)
   - **Tab 2:** `/ingestion` (Ingestion Monitoring)
3. Ensure you have the `cloudtrail_logs.json` sample file ready on your local machine for the manual upload portion.

## Demo Sequence

### Step 1: Connector Management (Tab 1)
**Goal:** Show that connectors are dynamically managed and configured via the UI, not hardcoded.

1. Navigate to `/integrations`.
2. Point out the available connectors (AWS, Wazuh, Suricata, OpenVAS).
3. Click **Configure** on the Wazuh connector.
4. Explain that the schema for this modal is driven entirely by the backend, dynamically rendering fields for Endpoint, Username, and Password.
5. Close the modal without saving (or input fake credentials if you want to show the failed state).

### Step 2: Live Ingestion Monitoring (Tab 2)
**Goal:** Show the SOC-style live monitoring console handling events.

1. Switch to the `/ingestion` tab.
2. Highlight the **Pipeline Topology** visualizer, explaining that it shows the exact sequence of processing (Connectors -> Validation -> Deduplication -> Enrichment -> Publisher).
3. Set the **Auto Refresh** dropdown in the top right to **2s**.
4. Point out the **Live Event Feed** table at the bottom. As the backend fetches data, new events will slide in smoothly at the top of the table. Emphasize that the smooth row animation is built to handle live SOC monitoring without janky re-renders.

### Step 3: Attack Simulation
**Goal:** Demonstrate events flowing through the pipeline end-to-end.

1. (Background) If you have a script or a cURL command ready to hit the backend `/api/v1/ingestion/trigger` endpoint, run it now.
   *Example:*
   ```bash
   curl -X POST "http://localhost:8000/api/v1/ingestion/trigger" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer dev_token" \
     -d '{"connector_name": "suricata"}'
   ```
2. Wait ~1-2 seconds.
3. Point to the UI (Tab 2) as the KPI metrics (Events Processed, Events / Minute) increment, and the chart updates with a spike in volume.

### Step 4: File Upload
**Goal:** Show manual log processing (CloudTrail).

1. Back in Tab 1, or via an API client (like Postman), upload the `cloudtrail_logs.json` to the `/api/v1/ingestion/upload` endpoint.
2. Explain that this bypasses the dynamic connector fetching but goes through the exact same Validation & Enrichment pipeline.

## Tips for a Smooth Demo
- **Do not refresh the page** during the 2s polling demonstration to preserve the chart history.
- If the backend is turned off, the UI will immediately show a red "Backend Connection Error" banner. You can actually turn off the backend to demonstrate failure handling!
