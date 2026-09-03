# Member 3 AI Intelligence Layer Architecture Mapping

This document maps the current procedural AI architecture to the target enterprise graph-based architecture using LangGraph.

| Current File | Future Responsibility | Reuse/Refactor/New | Reason | Migration Notes |
|---|---|---|---|---|
| `app/services/ai/investigation_service.py` | LangGraph Orchestrator Node | Refactor | Monolithic procedural execution logic needs to be converted into declarative state transitions (StateGraph). | Will be replaced by `app/services/langgraph/graph.py` serving as the compiled entry point. |
| `app/services/ai/ai_analyst_service.py` | LangGraph LLM Execution Nodes | Refactor | Currently a monolithic LLM wrapper. Needs to be split into specialized multi-agent nodes (Analyst, Verifier, Formatter). | Break down into single-purpose nodes that receive state dicts and output state dicts. |
| `app/services/ai/prompt_builder.py` | Prompt Nodes / State Injection | Refactor | Static string building is brittle. Transition to Pydantic-backed template rendering using Graph State. | Move into `app/services/prompts/` and align with LangChain prompt templates. |
| `app/services/ai/evidence_collector.py` | Evidence Retrieval Nodes (RAG) | Refactor | Evidence gathering needs to become asynchronous node steps in the graph that enrich the global state before LLM reasoning. | Move graph/RAG capabilities into `app/services/rag/`. |
| *None* | Verification Nodes | New | Currently lacking a ground-truth checking mechanism for hallucination prevention. | Create in `app/services/verification/` to run post-generation and flag unverified claims. |
| *None* | Response Formatter Nodes | New | Ad-hoc dictionary responses need to be replaced with strict Pydantic v2 validation layers (Structured Output). | Integrate with Pydantic contracts under `app/schemas/`. |
