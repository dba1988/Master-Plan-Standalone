import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from app.lib.database import Base


class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False)
    version_number = Column(Integer, nullable=False)
    status = Column(String(20), default="draft")  # draft, published, archived
    published_at = Column(DateTime, nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="versions")
    publisher = relationship("User", foreign_keys=[published_by])
    config = relationship("ProjectConfig", back_populates="version", uselist=False, cascade="all, delete-orphan")
    assets = relationship("Asset", back_populates="version", cascade="all, delete-orphan")
    layers = relationship("Layer", back_populates="version", cascade="all, delete-orphan")
    overlays = relationship("Overlay", back_populates="version", cascade="all, delete-orphan")

    __table_args__ = (
        UniqueConstraint('project_id', 'version_number', name='uq_project_version'),
    )
