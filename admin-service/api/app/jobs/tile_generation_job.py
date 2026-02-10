"""
Tile Generation Job

Background job that generates DZI tiles from a base map asset.
"""
import tempfile
from pathlib import Path
from uuid import UUID

import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import JobService
from app.services.tile_service import tile_service
from app.services.storage_service import storage_service


async def run_tile_generation_job(
    db: AsyncSession,
    job_id: UUID,
    project_slug: str,
    version_id: UUID,
    source_asset_key: str,
) -> dict:
    """
    Background job to generate tiles from base map.

    Steps:
    1. Download source image from storage
    2. Generate tiles locally
    3. Upload tiles to staging
    4. Update job with result

    Args:
        db: Database session
        job_id: Job ID for progress tracking
        project_slug: Project slug for storage paths
        version_id: Version ID
        source_asset_key: Storage key for source image

    Returns:
        dict with tiles_path, width, height, levels, tile_count
    """
    service = JobService(db)

    try:
        # Start job
        await service.start_job(job_id)
        await service.update_progress(job_id, 5, "Downloading source image...")

        # Create temp directory
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Download source image
            source_path = temp_path / "source.png"
            await _download_from_storage(source_asset_key, source_path)

            await service.update_progress(job_id, 10, "Generating tiles...")

            # Generate tiles with progress callback
            tiles_dir = temp_path / "tiles"

            def progress_callback(percent: int):
                # Scale 10-80% for tile generation
                scaled = 10 + int(percent * 0.7)
                # Note: This is sync, can't await here
                # Progress will be updated after tile generation completes

            result = tile_service.generate_tiles(
                source_path=str(source_path),
                output_dir=str(tiles_dir),
                progress_callback=progress_callback,
            )

            await service.update_progress(job_id, 80, "Uploading tiles to storage...")

            # Upload tiles to staging
            tiles_key_prefix = f"mp/{project_slug}/uploads/tiles/"
            tile_count = 0

            for tile_file in tiles_dir.rglob(f"*.{result['format']}"):
                relative_path = tile_file.relative_to(tiles_dir)
                key = f"{tiles_key_prefix}{relative_path}"

                with open(tile_file, "rb") as f:
                    content_type = f"image/{result['format']}"
                    await storage_service.storage.upload_file(
                        key=key,
                        body=f.read(),
                        content_type=content_type,
                    )
                tile_count += 1

                # Update progress periodically
                if tile_count % 100 == 0:
                    progress = 80 + int((tile_count / result["tile_count"]) * 15)
                    await service.update_progress(
                        job_id,
                        min(95, progress),
                        f"Uploading tiles... ({tile_count}/{result['tile_count']})"
                    )

            await service.update_progress(job_id, 95, "Finalizing...")

            # Build result
            job_result = {
                "tiles_path": tiles_key_prefix,
                "width": result["width"],
                "height": result["height"],
                "levels": result["levels"],
                "tile_count": tile_count,
                "tile_size": result["tile_size"],
                "format": result["format"],
            }

            await service.complete_job(job_id, job_result)
            return job_result

    except Exception as e:
        await service.fail_job(job_id, str(e))
        raise


async def _download_from_storage(key: str, local_path: Path) -> None:
    """Download file from storage to local path."""
    url = await storage_service.storage.get_presigned_download_url(key)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        local_path.write_bytes(response.content)
