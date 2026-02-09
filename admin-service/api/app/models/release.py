import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Release(Base):
    __tablename__ = "releases"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False)

    # Release metadata
    release_number = Column(Integer, nullable=False)
    release_tag = Column(String(50), nullable=True)  # v1.0.0, 2024-01-15, etc.

    # Snapshot storage
    snapshot_path = Column(String(500), nullable=False)  # R2 path to frozen JSON
    snapshot_url = Column(String(1000), nullable=True)  # CDN URL

    # Content hash for cache invalidation
    content_hash = Column(String(64), nullable=False)

    # Release status
    is_active = Column(Boolean, default=True)  # Current active release
    is_public = Column(Boolean, default=True)  # Visible to public viewer

    # Statistics snapshot at release time
    stats_snapshot = Column(JSONB, default=dict)  # { totalUnits, available, sold, etc. }

    # Publishing info
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    published_at = Column(DateTime, default=datetime.utcnow)

    # Rollback tracking
    superseded_by = Column(UUID(as_uuid=True), ForeignKey("releases.id"), nullable=True)
    superseded_at = Column(DateTime, nullable=True)

    version = relationship("ProjectVersion", foreign_keys=[version_id])
    publisher = relationship("User", foreign_keys=[published_by])
    superseding_release = relationship("Release", remote_side=[id], foreign_keys=[superseded_by])

    __table_args__ = (
        Index('ix_releases_version', 'version_id'),
        Index('ix_releases_active', 'is_active'),
    )
