# Explainability Layer

## Purpose
Translates complex graph analytics and AI reasoning into human-readable narratives.

## Responsibilities
- Provide step-by-step reasoning traces for AI conclusions.
- Map AI findings back to specific edges/nodes in the graph.
- Generate user-facing explanations for risk scores and attack paths.

## Inputs
- Final `VerifiedResponse`.
- Original traversal logs and `RiskEvidence`.

## Outputs
- Explainability metadata or text strings to accompany the final report.

## Dependencies
- Core graph logic

## Future Work
- Expose an API for users to ask "Why?" for specific findings and trigger dynamic explainability nodes.
