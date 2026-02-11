"""
Building Model

Represents a tower/building within a project.
"""
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Building(Base):
    __tablename__ = "buildings"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    ref = Column(String(50), nullable=False)  # "tower-a", "building-1"
    name = Column(JSONB, nullable=False)  # {"en": "Tower A", "ms": "Menara A"}
    floors_count = Column(Integer, nullable=False)  # 70
    floors_start = Column(Integer, default=1)  # Some buildings start at G or -1
    skip_floors = Column(ARRAY(Integer), default=list)  # [4, 13, 14, 44]
    metadata_ = Column("metadata", JSONB, default=dict)  # {architect, year, totalUnits}
    sort_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="buildings")
    views = relationship("BuildingView", back_populates="building", cascade="all, delete-orphan")
    stacks = relationship("BuildingStack", back_populates="building", cascade="all, delete-orphan")
    units = relationship("BuildingUnit", back_populates="building", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', 'ref', name='uq_building_ref'),
        Index('ix_buildings_project', 'project_id'),
    )
