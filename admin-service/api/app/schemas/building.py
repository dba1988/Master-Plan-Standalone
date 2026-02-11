"""
Building schemas for CRUD operations.
"""
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ViewType(str, Enum):
    """Building view types."""
    ELEVATION = "elevation"
    ROTATION = "rotation"
    FLOOR_PLAN = "floor_plan"


class UnitStatus(str, Enum):
    """Unit availability status."""
    AVAILABLE = "available"
    RESERVED = "reserved"
    SOLD = "sold"
    HIDDEN = "hidden"


# ============================================
# BUILDING SCHEMAS
# ============================================

class BuildingCreate(BaseModel):
    """Schema for creating a building."""
    ref: str = Field(..., min_length=1, max_length=50)
    name: Dict[str, str] = Field(..., description="Localized name {'en': 'Tower A'}")
    floors_count: int = Field(..., gt=0)
    floors_start: int = Field(default=1)
    skip_floors: List[int] = Field(default_factory=list, description="Floors to skip [4, 13, 14]")
    metadata: Optional[Dict[str, Any]] = None
    sort_order: int = Field(default=0)


class BuildingUpdate(BaseModel):
    """Schema for updating a building."""
    ref: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[Dict[str, str]] = None
    floors_count: Optional[int] = Field(None, gt=0)
    floors_start: Optional[int] = None
    skip_floors: Optional[List[int]] = None
    metadata: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class BuildingResponse(BaseModel):
    """Building response schema."""
    id: UUID
    project_id: UUID
    ref: str
    name: Dict[str, str]
    floors_count: int
    floors_start: int
    skip_floors: List[int]
    metadata: Optional[Dict[str, Any]] = None
    sort_order: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuildingListResponse(BaseModel):
    """List of buildings response."""
    buildings: List[BuildingResponse]
    total: int


class BuildingSummary(BaseModel):
    """Brief building summary for listing."""
    id: UUID
    ref: str
    name: Dict[str, str]
    floors_count: int
    views_count: int = 0
    units_count: int = 0

    class Config:
        from_attributes = True


# ============================================
# BUILDING VIEW SCHEMAS
# ============================================

class BuildingViewCreate(BaseModel):
    """Schema for creating a building view."""
    view_type: ViewType
    ref: str = Field(..., min_length=1, max_length=50)
    label: Optional[Dict[str, str]] = None
    angle: Optional[int] = Field(None, ge=0, lt=360)
    floor_number: Optional[int] = None
    view_box: Optional[str] = Field(None, max_length=100)
    asset_path: Optional[str] = Field(None, max_length=500)
    sort_order: int = Field(default=0)

    @field_validator('angle')
    @classmethod
    def validate_angle_for_rotation(cls, v, info):
        view_type = info.data.get('view_type')
        if view_type == ViewType.ROTATION and v is None:
            raise ValueError("angle is required for rotation views")
        return v

    @field_validator('floor_number')
    @classmethod
    def validate_floor_for_floor_plan(cls, v, info):
        view_type = info.data.get('view_type')
        if view_type == ViewType.FLOOR_PLAN and v is None:
            raise ValueError("floor_number is required for floor_plan views")
        return v


class BuildingViewUpdate(BaseModel):
    """Schema for updating a building view."""
    view_type: Optional[ViewType] = None
    ref: Optional[str] = Field(None, min_length=1, max_length=50)
    label: Optional[Dict[str, str]] = None
    angle: Optional[int] = Field(None, ge=0, lt=360)
    floor_number: Optional[int] = None
    view_box: Optional[str] = Field(None, max_length=100)
    asset_path: Optional[str] = Field(None, max_length=500)
    tiles_generated: Optional[bool] = None
    sort_order: Optional[int] = None
    is_active: Optional[bool] = None


class BuildingViewResponse(BaseModel):
    """Building view response schema."""
    id: UUID
    building_id: UUID
    view_type: str
    ref: str
    label: Optional[Dict[str, str]] = None
    angle: Optional[int] = None
    floor_number: Optional[int] = None
    view_box: Optional[str] = None
    asset_path: Optional[str] = None
    tiles_generated: bool
    sort_order: int
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class BuildingViewListResponse(BaseModel):
    """List of building views response."""
    views: List[BuildingViewResponse]
    total: int


# ============================================
# STACK SCHEMAS
# ============================================

class StackCreate(BaseModel):
    """Schema for creating a stack."""
    ref: str = Field(..., min_length=1, max_length=50)
    label: Optional[Dict[str, str]] = None
    floor_start: int = Field(..., ge=0)
    floor_end: int = Field(..., ge=0)
    unit_type: Optional[str] = Field(None, max_length=50)
    facing: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    sort_order: int = Field(default=0)

    @field_validator('floor_end')
    @classmethod
    def validate_floor_range(cls, v, info):
        floor_start = info.data.get('floor_start')
        if floor_start is not None and v < floor_start:
            raise ValueError("floor_end must be >= floor_start")
        return v


class StackUpdate(BaseModel):
    """Schema for updating a stack."""
    ref: Optional[str] = Field(None, min_length=1, max_length=50)
    label: Optional[Dict[str, str]] = None
    floor_start: Optional[int] = Field(None, ge=0)
    floor_end: Optional[int] = Field(None, ge=0)
    unit_type: Optional[str] = Field(None, max_length=50)
    facing: Optional[str] = Field(None, max_length=50)
    metadata: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None


class StackResponse(BaseModel):
    """Stack response schema."""
    id: UUID
    building_id: UUID
    ref: str
    label: Optional[Dict[str, str]] = None
    floor_start: int
    floor_end: int
    unit_type: Optional[str] = None
    facing: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    sort_order: int
    created_at: datetime
    units_count: int = 0

    class Config:
        from_attributes = True


class StackListResponse(BaseModel):
    """List of stacks response."""
    stacks: List[StackResponse]
    total: int


class BulkStackItem(BaseModel):
    """Single stack for bulk upsert."""
    ref: str = Field(..., min_length=1, max_length=50)
    label: Optional[Dict[str, str]] = None
    floor_start: int = Field(..., ge=0)
    floor_end: int = Field(..., ge=0)
    unit_type: Optional[str] = None
    facing: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None
    sort_order: int = Field(default=0)


class BulkStackRequest(BaseModel):
    """Request for bulk stack upsert."""
    stacks: List[BulkStackItem] = Field(..., min_length=1)


# ============================================
# BUILDING UNIT SCHEMAS
# ============================================

class BuildingUnitCreate(BaseModel):
    """Schema for creating a building unit."""
    ref: str = Field(..., min_length=1, max_length=50)
    floor_number: int
    unit_number: str = Field(..., min_length=1, max_length=20)
    stack_id: Optional[UUID] = None
    unit_type: Optional[str] = Field(None, max_length=50)
    area_sqm: Optional[Decimal] = Field(None, ge=0)
    area_sqft: Optional[Decimal] = Field(None, ge=0)
    status: UnitStatus = Field(default=UnitStatus.AVAILABLE)
    price: Optional[Decimal] = Field(None, ge=0)
    props: Optional[Dict[str, Any]] = None


class BuildingUnitUpdate(BaseModel):
    """Schema for updating a building unit."""
    ref: Optional[str] = Field(None, min_length=1, max_length=50)
    floor_number: Optional[int] = None
    unit_number: Optional[str] = Field(None, min_length=1, max_length=20)
    stack_id: Optional[UUID] = None
    unit_type: Optional[str] = Field(None, max_length=50)
    area_sqm: Optional[Decimal] = Field(None, ge=0)
    area_sqft: Optional[Decimal] = Field(None, ge=0)
    status: Optional[UnitStatus] = None
    price: Optional[Decimal] = Field(None, ge=0)
    props: Optional[Dict[str, Any]] = None


class BuildingUnitResponse(BaseModel):
    """Building unit response schema."""
    id: UUID
    building_id: UUID
    stack_id: Optional[UUID] = None
    ref: str
    floor_number: int
    unit_number: str
    unit_type: Optional[str] = None
    area_sqm: Optional[Decimal] = None
    area_sqft: Optional[Decimal] = None
    status: str
    price: Optional[Decimal] = None
    props: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class BuildingUnitListResponse(BaseModel):
    """List of building units response."""
    units: List[BuildingUnitResponse]
    total: int


class GenerateUnitsRequest(BaseModel):
    """Request to auto-generate units from stacks."""
    stack_ids: Optional[List[UUID]] = Field(None, description="Specific stacks, or None for all")
    unit_type_override: Optional[str] = None
    skip_floors: Optional[List[int]] = None


class GenerateUnitsResponse(BaseModel):
    """Response from unit generation."""
    created: int
    skipped: int
    message: str


# ============================================
# VIEW OVERLAY MAPPING SCHEMAS
# ============================================

class OverlayMappingCreate(BaseModel):
    """Schema for creating an overlay mapping."""
    target_type: str = Field(..., pattern="^(stack|unit)$")
    stack_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    geometry: Dict[str, Any] = Field(..., description="SVG path geometry")
    label_position: Optional[Dict[str, float]] = None
    sort_order: int = Field(default=0)

    @field_validator('geometry')
    @classmethod
    def validate_geometry(cls, v: Dict[str, Any]) -> Dict[str, Any]:
        if 'type' not in v:
            raise ValueError("Geometry must have a 'type' field")
        if v['type'] == 'path' and 'd' not in v:
            raise ValueError("Path geometry must have a 'd' field")
        return v

    @field_validator('stack_id')
    @classmethod
    def validate_stack_for_type(cls, v, info):
        target_type = info.data.get('target_type')
        if target_type == 'stack' and v is None:
            raise ValueError("stack_id is required when target_type is 'stack'")
        return v

    @field_validator('unit_id')
    @classmethod
    def validate_unit_for_type(cls, v, info):
        target_type = info.data.get('target_type')
        if target_type == 'unit' and v is None:
            raise ValueError("unit_id is required when target_type is 'unit'")
        return v


class OverlayMappingResponse(BaseModel):
    """Overlay mapping response schema."""
    id: UUID
    view_id: UUID
    target_type: str
    stack_id: Optional[UUID] = None
    unit_id: Optional[UUID] = None
    geometry: Dict[str, Any]
    label_position: Optional[Dict[str, float]] = None
    sort_order: int
    created_at: datetime

    class Config:
        from_attributes = True


class OverlayMappingListResponse(BaseModel):
    """List of overlay mappings response."""
    mappings: List[OverlayMappingResponse]
    total: int


class BulkOverlayMappingItem(BaseModel):
    """Single overlay mapping for bulk upsert."""
    target_type: str = Field(..., pattern="^(stack|unit)$")
    target_ref: str = Field(..., description="Stack or unit ref")
    geometry: Dict[str, Any]
    label_position: Optional[Dict[str, float]] = None
    sort_order: int = Field(default=0)


class BulkOverlayMappingRequest(BaseModel):
    """Request for bulk overlay mapping upsert."""
    mappings: List[BulkOverlayMappingItem] = Field(..., min_length=1)


class BulkOverlayMappingResponse(BaseModel):
    """Response from bulk overlay mapping upsert."""
    created: int
    updated: int
    errors: List[Dict[str, Any]]
