from datetime import datetime
from typing import Optional
import uuid
from sqlalchemy import String, DateTime, ForeignKey, Text, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

class RiskFinding(Base):
    __tablename__ = "risk_findings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    identity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("machine_identities.id", ondelete="CASCADE"), index=True)
    finding_type: Mapped[str] = mapped_column(String(100), index=True)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    description: Mapped[str] = mapped_column(Text)
    event_reference: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mitre_technique: Mapped[Optional[str]] = mapped_column(String(20), nullable=True, index=True)
    mitre_tactic: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    blast_radius_score: Mapped[Optional[int]] = mapped_column(nullable=True)
    compliance_refs: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    identity: Mapped["MachineIdentity"] = relationship(back_populates="risk_findings")
    
    __table_args__ = (
        CheckConstraint(severity.in_(['Low', 'Medium', 'High', 'Critical']), name='finding_severity_check'),
    )
