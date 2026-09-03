import os
import json
import logging
import time
import traceback
from typing import Dict, Any
from google import genai
from google.genai import types
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from app.core.config import settings

logger = logging.getLogger(__name__)

class GeminiRateLimitError(Exception):
    pass

class AIAnalystService:
    def __init__(self):
        api_key = settings.GEMINI_API_KEY or os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("GEMINI_API_KEY environment variable is missing.")
        
        self.client = genai.Client(api_key=api_key)

    @retry(
        reraise=True,
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type(Exception),
        before_sleep=lambda retry_state: logger.warning(
            f"Gemini API call failed. Retrying (attempt {retry_state.attempt_number})..."
        )
    )
    def _call_gemini_api(self, prompt: str, response_mime_type: str = "application/json", response_schema=None) -> str:
        # Note: the new SDK config format
        config_kwargs = {"response_mime_type": response_mime_type}
        if response_schema:
            config_kwargs["response_schema"] = response_schema
            
        response = self.client.models.generate_content(
            model='gemini-3.5-flash',
            contents=prompt,
            config=types.GenerateContentConfig(**config_kwargs)
        )
        return response.text

    def call_llm(self, prompt: str, workspace_id: str = "unknown", identity_id: str = "unknown", investigation_id: str = "unknown", user_id: str = "system") -> Dict[str, Any]:
        """
        Calls Gemini 3.5 Flash with retry and timeout constraints, returning the parsed JSON.
        """
        logger.info(f"Calling Gemini 3.5 Flash for identity investigation (ID: {investigation_id})...")
        start_time = time.time()
        retry_count = 0 # Handled by tenacity, but we can capture failure state here
        
        try:
            from app.schemas.ai_response import AIResponse
            raw_response = self._call_gemini_api(prompt, response_schema=AIResponse)
            if not raw_response:
                raise ValueError("Received empty response from Gemini API.")
            
            try:
                parsed_response = json.loads(raw_response)
            except json.JSONDecodeError as je:
                raise ValueError(f"JSON Parsing Error: {str(je)}")
            
            # Validate output keys
            required_keys = ["executive_summary", "risk_assessment", "attack_path_analysis", "findings", "recommendations"]
            for key in required_keys:
                if key not in parsed_response:
                    parsed_response[key] = "" if "analysis" in key or "summary" in key or "assessment" in key else []
            
            # Fallback parser for Findings and Recommendations if they are strings
            if isinstance(parsed_response.get("findings"), list):
                fixed_findings = []
                for f in parsed_response["findings"]:
                    if isinstance(f, str):
                        fixed_findings.append({"title": "Unstructured Finding", "description": f, "severity": "Medium"})
                    else:
                        fixed_findings.append(f)
                parsed_response["findings"] = fixed_findings
                
            if isinstance(parsed_response.get("recommendations"), list):
                fixed_recs = []
                for r in parsed_response["recommendations"]:
                    if isinstance(r, str):
                        fixed_recs.append({"action": "Review Finding", "rationale": r, "effort": "Medium"})
                    else:
                        fixed_recs.append(r)
                parsed_response["recommendations"] = fixed_recs
            
            parsed_response["success"] = True
            return parsed_response
            
        except Exception as e:
            duration = time.time() - start_time
            error_str = str(e).lower()
            error_type = type(e).__name__
            
            # 1. Map to enterprise error codes
            code = "UNKNOWN_ERROR"
            message = "An unexpected error occurred during AI analysis."
            
            if "json parsing error" in error_str:
                code = "AI_RESPONSE_INVALID"
                message = "The AI service returned an invalid response format."
            elif "401" in error_str or "403" in error_str or "api_key" in error_str or "unauthenticated" in error_str:
                code = "AI_AUTH_FAILED"
                message = "AI service authentication failed."
            elif "429" in error_str or "quota" in error_str or "rate limit" in error_str or "exhausted" in error_str:
                code = "AI_RATE_LIMITED"
                message = "AI service rate limit exceeded. Please try again later."
            elif "timeout" in error_str or "deadline" in error_str:
                code = "AI_TIMEOUT"
                message = "The AI service timed out."
            elif "503" in error_str or "500" in error_str or "unavailable" in error_str or "internal" in error_str:
                code = "AI_SERVICE_UNAVAILABLE"
                message = "The AI service is temporarily unavailable."
            elif "invalid argument" in error_str or "400" in error_str:
                code = "AI_INVALID_REQUEST"
                message = "The AI service rejected the request."

            # 2. Log complete exception securely in the backend
            logger.error(
                json.dumps({
                    "event": "AI_INVESTIGATION_FAILED",
                    "workspace_id": workspace_id,
                    "investigation_id": investigation_id,
                    "user_id": user_id,
                    "identity_id": identity_id,
                    "provider": "gemini-3.5-flash",
                    "latency_ms": round(duration * 1000, 2),
                    "failure_reason": str(e),
                    "exception_type": error_type,
                    "retry_count": retry_count,
                    "stack_trace": traceback.format_exc()
                })
            )
            
            # 3. Return sanitized error object
            return {
                "success": False,
                "code": code,
                "message": message
            }

    def generate_executive_report_summary(self, metrics: Dict[str, Any]) -> str:
        """
        Generates an executive summary strictly based on the provided metrics.
        Includes a validation constraint against hallucinations.
        """
        logger.info(json.dumps({
            "stage": "AI_SUMMARY_GENERATION",
            "status": "STARTED"
        }))
        prompt = f"""
        You are a Principal Cloud Security Architect. Generate a concise, professional executive summary 
        for an enterprise security report based strictly on the following metrics.
        
        CRITICAL CONSTRAINT: DO NOT hallucinate any numbers, identities, or risks. 
        Only use the data provided below. If data is zero or missing, state that clearly.
        
        Metrics:
        {json.dumps(metrics, indent=2)}
        
        Return ONLY the raw text summary paragraphs. No markdown formatting, no titles.
        """
        
        try:
            # We don't want JSON here, just plain text
            response = self.client.models.generate_content(
                model='gemini-3.5-flash',
                contents=prompt
            )
            summary = response.text.strip()
            # Simple validation: ensure it's not empty
            if not summary:
                raise ValueError("AI returned empty summary")
            
            logger.info(json.dumps({
                "stage": "AI_SUMMARY_GENERATION",
                "status": "SUCCESS"
            }))
            return summary
        except Exception as e:
            logger.error(json.dumps({
                "stage": "AI_SUMMARY_GENERATION",
                "status": "FAILED",
                "error": str(e)
            }))
            return "AI Summary unavailable."

    def generate_finding_explanation(self, prompt: str) -> str:
        """
        Generates a plain-text explanation for a specific finding based on graph evidence.
        Uses existing retry and error handling. Returns None on failure.
        """
        logger.info(json.dumps({
            "stage": "AI_EXPLAINABILITY_GENERATION",
            "status": "STARTED"
        }))
        try:
            response_text = self._call_gemini_api(prompt, response_mime_type="text/plain")
            if not response_text:
                raise ValueError("Received empty explanation from AI")
            
            logger.info(json.dumps({
                "stage": "AI_EXPLAINABILITY_GENERATION",
                "status": "SUCCESS"
            }))
            return response_text.strip()
        except Exception as e:
            error_str = str(e).lower()
            is_429 = "429" in error_str or "quota" in error_str or "rate limit" in error_str or "exhausted" in error_str
            logger.error(json.dumps({
                "stage": "AI_EXPLAINABILITY_GENERATION",
                "status": "FAILED",
                "error": str(e),
                "stack_trace": traceback.format_exc()
            }))
            if is_429:
                raise GeminiRateLimitError(str(e))
            return None

