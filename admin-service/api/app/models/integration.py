import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.lib.database import Base


class IntegrationConfig(Base):
    __tablename__ = "integration_configs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, unique=True)

    # Client API integration (for status polling)
    api_base_url = Column(String(500), nullable=True)
    auth_type = Column(String(20), default="none")  # none, bearer, api_key, basic
    auth_credentials = Column(String(1000), nullable=True)  # Encrypted credentials (Fernet)
    status_endpoint = Column(String(255), nullable=True)  # Relative path e.g. /api/units/status
    status_mapping = Column(JSONB, default=dict)  # Maps client status to canonical 5-status
    update_method = Column(String(20), default="polling")  # polling, sse, webhook
    polling_interval_seconds = Column(Integer, default=30)
    timeout_seconds = Column(Integer, default=10)
    retry_count = Column(Integer, default=3)

    # CRM integration
    crm_enabled = Column(Boolean, default=False)
    crm_type = Column(String(50), nullable=True)  # salesforce, hubspot, custom
    crm_config = Column(JSONB, default=dict)  # { apiUrl, apiKey, mappings }

    # Webhook configuration
    webhook_enabled = Column(Boolean, default=False)
    webhook_url = Column(String(500), nullable=True)
    webhook_secret = Column(String(255), nullable=True)
    webhook_events = Column(JSONB, default=list)  # ["status_change", "inquiry"]

    # Analytics integration
    analytics_enabled = Column(Boolean, default=False)
    analytics_config = Column(JSONB, default=dict)  # { gaId, gtmId }

    # Sync settings
    last_sync_at = Column(DateTime, nullable=True)
    sync_status = Column(String(20), default="idle")  # idle, syncing, error
    sync_error = Column(String(500), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    project = relationship("Project", back_populates="integration_config")
