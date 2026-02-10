"""
Jobs API endpoints.

Provides job status and real-time streaming via SSE.
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user
from app.lib.sse import SSEMessage, sse_manager
from app.models.user import User
from app.schemas.job import JobResponse, JobSummary
from app.services.job_service import JobService

router = APIRouter(prefix="/jobs", tags=["Jobs"])


@router.get("/{job_id}", response_model=JobResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get job status and details.

    Returns full job state including all logs.
    """
    service = JobService(db)
    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    return job


@router.get("/{job_id}/stream")
async def stream_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Stream job updates via Server-Sent Events.

    Sends current state immediately, then streams updates.
    Stream ends when job reaches terminal status (completed/failed/cancelled).
    Ping sent every 30s to keep connection alive.
    """
    service = JobService(db)
    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    # Create initial message with current state
    initial = SSEMessage(
        data=job.to_dict(),
        event="job_update",
        id="0",
    )

    # Check if already terminal
    if job.status in ("completed", "failed", "cancelled"):
        # Return just the current state
        async def single_response():
            yield initial.encode()

        return StreamingResponse(
            single_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            }
        )

    # Stream updates
    channel = service.get_channel(job_id)

    return StreamingResponse(
        sse_manager.stream(channel, ping_interval=30, initial_message=initial),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.post("/{job_id}/cancel", response_model=JobResponse)
async def cancel_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Cancel a running or queued job.

    Only works for jobs that haven't completed yet.
    """
    service = JobService(db)
    job = await service.get_job(job_id)

    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found"
        )

    if job.status in ("completed", "failed", "cancelled"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel job with status: {job.status}"
        )

    job = await service.cancel_job(job_id)
    return job


@router.get("", response_model=list[JobSummary])
async def list_jobs(
    project_id: Optional[UUID] = None,
    status: Optional[str] = None,
    job_type: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List jobs with optional filters.

    Returns summary info for each job.
    """
    service = JobService(db)
    jobs = await service.list_jobs(
        project_id=project_id,
        status=status,
        job_type=job_type,
        limit=min(limit, 100),
    )
    return jobs
