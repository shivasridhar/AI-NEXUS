# SentinelAI AI/LLM Integration Guide

## Overview

SentinelAI integrates **Google Gemini 3.5 Flash** as its AI backbone for security investigation, executive report generation, and finding explainability. The integration uses the `google-genai` Python SDK with structured JSON output, retry logic, and enterprise-grade error handling.

## Architecture

```
                        +-------------------+
                        |   AI Endpoints    |
                        | /api/v1/ai/*      |
                        +--------+----------+
                                 |
                    +------------+------------+
                    |                         |
           +-------v--------+    +-----------v-----------+
           | Investigation  |    | AI Workflow Service    |
           | Service        |    | (orchestration)       |
           +-------+--------+    +-----------+-----------+
                   |                         |
           +-------v--------+    +-----------v-----------+
           | Evidence        |    | Prompt Builder        |
           | Collector       |    | (prompt engineering)  |
           +-------+--------+    +-----------+-----------+
                   |                         |
                   +------------+------------+
                                |
                    +-----------v-----------+
                    | AIAnalystService      |
                    | (Gemini API client)   |
                    +-----------+-----------+
                                |
                    +-----------v-----------+
                    | Google Gemini 3.5     |
                    | Flash API             |
                    +-----------------------+
```

## Gemini API Integration

### Client Configuration

```python
from google import genai
from google.genai import types

client = genai.Client(api_key=settings.GEMINI_API_KEY)
```

**Model**: `gemini-3.5-flash`
**Environment variable**: `GEMINI_API_KEY`

### API Call Pattern

```python
response = client.models.generate_content(
    model='gemini-3.5-flash',
    contents=prompt,
    config=types.GenerateContentConfig(
        response_mime_type="application/json"  # Structured JSON output
    )
)
```

### Retry Strategy

Uses `tenacity` library for automatic retries:

- **Max attempts**: 3
- **Wait**: Exponential backoff (min 2s, max 10s)
- **Retry on**: Any exception
- **Logging**: Warning logged before each retry

---

## AI Capabilities

### 1. Identity Investigation (`call_llm`)

Generates comprehensive security investigation reports for machine identities.

**Input**: Evidence dictionary containing:
- Identity metadata (ARN, type, account)
- Risk scores and severity
- Access logs and events
- Attack path data
- Graph evidence

**Output** (JSON):
```json
{
  "executive_summary": "C-level summary of risk posture",
  "risk_assessment": "Detailed security risk assessment",
  "attack_path_analysis": "Lateral movement and exposure analysis",
  "findings": ["Finding 1 with evidence references", "..."],
  "recommendations": ["Actionable remediation step 1", "..."],
  "success": true
}
```

### 2. Executive Report Summary (`generate_executive_report_summary`)

Generates executive summaries for security reports based on metrics.

**Input**: Metrics dictionary (identity counts, risk scores, findings)
**Output**: Plain text summary paragraphs (no markdown, no JSON)
**Anti-hallucination**: Explicit constraint in prompt to only use provided data

### 3. Finding Explanation (`generate_finding_explanation`)

Generates human-readable explanations for specific risk findings using graph evidence.

**Input**: Prompt with graph evidence context
**Output**: Plain text explanation
**MIME type**: `text/plain` (not JSON)

---

## Prompt Engineering

### Investigation Prompt Structure

The prompt builder (`app/services/ai/prompt_builder.py`) constructs prompts with:

1. **Role assignment**: "You are SentinelAI, a Principal Cloud Security Architect and SOC Lead"
2. **Critical instructions**:
   - Evidence-based reasoning only
   - No hallucinations or assumptions
   - Every finding must reference evidence
   - Enterprise SOC analyst style
   - Strict JSON output format
3. **Evidence payload**: JSON-serialized evidence data
4. **Output schema**: Exact JSON structure expected

### Anti-Hallucination Measures

- Prompts explicitly state: "Do not assume permissions, actions, or vulnerabilities not explicitly documented in the evidence"
- "If evidence is missing, do not invent details"
- Executive summary prompt: "DO NOT hallucinate any numbers, identities, or risks. Only use the data provided below."
- Response validation checks for required keys

---

## Error Handling

### Enterprise Error Codes

| Code | Condition | User Message |
|------|-----------|--------------|
| `AI_RESPONSE_INVALID` | JSON parse failure | "The AI service returned an invalid response format" |
| `AI_AUTH_FAILED` | 401/403 or API key error | "AI service authentication failed" |
| `AI_RATE_LIMITED` | 429 or quota exhausted | "AI service rate limit exceeded" |
| `AI_TIMEOUT` | Timeout or deadline exceeded | "The AI service timed out" |
| `AI_SERVICE_UNAVAILABLE` | 500/503 or service down | "The AI service is temporarily unavailable" |
| `AI_INVALID_REQUEST` | 400 or invalid argument | "The AI service rejected the request" |
| `UNKNOWN_ERROR` | Any other error | "An unexpected error occurred" |

### Error Response Format

```json
{
  "success": false,
  "code": "AI_RATE_LIMITED",
  "message": "AI service rate limit exceeded. Please try again later."
}
```

### Logging

Failed AI calls produce structured JSON logs:
```json
{
  "event": "AI_INVESTIGATION_FAILED",
  "workspace_id": "...",
  "investigation_id": "...",
  "provider": "gemini-3.5-flash",
  "latency_ms": 1234.56,
  "failure_reason": "...",
  "exception_type": "ValueError",
  "retry_count": 0,
  "stack_trace": "..."
}
```

---

## Response Validation

After parsing the Gemini JSON response, required keys are validated:

```python
required_keys = [
    "executive_summary",
    "risk_assessment",
    "attack_path_analysis",
    "findings",
    "recommendations"
]
```

Missing keys are automatically populated with empty strings or empty lists to prevent downstream failures.

---

## Configuration

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Google Gemini API key |
| `ENABLE_GRAPH_EVIDENCE_ENGINE` | No | Enable graph-based evidence collection (default: true) |

## Rate Limit Handling

The `GeminiRateLimitError` exception is raised specifically for 429/quota errors in the explainability flow, allowing callers to implement backoff or graceful degradation.

## Cost Considerations

- **Model**: Gemini 3.5 Flash (optimized for speed and cost)
- **Structured output**: `response_mime_type="application/json"` reduces token waste
- **Retry limit**: Max 3 attempts prevents runaway costs
- **Evidence scoping**: Only relevant evidence is included in prompts to minimize token usage
