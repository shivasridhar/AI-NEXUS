# Prompt Engineering & Templates

## Purpose
Centralizes all LLM prompt templates, logic for state injection, and few-shot examples.

## Responsibilities
- Provide reusable `ChatPromptTemplate` instances.
- Inject dynamic LangGraph state into prompts safely.
- Maintain versioned prompt variations.

## Inputs
- LangGraph state variables (e.g. `RiskEvidence`, user queries).

## Outputs
- Formatted string or Message objects ready for LLM consumption.

## Dependencies
- `langchain-core.prompts`

## Future Work
- Migrate `prompt_builder.py` string templates to typed LangChain templates.
- Add dynamic prompt selection based on severity/context.
