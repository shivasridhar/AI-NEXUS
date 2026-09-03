# Retrieval-Augmented Generation (RAG) Layer

## Purpose
Handles evidence retrieval and vector/graph similarity search to augment LLM context.

## Responsibilities
- Provide unified interfaces for querying Neo4j and Postgres for AI context.
- Embed and index security policies or historical findings for semantic search.
- Act as evidence retrieval tools/nodes within the LangGraph architecture.

## Inputs
- Search queries or identifiers (e.g., identity ARN, workspace ID).

## Outputs
- Structured `RiskEvidence` or similar data models.

## Dependencies
- Neo4j, PostgreSQL (SQLAlchemy)
- `app.services.ai.evidence_collector` (currently being migrated)

## Future Work
- Break down `evidence_collector.py` into distinct RAG tools that the AI Analyst can invoke dynamically.
- Implement vector search capabilities for past remediation plans.
