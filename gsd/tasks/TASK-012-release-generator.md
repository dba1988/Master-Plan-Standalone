# TASK-012: Release.json Generator

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-008, TASK-009

## Objective

Generate release.json snapshot for publishing.

## Description

Create a service that:
- Assembles all version data into release.json
- Includes config, overlays, layers
- Excludes secrets and internal data
- Validates against schema

## Files to Create

```
admin-api/app/services/
└── release_service.py
```

## Implementation Steps

### Step 1: Release Service
```python
# app/services/release_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json

from app.models.project import Project
from app.models.version import ProjectVersion
from app.models.config import ProjectConfig
from app.models.layer import Layer
from app.models.overlay import Overlay
from app.models.integration import IntegrationConfig

class ReleaseService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def generate_release(
        self,
        project_slug: str,
        version_number: int
    ) -> Dict[str, Any]:
        """
        Generate release.json content for a version.

        Args:
            project_slug: Project slug
            version_number: Version number to publish

        Returns:
            release.json as dict
        """
        # Fetch all required data
        project = await self._get_project(project_slug)
        if not project:
            raise ValueError(f"Project not found: {project_slug}")

        version = await self._get_version(project.id, version_number)
        if not version:
            raise ValueError(f"Version not found: {version_number}")

        config = await self._get_config(version.id)
        layers = await self._get_layers(version.id)
        overlays = await self._get_overlays(version.id)
        integration = await self._get_integration(project.id)

        # Build release object
        release = {
            "$schema": "https://masterplan.example.com/schemas/release-v1.json",
            "version": "1.0.0",
            "published_at": datetime.utcnow().isoformat() + "Z",

            "project": {
                "slug": project.slug,
                "name": {
                    "en": project.name,
                    "ar": project.name_ar
                }
            },

            "config": self._build_config(config),
            "layers": self._build_layers(layers),
            "overlays": self._build_overlays(overlays),
            "integration": self._build_integration(integration)
        }

        return release

    async def _get_project(self, slug: str) -> Optional[Project]:
        result = await self.db.execute(
            select(Project).where(Project.slug == slug)
        )
        return result.scalar_one_or_none()

    async def _get_version(
        self,
        project_id: UUID,
        version_number: int
    ) -> Optional[ProjectVersion]:
        result = await self.db.execute(
            select(ProjectVersion).where(
                ProjectVersion.project_id == project_id,
                ProjectVersion.version_number == version_number
            )
        )
        return result.scalar_one_or_none()

    async def _get_config(self, version_id: UUID) -> Optional[ProjectConfig]:
        result = await self.db.execute(
            select(ProjectConfig).where(ProjectConfig.version_id == version_id)
        )
        return result.scalar_one_or_none()

    async def _get_layers(self, version_id: UUID) -> list[Layer]:
        result = await self.db.execute(
            select(Layer)
            .where(Layer.version_id == version_id)
            .order_by(Layer.z_index)
        )
        return result.scalars().all()

    async def _get_overlays(self, version_id: UUID) -> list[Overlay]:
        result = await self.db.execute(
            select(Overlay)
            .where(Overlay.version_id == version_id, Overlay.is_visible == True)
            .order_by(Overlay.sort_order)
        )
        return result.scalars().all()

    async def _get_integration(self, project_id: UUID) -> Optional[IntegrationConfig]:
        result = await self.db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    def _build_config(self, config: Optional[ProjectConfig]) -> Dict[str, Any]:
        if not config:
            return {
                "base_tiles_path": "tiles/map.dzi",
                "default_view_box": "0 0 4096 4096",
                "default_zoom": {"min": 1.0, "max": 2.5, "default": 1.0},
                "default_styles": {}
            }

        return {
            "base_tiles_path": config.base_tiles_path or "tiles/map.dzi",
            "default_view_box": config.default_view_box or "0 0 4096 4096",
            "default_zoom": config.default_zoom or {"min": 1.0, "max": 2.5, "default": 1.0},
            "default_styles": config.default_styles or {}
        }

    def _build_layers(self, layers: list[Layer]) -> list[Dict[str, Any]]:
        return [
            {
                "id": str(layer.id),
                "name": layer.name,
                "layer_type": layer.layer_type,
                "z_index": layer.z_index,
                "is_visible": layer.is_visible
            }
            for layer in layers
        ]

    def _build_overlays(self, overlays: list[Overlay]) -> list[Dict[str, Any]]:
        return [
            {
                "overlay_type": overlay.overlay_type,
                "ref": overlay.ref,
                "layer_id": str(overlay.layer_id) if overlay.layer_id else None,
                "geometry": overlay.geometry,
                "label": overlay.label,
                "label_position": overlay.label_position,
                "props": overlay.props or {},
                "style_override": overlay.style_override
            }
            for overlay in overlays
        ]

    def _build_integration(
        self,
        integration: Optional[IntegrationConfig]
    ) -> Dict[str, Any]:
        """Build integration config WITHOUT secrets"""
        if not integration:
            return {
                "status_endpoint": None,
                "update_method": "polling",
                "polling_interval_seconds": 30
            }

        # Note: We expose the public status proxy endpoint, not the client API
        return {
            "status_endpoint": f"/api/public/status",
            "update_method": integration.update_method,
            "polling_interval_seconds": integration.polling_interval_seconds
        }

    def validate_release(self, release: Dict[str, Any]) -> list[str]:
        """Validate release against schema, return list of errors"""
        errors = []

        # Required fields
        if not release.get("project", {}).get("slug"):
            errors.append("Missing project.slug")

        if not release.get("config"):
            errors.append("Missing config")

        if not release.get("overlays"):
            errors.append("No overlays defined")

        # Overlay validation
        for i, overlay in enumerate(release.get("overlays", [])):
            if not overlay.get("ref"):
                errors.append(f"Overlay {i}: missing ref")
            if not overlay.get("geometry"):
                errors.append(f"Overlay {i}: missing geometry")

        return errors

    def to_json(self, release: Dict[str, Any], pretty: bool = True) -> str:
        """Convert release to JSON string"""
        if pretty:
            return json.dumps(release, indent=2, default=str)
        return json.dumps(release, default=str)
```

### Step 2: Release Schema Validation (Optional)
```python
# app/schemas/release.py
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class ReleaseProject(BaseModel):
    slug: str
    name: Dict[str, str]

class ReleaseConfig(BaseModel):
    base_tiles_path: str
    default_view_box: str
    default_zoom: Dict[str, float]
    default_styles: Dict[str, Any]

class ReleaseLayer(BaseModel):
    id: str
    name: str
    layer_type: str
    z_index: int
    is_visible: bool

class ReleaseOverlay(BaseModel):
    overlay_type: str
    ref: str
    layer_id: Optional[str]
    geometry: Dict[str, Any]
    label: Optional[Dict[str, str]]
    label_position: Optional[List[float]]
    props: Dict[str, Any]
    style_override: Optional[Dict[str, Any]]

class ReleaseIntegration(BaseModel):
    status_endpoint: Optional[str]
    update_method: str
    polling_interval_seconds: int

class Release(BaseModel):
    schema_: str = "$schema"
    version: str
    published_at: datetime
    project: ReleaseProject
    config: ReleaseConfig
    layers: List[ReleaseLayer]
    overlays: List[ReleaseOverlay]
    integration: ReleaseIntegration
```

## Release.json Example

```json
{
  "$schema": "https://masterplan.example.com/schemas/release-v1.json",
  "version": "1.0.0",
  "published_at": "2026-02-09T10:30:00Z",
  "project": {
    "slug": "malaysia-project-1",
    "name": {
      "en": "Malaysia Development",
      "ms": "Pembangunan Malaysia"
    }
  },
  "config": {
    "base_tiles_path": "tiles/project/map.dzi",
    "default_view_box": "0 0 4096 4096",
    "default_zoom": {
      "min": 1.0,
      "max": 2.5,
      "default": 1.2
    },
    "default_styles": {
      "unit": {
        "available": {
          "fill": "rgba(75, 156, 85, 0.50)",
          "fillOpacity": 0.7
        }
      }
    }
  },
  "layers": [
    {
      "id": "layer-units",
      "name": "Units",
      "layer_type": "units",
      "z_index": 1,
      "is_visible": true
    }
  ],
  "overlays": [
    {
      "overlay_type": "unit",
      "ref": "UNIT-001",
      "layer_id": "layer-units",
      "geometry": {
        "type": "path",
        "d": "M100,100 L200,100 L200,200 Z"
      },
      "label": {
        "en": "001"
      },
      "label_position": [150, 150],
      "props": {},
      "style_override": null
    }
  ],
  "integration": {
    "status_endpoint": "/api/public/status",
    "update_method": "polling",
    "polling_interval_seconds": 30
  }
}
```

## Acceptance Criteria

- [ ] Generates complete release.json
- [ ] Includes all visible overlays
- [ ] Config values included
- [ ] Secrets NOT included
- [ ] Validates against schema
- [ ] Can serialize to JSON
