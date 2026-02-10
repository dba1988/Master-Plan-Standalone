"""Job model for background task tracking."""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Text, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Job(Base):
    """
    Background job tracking.

    Job types:
    - tile_generation: Generate DZI tiles from base map
    - svg_import: Parse and import SVG overlays
    - publish: Publish version to release

    Status flow: queued → running → completed/failed/cancelled
    """
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False)

    # Status tracking
    status = Column(String(20), default="queued")  # queued, running, completed, failed, cancelled
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text, nullable=True)  # Current step description

    # Result data
    result = Column(JSONB, nullable=True)  # Success result
    error = Column(Text, nullable=True)  # Error message on failure
    logs = Column(JSONB, default=list)  # Array of log entries

    # Relations
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="SET NULL"), nullable=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    # Relationships
    project = relationship("Project", foreign_keys=[project_id])
    version = relationship("ProjectVersion", foreign_keys=[version_id])
    creator = relationship("User", foreign_keys=[created_by])

    __table_args__ = (
        Index('ix_jobs_project', 'project_id'),
        Index('ix_jobs_status', 'status'),
        Index('ix_jobs_type', 'job_type'),
    )

    def to_dict(self):
        """Convert to dictionary for API responses."""
        return {
            "id": str(self.id),
            "job_type": self.job_type,
            "status": self.status,
            "progress": self.progress,
            "message": self.message,
            "result": self.result,
            "error": self.error,
            "logs": self.logs or [],
            "project_id": str(self.project_id),
            "version_id": str(self.version_id) if self.version_id else None,
            "created_by": str(self.created_by),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }
