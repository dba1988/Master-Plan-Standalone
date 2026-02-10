"""
Integration Config schemas.

Handles client API integration configuration with encrypted credentials.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class AuthType(str, Enum):
    """Supported authentication types."""
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"


class UpdateMethod(str, Enum):
    """Supported update methods."""
    POLLING = "polling"
    SSE = "sse"
    WEBHOOK = "webhook"


# Default status mapping - matches STATUS-TAXONOMY.md
DEFAULT_STATUS_MAPPING = {
    "available": ["Available", "AVAILABLE", "available", "Open", "OPEN", "open"],
    "reserved": ["Reserved", "RESERVED", "reserved", "Hold", "HOLD", "hold", "OnHold", "Pending", "PENDING"],
    "sold": ["Sold", "SOLD", "sold", "Purchased", "PURCHASED", "purchased", "Closed", "CLOSED"],
    "hidden": ["Hidden", "HIDDEN", "hidden", "Unavailable", "UNAVAILABLE", "NotForSale", "Blocked", "BLOCKED"],
    "unreleased": ["Unreleased", "UNRELEASED", "unreleased", "Future", "FUTURE", "ComingSoon", "COMING_SOON"]
}


class BearerCredentials(BaseModel):
    """Bearer token credentials."""
    token: str


class ApiKeyCredentials(BaseModel):
    """API key credentials."""
    api_key: str
    api_key_header: str = "X-API-Key"


class BasicCredentials(BaseModel):
    """Basic auth credentials."""
    username: str
    password: str


class IntegrationConfigUpdate(BaseModel):
    """Schema for updating integration configuration."""
    api_base_url: Optional[str] = Field(None, max_length=500)
    auth_type: Optional[AuthType] = None
    auth_credentials: Optional[Dict[str, str]] = Field(
        None,
        description="Credentials based on auth_type. Will be encrypted before storage."
    )
    status_endpoint: Optional[str] = Field(None, max_length=255)
    status_mapping: Optional[Dict[str, List[str]]] = None
    update_method: Optional[UpdateMethod] = None
    polling_interval_seconds: Optional[int] = Field(None, ge=5, le=300)
    timeout_seconds: Optional[int] = Field(None, ge=1, le=60)
    retry_count: Optional[int] = Field(None, ge=0, le=10)

    @field_validator('api_base_url')
    @classmethod
    def validate_url(cls, v: Optional[str]) -> Optional[str]:
        if v and not (v.startswith('http://') or v.startswith('https://')):
            raise ValueError('api_base_url must start with http:// or https://')
        return v

    @field_validator('status_endpoint')
    @classmethod
    def validate_endpoint(cls, v: Optional[str]) -> Optional[str]:
        if v and not v.startswith('/'):
            raise ValueError('status_endpoint must start with /')
        return v


class IntegrationConfigResponse(BaseModel):
    """Integration configuration response (credentials hidden)."""
    id: UUID
    project_id: UUID
    api_base_url: Optional[str] = None
    auth_type: str
    status_endpoint: Optional[str] = None
    status_mapping: Dict[str, List[str]]
    update_method: str
    polling_interval_seconds: int
    timeout_seconds: int
    retry_count: int
    has_credentials: bool
    last_sync_at: Optional[datetime] = None
    sync_status: str
    sync_error: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ConnectionTestRequest(BaseModel):
    """Optional override for connection test."""
    api_base_url: Optional[str] = None
    status_endpoint: Optional[str] = None


class ConnectionTestResponse(BaseModel):
    """Response from connection test."""
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    sample_data: Optional[List[Dict[str, Any]]] = None
    error: Optional[str] = None


class StatusMappingResult(BaseModel):
    """Result of status mapping."""
    original_status: str
    canonical_status: str
    matched: bool
