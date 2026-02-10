"""Release manifest schemas."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TileConfig(BaseModel):
    """Tile configuration in release manifest."""
    base_url: str = "tiles"
    format: str = "dzi"
    tile_size: int = 256
    overlap: int = 1
    levels: int = Field(ge=1)
    width: int = Field(ge=1)
    height: int = Field(ge=1)


class ZoomConfig(BaseModel):
    """Zoom configuration."""
    min: float = 0.5
    max: float = 3.0
    default: float = 1.0


class ReleaseConfig(BaseModel):
    """Project configuration in release manifest."""
    default_view_box: str
    default_zoom: ZoomConfig
    default_locale: str = "en"
    supported_locales: List[str] = ["en"]
    status_styles: Dict[str, Any] = {}
    interaction_styles: Dict[str, Any] = {}


class ReleaseOverlay(BaseModel):
    """Overlay in release manifest."""
    ref: str
    overlay_type: str
    geometry: Dict[str, Any]
    label: Optional[Dict[str, str]] = None
    label_position: Optional[List[float]] = None
    props: Dict[str, Any] = {}
    layer: Optional[str] = None
    sort_order: int = 0


class ReleaseManifest(BaseModel):
    """
    Complete release.json manifest.

    This is the contract between admin-service and public-service.
    Once published, this file is immutable.
    """
    version: int = 3  # Manifest schema version
    release_id: str
    project_slug: str
    published_at: datetime
    published_by: str

    config: ReleaseConfig
    tiles: Optional[TileConfig] = None
    overlays: List[ReleaseOverlay] = []

    checksum: str = Field(..., description="SHA256 hash of overlay data")

    model_config = {"json_schema_extra": {
        "example": {
            "version": 3,
            "release_id": "rel_20240115100000_a1b2c3d4",
            "project_slug": "my-project",
            "published_at": "2024-01-15T10:00:00Z",
            "published_by": "user@example.com",
            "config": {
                "default_view_box": "0 0 4096 4096",
                "default_zoom": {"min": 0.5, "max": 3.0, "default": 1.0},
                "default_locale": "en",
                "supported_locales": ["en", "ar"],
                "status_styles": {}
            },
            "tiles": {
                "base_url": "tiles",
                "format": "dzi",
                "tile_size": 256,
                "overlap": 1,
                "levels": 5,
                "width": 4096,
                "height": 4096
            },
            "overlays": [
                {
                    "ref": "UNIT-001",
                    "overlay_type": "unit",
                    "geometry": {"type": "path", "d": "M100,100..."},
                    "label": {"en": "Unit 1"},
                    "label_position": [150, 150],
                    "props": {}
                }
            ],
            "checksum": "sha256:abc123..."
        }
    }}


class PublishRequest(BaseModel):
    """Request to publish a version."""
    target_environment: str = Field(default="production")


class PublishResponse(BaseModel):
    """Response after starting publish job."""
    job_id: UUID
    status: str = "queued"
    message: str = "Publish job started"


class PublishValidationResponse(BaseModel):
    """Response from validation check."""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []


class BuildRequest(BaseModel):
    """Request to start a build job."""
    pass  # No options needed for now, could add force_rebuild etc.


class BuildTilesInfo(BaseModel):
    """Tile generation info in build response."""
    levels: List[str] = []
    total_count: int = 0
    metadata: Dict[str, Any] = {}


class BuildStatusResponse(BaseModel):
    """Response for build status check."""
    has_build: bool
    build_id: Optional[str] = None
    build_path: Optional[str] = None
    preview_url: Optional[str] = None
    built_at: Optional[datetime] = None
    overlay_count: int = 0
    tiles: Optional[BuildTilesInfo] = None


class BuildValidationResponse(BaseModel):
    """Response from build validation check."""
    valid: bool
    errors: List[str] = []
    warnings: List[str] = []
    base_map_count: int = 0
    overlay_count: int = 0


class ReleaseHistoryItem(BaseModel):
    """Single release in history."""
    version_number: int
    release_id: str
    release_url: Optional[str] = None
    published_at: datetime
    published_by: Optional[str] = None  # User email
    overlay_count: Optional[int] = None
    is_current: bool = False


class ReleaseHistoryResponse(BaseModel):
    """Response for release history."""
    project_slug: str
    current_release_id: Optional[str] = None
    releases: List[ReleaseHistoryItem] = []
    total: int = 0
