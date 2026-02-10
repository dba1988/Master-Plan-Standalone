"""
Job Service

Manages background job lifecycle with SSE broadcasting.
"""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.sse import SSEMessage, sse_manager
from app.models.job import Job


class JobService:
    """Service for managing background jobs."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_job(
        self,
        job_type: str,
        project_id: UUID,
        created_by: UUID,
        version_id: Optional[UUID] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Job:
        """
        Create a new job.

        Args:
            job_type: Type of job (tile_generation, svg_import, publish)
            project_id: Related project
            created_by: User who initiated the job
            version_id: Related version (optional)
            metadata: Initial job metadata stored in result

        Returns:
            Created Job instance
        """
        job = Job(
            job_type=job_type,
            project_id=project_id,
            created_by=created_by,
            version_id=version_id,
            status="queued",
            progress=0,
            message="Job queued",
            result=metadata,
            logs=[],
        )

        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)

        # Broadcast job created
        await self._broadcast_update(job)

        return job

    async def get_job(self, job_id: UUID) -> Optional[Job]:
        """Get job by ID."""
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def list_jobs(
        self,
        project_id: Optional[UUID] = None,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
    ) -> List[Job]:
        """List jobs with optional filters."""
        query = select(Job).order_by(Job.created_at.desc()).limit(limit)

        if project_id:
            query = query.where(Job.project_id == project_id)
        if status:
            query = query.where(Job.status == status)
        if job_type:
            query = query.where(Job.job_type == job_type)

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def start_job(self, job_id: UUID) -> Optional[Job]:
        """Mark job as running."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = "running"
        job.started_at = datetime.utcnow()
        job.progress = 0
        job.message = "Job started"

        await self._add_log(job, "Job started", "info")
        await self.db.commit()
        await self.db.refresh(job)
        await self._broadcast_update(job)

        return job

    async def update_progress(
        self,
        job_id: UUID,
        progress: int,
        message: Optional[str] = None,
    ) -> Optional[Job]:
        """
        Update job progress.

        Args:
            job_id: Job ID
            progress: Progress 0-100
            message: Optional status message
        """
        job = await self.get_job(job_id)
        if not job:
            return None

        job.progress = min(100, max(0, progress))
        if message:
            job.message = message

        await self.db.commit()
        await self.db.refresh(job)
        await self._broadcast_update(job)

        return job

    async def add_log(
        self,
        job_id: UUID,
        message: str,
        level: str = "info",
    ) -> Optional[Job]:
        """Add log entry to job."""
        job = await self.get_job(job_id)
        if not job:
            return None

        await self._add_log(job, message, level)
        await self.db.commit()
        await self.db.refresh(job)

        return job

    async def complete_job(
        self,
        job_id: UUID,
        result: Optional[Dict[str, Any]] = None,
    ) -> Optional[Job]:
        """Mark job as completed with result."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = "completed"
        job.progress = 100
        job.message = "Job completed"
        job.completed_at = datetime.utcnow()
        if result:
            # Merge with existing metadata
            job.result = {**(job.result or {}), **result}

        await self._add_log(job, "Job completed successfully", "info")
        await self.db.commit()
        await self.db.refresh(job)
        await self._broadcast_update(job, event="completed")

        return job

    async def fail_job(
        self,
        job_id: UUID,
        error: str,
    ) -> Optional[Job]:
        """Mark job as failed with error."""
        job = await self.get_job(job_id)
        if not job:
            return None

        job.status = "failed"
        job.error = error
        job.message = f"Job failed: {error}"
        job.completed_at = datetime.utcnow()

        await self._add_log(job, f"Job failed: {error}", "error")
        await self.db.commit()
        await self.db.refresh(job)
        await self._broadcast_update(job, event="failed")

        return job

    async def cancel_job(self, job_id: UUID) -> Optional[Job]:
        """Cancel a running or queued job."""
        job = await self.get_job(job_id)
        if not job:
            return None

        if job.status not in ("queued", "running"):
            return job  # Already terminal

        job.status = "cancelled"
        job.message = "Job cancelled"
        job.completed_at = datetime.utcnow()

        await self._add_log(job, "Job cancelled by user", "warn")
        await self.db.commit()
        await self.db.refresh(job)
        await self._broadcast_update(job, event="cancelled")

        return job

    async def _add_log(self, job: Job, message: str, level: str) -> None:
        """Add log entry to job (internal)."""
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message,
        }
        if job.logs is None:
            job.logs = []
        job.logs = job.logs + [log_entry]

    async def _broadcast_update(
        self,
        job: Job,
        event: str = "job_update",
    ) -> None:
        """Broadcast job update via SSE."""
        channel = f"job:{job.id}"
        message = SSEMessage(
            data=job.to_dict(),
            event=event,
            id=str(job.progress),
        )
        await sse_manager.broadcast(channel, message)

    def get_channel(self, job_id: UUID) -> str:
        """Get SSE channel for a job."""
        return f"job:{job_id}"
