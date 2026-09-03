# Phase X — Cross-Stage Integration Plan

This plan addresses the integration of all eight SentinelAI stages into a unified, end-to-end pipeline. As discovered during the initial inspection, Stage 1 is fully complete, but Stages 2-6 do not yet have formalized schema contracts or complete implementations. 

As the Lead Integration Architect, I will define the missing schemas, build lightweight stub services for the unfinished stages, and wire them together using a joint integration adapter layer to prove the end-to-end flow.

## ⚠️ User Review Required (Step 0 - Architectural Decision)

Before we write any integration code, we must make a foundational decision on the pipeline architecture. **Please review and approve or modify the following recommendation:**

> [!IMPORTANT]  
> **Recommended Architecture: Asynchronous Shared Event Stream**
>
> **1. Synchronous vs Asynchronous:**  
> Connecting 8 stages synchronously via HTTP/RPC is an anti-pattern for a high-volume SIEM. A slowdown in Stage 6 (Explainability) would cause backpressure all the way to Stage 1, stalling ingestion and dropping events. **Decision:** We will use an **asynchronous, event-driven** model for the core ingestion pipeline (Stages 1-6). Stage 7 (API) and Stage 8 (Dashboard) will remain synchronous request/response when querying the final datastore, but will subscribe via WebSockets for live updates.
>
> **2. Sequential Chain vs Shared Stream:**  
> Rather than a strict sequential chain (Stage 1 -> Stage 2 -> Stage 3), we will implement a **Shared Event Stream (Pub/Sub)** pattern. Each stage will subscribe to the specific event schemas it cares about (e.g., Stage 4 Risk Engine subscribes to `NormalizedEvent` and `CorrelatedIncident`), perform its work independently, and publish its output back to the stream. This allows stages to scale at their own pace and prevents total pipeline blockage if one stage fails.

If you agree with this recommendation, click **Proceed**. If you prefer a strict synchronous chain or a different pattern, please reply with your choice.

## Proposed Changes

To execute the integration based on the event-driven stream pattern, the following changes will be made:

### 1. Define Versioned Schema Contracts
Each stage must have a strictly versioned output contract. We will create these in `app/schemas/`:
- `NormalizedEventV1` (Stage 2)
- `CorrelatedIncidentV1` (Stage 3)
- `RiskAssessmentV1` (Stage 4)
- `AIRecommendationV1` (Stage 5)
- `ExplainableDecisionV1` (Stage 6)

*Note: `SecurityEventV1` (Stage 1) is already defined but will be updated to explicitly include a schema version.*

### 2. Implement the Integration Adapter (Neutral Zone)
We will create a neutral integration layer that acts as the cross-stage boundary.
#### [NEW] `sentinel_backend/integration/adapters/event_bus.py`
A lightweight in-memory Pub/Sub broker (designed to be easily swapped for Kafka/Redis later) that handles topic routing, idempotency checks, and timeouts.

### 3. Build Stub Services for Stages 2-6
Since Stages 2-6 are not fully implemented, we will build stub services that adhere to their contracts, allowing us to validate the end-to-end flow without blocking.
#### [NEW] `sentinel_backend/integration/stubs/stage2_normalizer_stub.py`
#### [NEW] `sentinel_backend/integration/stubs/stage3_correlator_stub.py`
#### [NEW] `sentinel_backend/integration/stubs/stage4_risk_stub.py`
#### [NEW] `sentinel_backend/integration/stubs/stage5_ai_stub.py`
#### [NEW] `sentinel_backend/integration/stubs/stage6_explainability_stub.py`

These stubs will listen to the `EventBus`, generate realistic fixture data, and publish their outputs back to the bus.

### 4. Consumer-Driven Contract Tests
We will write boundary tests to prove that each stub correctly consumes its expected input and produces valid output.
#### [NEW] `sentinel_backend/tests/integration/test_stage_contracts.py`

### 5. Generate the Final Integration Report
We will produce a comprehensive Phase X Integration Report detailing the final topology, latency measurements for a trace event, and the exact boundary definitions.

## Verification Plan

### Automated Validation
- Run the new `test_stage_contracts.py` suite to verify that each stage's stub strictly adheres to its Pydantic schema contract.
- Run a trace test that pushes a `SecurityEvent` into the `EventBus` and asserts that a corresponding `ExplainableDecision` is eventually published.

### End-to-End Simulation
- Trigger the Stage 1 `/trigger` API.
- Observe the logs to ensure the event flows successfully across the integration adapters (Stage 1 -> Bus -> Stage 2 Stub -> Bus -> ... -> Stage 6 Stub).
- Document the end-to-end latency in the final report.
