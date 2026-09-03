# AI Generation Node

## Purpose
The `generate_ai_draft` node serves as the primary LLM interface within the LangGraph orchestrator. It consumes validated evidence and prompt templates to generate an initial, structured security report draft. 

## Execution Flow
1. **Validation**: Checks if `RiskEvidence` is present in the `WorkflowState`.
2. **Prompt Construction**: Loads base templates from `PromptManager` and injects evidence via the legacy `PromptBuilder`.
3. **LLM Invocation**: Calls `AIAnalystService` wrapped in a Tenacity `@retry` decorator for resilience.
4. **Schema Enforcement**: Parses the output dictionary into the strictly-typed `AIResponse` Pydantic model.
5. **State Update**: Populates `state.ai_draft`, records generation metrics (latency, model info), and returns the updated state.

## Dependencies
- `PromptManager`: Handles loading versioned templates from disk (`app/services/prompts/templates`).
- `PromptBuilder`: Legacy service reused for evidence structure injection.
- `AIAnalystService`: Legacy service reused to abstract the Google Gemini API client.
- `AIResponse`: Pydantic v2 schema for strict output validation.
- `Tenacity`: Handles retry logic.

## Prompt Loading
Prompts are loaded from `app/services/prompts/templates/*.md` via `PromptManager`. The manager uses Python's `@lru_cache` to cache disk reads, improving execution speed while keeping templates separated from the codebase logic. Versioning is supported via naming conventions (e.g., `system_v1.md`).

## Retry Strategy
Uses `tenacity` exponential backoff (min: 2s, max: 10s, attempts: 3).
- **Retried**: Network timeouts, `429 Rate Limited`, `503 Unavailable`, `UNKNOWN_ERROR`.
- **NOT Retried**: `AI_AUTH_FAILED`, `AI_RESPONSE_INVALID` (JSON parsing fails), `AI_INVALID_REQUEST`, Pydantic `ValidationError`.

## Validation
Every LLM response is unpacked directly into the `AIResponse` Pydantic schema. If required fields are missing or wrongly typed, a `ValidationError` is raised, forcing the graph to fail securely rather than passing malformed data to downstream components.

## Failure Handling
- **Transient Failures**: Exhausting 3 retries raises a `RetryError`, which the orchestrator will catch and log as a fatal failure.
- **Validation Failures**: Raising `ValueError` ensures no corrupted drafts enter the verification pipeline.
- All failures are logged securely using structured JSON without exposing the raw prompt contents or PII.

## Future Improvements
- Pass `estimated_token_usage` natively once the Gemini API SDK starts returning token count metadata consistently.
- Introduce dynamic prompt selection based on the `severity` inside the `RiskEvidence`.
- Migrate `PromptBuilder` evidence injection into `PromptManager` Jinja templates for full LangChain compatibility.
