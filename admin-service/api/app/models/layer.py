import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Layer(Base):
    __tablename__ = "layers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False)

    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=True)
    slug = Column(String(100), nullable=False)

    layer_type = Column(String(50), default="overlay")  # base, overlay, annotation

    # Display settings
    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)
    is_interactive = Column(Boolean, default=True)

    # Zoom constraints
    min_zoom = Column(Integer, nullable=True)
    max_zoom = Column(Integer, nullable=True)

    # Style configuration
    default_style = Column(JSONB, default=dict)  # { fill, stroke, opacity }

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    version = relationship("ProjectVersion", back_populates="layers")
    overlays = relationship("Overlay", back_populates="layer")

    __table_args__ = (
        Index('ix_layers_version', 'version_id'),
    )
