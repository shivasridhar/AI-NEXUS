from sqlalchemy import String, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
import uuid

from app.models.base import Base

class CriticalityConfig(Base):
    __tablename__ = "criticality_configs"
    
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), index=True, nullable=False)
    asset_id: Mapped[str] = mapped_column(String(512), index=True, nullable=False)
    criticality: Mapped[int] = mapped_column(Integer, nullable=True)
    
    __table_args__ = (
        UniqueConstraint('workspace_id', 'asset_id', name='uq_workspace_asset'),
    )
