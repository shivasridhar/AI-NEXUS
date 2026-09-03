"""
AI Intelligence Layer — Centralized API Contracts
Stage 5 (Investigation) and Stage 6 (Verification) public interfaces.

Import from this module when you need any AI-layer schema outside of the
ai endpoint itself, to avoid scattered cross-package imports.
"""
from app.schemas.ai_response import AIResponse, Finding, Recommendation
from app.schemas.verified_response import VerifiedResponse, VerificationResult
from app.schemas.claims import Claim, Citation, CitationReference, ClaimEntity
from app.schemas.risk_evidence import RiskEvidence

__all__ = [
    # Core AI output
    "AIResponse",
    "Finding",
    "Recommendation",
    # Verification pipeline
    "VerifiedResponse",
    "VerificationResult",
    # Claims and citations
    "Claim",
    "ClaimEntity",
    "Citation",
    "CitationReference",
    # Evidence
    "RiskEvidence",
]
