# TASK-013: Publish Workflow

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-010, TASK-011, TASK-012

## Objective

Implement the complete publish workflow as a background job.

## Description

Create the end-to-end publish workflow:
- Validate version is ready
- Generate tiles if needed
- Generate release.json
- Upload to storage
- Update version status
- Track progress via job status

## Files to Create

```
admin-api/app/
├── models/
│   └── job.py
├── schemas/
│   └── job.py
├── api/
│   └── publish.py
└── services/
    ├── publish_service.py
    └── job_service.py
```

## Implementation Steps

### Step 1: Job Model
```python
# app/models/job.py
from sqlalchemy import Column, String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.core.database import Base
import uuid
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_type = Column(String(50), nullable=False)  # publish, build_tiles
    status = Column(String(20), default=JobStatus.QUEUED.value)
    progress = Column(Integer, default=0)  # 0-100
    params = Column(JSONB, default=dict)
    result = Column(JSONB, nullable=True)
    error = Column(Text, nullable=True)
    logs = Column(JSONB, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
```

### Step 2: Job Schemas
```python
# app/schemas/job.py
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class PublishRequest(BaseModel):
    target_environment: str = "production"  # dev, staging, production

class JobResponse(BaseModel):
    id: UUID
    job_type: str
    status: JobStatus
    progress: int
    created_at: datetime
    started_at: Optional[datetime]
    completed_at: Optional[datetime]
    result: Optional[Dict[str, Any]]
    error: Optional[str]

    class Config:
        from_attributes = True

class JobDetailResponse(JobResponse):
    logs: List[Dict[str, Any]]
    params: Dict[str, Any]
```

### Step 3: Publish Service
```python
# app/services/publish_service.py
import asyncio
from datetime import datetime
from typing import Optional
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job, JobStatus
from app.models.version import ProjectVersion
from app.services.tile_service import TileService
from app.services.release_service import ReleaseService
from app.services.storage_service import StorageBackend

class PublishService:
    def __init__(
        self,
        db: AsyncSession,
        storage: StorageBackend
    ):
        self.db = db
        self.storage = storage

    async def create_publish_job(
        self,
        project_slug: str,
        version_number: int,
        target_env: str,
        user_id: UUID
    ) -> Job:
        """Create a publish job"""
        job = Job(
            job_type="publish",
            status=JobStatus.QUEUED.value,
            params={
                "project_slug": project_slug,
                "version_number": version_number,
                "target_env": target_env,
                "user_id": str(user_id)
            }
        )
        self.db.add(job)
        await self.db.commit()
        await self.db.refresh(job)
        return job

    async def execute_publish(self, job_id: UUID):
        """Execute the publish workflow"""
        # Get job
        job = await self._get_job(job_id)
        if not job:
            return

        try:
            # Update status
            job.status = JobStatus.RUNNING.value
            job.started_at = datetime.utcnow()
            await self.db.commit()

            params = job.params
            project_slug = params["project_slug"]
            version_number = params["version_number"]
            target_env = params["target_env"]

            # Step 1: Validate (10%)
            await self._log(job, "Validating version...")
            await self._update_progress(job, 10)

            # Step 2: Generate release.json (30%)
            await self._log(job, "Generating release.json...")
            release_service = ReleaseService(self.db)
            release = await release_service.generate_release(
                project_slug, version_number
            )

            errors = release_service.validate_release(release)
            if errors:
                raise ValueError(f"Validation errors: {errors}")

            await self._update_progress(job, 30)

            # Step 3: Upload release.json (50%)
            await self._log(job, "Uploading release.json...")
            release_json = release_service.to_json(release)
            release_path = f"{target_env}/{project_slug}/release.json"

            await self.storage.upload_file(
                release_json.encode(),
                release_path,
                "application/json"
            )
            await self._update_progress(job, 50)

            # Step 4: Copy tiles if needed (80%)
            await self._log(job, "Processing tiles...")
            # Tiles should already be in storage from build step
            await self._update_progress(job, 80)

            # Step 5: Update version status (100%)
            await self._log(job, "Updating version status...")
            await self._mark_published(project_slug, version_number)

            job.status = JobStatus.COMPLETED.value
            job.progress = 100
            job.completed_at = datetime.utcnow()
            job.result = {
                "release_url": f"/{release_path}",
                "overlay_count": len(release["overlays"]),
                "published_at": release["published_at"]
            }
            await self._log(job, "Publish completed successfully!")
            await self.db.commit()

        except Exception as e:
            job.status = JobStatus.FAILED.value
            job.error = str(e)
            job.completed_at = datetime.utcnow()
            await self._log(job, f"Error: {str(e)}", level="error")
            await self.db.commit()
            raise

    async def _get_job(self, job_id: UUID) -> Optional[Job]:
        from sqlalchemy import select
        result = await self.db.execute(
            select(Job).where(Job.id == job_id)
        )
        return result.scalar_one_or_none()

    async def _update_progress(self, job: Job, progress: int):
        job.progress = progress
        await self.db.commit()

    async def _log(self, job: Job, message: str, level: str = "info"):
        log_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "level": level,
            "message": message
        }
        job.logs = (job.logs or []) + [log_entry]
        await self.db.commit()

    async def _mark_published(self, project_slug: str, version_number: int):
        from sqlalchemy import select, update
        from app.models.project import Project
        from app.models.version import ProjectVersion

        # Get project
        result = await self.db.execute(
            select(Project).where(Project.slug == project_slug)
        )
        project = result.scalar_one()

        # Update version status
        await self.db.execute(
            update(ProjectVersion)
            .where(
                ProjectVersion.project_id == project.id,
                ProjectVersion.version_number == version_number
            )
            .values(
                status="published",
                published_at=datetime.utcnow()
            )
        )
        await self.db.commit()
```

### Step 4: Publish Endpoints
```python
# app/api/publish.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.services.publish_service import PublishService
from app.services.storage_service import get_storage, StorageBackend
from app.schemas.job import PublishRequest, JobResponse, JobDetailResponse

router = APIRouter(tags=["Publish"])

@router.post(
    "/projects/{slug}/versions/{version}/publish",
    response_model=JobResponse
)
async def publish_version(
    slug: str,
    version: int,
    request: PublishRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    storage: StorageBackend = Depends(get_storage),
    current_user: User = Depends(require_role(["admin"]))
):
    """Start a publish job"""
    service = PublishService(db, storage)

    # Create job
    job = await service.create_publish_job(
        slug, version,
        request.target_environment,
        current_user.id
    )

    # Execute in background
    background_tasks.add_task(service.execute_publish, job.id)

    return JobResponse.from_orm(job)

@router.get("/jobs/{job_id}", response_model=JobDetailResponse)
async def get_job(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Get job status and details"""
    from sqlalchemy import select
    from app.models.job import Job

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    return JobDetailResponse.from_orm(job)
```

## Publish Workflow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         Publish Workflow                                │
└─────────────────────────────────────────────────────────────────────────┘

POST /projects/{slug}/versions/{v}/publish
                    │
                    ▼
         ┌─────────────────────┐
         │   Create Job        │
         │   status: queued    │
         └──────────┬──────────┘
                    │ (background)
                    ▼
         ┌─────────────────────┐
         │  1. Validate        │  10%
         │  - Check assets     │
         │  - Check overlays   │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  2. Generate        │  30%
         │     release.json    │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  3. Upload          │  50%
         │     release.json    │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  4. Process Tiles   │  80%
         │  (copy/verify)      │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │  5. Mark Published  │  100%
         │  Update DB status   │
         └──────────┬──────────┘
                    │
                    ▼
         ┌─────────────────────┐
         │   Job Complete      │
         │   status: completed │
         │   result: {...}     │
         └─────────────────────┘
```

## Acceptance Criteria

- [ ] Publish creates background job
- [ ] Job progress tracked (0-100%)
- [ ] Logs captured for each step
- [ ] Release.json uploaded to storage
- [ ] Version marked as published
- [ ] Errors captured and job marked failed
- [ ] Can poll job status
