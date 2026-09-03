# LangGraph Orchestration Layer

## Purpose
Manages the declarative state graph and workflow execution for AI reasoning loops.

## Responsibilities
- Compile and execute the StateGraph.
- Manage state transitions between Analyst, Verifier, and Formatter nodes.
- Handle human-in-the-loop (HITL) checkpoints.

## Inputs
- Validated state inputs (from Pydantic models).
- Evidence retrieved from RAG and graph nodes.

## Outputs
- Final serialized state containing the `VerifiedResponse`.

## Dependencies
- `langgraph`, `langchain-core`
- Local `prompts`, `rag`, and `verification` modules.

## Future Work
- Implement the `CompiledGraph` entry point replacing `investigation_service.py`.
