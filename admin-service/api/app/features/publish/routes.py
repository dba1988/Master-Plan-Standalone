"""
Publish endpoints.

Handles build and publish workflow:
- Build: Generate tiles + manifest for preview
- Publish: Make build live as an immutable release
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.asset import Asset
from app.models.overlay import Overlay
from app.models.project import Project
from app.models.user import User
from app.models.version import ProjectVersion
from app.schemas.job import JobCreateResponse
from app.schemas.release import (
    BuildRequest,
    BuildStatusResponse,
    BuildTilesInfo,
    BuildValidationResponse,
    PublishRequest,
    PublishValidationResponse,
    ReleaseHistoryItem,
    ReleaseHistoryResponse,
)
from app.services.job_service import JobService
from app.services.release_service import ReleaseService
from app.services.storage_service import storage_service
from app.jobs.build_job import run_build_job
from app.jobs.publish_job import run_publish_job

router = APIRouter(tags=["Build & Publish"])


@router.get(
    "/projects/{slug}/versions/{version_number}/publish/validate",
    response_model=PublishValidationResponse,
)
async def validate_for_publish(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate if a version is ready for publishing.

    Returns validation errors and warnings without starting the publish job.
    """
    service = ReleaseService(db)
    is_valid, errors, warnings = await service.validate_for_publish(
        slug, version_number
    )

    return PublishValidationResponse(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
    )


@router.post(
    "/projects/{slug}/versions/{version_number}/publish",
    response_model=JobCreateResponse,
)
async def publish_version(
    slug: str,
    version_number: int,
    data: PublishRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Start publish job for a version.

    Creates an immutable release from the draft version.
    Returns job ID for tracking progress via /jobs/{id}/stream.
    """
    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get version
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.version_number == version_number
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    if version.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot publish version with status: {version.status}"
        )

    # Create job
    job_service = JobService(db)
    job = await job_service.create_job(
        job_type="publish",
        project_id=project.id,
        version_id=version.id,
        created_by=current_user.id,
        metadata={
            "version_number": version_number,
            "target_environment": data.target_environment if data else "production",
        }
    )

    # Start background task
    background_tasks.add_task(
        _run_publish_job,
        job_id=job.id,
        project_slug=slug,
        version_number=version_number,
        user_email=current_user.email,
        user_id=current_user.id,
    )

    return JobCreateResponse(
        job_id=job.id,
        status="queued",
        message="Publish job started"
    )


async def _run_publish_job(
    job_id: UUID,
    project_slug: str,
    version_number: int,
    user_email: str,
    user_id: UUID,
):
    """
    Wrapper to run publish job with a new database session.
    """
    from app.lib.database import async_session_maker

    async with async_session_maker() as db:
        try:
            await run_publish_job(
                db=db,
                job_id=job_id,
                project_slug=project_slug,
                version_number=version_number,
                user_email=user_email,
                user_id=user_id,
            )
        except Exception as e:
            print(f"Publish job {job_id} failed: {e}")


# ============================================================================
# BUILD ENDPOINTS
# ============================================================================


@router.get(
    "/projects/{slug}/versions/{version_number}/build/validate",
    response_model=BuildValidationResponse,
)
async def validate_for_build(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Validate if a version is ready for building.

    Checks:
    - Version exists and is a draft
    - Has base map assets (optional but recommended)
    - Has overlays defined
    """
    errors = []
    warnings = []

    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        errors.append("Project not found")
        return BuildValidationResponse(
            valid=False,
            errors=errors,
            warnings=warnings,
            base_map_count=0,
            overlay_count=0,
        )

    # Get version
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.version_number == version_number
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        errors.append("Version not found")
        return BuildValidationResponse(
            valid=False,
            errors=errors,
            warnings=warnings,
            base_map_count=0,
            overlay_count=0,
        )

    if version.status != "draft":
        errors.append(f"Cannot build version with status: {version.status}")

    # Count base maps
    base_map_result = await db.execute(
        select(func.count(Asset.id)).where(
            Asset.project_id == project.id,
            Asset.asset_type == "base_map"
        )
    )
    base_map_count = base_map_result.scalar_one()

    if base_map_count == 0:
        warnings.append("No base map assets found - tiles will not be generated")

    # Count overlays
    overlay_result = await db.execute(
        select(func.count(Overlay.id)).where(
            Overlay.project_id == project.id
        )
    )
    overlay_count = overlay_result.scalar_one()

    if overlay_count == 0:
        warnings.append("No overlays defined")

    is_valid = len(errors) == 0
    return BuildValidationResponse(
        valid=is_valid,
        errors=errors,
        warnings=warnings,
        base_map_count=base_map_count,
        overlay_count=overlay_count,
    )


@router.post(
    "/projects/{slug}/versions/{version_number}/build",
    response_model=JobCreateResponse,
)
async def start_build(
    slug: str,
    version_number: int,
    data: BuildRequest = None,
    background_tasks: BackgroundTasks = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Start build job for a version.

    Generates tiles from all base_map assets and creates a preview manifest.
    Returns job ID for tracking progress via /jobs/{id}/stream.

    After build completes, use /build/status to get the preview URL.
    """
    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get version
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.version_number == version_number
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    if version.status != "draft":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot build version with status: {version.status}"
        )

    # Create job
    job_service = JobService(db)
    job = await job_service.create_job(
        job_type="build",
        project_id=project.id,
        version_id=version.id,
        created_by=current_user.id,
        metadata={
            "version_number": version_number,
        }
    )

    # Start background task
    background_tasks.add_task(
        _run_build_job,
        job_id=job.id,
        project_slug=slug,
        version_number=version_number,
        user_email=current_user.email,
        user_id=current_user.id,
    )

    return JobCreateResponse(
        job_id=job.id,
        status="queued",
        message="Build job started"
    )


@router.get(
    "/projects/{slug}/versions/{version_number}/build/status",
    response_model=BuildStatusResponse,
)
async def get_build_status(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the latest build status for a version.

    Returns the most recent successful build if one exists.
    """
    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get version
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.version_number == version_number
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Find latest successful build job
    from app.models.job import Job

    job_result = await db.execute(
        select(Job).where(
            Job.project_id == project.id,
            Job.version_id == version.id,
            Job.job_type == "build",
            Job.status == "completed"
        ).order_by(Job.completed_at.desc()).limit(1)
    )
    build_job = job_result.scalar_one_or_none()

    if not build_job or not build_job.result:
        return BuildStatusResponse(
            has_build=False,
        )

    result = build_job.result
    tiles_info = result.get("tiles", {})

    # Generate presigned URL for preview (valid for 1 hour)
    build_path = result.get("build_path")
    preview_url = None
    if build_path:
        manifest_key = f"{build_path}/release.json"
        preview_url = await storage_service.storage.get_presigned_download_url(
            manifest_key, expires_in=3600
        )

    return BuildStatusResponse(
        has_build=True,
        build_id=result.get("build_id"),
        build_path=result.get("build_path"),
        preview_url=preview_url,
        built_at=build_job.completed_at,
        overlay_count=result.get("overlay_count", 0),
        tiles=BuildTilesInfo(
            levels=tiles_info.get("levels", []),
            total_count=tiles_info.get("total_count", 0),
            metadata=tiles_info.get("metadata", {}),
        ),
    )


@router.get(
    "/projects/{slug}/versions/{version_number}/build/preview",
)
async def get_build_preview(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the preview manifest content for the latest build.

    Returns the release.json content directly.
    """
    from fastapi.responses import JSONResponse

    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get version
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.version_number == version_number
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Version not found"
        )

    # Find latest successful build job
    from app.models.job import Job

    job_result = await db.execute(
        select(Job).where(
            Job.project_id == project.id,
            Job.version_id == version.id,
            Job.job_type == "build",
            Job.status == "completed"
        ).order_by(Job.completed_at.desc()).limit(1)
    )
    build_job = job_result.scalar_one_or_none()

    if not build_job or not build_job.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No build found for this version"
        )

    result = build_job.result
    build_path = result.get("build_path")

    if not build_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Build path not found"
        )

    # Download and return the manifest
    import json
    manifest_key = f"{build_path}/release.json"
    try:
        content = await storage_service.storage.download_file(manifest_key)
        manifest = json.loads(content)
        return JSONResponse(content=manifest)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load preview manifest: {str(e)}"
        )


async def _run_build_job(
    job_id: UUID,
    project_slug: str,
    version_number: int,
    user_email: str,
    user_id: UUID,
):
    """
    Wrapper to run build job with a new database session.
    """
    from app.lib.database import async_session_maker

    async with async_session_maker() as db:
        try:
            await run_build_job(
                db=db,
                job_id=job_id,
                project_slug=project_slug,
                version_number=version_number,
                user_email=user_email,
                user_id=user_id,
            )
        except Exception as e:
            print(f"Build job {job_id} failed: {e}")


# ============================================================================
# RELEASE HISTORY ENDPOINTS
# ============================================================================


@router.get(
    "/projects/{slug}/releases",
    response_model=ReleaseHistoryResponse,
)
async def get_release_history(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get release history for a project.

    Returns all published versions with their release info.
    """
    from sqlalchemy.orm import selectinload

    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Get all published versions with publisher info
    versions_result = await db.execute(
        select(ProjectVersion)
        .options(selectinload(ProjectVersion.publisher))
        .where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.status == "published",
            ProjectVersion.release_id.isnot(None)
        )
        .order_by(ProjectVersion.published_at.desc())
    )
    versions = list(versions_result.scalars().all())

    # Build release history items
    releases = []
    for v in versions:
        releases.append(ReleaseHistoryItem(
            version_number=v.version_number,
            release_id=v.release_id,
            release_url=v.release_url,
            published_at=v.published_at,
            published_by=v.publisher.email if v.publisher else None,
            is_current=(v.release_id == project.current_release_id),
        ))

    return ReleaseHistoryResponse(
        project_slug=slug,
        current_release_id=project.current_release_id,
        releases=releases,
        total=len(releases),
    )


@router.get(
    "/projects/{slug}/releases/{release_id}",
)
async def get_release_manifest(
    slug: str,
    release_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the manifest for a specific release.

    Returns the release.json content directly.
    """
    from fastapi.responses import JSONResponse
    import json

    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Verify this release exists for this project
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.release_id == release_id
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release not found"
        )

    # Download and return the manifest
    manifest_key = f"mp/{slug}/releases/{release_id}/release.json"
    try:
        content = await storage_service.storage.download_file(manifest_key)
        manifest = json.loads(content)
        return JSONResponse(content=manifest)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to load release manifest: {str(e)}"
        )


@router.get(
    "/projects/{slug}/releases/{release_id}/url",
)
async def get_release_url(
    slug: str,
    release_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a presigned URL to access a release manifest.

    Returns a URL valid for 1 hour.
    """
    # Get project
    project_result = await db.execute(
        select(Project).where(
            Project.slug == slug,
            Project.is_active == True
        )
    )
    project = project_result.scalar_one_or_none()

    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    # Verify this release exists for this project
    version_result = await db.execute(
        select(ProjectVersion).where(
            ProjectVersion.project_id == project.id,
            ProjectVersion.release_id == release_id
        )
    )
    version = version_result.scalar_one_or_none()

    if not version:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Release not found"
        )

    # Generate presigned URL
    manifest_key = f"mp/{slug}/releases/{release_id}/release.json"
    url = await storage_service.storage.get_presigned_download_url(
        manifest_key, expires_in=3600
    )

    return {"url": url, "expires_in": 3600}
