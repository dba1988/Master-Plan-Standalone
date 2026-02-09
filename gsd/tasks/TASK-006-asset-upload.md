# TASK-006: Asset Upload Endpoints

**Phase**: 2 - Storage + Assets
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-005

## Objective

Implement asset upload workflow using signed URLs.

## Description

Create endpoints for:
- Request signed upload URL
- Confirm upload completion
- List assets for a version
- Delete assets

## Files to Create

```
admin-api/app/
├── schemas/
│   └── asset.py
├── api/
│   └── assets.py
└── services/
    └── asset_service.py
```

## Implementation Steps

### Step 1: Asset Schemas
```python
# app/schemas/asset.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class AssetType(str, Enum):
    BASE_MAP = "base_map"
    OVERLAY_SVG = "overlay_svg"
    ICON = "icon"
    OTHER = "other"

class UploadUrlRequest(BaseModel):
    filename: str = Field(..., min_length=1, max_length=255)
    asset_type: AssetType
    content_type: str = Field(..., min_length=1)

class UploadUrlResponse(BaseModel):
    upload_url: str
    storage_path: str
    expires_in_seconds: int = 300

class AssetConfirmRequest(BaseModel):
    storage_path: str
    asset_type: AssetType
    filename: str
    file_size: int
    metadata: Optional[Dict[str, Any]] = None

class AssetResponse(BaseModel):
    id: UUID
    asset_type: str
    filename: str
    storage_path: str
    file_size: Optional[int]
    mime_type: Optional[str]
    metadata: Optional[Dict[str, Any]]
    created_at: datetime

    class Config:
        from_attributes = True

class AssetListResponse(BaseModel):
    assets: list[AssetResponse]
    total: int
```

### Step 2: Asset Service
```python
# app/services/asset_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from typing import List, Optional
from uuid import UUID
from datetime import timedelta
from app.models.asset import Asset
from app.models.version import ProjectVersion
from app.services.storage_service import StorageBackend
from app.schemas.asset import AssetType, AssetConfirmRequest

class AssetService:
    def __init__(self, db: AsyncSession, storage: StorageBackend):
        self.db = db
        self.storage = storage

    def _build_storage_path(
        self,
        project_slug: str,
        version_number: int,
        asset_type: str,
        filename: str
    ) -> str:
        """Build organized storage path"""
        return f"projects/{project_slug}/v{version_number}/{asset_type}/{filename}"

    async def get_version(
        self,
        project_slug: str,
        version_number: int
    ) -> Optional[ProjectVersion]:
        """Get version with validation"""
        result = await self.db.execute(
            select(ProjectVersion)
            .join(ProjectVersion.project)
            .where(
                ProjectVersion.project.has(slug=project_slug),
                ProjectVersion.version_number == version_number
            )
        )
        return result.scalar_one_or_none()

    async def generate_upload_url(
        self,
        project_slug: str,
        version_number: int,
        filename: str,
        asset_type: AssetType,
        content_type: str
    ) -> tuple[str, str]:
        """Generate signed URL for upload"""
        storage_path = self._build_storage_path(
            project_slug, version_number, asset_type.value, filename
        )

        upload_url = await self.storage.generate_upload_url(
            storage_path,
            content_type,
            expires_in=timedelta(minutes=5)
        )

        return upload_url, storage_path

    async def confirm_upload(
        self,
        version_id: UUID,
        data: AssetConfirmRequest,
        user_id: UUID
    ) -> Asset:
        """Confirm upload and create asset record"""
        # Verify file exists in storage
        exists = await self.storage.file_exists(data.storage_path)
        if not exists:
            raise ValueError("File not found in storage")

        # Check for existing asset with same path
        result = await self.db.execute(
            select(Asset).where(
                Asset.version_id == version_id,
                Asset.storage_path == data.storage_path
            )
        )
        existing = result.scalar_one_or_none()

        if existing:
            # Update existing
            existing.filename = data.filename
            existing.file_size = data.file_size
            existing.metadata = data.metadata
            await self.db.commit()
            await self.db.refresh(existing)
            return existing

        # Create new asset record
        asset = Asset(
            version_id=version_id,
            asset_type=data.asset_type.value,
            filename=data.filename,
            storage_path=data.storage_path,
            file_size=data.file_size,
            mime_type=self._get_mime_type(data.filename),
            metadata=data.metadata,
            uploaded_by=user_id
        )
        self.db.add(asset)
        await self.db.commit()
        await self.db.refresh(asset)
        return asset

    async def list_assets(
        self,
        version_id: UUID,
        asset_type: Optional[AssetType] = None
    ) -> tuple[List[Asset], int]:
        """List assets for a version"""
        query = select(Asset).where(Asset.version_id == version_id)

        if asset_type:
            query = query.where(Asset.asset_type == asset_type.value)

        result = await self.db.execute(query.order_by(Asset.created_at.desc()))
        assets = result.scalars().all()

        return assets, len(assets)

    async def delete_asset(self, asset_id: UUID) -> bool:
        """Delete asset from DB and storage"""
        result = await self.db.execute(
            select(Asset).where(Asset.id == asset_id)
        )
        asset = result.scalar_one_or_none()

        if not asset:
            return False

        # Delete from storage
        await self.storage.delete_file(asset.storage_path)

        # Delete from DB
        await self.db.delete(asset)
        await self.db.commit()

        return True

    def _get_mime_type(self, filename: str) -> str:
        import mimetypes
        mime_type, _ = mimetypes.guess_type(filename)
        return mime_type or "application/octet-stream"
```

### Step 3: Asset Endpoints
```python
# app/api/assets.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.storage_service import get_storage, StorageBackend
from app.services.asset_service import AssetService
from app.schemas.asset import (
    UploadUrlRequest, UploadUrlResponse,
    AssetConfirmRequest, AssetResponse, AssetListResponse, AssetType
)

router = APIRouter(tags=["Assets"])

@router.post(
    "/projects/{slug}/versions/{version}/assets/upload-url",
    response_model=UploadUrlResponse
)
async def get_upload_url(
    slug: str,
    version: int,
    request: UploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current_user: User = Depends(get_current_user)
):
    """Get signed URL for direct upload to storage"""
    service = AssetService(db, storage)

    # Verify version exists
    ver = await service.get_version(slug, version)
    if not ver:
        raise HTTPException(status_code=404, detail="Project version not found")

    if ver.status != "draft":
        raise HTTPException(status_code=400, detail="Can only upload to draft versions")

    upload_url, storage_path = await service.generate_upload_url(
        slug, version,
        request.filename,
        request.asset_type,
        request.content_type
    )

    return UploadUrlResponse(
        upload_url=upload_url,
        storage_path=storage_path,
        expires_in_seconds=300
    )

@router.post(
    "/projects/{slug}/versions/{version}/assets/confirm",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED
)
async def confirm_upload(
    slug: str,
    version: int,
    request: AssetConfirmRequest,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current_user: User = Depends(get_current_user)
):
    """Confirm upload completion and create asset record"""
    service = AssetService(db, storage)

    ver = await service.get_version(slug, version)
    if not ver:
        raise HTTPException(status_code=404, detail="Project version not found")

    try:
        asset = await service.confirm_upload(ver.id, request, current_user.id)
        return AssetResponse.from_orm(asset)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get(
    "/projects/{slug}/versions/{version}/assets",
    response_model=AssetListResponse
)
async def list_assets(
    slug: str,
    version: int,
    asset_type: Optional[AssetType] = Query(None),
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current_user: User = Depends(get_current_user)
):
    """List all assets for a version"""
    service = AssetService(db, storage)

    ver = await service.get_version(slug, version)
    if not ver:
        raise HTTPException(status_code=404, detail="Project version not found")

    assets, total = await service.list_assets(ver.id, asset_type)

    return AssetListResponse(
        assets=[AssetResponse.from_orm(a) for a in assets],
        total=total
    )

@router.delete(
    "/projects/{slug}/versions/{version}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT
)
async def delete_asset(
    slug: str,
    version: int,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current_user: User = Depends(get_current_user)
):
    """Delete an asset"""
    service = AssetService(db, storage)

    deleted = await service.delete_asset(asset_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Asset not found")
```

## Upload Flow

```
┌─────────────────┐         ┌─────────────────┐         ┌─────────────────┐
│     Client      │         │    Admin API    │         │  S3/GCS/Local   │
└────────┬────────┘         └────────┬────────┘         └────────┬────────┘
         │                           │                           │
         │  1. POST /upload-url      │                           │
         │  {filename, type, mime}   │                           │
         ├──────────────────────────▶│                           │
         │                           │                           │
         │  2. {upload_url, path}    │                           │
         │◀──────────────────────────┤                           │
         │                           │                           │
         │  3. PUT {upload_url}      │                           │
         │  [file binary]            │                           │
         ├───────────────────────────────────────────────────────▶
         │                           │                           │
         │  4. POST /confirm         │                           │
         │  {path, size, metadata}   │                           │
         ├──────────────────────────▶│                           │
         │                           │  5. Verify exists         │
         │                           ├──────────────────────────▶│
         │                           │                           │
         │  6. {asset record}        │                           │
         │◀──────────────────────────┤                           │
         │                           │                           │
```

## Acceptance Criteria

- [ ] Can request signed upload URL
- [ ] Can upload file directly to storage
- [ ] Can confirm upload and create DB record
- [ ] Can list assets with filtering
- [ ] Can delete assets (DB + storage)
- [ ] Only draft versions accept uploads
- [ ] Duplicate paths update existing asset
