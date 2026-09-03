import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import String, DateTime, ForeignKey, Text, Float, Table, Column
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.models.base import Base

incident_event_association = Table(
    "incident_events",
    Base.metadata,
    Column("incident_id", UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True),
    Column("event_id", UUID(as_uuid=True), ForeignKey("canonical_events.id", ondelete="CASCADE"), primary_key=True)
)

class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="Open", index=True)
    severity: Mapped[str] = mapped_column(String(50), index=True)
    confidence_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    
    affected_assets: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    contributing_sources: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    mitre_techniques: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True, default=list)
    
    start_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    end_time: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    
    # Relationship to canonical events
    events: Mapped[List["CanonicalEvent"]] = relationship(
        "CanonicalEvent", 
        secondary=incident_event_association, 
        lazy="selectin"
    )
