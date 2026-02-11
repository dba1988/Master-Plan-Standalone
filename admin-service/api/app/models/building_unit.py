"""
BuildingUnit Model

Represents an individual apartment/unit within a building.
"""
import uuid
from datetime import datetime
from decimal import Decimal
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Index, Numeric
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class BuildingUnit(Base):
    __tablename__ = "building_units"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    stack_id = Column(UUID(as_uuid=True), ForeignKey("building_stacks.id", ondelete="SET NULL"), nullable=True)
    ref = Column(String(50), nullable=False)  # "A-15-01" (building-floor-unit)
    floor_number = Column(Integer, nullable=False)
    unit_number = Column(String(20), nullable=False)  # "01", "02", "A", "B"
    unit_type = Column(String(50), nullable=True)  # "1BR", "2BR"
    area_sqm = Column(Numeric(10, 2), nullable=True)
    area_sqft = Column(Numeric(10, 2), nullable=True)
    status = Column(String(20), default="available")  # available, reserved, sold, hidden
    price = Column(Numeric(15, 2), nullable=True)
    props = Column(JSONB, default=dict)  # {bedrooms, bathrooms, balcony}
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    building = relationship("Building", back_populates="units")
    stack = relationship("BuildingStack", back_populates="units")
    overlay_mappings = relationship("ViewOverlayMapping", back_populates="unit", foreign_keys="ViewOverlayMapping.unit_id")

    __table_args__ = (
        UniqueConstraint('building_id', 'ref', name='uq_building_unit_ref'),
        Index('ix_building_units_building', 'building_id'),
        Index('ix_building_units_floor', 'building_id', 'floor_number'),
        Index('ix_building_units_stack', 'stack_id'),
        Index('ix_building_units_status', 'status'),
    )
