"""
Overlay CRUD endpoints.

Supports:
- List overlays with type/layer filtering
- Get single overlay
- Create/Update/Delete overlay
- Bulk upsert for SVG import
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.user import User
from app.schemas.overlay import (
    BulkUpsertRequest,
    BulkUpsertResponse,
    OverlayCreate,
    OverlayListResponse,
    OverlayResponse,
    OverlayType,
    OverlayUpdate,
)
from app.services.overlay_service import OverlayService

router = APIRouter(tags=["Overlays"])


@router.get(
    "/projects/{slug}/versions/{version_number}/overlays",
    response_model=OverlayListResponse,
)
async def list_overlays(
    slug: str,
    version_number: int,
    overlay_type: Optional[OverlayType] = Query(None, description="Filter by overlay type"),
    layer_id: Optional[UUID] = Query(None, description="Filter by layer ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all overlays for a project version.

    Optionally filter by overlay type and/or layer.
    Results are sorted by sort_order then ref.
    """
    service = OverlayService(db)
    result = await service.list_overlays(
        project_slug=slug,
        version_number=version_number,
        overlay_type=overlay_type,
        layer_id=layer_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or version not found"
        )

    overlays, total = result
    return OverlayListResponse(
        overlays=[OverlayResponse.model_validate(o) for o in overlays],
        total=total,
    )


@router.get(
    "/projects/{slug}/versions/{version_number}/overlays/{overlay_id}",
    response_model=OverlayResponse,
)
async def get_overlay(
    slug: str,
    version_number: int,
    overlay_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific overlay by ID.
    """
    service = OverlayService(db)
    overlay = await service.get_overlay(
        project_slug=slug,
        version_number=version_number,
        overlay_id=overlay_id,
    )

    if not overlay:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overlay not found"
        )

    return OverlayResponse.model_validate(overlay)


@router.post(
    "/projects/{slug}/versions/{version_number}/overlays",
    response_model=OverlayResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_overlay(
    slug: str,
    version_number: int,
    data: OverlayCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Create a new overlay.

    Only works for draft versions.
    Ref must be unique within (version, overlay_type).
    """
    service = OverlayService(db)
    overlay = await service.create_overlay(
        project_slug=slug,
        version_number=version_number,
        data=data,
    )

    if not overlay:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create overlay. Project/version not found, version is not a draft, or ref already exists."
        )

    return OverlayResponse.model_validate(overlay)


@router.put(
    "/projects/{slug}/versions/{version_number}/overlays/{overlay_id}",
    response_model=OverlayResponse,
)
async def update_overlay(
    slug: str,
    version_number: int,
    overlay_id: UUID,
    data: OverlayUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Update an existing overlay.

    Only works for draft versions.
    """
    service = OverlayService(db)
    overlay = await service.update_overlay(
        project_slug=slug,
        version_number=version_number,
        overlay_id=overlay_id,
        data=data,
    )

    if not overlay:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update overlay. Project/version not found, version is not a draft, overlay not found, or ref conflict."
        )

    return OverlayResponse.model_validate(overlay)


@router.delete(
    "/projects/{slug}/versions/{version_number}/overlays/{overlay_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_overlay(
    slug: str,
    version_number: int,
    overlay_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Delete an overlay.

    Only works for draft versions.
    """
    service = OverlayService(db)
    deleted = await service.delete_overlay(
        project_slug=slug,
        version_number=version_number,
        overlay_id=overlay_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overlay not found or version is not a draft"
        )


@router.post(
    "/projects/{slug}/versions/{version_number}/overlays/bulk",
    response_model=BulkUpsertResponse,
)
async def bulk_upsert_overlays(
    slug: str,
    version_number: int,
    data: BulkUpsertRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Bulk create or update overlays.

    Matches existing overlays by (version_id, overlay_type, ref).
    - If exists: updates the overlay
    - If not exists: creates new overlay

    Only works for draft versions.
    """
    service = OverlayService(db)
    result = await service.bulk_upsert(
        project_slug=slug,
        version_number=version_number,
        overlays=data.overlays,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project/version not found or version is not a draft"
        )

    created, updated, errors = result
    return BulkUpsertResponse(
        created=created,
        updated=updated,
        errors=errors,
    )


@router.delete(
    "/projects/{slug}/versions/{version_number}/overlays/by-type/{overlay_type}",
    status_code=status.HTTP_200_OK,
)
async def delete_overlays_by_type(
    slug: str,
    version_number: int,
    overlay_type: OverlayType,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Delete all overlays of a specific type.

    Only works for draft versions.
    Returns count of deleted overlays.
    """
    service = OverlayService(db)
    count = await service.delete_by_type(
        project_slug=slug,
        version_number=version_number,
        overlay_type=overlay_type,
    )

    if count is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project/version not found or version is not a draft"
        )

    return {"deleted": count}
