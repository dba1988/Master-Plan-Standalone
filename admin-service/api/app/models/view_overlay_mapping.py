"""
ViewOverlayMapping Model

Maps overlay geometry to a specific view for stacks or units.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class ViewOverlayMapping(Base):
    __tablename__ = "view_overlay_mappings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    view_id = Column(UUID(as_uuid=True), ForeignKey("building_views.id", ondelete="CASCADE"), nullable=False)
    target_type = Column(String(20), nullable=False)  # 'stack' | 'unit'
    # Reference to either stack or unit
    stack_id = Column(UUID(as_uuid=True), ForeignKey("building_stacks.id", ondelete="CASCADE"), nullable=True)
    unit_id = Column(UUID(as_uuid=True), ForeignKey("building_units.id", ondelete="CASCADE"), nullable=True)
    geometry = Column(JSONB, nullable=False)  # {type: "path", d: "M..."}
    label_position = Column(JSONB, nullable=True)  # {x: 100, y: 200}
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    view = relationship("BuildingView", back_populates="overlay_mappings")
    stack = relationship("BuildingStack", foreign_keys=[stack_id])
    unit = relationship("BuildingUnit", back_populates="overlay_mappings", foreign_keys=[unit_id])

    __table_args__ = (
        UniqueConstraint('view_id', 'target_type', 'stack_id', name='uq_view_stack_mapping'),
        UniqueConstraint('view_id', 'target_type', 'unit_id', name='uq_view_unit_mapping'),
        Index('ix_overlay_mappings_view', 'view_id'),
        Index('ix_overlay_mappings_target', 'target_type'),
    )
