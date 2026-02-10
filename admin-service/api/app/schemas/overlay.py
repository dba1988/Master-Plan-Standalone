"""
Overlay schemas for CRUD operations.
"""
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class OverlayType(str, Enum):
    """Supported overlay types."""
    ZONE = "zone"
    UNIT = "unit"
    POI = "poi"


class PathGeometry(BaseModel):
    """Path-based geometry for complex shapes."""
    type: str = "path"
    d: str = Field(..., description="SVG path data")


class PointGeometry(BaseModel):
    """Point geometry for POIs."""
    type: str = "point"
    x: float
    y: float


# Union type for geometry
Geometry = Union[PathGeometry, PointGeometry, Dict[str, Any]]


class LocalizedLabel(BaseModel):
    """Localized label with English and Arabic."""
    en: Optional[str] = None
    ar: Optional[str] = None


class OverlayCreate(BaseModel):
    """Schema for creating an overlay."""
    overlay_type: OverlayType
    ref: str = Field(..., min_length=1, max_length=255)
    geometry: Dict[str, Any] = Field(..., description="Path or point geometry")
    view_box: Optional[str] = Field(None, max_length=100)
    label: Optional[Dict[str, str]] = None
    label_position: Optional[List[float]] = Field(None, description="[x, y] coordinates")
    props: Optional[Dict[str, Any]] = None
    style_override: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = 0
    is_visible: Optional[bool] = True
    layer_id: Optional[UUID] = None

    @field_validator('geometry')
    @classmethod
    def validate_geometry(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if 'type' not in v:
            raise ValueError("Geometry must have a 'type' field")
        geo_type = v['type']
        if geo_type == 'path' and 'd' not in v:
            raise ValueError("Path geometry must have a 'd' field")
        if geo_type == 'point' and ('x' not in v or 'y' not in v):
            raise ValueError("Point geometry must have 'x' and 'y' fields")
        return v

    @field_validator('label_position')
    @classmethod
    def validate_label_position(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None and len(v) != 2:
            raise ValueError("label_position must be [x, y]")
        return v


class OverlayUpdate(BaseModel):
    """Schema for updating an overlay."""
    overlay_type: Optional[OverlayType] = None
    ref: Optional[str] = Field(None, min_length=1, max_length=255)
    geometry: Optional[Dict[str, Any]] = None
    view_box: Optional[str] = Field(None, max_length=100)
    label: Optional[Dict[str, str]] = None
    label_position: Optional[List[float]] = None
    props: Optional[Dict[str, Any]] = None
    style_override: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    layer_id: Optional[UUID] = None

    @field_validator('geometry')
    @classmethod
    def validate_geometry(cls, v: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if v is None:
            return v
        if 'type' not in v:
            raise ValueError("Geometry must have a 'type' field")
        geo_type = v['type']
        if geo_type == 'path' and 'd' not in v:
            raise ValueError("Path geometry must have a 'd' field")
        if geo_type == 'point' and ('x' not in v or 'y' not in v):
            raise ValueError("Point geometry must have 'x' and 'y' fields")
        return v

    @field_validator('label_position')
    @classmethod
    def validate_label_position(cls, v: Optional[List[float]]) -> Optional[List[float]]:
        if v is not None and len(v) != 2:
            raise ValueError("label_position must be [x, y]")
        return v


class OverlayResponse(BaseModel):
    """Overlay response schema."""
    id: UUID
    overlay_type: str
    ref: str
    geometry: Dict[str, Any]
    view_box: Optional[str] = None
    label: Optional[Dict[str, str]] = None
    label_position: Optional[List[float]] = None
    status: str
    props: Optional[Dict[str, Any]] = None
    style_override: Optional[Dict[str, Any]] = None
    sort_order: int
    is_visible: bool
    layer_id: Optional[UUID] = None
    source_level: Optional[str] = None  # Asset level: "project", "zone-a", etc.
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class OverlayListResponse(BaseModel):
    """List of overlays response."""
    overlays: List[OverlayResponse]
    total: int


class BulkOverlayItem(BaseModel):
    """Single overlay for bulk upsert."""
    overlay_type: OverlayType
    ref: str = Field(..., min_length=1, max_length=255)
    geometry: Dict[str, Any]
    view_box: Optional[str] = None
    label: Optional[Dict[str, str]] = None
    label_position: Optional[List[float]] = None
    props: Optional[Dict[str, Any]] = None
    style_override: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = 0
    is_visible: Optional[bool] = True
    layer_id: Optional[UUID] = None
    source_level: Optional[str] = None  # Asset level: "project", "zone-a", etc.

    @field_validator('geometry')
    @classmethod
    def validate_geometry(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if 'type' not in v:
            raise ValueError("Geometry must have a 'type' field")
        return v


class BulkUpsertRequest(BaseModel):
    """Request for bulk overlay upsert."""
    overlays: List[BulkOverlayItem] = Field(..., min_length=1)


class BulkUpsertError(BaseModel):
    """Error detail for bulk upsert."""
    index: int
    ref: str
    error: str


class BulkUpsertResponse(BaseModel):
    """Response from bulk upsert operation."""
    created: int
    updated: int
    errors: List[BulkUpsertError]
