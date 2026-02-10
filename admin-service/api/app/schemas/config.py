"""
Project Config schemas.

Configuration includes theme, map settings, status colors, popup config, and filter config.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


# Default status colors - matches gsd/parity/STATUS-TAXONOMY.md
DEFAULT_STATUS_COLORS = {
    "available": {
        "fill": "rgba(75, 156, 85, 0.50)",
        "fillOpacity": 0.7,
        "stroke": "#FFFFFF",
        "strokeWidth": 1,
        "solid": "#4B9C55"
    },
    "reserved": {
        "fill": "rgba(255, 193, 7, 0.60)",
        "fillOpacity": 0.6,
        "stroke": "#FFFFFF",
        "strokeWidth": 1,
        "solid": "#FFC107"
    },
    "sold": {
        "fill": "rgba(170, 70, 55, 0.60)",
        "fillOpacity": 0.5,
        "stroke": "#FFFFFF",
        "strokeWidth": 1,
        "solid": "#AA4637"
    },
    "hidden": {
        "fill": "rgba(158, 158, 158, 0.30)",
        "fillOpacity": 0.3,
        "stroke": "#FFFFFF",
        "strokeWidth": 1,
        "solid": "#9E9E9E"
    },
    "unreleased": {
        "fill": "transparent",
        "fillOpacity": 0,
        "stroke": "transparent",
        "strokeWidth": 0,
        "solid": "#616161"
    }
}

# Default interaction colors
DEFAULT_INTERACTION_COLORS = {
    "hover": {
        "fill": "rgba(218, 165, 32, 0.3)",
        "stroke": "#F1DA9E",
        "strokeWidth": 2
    },
    "active": {
        "fill": "rgba(63, 82, 119, 0.4)",
        "stroke": "#3F5277",
        "strokeWidth": 2
    }
}

# Default map settings
DEFAULT_MAP_SETTINGS = {
    "defaultViewBox": "0 0 4096 4096",
    "zoom": {
        "min": 0.5,
        "max": 4.0,
        "default": 1.0
    },
    "baseTilesPath": None
}

# Default theme
DEFAULT_THEME = {
    "primaryColor": "#3F5277",
    "secondaryColor": "#DAA520",
    "fontFamily": "'IBM Plex Sans Arabic', Arial, sans-serif",
    "defaultLocale": "en",
    "supportedLocales": ["en", "ar"]
}


class ZoomConfig(BaseModel):
    """Zoom level configuration."""
    min: float = 0.5
    max: float = 4.0
    default: float = 1.0


class MapSettingsUpdate(BaseModel):
    """Map settings for update."""
    defaultViewBox: Optional[str] = None
    zoom: Optional[ZoomConfig] = None
    baseTilesPath: Optional[str] = None


class ThemeUpdate(BaseModel):
    """Theme configuration for update."""
    primaryColor: Optional[str] = None
    secondaryColor: Optional[str] = None
    fontFamily: Optional[str] = None
    defaultLocale: Optional[str] = None
    supportedLocales: Optional[List[str]] = None


class PopupConfigUpdate(BaseModel):
    """Popup/tooltip configuration for update."""
    enabled: Optional[bool] = None
    showPrice: Optional[bool] = None
    showArea: Optional[bool] = None
    showStatus: Optional[bool] = None
    fields: Optional[List[str]] = None


class FilterConfigUpdate(BaseModel):
    """Filter configuration for update."""
    enableStatusFilter: Optional[bool] = None
    enableTypeFilter: Optional[bool] = None
    enableLayerFilter: Optional[bool] = None
    defaultStatuses: Optional[List[str]] = None


class ProjectConfigUpdate(BaseModel):
    """Schema for updating project configuration."""
    theme: Optional[Dict[str, Any]] = None
    map_settings: Optional[Dict[str, Any]] = None
    status_colors: Optional[Dict[str, Any]] = None
    popup_config: Optional[Dict[str, Any]] = None
    filter_config: Optional[Dict[str, Any]] = None


class ProjectConfigResponse(BaseModel):
    """Project configuration response."""
    id: UUID
    version_id: UUID
    theme: Dict[str, Any]
    map_settings: Dict[str, Any]
    status_colors: Dict[str, Any]
    popup_config: Dict[str, Any]
    filter_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectConfigWithDefaultsResponse(BaseModel):
    """Project configuration with defaults applied."""
    id: UUID
    version_id: UUID
    theme: Dict[str, Any]
    map_settings: Dict[str, Any]
    status_colors: Dict[str, Any]
    interaction_colors: Dict[str, Any]
    popup_config: Dict[str, Any]
    filter_config: Dict[str, Any]
    created_at: datetime
    updated_at: datetime
