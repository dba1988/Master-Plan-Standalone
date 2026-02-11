"""
BuildingStack Model

Represents a vertical stack of units (same position on each floor).
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class BuildingStack(Base):
    __tablename__ = "building_stacks"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    building_id = Column(UUID(as_uuid=True), ForeignKey("buildings.id", ondelete="CASCADE"), nullable=False)
    ref = Column(String(50), nullable=False)  # "A1", "B2", "C3"
    label = Column(JSONB, nullable=True)  # {"en": "Stack A1"}
    floor_start = Column(Integer, nullable=False)  # 1
    floor_end = Column(Integer, nullable=False)  # 70
    unit_type = Column(String(50), nullable=True)  # "1BR", "2BR", "Studio", "Penthouse"
    facing = Column(String(50), nullable=True)  # "North", "Sea View", "City View"
    metadata_ = Column("metadata", JSONB, default=dict)
    sort_order = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)

    building = relationship("Building", back_populates="stacks")
    units = relationship("BuildingUnit", back_populates="stack")

    __table_args__ = (
        UniqueConstraint('building_id', 'ref', name='uq_building_stack_ref'),
        Index('ix_building_stacks_building', 'building_id'),
    )
