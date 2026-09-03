# SentinelAI Stage 1 Implementation Plan

## Phase 0 (Today)
**Objective:** Freeze the architecture before writing any code.

Deliverables:
* ✅ Stage 1 architecture finalized
* ✅ Folder additions finalized
* ✅ SecurityEvent contract finalized
* ✅ Connector architecture finalized

*Note: No coding yet.*

---

## Phase 1: Foundation
This phase creates the new architecture **without touching existing code**.

We will implement:
```text
app/
    services/
        connectors/
            __init__.py
            base_connector.py
        ingestion_pipeline/
            __init__.py
    schemas/
        security_event.py
```
Nothing else. No APIs, no parser, no risk engine, no graph. Just the foundation.

---

## Phase 2: SecurityEvent Contract
We will freeze one enterprise event model. Every connector must output this standard model.

**Example mapping:**
`SecurityEvent` → `event_id`, `source`, `vendor`, `event_type`, `timestamp`, `severity`, `asset`, `identity`, `raw_payload`, `metadata`

This is one of the most important files in the project.

---

## Phase 3: Base Connector
We will implement an abstract `BaseConnector` class containing the following interface:
* `connect()`
* `authenticate()`
* `fetch_events()`
* `health_check()`
* `disconnect()`

Every future connector must inherit from this class.

---

## Phase 4: Connector Manager
We will build a `ConnectorManager` responsible for:
* Loading connectors
* Authentication
* Health checks
* Fetching events
* Returning standard `SecurityEvent` objects

This manager still will not touch the legacy CloudTrail implementation.

---

## Phase 5: Individual Connectors
Connectors will be implemented one at a time in the following order:
1. **AWS IAM**
2. **AWS Security Hub**
3. **Wazuh**
4. **Suricata**
5. **OpenVAS**

Every connector outputs a `List[SecurityEvent]` and nothing more.

---

## Phase 6: Validation Pipeline
We will introduce a processing pipeline between the Connector and the Universal Ingestion layer:
`Connector` → `Validation` → `Duplicate Detection` → `Metadata Enrichment` → `Universal Ingestion`

---

## Phase 7: Universal Ingestion
This is where the current SentinelAI architecture gets reused. The flow will be:
`Connector` → `Validation` → `Universal Ingestion` → `identity_discovery.py` → `risk_engine.py` → `graph_sync_service.py`

There will be no duplicate code and no new risk engine created.

---

## Phase 8: API
We will add exactly one new endpoint:
`POST /v1/ingest/universal`

The existing CloudTrail upload endpoints will continue working seamlessly.

---

## Phase 9: Simulation
We will simulate connections and ensure the end-to-end flow works:
* `Hydra` → `Wazuh` → `SecurityEvent`
* `Suricata` → `SecurityEvent`
* `OpenVAS` → `SecurityEvent`
* `AWS` → `SecurityEvent`

---

## Phase 10: Testing
The testing sequence will follow:
`Connector tests` → `Pipeline tests` → `Integration tests` → `Regression tests`

---

## How We'll Work Together
To ensure enterprise-grade stability and avoid generating thousands of lines of code at once, we will follow this iterative cycle:
`Design` → `Implementation Prompt` → `AI Generates Code` → `Review` → `Fix` → `Next Module`

---

## Starting Point: Module 1 Foundation
We begin with the creation of the foundational files (`base_connector.py`, `security_event.py`, etc.). 

**Status:**
- No existing files are modified.
- No functionality changes.
- No risk of breaking the project.

**Review Process:**
1. Execute the implementation prompt for Module 1.
2. Review generated code for:
   * Architecture quality
   * SOLID principles
   * Backward compatibility
   * Production readiness
   * Merge conflict risk
3. Once approved, proceed to Module 2.

By the end of Stage 1, we will have an enterprise-grade implementation without risking the existing SentinelAI codebase.
