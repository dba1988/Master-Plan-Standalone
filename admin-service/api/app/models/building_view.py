"""
BuildingView Model

Represents a view angle/elevation/floor plan for a building.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class BuildingView(Base):
    __tablename__ = "building_views"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    view_type = Column(String(20), nullable=False)  # 'elevation' | 'rotation' | 'floor_plan'
    ref = Column(String(50), nullable=False)  # 'front', 'back', 'rotation-0', 'floor-15'
    label = Column(JSONB, nullable=True)  # {"en": "Front View", "ms": "Pandangan Hadapan"}
    angle = Column(Integer, nullable=True)  # 0, 15, 30... for rotation; NULL for elevation
    floor_number = Column(Integer, nullable=True)  # Only for floor_plan type
    view_box = Column(String(100), nullable=True)  # SVG viewBox for overlays
    asset_path = Column(String(500), nullable=True)  # R2 path to base image
    tiles_generated = Column(Boolean, default=False)
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    building = relationship("Building", back_populates="views")
    overlay_mappings = relationship("ViewOverlayMapping", back_populates="view", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('building_id', 'ref', name='uq_building_view_ref'),
        Index('ix_building_views_building', 'building_id'),
        Index('ix_building_views_type', 'view_type'),
        CheckConstraint(
            "(view_type = 'elevation' AND angle IS NULL AND floor_number IS NULL) OR "
            "(view_type = 'rotation' AND angle IS NOT NULL AND floor_number IS NULL) OR "
            "(view_type = 'floor_plan' AND floor_number IS NOT NULL)",
            name='ck_building_view_type_fields'
        ),
    )
