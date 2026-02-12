"""
Building Release Manifest Schemas

Defines the structure for building manifests in the release artifact.
"""
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class BuildingViewTiles(BaseModel):
    """Tile configuration for a building view."""
    tiles_url: str
    view_box: str
    width: int
    height: int
    tile_size: int = 256
    levels: int
    format: str = "webp"


class ElevationView(BaseModel):
    """Elevation view in building manifest."""
    ref: str
    label: Optional[Dict[str, str]] = None
    tiles_url: str
    view_box: str
    overlays_url: str


class RotationView(BaseModel):
    """Rotation view (single angle) in building manifest."""
    angle: int
    tiles_url: str
    view_box: Optional[str] = None
    overlays_url: str


class RotationConfig(BaseModel):
    """Configuration for rotation views."""
    total_angles: int
    angle_step: int
    default_angle: int = 0


class FloorPlanConfig(BaseModel):
    """Floor plan configuration."""
    available_floors: List[int] = []
    typical_floor: Optional[Dict[str, Any]] = None


class BuildingStackSummary(BaseModel):
    """Stack summary in building manifest."""
    ref: str
    label: Optional[Dict[str, str]] = None
    unit_type: Optional[str] = None
    facing: Optional[str] = None
    floors: List[int]  # [floor_start, floor_end]


class BuildingViews(BaseModel):
    """All views for a building."""
    elevations: List[ElevationView] = []
    rotations: List[RotationView] = []
    rotation_config: Optional[RotationConfig] = None


class BuildingConfig(BaseModel):
    """Building-specific configuration."""
    default_view: str = "front"
    status_styles: Dict[str, Any] = {}


class BuildingManifest(BaseModel):
    """
    Complete building manifest (buildings/{ref}.json).

    This defines all views, stacks, and floor plans for a single building.
    """
    version: int = 1
    building_ref: str
    name: Dict[str, str]
    floors_count: int
    floors_start: int = 1
    skip_floors: List[int] = []

    views: BuildingViews
    floor_plans: FloorPlanConfig = FloorPlanConfig()
    stacks: List[BuildingStackSummary] = []
    config: BuildingConfig = BuildingConfig()


class BuildingManifestInfo(BaseModel):
    """
    Building info in project manifest.

    Points to the full building manifest file.
    """
    ref: str
    name: Dict[str, str]
    manifest_path: str


class StackOverlay(BaseModel):
    """Stack overlay in view overlay file."""
    ref: str
    geometry: Dict[str, Any]
    label_position: Optional[Dict[str, float]] = None
    unit_type: Optional[str] = None
    floors_visible: List[int] = []  # [floor_start, floor_end]
    units_count: int = 0
    available_count: int = 0
    reserved_count: int = 0
    sold_count: int = 0


class ViewOverlayFile(BaseModel):
    """
    Overlay file for a specific view (overlays/{building}/{view}-stacks.json).

    Contains all stack/unit overlays for rendering on the view.
    """
    view_ref: str
    view_box: str
    stacks: List[StackOverlay] = []


class UnitOverlay(BaseModel):
    """Unit overlay in floor plan overlay file."""
    ref: str
    unit_number: str
    geometry: Dict[str, Any]
    label_position: Optional[Dict[str, float]] = None
    unit_type: Optional[str] = None
    status: str = "available"
    stack_ref: Optional[str] = None


class FloorPlanOverlayFile(BaseModel):
    """
    Overlay file for a floor plan (overlays/{building}/floor-{n}.json).

    Contains all unit overlays for a specific floor.
    """
    floor_number: int
    view_box: str
    units: List[UnitOverlay] = []
