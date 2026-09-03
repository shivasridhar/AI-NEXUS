from datetime import datetime
from typing import Any, Dict, Optional
import uuid
from sqlalchemy import String, DateTime, Index, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func
from app.models.base import Base

class CanonicalEvent(Base):
    __tablename__ = "canonical_events"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    
    source_tool: Mapped[str] = mapped_column(String(100), index=True) # e.g., 'wazuh', 'suricata', 'openvas'
    event_type: Mapped[str] = mapped_column(String(100), index=True)
    
    severity_raw: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    severity_normalized: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) # 0-100 scale
    
    timestamp_utc: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    
    actor_identifier: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    asset_identifier: Mapped[Optional[str]] = mapped_column(String(512), nullable=True, index=True)
    
    raw_event_json: Mapped[Dict[str, Any]] = mapped_column(JSONB)
    
    # Soft pointer to AccessLog for eventual reconciliation
    linked_access_log_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    
    __table_args__ = (
        Index('idx_canonical_event_time_actor', 'timestamp_utc', 'actor_identifier'),
    )
