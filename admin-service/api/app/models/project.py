import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.lib.database import Base


class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    current_release_id = Column(String(50), nullable=True)  # Active release ID
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    creator = relationship("User", back_populates="projects", foreign_keys=[created_by])
    versions = relationship("ProjectVersion", back_populates="project", cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="project", cascade="all, delete-orphan")
    overlays = relationship("Overlay", back_populates="project", cascade="all, delete-orphan")
    config = relationship("ProjectConfig", back_populates="project", uselist=False, cascade="all, delete-orphan")
    integration_config = relationship("IntegrationConfig", back_populates="project", uselist=False, cascade="all, delete-orphan")
    buildings = relationship("Building", back_populates="project", cascade="all, delete-orphan")
