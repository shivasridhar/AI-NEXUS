from datetime import datetime
from typing import List, Optional
import uuid
from sqlalchemy import String, DateTime, Integer, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

class RiskScore(Base):
    __tablename__ = "risk_scores"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_identities.id", ondelete="CASCADE"), index=True)
    score: Mapped[int] = mapped_column(Integer)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    reasons: Mapped[List[str]] = mapped_column(ARRAY(String))
    legacy_comparison_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    risk_evidence: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    calculated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=func.now())
    
    identity: Mapped["MachineIdentity"] = relationship(back_populates="risk_scores")
    
    __table_args__ = (
        CheckConstraint('score >= 0 AND score <= 100', name='score_range_check'),
        CheckConstraint(severity.in_(['Low', 'Medium', 'High', 'Critical']), name='severity_check'),
    )
