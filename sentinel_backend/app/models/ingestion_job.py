from sqlalchemy import Column, String, DateTime, ForeignKey, BigInteger, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.sql import func
import uuid
from app.models.base import Base

class IngestionJob(Base):
    __tablename__ = "ingestion_jobs"
    
    job_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    workspace_id = Column(UUID(as_uuid=True), ForeignKey("workspaces.id", ondelete="CASCADE"), nullable=False, index=True)
    s3_bucket_name = Column(String(255), nullable=False)
    status = Column(String(50), nullable=False)
    events_processed = Column(BigInteger, default=0)
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True), nullable=True)
    error_message = Column(String(1024), nullable=True)
    risk_findings_generated = Column(BigInteger, default=0)
    
    __table_args__ = (
        CheckConstraint(status.in_(['pending', 'running', 'completed', 'failed']), name='status_check'),
    )
