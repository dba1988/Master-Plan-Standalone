import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Asset(Base):
    __tablename__ = "assets"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)

    asset_type = Column(String(50), nullable=False)  # base_map, overlay_svg, icon, other
    level = Column(String(100), nullable=True)  # Hierarchy level: "project", "zone-a", "zone-gc", etc.
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=True)
    mime_type = Column(String(100), nullable=False)
    file_size = Column(Integer, nullable=False)  # bytes

    # Storage location
    storage_path = Column(String(500), nullable=False)  # R2/S3 path
    storage_url = Column(String(1000), nullable=True)  # CDN URL if applicable

    # Image-specific metadata
    width = Column(Integer, nullable=True)
    height = Column(Integer, nullable=True)

    # Tile-specific metadata
    tile_metadata = Column(JSONB, nullable=True)  # { levels, tileSize, format }

    # Processing status
    processing_status = Column(String(20), default="pending")  # pending, processing, completed, failed
    processing_error = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="assets")

    __table_args__ = (
        Index('ix_assets_project_type', 'project_id', 'asset_type'),
        Index('ix_assets_project_level', 'project_id', 'level'),
    )
