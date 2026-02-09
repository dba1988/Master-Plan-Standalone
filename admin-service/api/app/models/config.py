import uuid
from datetime import datetime
from sqlalchemy import Column, String, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class ProjectConfig(Base):
    __tablename__ = "project_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Theme configuration
    theme = Column(JSONB, default=dict)  # { primaryColor, fontFamily, etc. }

    # Map settings
    map_settings = Column(JSONB, default=dict)  # { initialZoom, minZoom, maxZoom, bounds }

    # Status colors (5-status taxonomy)
    status_colors = Column(JSONB, default=lambda: {
        "available": "#52c41a",
        "reserved": "#faad14",
        "sold": "#ff4d4f",
        "hidden": "#8c8c8c",
        "unreleased": "#d9d9d9"
    })

    # Popup/tooltip configuration
    popup_config = Column(JSONB, default=dict)  # { showPrice, showArea, fields[] }

    # Filter configuration
    filter_config = Column(JSONB, default=dict)  # { enableStatusFilter, enableLayerFilter }

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    version = relationship("ProjectVersion", back_populates="config")
