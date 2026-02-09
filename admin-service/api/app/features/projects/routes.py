from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_admin, require_editor
from app.models.user import User
from app.schemas.project import (
    ProjectCreate,
    ProjectDetailResponse,
    ProjectListResponse,
    ProjectResponse,
    ProjectUpdate,
    VersionCreate,
    VersionInfo,
    VersionResponse,
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])


@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all active projects with pagination.
    """
    service = ProjectService(db)
    projects, total = await service.list_projects(skip=skip, limit=limit)

    return ProjectListResponse(
        items=[ProjectResponse.model_validate(p) for p in projects],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("", response_model=ProjectDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Create a new project. Admin only.
    Automatically creates version 1 as draft.
    """
    service = ProjectService(db)

    # Check slug uniqueness
    if await service.slug_exists(data.slug):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Project with slug '{data.slug}' already exists"
        )

    project = await service.create_project(data, current_user.id)

    return _build_project_detail_response(project)


@router.get("/{slug}", response_model=ProjectDetailResponse)
async def get_project(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get project details with all versions.
    """
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )

    return _build_project_detail_response(project)


@router.put("/{slug}", response_model=ProjectResponse)
async def update_project(
    slug: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Update project details. Admin or Editor only.
    """
    service = ProjectService(db)
    project = await service.update_project(slug, data)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )

    return ProjectResponse.model_validate(project)


@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_admin),
):
    """
    Soft delete a project. Admin only.
    Sets is_active to False.
    """
    service = ProjectService(db)
    deleted = await service.delete_project(slug)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )


@router.post("/{slug}/versions", response_model=VersionResponse, status_code=status.HTTP_201_CREATED)
async def create_version(
    slug: str,
    data: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Create a new version for a project. Admin or Editor only.
    Optionally clone from an existing version.
    """
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )

    # Validate base_version exists if provided
    if data.base_version:
        base = await service.get_version(project.id, data.base_version)
        if not base:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Version {data.base_version} not found"
            )

    version = await service.create_version(project.id, data)

    return VersionResponse.model_validate(version)


@router.get("/{slug}/versions/{version_number}", response_model=VersionResponse)
async def get_version(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific version of a project.
    """
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project '{slug}' not found"
        )

    version = await service.get_version(project.id, version_number)

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Version {version_number} not found"
        )

    return VersionResponse.model_validate(version)


def _build_project_detail_response(project) -> ProjectDetailResponse:
    """Build ProjectDetailResponse with version info."""
    versions = sorted(project.versions, key=lambda v: v.version_number)

    version_infos = [
        VersionInfo(
            id=v.id,
            version_number=v.version_number,
            status=v.status,
            created_at=v.created_at,
            published_at=v.published_at,
        )
        for v in versions
    ]

    # Find current draft and published version
    current_draft = None
    published_version = None

    for v in versions:
        if v.status == "draft":
            current_draft = v.version_number
        elif v.status == "published":
            published_version = v.version_number

    return ProjectDetailResponse(
        id=project.id,
        slug=project.slug,
        name=project.name,
        name_ar=project.name_ar,
        description=project.description,
        is_active=project.is_active,
        created_at=project.created_at,
        updated_at=project.updated_at,
        versions=version_infos,
        current_draft=current_draft,
        published_version=published_version,
    )
