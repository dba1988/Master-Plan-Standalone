# TASK-008: Project Config Endpoints

**Phase**: 3 - Overlays + Config
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-004, TASK-000 (parity harness for status styles)

## Objective

Implement project configuration management per version.

## Description

Create endpoints for managing project-level configuration:
- Get config for a version
- Update config for a version
- Config includes: tiles path, viewBox, zoom, default styles

## Files to Create

```
admin-service/api/app/
├── schemas/
│   └── config.py
├── api/
│   └── config.py
└── services/
    └── config_service.py
```

## Implementation Steps

### Step 1: Config Schemas
```python
# app/schemas/config.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime

class ZoomConfig(BaseModel):
    min: float = 1.0
    max: float = 2.5
    default: float = 1.0

class UnitStatusStyle(BaseModel):
    fill: str
    fillOpacity: Optional[float] = 1.0
    stroke: Optional[str] = "#FFFFFF"
    strokeWidth: Optional[float] = 1.0

class DefaultStyles(BaseModel):
    unit: Optional[Dict[str, UnitStatusStyle]] = None  # { available: {...}, sold: {...} }
    hover: Optional[UnitStatusStyle] = None

class ProjectConfigBase(BaseModel):
    base_tiles_path: Optional[str] = None
    default_view_box: Optional[str] = "0 0 4096 4096"
    default_zoom: Optional[ZoomConfig] = None
    default_styles: Optional[Dict[str, Any]] = None
    default_locale: Optional[str] = "en"
    supported_locales: Optional[List[str]] = ["en"]

class ProjectConfigCreate(ProjectConfigBase):
    pass

class ProjectConfigUpdate(ProjectConfigBase):
    pass

class ProjectConfigResponse(ProjectConfigBase):
    id: UUID
    version_id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

# Default styles - MUST match gsd/parity/STATUS-TAXONOMY.md (5 canonical statuses)
DEFAULT_UNIT_STYLES = {
    "unit": {
        "available": {
            "fill": "rgba(75, 156, 85, 0.70)",
            "fillOpacity": 0.7,
            "stroke": "#FFFFFF",
            "strokeWidth": 1
        },
        "reserved": {
            "fill": "rgba(255, 193, 7, 0.70)",
            "fillOpacity": 0.7,
            "stroke": "#FFFFFF",
            "strokeWidth": 1
        },
        "sold": {
            "fill": "rgba(211, 47, 47, 0.70)",
            "fillOpacity": 0.7,
            "stroke": "#FFFFFF",
            "strokeWidth": 1
        },
        "hidden": {
            "fill": "rgba(158, 158, 158, 0.50)",
            "fillOpacity": 0.5,
            "stroke": "#CCCCCC",
            "strokeWidth": 1
        },
        "unreleased": {
            "fill": "rgba(97, 97, 97, 0.40)",
            "fillOpacity": 0.4,
            "stroke": "#888888",
            "strokeWidth": 1
        }
    },
    "hover": {
        "fill": "#DAA520",
        "fillOpacity": 0.5,
        "stroke": "#F1DA9E",
        "strokeWidth": 2
    }
}
```

### Step 2: Config Service
```python
# app/services/config_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
from app.models.config import ProjectConfig
from app.models.version import ProjectVersion
from app.schemas.config import ProjectConfigUpdate, DEFAULT_UNIT_STYLES

class ConfigService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self, version_id: UUID) -> Optional[ProjectConfig]:
        result = await self.db.execute(
            select(ProjectConfig).where(ProjectConfig.version_id == version_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create_config(self, version_id: UUID) -> ProjectConfig:
        config = await self.get_config(version_id)

        if not config:
            # Create default config
            config = ProjectConfig(
                version_id=version_id,
                default_view_box="0 0 4096 4096",
                default_zoom={"min": 1.0, "max": 2.5, "default": 1.0},
                default_styles=DEFAULT_UNIT_STYLES,
                default_locale="en",
                supported_locales=["en"]
            )
            self.db.add(config)
            await self.db.commit()
            await self.db.refresh(config)

        return config

    async def update_config(
        self,
        version_id: UUID,
        data: ProjectConfigUpdate
    ) -> ProjectConfig:
        config = await self.get_or_create_config(version_id)

        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(config, key, value)

        await self.db.commit()
        await self.db.refresh(config)
        return config
```

### Step 3: Config Endpoints
```python
# app/api/config.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.config_service import ConfigService
from app.services.project_service import ProjectService
from app.schemas.config import (
    ProjectConfigUpdate, ProjectConfigResponse
)

router = APIRouter(tags=["Project Config"])

async def get_version_or_404(db, slug: str, version: int):
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    ver = next(
        (v for v in project.versions if v.version_number == version),
        None
    )
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    return ver

@router.get(
    "/projects/{slug}/versions/{version}/config",
    response_model=ProjectConfigResponse
)
async def get_config(
    slug: str,
    version: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)
    service = ConfigService(db)

    config = await service.get_or_create_config(ver.id)
    return ProjectConfigResponse.from_orm(config)

@router.put(
    "/projects/{slug}/versions/{version}/config",
    response_model=ProjectConfigResponse
)
async def update_config(
    slug: str,
    version: int,
    data: ProjectConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)

    if ver.status != "draft":
        raise HTTPException(status_code=400, detail="Can only modify draft versions")

    service = ConfigService(db)
    config = await service.update_config(ver.id, data)

    return ProjectConfigResponse.from_orm(config)
```

## Config Example

```json
{
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
        "fillOpacity": 0.7,
        "stroke": "#FFFFFF",
        "strokeWidth": 1
      },
      "sold": {
        "fill": "rgba(170, 70, 55, 0.60)",
        "fillOpacity": 0.5
      }
    },
    "hover": {
      "fill": "#DAA520",
      "fillOpacity": 0.5,
      "stroke": "#F1DA9E",
      "strokeWidth": 2
    }
  },
  "default_locale": "en",
  "supported_locales": ["en", "ar"]
}
```

## Acceptance Criteria

- [ ] Can get config (creates default if missing)
- [ ] Can update config
- [ ] Default styles match ROSHN production
- [ ] Only draft versions can be modified
- [ ] Config stored as JSONB fields
