# TASK-007: Overlay CRUD

**Phase**: 3 - Overlays + Config
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-004

## Objective

Implement overlay management with bulk upsert for importing SVG data.

## Description

Create CRUD operations for overlays (zones, units, POIs):
- List overlays with filtering
- Get single overlay
- Create/update overlay
- Delete overlay
- Bulk upsert (for SVG import)

## Files to Create

```
admin-api/app/
├── schemas/
│   └── overlay.py
├── api/
│   └── overlays.py
└── services/
    └── overlay_service.py
```

## Implementation Steps

### Step 1: Overlay Schemas
```python
# app/schemas/overlay.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List, Union
from uuid import UUID
from datetime import datetime
from enum import Enum

class OverlayType(str, Enum):
    ZONE = "zone"
    UNIT = "unit"
    POI = "poi"

class GeometryPath(BaseModel):
    type: str = "path"
    d: str  # SVG path data

class GeometryPoint(BaseModel):
    type: str = "point"
    x: float
    y: float

Geometry = Union[GeometryPath, GeometryPoint]

class LocalizedText(BaseModel):
    en: str = ""
    ar: Optional[str] = None

class OverlayBase(BaseModel):
    overlay_type: OverlayType
    ref: str = Field(..., min_length=1, max_length=255)
    geometry: Dict[str, Any]  # GeometryPath or GeometryPoint
    view_box: Optional[str] = None
    label: Optional[Dict[str, str]] = None  # { en: "...", ar: "..." }
    label_position: Optional[List[float]] = None  # [x, y]
    props: Optional[Dict[str, Any]] = None
    style_override: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = 0
    is_visible: Optional[bool] = True
    layer_id: Optional[UUID] = None

class OverlayCreate(OverlayBase):
    pass

class OverlayUpdate(BaseModel):
    geometry: Optional[Dict[str, Any]] = None
    view_box: Optional[str] = None
    label: Optional[Dict[str, str]] = None
    label_position: Optional[List[float]] = None
    props: Optional[Dict[str, Any]] = None
    style_override: Optional[Dict[str, Any]] = None
    sort_order: Optional[int] = None
    is_visible: Optional[bool] = None
    layer_id: Optional[UUID] = None

class OverlayResponse(BaseModel):
    id: UUID
    overlay_type: str
    ref: str
    geometry: Dict[str, Any]
    view_box: Optional[str]
    label: Optional[Dict[str, str]]
    label_position: Optional[List[float]]
    props: Dict[str, Any]
    style_override: Optional[Dict[str, Any]]
    sort_order: int
    is_visible: bool
    layer_id: Optional[UUID]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class OverlayListResponse(BaseModel):
    overlays: List[OverlayResponse]
    total: int

class BulkUpsertRequest(BaseModel):
    overlays: List[OverlayCreate]

class BulkUpsertResponse(BaseModel):
    created: int
    updated: int
    errors: List[Dict[str, Any]]
```

### Step 2: Overlay Service
```python
# app/services/overlay_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.dialects.postgresql import insert
from typing import List, Optional
from uuid import UUID
from app.models.overlay import Overlay
from app.models.version import ProjectVersion
from app.schemas.overlay import OverlayCreate, OverlayUpdate, OverlayType

class OverlayService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_overlays(
        self,
        version_id: UUID,
        overlay_type: Optional[OverlayType] = None,
        layer_id: Optional[UUID] = None
    ) -> List[Overlay]:
        query = select(Overlay).where(Overlay.version_id == version_id)

        if overlay_type:
            query = query.where(Overlay.overlay_type == overlay_type.value)

        if layer_id:
            query = query.where(Overlay.layer_id == layer_id)

        query = query.order_by(Overlay.sort_order, Overlay.ref)

        result = await self.db.execute(query)
        return result.scalars().all()

    async def get_overlay(
        self,
        version_id: UUID,
        overlay_id: UUID
    ) -> Optional[Overlay]:
        result = await self.db.execute(
            select(Overlay).where(
                Overlay.version_id == version_id,
                Overlay.id == overlay_id
            )
        )
        return result.scalar_one_or_none()

    async def get_overlay_by_ref(
        self,
        version_id: UUID,
        overlay_type: OverlayType,
        ref: str
    ) -> Optional[Overlay]:
        result = await self.db.execute(
            select(Overlay).where(
                Overlay.version_id == version_id,
                Overlay.overlay_type == overlay_type.value,
                Overlay.ref == ref
            )
        )
        return result.scalar_one_or_none()

    async def create_overlay(
        self,
        version_id: UUID,
        data: OverlayCreate
    ) -> Overlay:
        overlay = Overlay(
            version_id=version_id,
            overlay_type=data.overlay_type.value,
            ref=data.ref,
            geometry=data.geometry,
            view_box=data.view_box,
            label=data.label,
            label_position=data.label_position,
            props=data.props or {},
            style_override=data.style_override,
            sort_order=data.sort_order or 0,
            is_visible=data.is_visible if data.is_visible is not None else True,
            layer_id=data.layer_id
        )
        self.db.add(overlay)
        await self.db.commit()
        await self.db.refresh(overlay)
        return overlay

    async def update_overlay(
        self,
        overlay: Overlay,
        data: OverlayUpdate
    ) -> Overlay:
        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(overlay, key, value)

        await self.db.commit()
        await self.db.refresh(overlay)
        return overlay

    async def delete_overlay(self, overlay: Overlay) -> bool:
        await self.db.delete(overlay)
        await self.db.commit()
        return True

    async def bulk_upsert(
        self,
        version_id: UUID,
        overlays: List[OverlayCreate]
    ) -> tuple[int, int, List[dict]]:
        """Bulk create or update overlays"""
        created = 0
        updated = 0
        errors = []

        for data in overlays:
            try:
                existing = await self.get_overlay_by_ref(
                    version_id, data.overlay_type, data.ref
                )

                if existing:
                    # Update
                    update_data = OverlayUpdate(**data.dict(exclude={'overlay_type', 'ref'}))
                    await self.update_overlay(existing, update_data)
                    updated += 1
                else:
                    # Create
                    await self.create_overlay(version_id, data)
                    created += 1

            except Exception as e:
                errors.append({
                    "ref": data.ref,
                    "error": str(e)
                })

        return created, updated, errors

    async def delete_by_type(
        self,
        version_id: UUID,
        overlay_type: OverlayType
    ) -> int:
        """Delete all overlays of a type (for reimport)"""
        result = await self.db.execute(
            delete(Overlay).where(
                Overlay.version_id == version_id,
                Overlay.overlay_type == overlay_type.value
            )
        )
        await self.db.commit()
        return result.rowcount
```

### Step 3: Overlay Endpoints
```python
# app/api/overlays.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from typing import Optional
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.overlay_service import OverlayService
from app.services.project_service import ProjectService
from app.schemas.overlay import (
    OverlayCreate, OverlayUpdate, OverlayResponse,
    OverlayListResponse, OverlayType, BulkUpsertRequest, BulkUpsertResponse
)

router = APIRouter(tags=["Overlays"])

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
    "/projects/{slug}/versions/{version}/overlays",
    response_model=OverlayListResponse
)
async def list_overlays(
    slug: str,
    version: int,
    overlay_type: Optional[OverlayType] = Query(None),
    layer_id: Optional[UUID] = Query(None),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)
    service = OverlayService(db)

    overlays = await service.list_overlays(ver.id, overlay_type, layer_id)

    return OverlayListResponse(
        overlays=[OverlayResponse.from_orm(o) for o in overlays],
        total=len(overlays)
    )

@router.get(
    "/projects/{slug}/versions/{version}/overlays/{overlay_id}",
    response_model=OverlayResponse
)
async def get_overlay(
    slug: str,
    version: int,
    overlay_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)
    service = OverlayService(db)

    overlay = await service.get_overlay(ver.id, overlay_id)
    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")

    return OverlayResponse.from_orm(overlay)

@router.post(
    "/projects/{slug}/versions/{version}/overlays",
    response_model=OverlayResponse,
    status_code=status.HTTP_201_CREATED
)
async def create_overlay(
    slug: str,
    version: int,
    data: OverlayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)

    if ver.status != "draft":
        raise HTTPException(status_code=400, detail="Can only modify draft versions")

    service = OverlayService(db)
    overlay = await service.create_overlay(ver.id, data)

    return OverlayResponse.from_orm(overlay)

@router.put(
    "/projects/{slug}/versions/{version}/overlays/{overlay_id}",
    response_model=OverlayResponse
)
async def update_overlay(
    slug: str,
    version: int,
    overlay_id: UUID,
    data: OverlayUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)

    if ver.status != "draft":
        raise HTTPException(status_code=400, detail="Can only modify draft versions")

    service = OverlayService(db)
    overlay = await service.get_overlay(ver.id, overlay_id)

    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")

    updated = await service.update_overlay(overlay, data)
    return OverlayResponse.from_orm(updated)

@router.delete(
    "/projects/{slug}/versions/{version}/overlays/{overlay_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_overlay(
    slug: str,
    version: int,
    overlay_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    ver = await get_version_or_404(db, slug, version)

    if ver.status != "draft":
        raise HTTPException(status_code=400, detail="Can only modify draft versions")

    service = OverlayService(db)
    overlay = await service.get_overlay(ver.id, overlay_id)

    if not overlay:
        raise HTTPException(status_code=404, detail="Overlay not found")

    await service.delete_overlay(overlay)

@router.post(
    "/projects/{slug}/versions/{version}/overlays/bulk",
    response_model=BulkUpsertResponse
)
async def bulk_upsert_overlays(
    slug: str,
    version: int,
    data: BulkUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Bulk create or update overlays (for SVG import)"""
    ver = await get_version_or_404(db, slug, version)

    if ver.status != "draft":
        raise HTTPException(status_code=400, detail="Can only modify draft versions")

    service = OverlayService(db)
    created, updated, errors = await service.bulk_upsert(ver.id, data.overlays)

    return BulkUpsertResponse(
        created=created,
        updated=updated,
        errors=errors
    )
```

## Acceptance Criteria

- [ ] Can list overlays with type filter
- [ ] Can get single overlay by ID
- [ ] Can create overlay
- [ ] Can update overlay
- [ ] Can delete overlay
- [ ] Bulk upsert creates new / updates existing
- [ ] Only draft versions can be modified
- [ ] Geometry stored as JSONB
