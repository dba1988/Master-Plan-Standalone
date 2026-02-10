"""
Tile Generation endpoints.

Triggers background jobs for tile generation from base map assets.
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.asset import Asset
from app.models.project import Project
from app.models.user import User
from app.models.version import ProjectVersion
from app.schemas.job import JobCreateResponse
from app.services.job_service import JobService
from app.jobs.tile_generation_job import run_tile_generation_job

router = APIRouter(prefix="/tiles", tags=["Tiles"])


@router.post(
    "/projects/{slug}/versions/{version_number}/generate-tiles",
    response_model=JobCreateResponse,
)
async def generate_tiles(
    slug: str,
    version_number: int,
    asset_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Start tile generation job for a base map asset.

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
            detail="Can only generate tiles for draft versions"
        )

    # Get asset
    asset_result = await db.execute(
        select(Asset).where(
            Asset.id == asset_id,
            Asset.version_id == version.id
        )
    )
    asset = asset_result.scalar_one_or_none()

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    if asset.asset_type != "base_map":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Asset must be a base_map type"
        )

    # Create job
    job_service = JobService(db)
    job = await job_service.create_job(
        job_type="tile_generation",
        project_id=project.id,
        version_id=version.id,
        created_by=current_user.id,
        metadata={
            "asset_id": str(asset_id),
            "asset_key": asset.storage_path,
        }
    )

    # Start background task
    # Note: We need to pass a new db session to the background task
    background_tasks.add_task(
        _run_tile_job,
        job_id=job.id,
        project_slug=slug,
        version_id=version.id,
        source_asset_key=asset.storage_path,
    )

    return JobCreateResponse(
        job_id=job.id,
        status="queued",
        message="Tile generation started"
    )


async def _run_tile_job(
    job_id: UUID,
    project_slug: str,
    version_id: UUID,
    source_asset_key: str,
):
    """
    Wrapper to run tile generation with a new database session.

    Background tasks need their own session since the request session
    will be closed after the response is sent.
    """
    from app.lib.database import async_session_maker

    async with async_session_maker() as db:
        try:
            await run_tile_generation_job(
                db=db,
                job_id=job_id,
                project_slug=project_slug,
                version_id=version_id,
                source_asset_key=source_asset_key,
            )
        except Exception as e:
            # Job already marked as failed in run_tile_generation_job
            print(f"Tile generation job {job_id} failed: {e}")
