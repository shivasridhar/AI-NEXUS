from pydantic import BaseModel, Field
from typing import List, Optional

class ClaimEntity(BaseModel):
    arns: List[str] = Field(default_factory=list)
    ips: List[str] = Field(default_factory=list)
    events: List[str] = Field(default_factory=list)
    users: List[str] = Field(default_factory=list)
    roles: List[str] = Field(default_factory=list)

class Claim(BaseModel):
    claim_id: str = Field(...)
    claim_text: str = Field(...)
    section: str = Field(...)
    entities: ClaimEntity = Field(default_factory=ClaimEntity)

class CitationReference(BaseModel):
    type: str = Field(...)
    ref: str = Field(...)
    time: Optional[str] = None

class Citation(BaseModel):
    citation_id: str = Field(...)
    claim: str = Field(...)
    references: List[CitationReference] = Field(default_factory=list)
