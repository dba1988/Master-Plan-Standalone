# TASK-010b: Tile Generation Job Integration

**Phase**: 4 - Build Pipeline
**Status**: [x] Completed
**Priority**: P0 - Critical
**Depends On**: TASK-010a (tile core), TASK-013a (job infrastructure)
**Blocks**: TASK-013b (publish workflow)
**Estimated Time**: 2-3 hours

## Objective

Integrate tile generation with the job system, including progress tracking, R2 upload, and error handling.

## Scope

This task covers job orchestration and R2 integration. Core tile logic is in TASK-010a.

## Files to Create/Modify

```
admin-service/api/app/
├── jobs/
│   └── tile_generation_job.py
└── api/
    └── tiles.py  (endpoints)
```

## Implementation

### Tile Generation Job

```python
# app/jobs/tile_generation_job.py
import tempfile
import shutil
from pathlib import Path
from uuid import UUID

from app.services.tile_service import tile_service
from app.services.r2_storage_service import r2_storage
from app.services.job_service import job_service
from app.models import Job

async def run_tile_generation_job(
    job_id: UUID,
    project_slug: str,
    version_id: UUID,
    source_asset_key: str,
) -> dict:
    """
    Background job to generate tiles from base map.

    1. Download source image from R2
    2. Generate tiles locally
    3. Upload tiles to R2 staging
    4. Update job with result
    """

    job = await job_service.get_job(job_id)

    try:
        # Update status
        await job_service.update_progress(job_id, 5, "Downloading source image...")

        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Download source
            source_path = Path(temp_dir) / "source.png"
            await download_from_r2(source_asset_key, source_path)

            await job_service.update_progress(job_id, 10, "Generating tiles...")

            # Generate tiles with progress
            tiles_dir = Path(temp_dir) / "tiles"

            def progress_callback(percent):
                # Scale 10-80% for tile generation
                scaled = 10 + int(percent * 0.7)
                job_service.update_progress_sync(job_id, scaled, f"Generating tiles... {percent}%")

            result = tile_service.generate_tiles(
                source_path=str(source_path),
                output_dir=str(tiles_dir),
                progress_callback=progress_callback,
            )

            await job_service.update_progress(job_id, 80, "Uploading tiles to storage...")

            # Upload tiles to R2
            tiles_key_prefix = f"mp/{project_slug}/uploads/tiles/"
            tile_count = 0

            for tile_file in tiles_dir.rglob("*.png"):
                relative_path = tile_file.relative_to(tiles_dir)
                key = f"{tiles_key_prefix}{relative_path}"

                with open(tile_file, "rb") as f:
                    await r2_storage.upload_file(
                        key=key,
                        body=f.read(),
                        content_type="image/png",
                        public=True,
                    )
                tile_count += 1

            await job_service.update_progress(job_id, 95, "Finalizing...")

            # Build result
            job_result = {
                "tiles_path": tiles_key_prefix,
                "width": result["width"],
                "height": result["height"],
                "levels": result["levels"],
                "tile_count": tile_count,
                "tile_size": result["tile_size"],
            }

            await job_service.complete_job(job_id, job_result)
            return job_result

    except Exception as e:
        await job_service.fail_job(job_id, str(e))
        raise


async def download_from_r2(key: str, local_path: Path) -> None:
    """Download file from R2 to local path."""
    url = await r2_storage.get_presigned_download_url(key)
    # Use httpx or aiohttp to download
    import httpx
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        local_path.write_bytes(response.content)
```

### Tiles API Endpoint

```python
# app/api/tiles.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.core.database import get_db
from app.api.deps import get_current_user
from app.models import User
from app.services.job_service import job_service
from app.services.project_service import project_service
from app.jobs.tile_generation_job import run_tile_generation_job

router = APIRouter(tags=["Tiles"])

@router.post("/projects/{slug}/versions/{version}/generate-tiles")
async def generate_tiles(
    slug: str,
    version: int,
    asset_id: UUID,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Start tile generation job for a base map asset.

    Returns job ID for tracking progress.
    """
    # Get project and version
    project = await project_service.get_by_slug(db, slug)
    if not project:
        raise HTTPException(404, "Project not found")

    version_obj = next(
        (v for v in project.versions if v.version_number == version),
        None
    )
    if not version_obj:
        raise HTTPException(404, "Version not found")

    if version_obj.status != "draft":
        raise HTTPException(400, "Can only generate tiles for draft versions")

    # Get asset
    asset = await get_asset(db, asset_id)
    if not asset or asset.asset_type != "base_map":
        raise HTTPException(400, "Invalid base map asset")

    # Create job
    job = await job_service.create_job(
        db=db,
        job_type="tile_generation",
        project_id=project.id,
        version_id=version_obj.id,
        created_by=current_user.id,
        metadata={
            "asset_id": str(asset_id),
            "asset_key": asset.storage_path,
        }
    )

    # Start background task
    background_tasks.add_task(
        run_tile_generation_job,
        job_id=job.id,
        project_slug=slug,
        version_id=version_obj.id,
        source_asset_key=asset.storage_path,
    )

    return {
        "job_id": job.id,
        "status": "queued",
        "message": "Tile generation started",
    }


@router.get("/jobs/{job_id}")
async def get_job_status(
    job_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get job status and progress."""
    job = await job_service.get_job(db, job_id)
    if not job:
        raise HTTPException(404, "Job not found")

    return {
        "id": job.id,
        "job_type": job.job_type,
        "status": job.status,
        "progress": job.progress,
        "message": job.message,
        "result": job.result,
        "error": job.error,
        "created_at": job.created_at,
        "completed_at": job.completed_at,
    }
```

## Job Model (from TASK-012)

```python
# app/models/job.py
class Job(Base):
    __tablename__ = "jobs"

    id = Column(UUID, primary_key=True, default=uuid4)
    job_type = Column(String(50), nullable=False)  # tile_generation, publish, etc.
    status = Column(String(20), default="queued")  # queued, running, completed, failed
    progress = Column(Integer, default=0)  # 0-100
    message = Column(Text)
    result = Column(JSONB)
    error = Column(Text)

    project_id = Column(UUID, ForeignKey("projects.id"))
    version_id = Column(UUID, ForeignKey("versions.id"))
    created_by = Column(UUID, ForeignKey("users.id"))

    created_at = Column(DateTime, default=datetime.utcnow)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
```

## Acceptance Criteria

- [x] Job creates and returns job_id
- [x] Progress updates at each stage (download, generate, upload)
- [x] Tiles uploaded to R2 staging path
- [x] Job completes with result metadata
- [x] Failed jobs have error captured
- [x] GET /jobs/{id} returns status
- [x] Only draft versions can generate tiles
