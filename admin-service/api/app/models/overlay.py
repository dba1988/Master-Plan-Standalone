import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Overlay(Base):
    __tablename__ = "overlays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False)
    layer_id = Column(UUID(as_uuid=True), ForeignKey("layers.id", ondelete="SET NULL"), nullable=True)

    overlay_type = Column(String(20), nullable=False)  # zone, unit, poi
    ref = Column(String(255), nullable=False)  # External reference (lot number, zone id)

    # Geometry data
    geometry = Column(JSONB, nullable=False)  # { type: "path", d: "M..." } or { type: "polygon", points: [...] }
    view_box = Column(String(100), nullable=True)  # SVG viewBox if applicable

    # Labels
    label = Column(JSONB, nullable=True)  # { en: "Zone A", ar: "..." }
    label_position = Column(JSONB, nullable=True)  # { x, y } or [x, y]

    # 5-status taxonomy
    status = Column(String(20), default="available")  # available, reserved, sold, hidden, unreleased

    # Custom properties
    props = Column(JSONB, default=dict)  # { area, price, bedrooms, etc. }
    style_override = Column(JSONB, nullable=True)  # Override layer default style

    # Display settings
    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    version = relationship("ProjectVersion", back_populates="overlays")
    layer = relationship("Layer", back_populates="overlays")

    __table_args__ = (
        UniqueConstraint('version_id', 'overlay_type', 'ref', name='uq_overlay_ref'),
        Index('ix_overlays_version', 'version_id'),
        Index('ix_overlays_type', 'overlay_type'),
        Index('ix_overlays_ref', 'ref'),
        Index('ix_overlays_status', 'status'),
    )
