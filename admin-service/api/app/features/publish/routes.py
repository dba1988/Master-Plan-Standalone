"""
Publish endpoints.

Handles version publishing workflow.
"""
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.project import Project
from app.models.user import User
from app.models.version import ProjectVersion
from app.schemas.job import JobCreateResponse
from app.schemas.release import PublishRequest, PublishValidationResponse
from app.services.job_service import JobService
from app.services.release_service import ReleaseService
from app.jobs.publish_job import run_publish_job

router = APIRouter(tags=["Publish"])


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
