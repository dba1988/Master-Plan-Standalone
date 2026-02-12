"""
Building CRUD endpoints.

Supports:
- Building management (create, list, update, delete)
- Building views (elevation, rotation, floor plan)
- View image upload and tile generation
- SVG import for stack/unit overlays
- Stacks (vertical unit groupings)
- Building units (individual apartments)
- View overlay mappings (geometry per view)
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.building import Building
from app.models.project import Project
from app.models.user import User
from app.models.version import ProjectVersion
from app.schemas.building import (
    BuildingCreate,
    BuildingUpdate,
    BuildingResponse,
    BuildingListResponse,
    BuildingViewCreate,
    BuildingViewUpdate,
    BuildingViewResponse,
    BuildingViewListResponse,
    StackCreate,
    StackUpdate,
    StackResponse,
    StackListResponse,
    BulkStackRequest,
    BuildingUnitCreate,
    BuildingUnitUpdate,
    BuildingUnitResponse,
    BuildingUnitListResponse,
    GenerateUnitsRequest,
    GenerateUnitsResponse,
    OverlayMappingCreate,
    OverlayMappingResponse,
    OverlayMappingListResponse,
    BulkOverlayMappingRequest,
    BulkOverlayMappingResponse,
    ViewType,
)
from app.schemas.job import JobCreateResponse
from app.services.building_service import BuildingService
from app.services.job_service import JobService
from app.services.storage_service import storage_service
from app.services.svg_parser import svg_parser

router = APIRouter(tags=["Buildings"])


# ============================================
# REQUEST/RESPONSE SCHEMAS FOR VIEW ASSETS
# ============================================

class ViewUploadUrlRequest(BaseModel):
    """Request for view image upload URL."""
    filename: str
    content_type: str = "image/png"


class ViewUploadUrlResponse(BaseModel):
    """Response with presigned upload URL."""
    upload_url: str
    storage_path: str
    expires_in_seconds: int


class ViewUploadConfirmRequest(BaseModel):
    """Confirm view image upload."""
    storage_path: str


class SVGImportRequest(BaseModel):
    """Request to import overlays from SVG."""
    svg_content: str
    target_type: str = "stack"  # 'stack' or 'unit'
    id_pattern: Optional[str] = None


# ============================================
# BUILDING ENDPOINTS
# ============================================

@router.get(
    "/projects/{slug}/buildings",
    response_model=BuildingListResponse,
)
async def list_buildings(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all buildings for a project."""
    service = BuildingService(db)
    result = await service.list_buildings(project_slug=slug)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    buildings, total = result
    return BuildingListResponse(
        buildings=[BuildingResponse.model_validate(b) for b in buildings],
        total=total,
    )


@router.get(
    "/projects/{slug}/buildings/{building_id}",
    response_model=BuildingResponse,
)
async def get_building(
    slug: str,
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific building by ID."""
    service = BuildingService(db)
    building = await service.get_building(project_slug=slug, building_id=building_id)

    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    return BuildingResponse.model_validate(building)


@router.post(
    "/projects/{slug}/buildings",
    response_model=BuildingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_building(
    slug: str,
    data: BuildingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Create a new building."""
    service = BuildingService(db)
    building = await service.create_building(project_slug=slug, data=data)

    if not building:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create building. Project not found, no draft version, or ref already exists."
        )

    return BuildingResponse.model_validate(building)


@router.put(
    "/projects/{slug}/buildings/{building_id}",
    response_model=BuildingResponse,
)
async def update_building(
    slug: str,
    building_id: UUID,
    data: BuildingUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Update an existing building."""
    service = BuildingService(db)
    building = await service.update_building(
        project_slug=slug,
        building_id=building_id,
        data=data,
    )

    if not building:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update building."
        )

    return BuildingResponse.model_validate(building)


@router.delete(
    "/projects/{slug}/buildings/{building_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_building(
    slug: str,
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Delete a building (cascades to views, stacks, units)."""
    service = BuildingService(db)
    deleted = await service.delete_building(project_slug=slug, building_id=building_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found or no draft version exists"
        )


# ============================================
# BUILDING VIEW ENDPOINTS
# ============================================

@router.get(
    "/projects/{slug}/buildings/{building_id}/views",
    response_model=BuildingViewListResponse,
)
async def list_views(
    slug: str,
    building_id: UUID,
    view_type: Optional[ViewType] = Query(None, description="Filter by view type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all views for a building."""
    service = BuildingService(db)
    result = await service.list_views(
        project_slug=slug,
        building_id=building_id,
        view_type=view_type,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    views, total = result
    return BuildingViewListResponse(
        views=[BuildingViewResponse.model_validate(v) for v in views],
        total=total,
    )


@router.get(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}",
    response_model=BuildingViewResponse,
)
async def get_view(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific view by ID."""
    service = BuildingService(db)
    view = await service.get_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
    )

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View not found"
        )

    return BuildingViewResponse.model_validate(view)


@router.post(
    "/projects/{slug}/buildings/{building_id}/views",
    response_model=BuildingViewResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_view(
    slug: str,
    building_id: UUID,
    data: BuildingViewCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Create a new building view."""
    service = BuildingService(db)
    view = await service.create_view(
        project_slug=slug,
        building_id=building_id,
        data=data,
    )

    if not view:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create view."
        )

    return BuildingViewResponse.model_validate(view)


@router.put(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}",
    response_model=BuildingViewResponse,
)
async def update_view(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    data: BuildingViewUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Update an existing view."""
    service = BuildingService(db)
    view = await service.update_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
        data=data,
    )

    if not view:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update view."
        )

    return BuildingViewResponse.model_validate(view)


@router.delete(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_view(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Delete a view."""
    service = BuildingService(db)
    deleted = await service.delete_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View not found"
        )


# ============================================
# STACK ENDPOINTS
# ============================================

@router.get(
    "/projects/{slug}/buildings/{building_id}/stacks",
    response_model=StackListResponse,
)
async def list_stacks(
    slug: str,
    building_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List all stacks for a building."""
    service = BuildingService(db)
    result = await service.list_stacks(project_slug=slug, building_id=building_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    stacks, total = result
    return StackListResponse(
        stacks=[StackResponse.model_validate(s) for s in stacks],
        total=total,
    )


@router.get(
    "/projects/{slug}/buildings/{building_id}/stacks/{stack_id}",
    response_model=StackResponse,
)
async def get_stack(
    slug: str,
    building_id: UUID,
    stack_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific stack by ID."""
    service = BuildingService(db)
    stack = await service.get_stack(
        project_slug=slug,
        building_id=building_id,
        stack_id=stack_id,
    )

    if not stack:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stack not found"
        )

    return StackResponse.model_validate(stack)


@router.post(
    "/projects/{slug}/buildings/{building_id}/stacks",
    response_model=StackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_stack(
    slug: str,
    building_id: UUID,
    data: StackCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Create a new stack."""
    service = BuildingService(db)
    stack = await service.create_stack(
        project_slug=slug,
        building_id=building_id,
        data=data,
    )

    if not stack:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create stack."
        )

    return StackResponse.model_validate(stack)


@router.post(
    "/projects/{slug}/buildings/{building_id}/stacks/bulk",
)
async def bulk_upsert_stacks(
    slug: str,
    building_id: UUID,
    data: BulkStackRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Bulk create or update stacks."""
    service = BuildingService(db)
    result = await service.bulk_upsert_stacks(
        project_slug=slug,
        building_id=building_id,
        stacks=data.stacks,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Building not found or no draft version exists"
        )

    created, updated, errors = result
    return {"created": created, "updated": updated, "errors": errors}


@router.delete(
    "/projects/{slug}/buildings/{building_id}/stacks/{stack_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_stack(
    slug: str,
    building_id: UUID,
    stack_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Delete a stack."""
    service = BuildingService(db)
    deleted = await service.delete_stack(
        project_slug=slug,
        building_id=building_id,
        stack_id=stack_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Stack not found"
        )


# ============================================
# BUILDING UNIT ENDPOINTS
# ============================================

@router.get(
    "/projects/{slug}/buildings/{building_id}/units",
    response_model=BuildingUnitListResponse,
)
async def list_units(
    slug: str,
    building_id: UUID,
    floor: Optional[int] = Query(None, description="Filter by floor number"),
    stack_id: Optional[UUID] = Query(None, description="Filter by stack ID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List units for a building with optional filters."""
    service = BuildingService(db)
    result = await service.list_units(
        project_slug=slug,
        building_id=building_id,
        floor_number=floor,
        stack_id=stack_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    units, total = result
    return BuildingUnitListResponse(
        units=[BuildingUnitResponse.model_validate(u) for u in units],
        total=total,
    )


@router.get(
    "/projects/{slug}/buildings/{building_id}/units/{unit_id}",
    response_model=BuildingUnitResponse,
)
async def get_unit(
    slug: str,
    building_id: UUID,
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a specific unit by ID."""
    service = BuildingService(db)
    unit = await service.get_unit(
        project_slug=slug,
        building_id=building_id,
        unit_id=unit_id,
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )

    return BuildingUnitResponse.model_validate(unit)


@router.post(
    "/projects/{slug}/buildings/{building_id}/units",
    response_model=BuildingUnitResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_unit(
    slug: str,
    building_id: UUID,
    data: BuildingUnitCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Create a new unit."""
    service = BuildingService(db)
    unit = await service.create_unit(
        project_slug=slug,
        building_id=building_id,
        data=data,
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create unit."
        )

    return BuildingUnitResponse.model_validate(unit)


@router.put(
    "/projects/{slug}/buildings/{building_id}/units/{unit_id}",
    response_model=BuildingUnitResponse,
)
async def update_unit(
    slug: str,
    building_id: UUID,
    unit_id: UUID,
    data: BuildingUnitUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Update an existing unit."""
    service = BuildingService(db)
    unit = await service.update_unit(
        project_slug=slug,
        building_id=building_id,
        unit_id=unit_id,
        data=data,
    )

    if not unit:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not update unit."
        )

    return BuildingUnitResponse.model_validate(unit)


@router.post(
    "/projects/{slug}/buildings/{building_id}/units/generate",
    response_model=GenerateUnitsResponse,
)
async def generate_units(
    slug: str,
    building_id: UUID,
    data: GenerateUnitsRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Auto-generate units from stacks.

    Creates a unit for each floor in each stack's range,
    respecting building skip_floors and optional additional skip_floors.
    """
    service = BuildingService(db)
    result = await service.generate_units_from_stacks(
        project_slug=slug,
        building_id=building_id,
        stack_ids=data.stack_ids,
        skip_floors=data.skip_floors,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Building not found or no draft version exists"
        )

    created, skipped = result
    return GenerateUnitsResponse(
        created=created,
        skipped=skipped,
        message=f"Generated {created} units, skipped {skipped} (existing or skip floors)",
    )


@router.delete(
    "/projects/{slug}/buildings/{building_id}/units/{unit_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_unit(
    slug: str,
    building_id: UUID,
    unit_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Delete a unit."""
    service = BuildingService(db)
    deleted = await service.delete_unit(
        project_slug=slug,
        building_id=building_id,
        unit_id=unit_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Unit not found"
        )


# ============================================
# VIEW OVERLAY MAPPING ENDPOINTS
# ============================================

@router.get(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/overlays",
    response_model=OverlayMappingListResponse,
)
async def list_overlay_mappings(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """List overlay mappings for a view."""
    service = BuildingService(db)
    result = await service.list_overlay_mappings(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View not found"
        )

    mappings, total = result
    return OverlayMappingListResponse(
        mappings=[OverlayMappingResponse.model_validate(m) for m in mappings],
        total=total,
    )


@router.post(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/overlays",
    response_model=OverlayMappingResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_overlay_mapping(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    data: OverlayMappingCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Create a new overlay mapping."""
    service = BuildingService(db)
    mapping = await service.create_overlay_mapping(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
        data=data,
    )

    if not mapping:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Could not create overlay mapping."
        )

    return OverlayMappingResponse.model_validate(mapping)


@router.post(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/overlays/bulk",
    response_model=BulkOverlayMappingResponse,
)
async def bulk_upsert_overlay_mappings(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    data: BulkOverlayMappingRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Bulk create or update overlay mappings.

    Resolves target_ref to stack_id or unit_id based on target_type.
    """
    service = BuildingService(db)
    result = await service.bulk_upsert_overlay_mappings(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
        mappings=data.mappings,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="View not found or no draft version exists"
        )

    created, updated, errors = result
    return BulkOverlayMappingResponse(
        created=created,
        updated=updated,
        errors=errors,
    )


@router.delete(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/overlays/{mapping_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_overlay_mapping(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    mapping_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """Delete an overlay mapping."""
    service = BuildingService(db)
    deleted = await service.delete_overlay_mapping(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
        mapping_id=mapping_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Overlay mapping not found"
        )


# ============================================
# VIEW IMAGE UPLOAD ENDPOINTS
# ============================================

@router.post(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/upload-url",
    response_model=ViewUploadUrlResponse,
)
async def request_view_upload_url(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    data: ViewUploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Request a presigned URL for uploading a view image.

    Use this for elevation, rotation, or floor plan images.
    After upload, call the confirm endpoint.
    """
    service = BuildingService(db)
    view = await service.get_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
    )

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View not found"
        )

    # Get building for path
    building = await service.get_building(project_slug=slug, building_id=building_id)

    # Generate storage path
    ext = data.filename.split(".")[-1] if "." in data.filename else "png"
    storage_path = f"mp/{slug}/buildings/{building.ref}/views/{view.ref}.{ext}"

    # Generate presigned upload URL
    upload_url = await storage_service.storage.get_presigned_upload_url(
        key=storage_path,
        content_type=data.content_type,
        expires_in=3600,
    )

    return ViewUploadUrlResponse(
        upload_url=upload_url,
        storage_path=storage_path,
        expires_in_seconds=3600,
    )


@router.post(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/confirm-upload",
    response_model=BuildingViewResponse,
)
async def confirm_view_upload(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    data: ViewUploadConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Confirm view image upload and update view record.

    Call this after successfully uploading the image using the presigned URL.
    """
    service = BuildingService(db)
    view = await service.get_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
    )

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View not found"
        )

    # Verify file exists in storage
    exists = await storage_service.storage.file_exists(data.storage_path)
    if not exists:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File not found in storage"
        )

    # Update view with asset path
    from app.schemas.building import BuildingViewUpdate
    updated_view = await service.update_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
        data=BuildingViewUpdate(asset_path=data.storage_path, tiles_generated=False),
    )

    return BuildingViewResponse.model_validate(updated_view)


# ============================================
# BUILDING TILE GENERATION
# ============================================

@router.post(
    "/projects/{slug}/buildings/{building_id}/generate-tiles",
    response_model=JobCreateResponse,
)
async def generate_building_tiles(
    slug: str,
    building_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Start tile generation for all views of a building.

    Returns job ID for tracking progress via /jobs/{id}/stream.
    """
    service = BuildingService(db)
    building = await service.get_building(project_slug=slug, building_id=building_id)

    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    # Get project for job creation
    project_result = await db.execute(
        select(Project).where(Project.slug == slug)
    )
    project = project_result.scalar_one_or_none()

    # Check draft version
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.status == "draft"
        ).limit(1)
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No draft version exists"
        )

    # Create job
    job_service = JobService(db)
    job = await job_service.create_job(
        job_type="building_tiles",
        project_id=project.id,
        version_id=version.id,
        created_by=current_user.id,
        metadata={
            "building_id": str(building_id),
            "building_ref": building.ref,
        }
    )

    # Generate build path
    from app.services.release_service import generate_release_id
    build_id = generate_release_id().replace("rel_", "bld_")
    build_path = f"mp/{slug}/builds/{build_id}"

    # Start background task
    background_tasks.add_task(
        _run_building_tile_job,
        job_id=job.id,
        project_slug=slug,
        building_id=building_id,
        build_path=build_path,
    )

    return JobCreateResponse(
        job_id=job.id,
        status="queued",
        message=f"Building tile generation started for {building.ref}"
    )


async def _run_building_tile_job(
    job_id: UUID,
    project_slug: str,
    building_id: UUID,
    build_path: str,
):
    """Run building tile generation with new database session."""
    from app.lib.database import async_session_maker
    from app.jobs.building_build_job import run_building_build_job

    async with async_session_maker() as db:
        try:
            await run_building_build_job(
                db=db,
                job_id=job_id,
                project_slug=project_slug,
                building_id=building_id,
                build_path=build_path,
            )
        except Exception as e:
            print(f"Building tile job {job_id} failed: {e}")


# ============================================
# SVG IMPORT FOR VIEW OVERLAYS
# ============================================

@router.post(
    "/projects/{slug}/buildings/{building_id}/views/{view_id}/import-svg",
)
async def import_view_overlays_from_svg(
    slug: str,
    building_id: UUID,
    view_id: UUID,
    data: SVGImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Import stack or unit overlays from SVG content.

    Parses the SVG and creates overlay mappings for the view.
    Path IDs in the SVG should match stack/unit refs.

    - **target_type**: 'stack' for elevation views, 'unit' for floor plans
    - **id_pattern**: Optional regex to filter paths by ID
    """
    service = BuildingService(db)

    view = await service.get_view(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
    )

    if not view:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="View not found"
        )

    # Parse SVG
    try:
        parsed = svg_parser.parse_svg(data.svg_content, id_pattern=data.id_pattern)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse SVG: {str(e)}"
        )

    if not parsed:
        return {
            "success": True,
            "parsed_count": 0,
            "created": 0,
            "updated": 0,
            "errors": [],
            "message": "No matching paths found in SVG",
        }

    # Get viewBox from SVG
    view_box = svg_parser.get_viewbox(data.svg_content)

    # Update view's viewBox if found
    if view_box and not view.view_box:
        from app.schemas.building import BuildingViewUpdate
        await service.update_view(
            project_slug=slug,
            building_id=building_id,
            view_id=view_id,
            data=BuildingViewUpdate(view_box=view_box),
        )

    # Convert to overlay mapping format
    from app.schemas.building import BulkOverlayMappingItem
    mappings = [
        BulkOverlayMappingItem(
            target_type=data.target_type,
            target_ref=p.id,
            geometry={"type": "path", "d": p.path_data},
            label_position={"x": p.centroid[0], "y": p.centroid[1]},
            sort_order=idx,
        )
        for idx, p in enumerate(parsed)
    ]

    # Bulk upsert
    result = await service.bulk_upsert_overlay_mappings(
        project_slug=slug,
        building_id=building_id,
        view_id=view_id,
        mappings=mappings,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to import overlays"
        )

    created, updated, errors = result

    return {
        "success": True,
        "parsed_count": len(parsed),
        "created": created,
        "updated": updated,
        "errors": errors,
        "view_box": view_box,
        "message": f"Imported {created} new mappings, updated {updated} existing",
    }


@router.post(
    "/projects/{slug}/buildings/{building_id}/import-stacks-svg",
)
async def import_stacks_from_svg(
    slug: str,
    building_id: UUID,
    data: SVGImportRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Import stack definitions from SVG content.

    Creates stacks from path elements in the SVG.
    Each path ID becomes a stack ref.
    Floor ranges can be specified in path metadata or defaults are used.

    This is different from import-svg on a view - this creates
    the actual Stack entities, not overlay mappings.
    """
    service = BuildingService(db)

    building = await service.get_building(project_slug=slug, building_id=building_id)
    if not building:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Building not found"
        )

    # Parse SVG
    try:
        parsed = svg_parser.parse_svg(data.svg_content, id_pattern=data.id_pattern)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to parse SVG: {str(e)}"
        )

    if not parsed:
        return {
            "success": True,
            "parsed_count": 0,
            "created": 0,
            "updated": 0,
            "errors": [],
        }

    # Convert to stack format
    from app.schemas.building import BulkStackItem
    stacks = [
        BulkStackItem(
            ref=p.id,
            label={"en": p.id},
            floor_start=building.floors_start,
            floor_end=building.floors_start + building.floors_count - 1,
            sort_order=idx,
        )
        for idx, p in enumerate(parsed)
    ]

    # Bulk upsert stacks
    result = await service.bulk_upsert_stacks(
        project_slug=slug,
        building_id=building_id,
        stacks=stacks,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to import stacks"
        )

    created, updated, errors = result

    return {
        "success": True,
        "parsed_count": len(parsed),
        "created": created,
        "updated": updated,
        "errors": errors,
        "message": f"Imported {created} new stacks, updated {updated} existing",
    }
