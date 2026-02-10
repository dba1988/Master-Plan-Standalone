"""
Asset schemas for upload workflow.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class AssetType(str, Enum):
    """Supported asset types."""
    BASE_MAP = "base_map"
    OVERLAY_SVG = "overlay_svg"
    ICON = "icon"
    OTHER = "other"


class UploadUrlRequest(BaseModel):
    """Request for a signed upload URL."""
    filename: str = Field(..., min_length=1, max_length=255)
    asset_type: AssetType
    content_type: str = Field(..., min_length=1, max_length=100)


class UploadUrlResponse(BaseModel):
    """Response with signed upload URL."""
    upload_url: str
    storage_path: str
    expires_in_seconds: int


class UploadConfirmRequest(BaseModel):
    """Request to confirm upload and create asset record."""
    storage_path: str = Field(..., min_length=1)
    asset_type: AssetType
    filename: str = Field(..., min_length=1, max_length=255)
    file_size: int = Field(..., gt=0)
    metadata: Optional[Dict[str, Any]] = None


class AssetResponse(BaseModel):
    """Asset response schema."""
    id: UUID
    asset_type: str
    filename: str
    original_filename: Optional[str] = None
    storage_path: str
    storage_url: Optional[str] = None
    file_size: int
    mime_type: str
    width: Optional[int] = None
    height: Optional[int] = None
    processing_status: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AssetListResponse(BaseModel):
    """List of assets response."""
    assets: list[AssetResponse]
    total: int


class AssetDownloadResponse(BaseModel):
    """Response with download URL."""
    download_url: str
    expires_in_seconds: int
