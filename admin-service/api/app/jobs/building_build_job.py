"""
Building Build Job

Background job that generates tiles for building view assets (elevation, rotation, floor plans).
"""
import tempfile
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_view import BuildingView
from app.services.job_service import JobService
from app.services.storage_service import storage_service
from app.services.tile_service import tile_service

# Concurrency limit for parallel uploads
UPLOAD_WORKERS = 20


async def run_building_build_job(
    db: AsyncSession,
    job_id: UUID,
    project_slug: str,
    building_id: UUID,
    build_path: str,
) -> Dict[str, Any]:
    """
    Background job to generate tiles for all views of a building.

    Steps:
    1. Find all views for the building
    2. Download and tile each view image
    3. Upload tiles to build folder
    4. Update view records with tiles_generated flag
    5. Return tiles metadata

    Args:
        db: Database session
        job_id: Job ID for progress tracking
        project_slug: Project slug
        building_id: Building to process
        build_path: Base path for this build

    Returns:
        dict with view tiles metadata
    """
    job_service = JobService(db)

    try:
        await job_service.start_job(job_id)
        await job_service.update_progress(job_id, 5, "Finding building views...")

        # Get building
        building_result = await db.execute(
            select(Building).where(Building.id == building_id)
        )
        building = building_result.scalar_one_or_none()

        if not building:
            await job_service.fail_job(job_id, "Building not found")
            return {"error": "Building not found"}

        # Get all views with asset paths
        view_result = await db.execute(
            select(BuildingView).where(
                BuildingView.building_id == building_id,
                BuildingView.is_active == True,
                BuildingView.asset_path.isnot(None)
            ).order_by(BuildingView.view_type, BuildingView.sort_order)
        )
        views = list(view_result.scalars().all())

        if not views:
            await job_service.add_log(job_id, "No views with assets found", "warn")
            await job_service.complete_job(job_id, {"views_processed": 0})
            return {"views_processed": 0}

        await job_service.add_log(job_id, f"Found {len(views)} view(s) to process", "info")

        all_tiles_metadata: Dict[str, Dict[str, Any]] = {}
        total_tile_count = 0

        for idx, view in enumerate(views):
            view_progress_base = 10 + int((idx / len(views)) * 80)

            await job_service.update_progress(
                job_id,
                view_progress_base,
                f"Processing view: {view.ref} ({idx + 1}/{len(views)})..."
            )

            try:
                tiles_metadata = await _generate_tiles_for_view(
                    job_service=job_service,
                    job_id=job_id,
                    db=db,
                    view=view,
                    building_ref=building.ref,
                    build_path=build_path,
                    progress_base=view_progress_base,
                    progress_range=int(80 / len(views)),
                )

                all_tiles_metadata[view.ref] = tiles_metadata
                total_tile_count += tiles_metadata.get("tile_count", 0)

                # Mark view as tiles generated
                view.tiles_generated = True

                await job_service.add_log(
                    job_id,
                    f"Generated {tiles_metadata.get('tile_count', 0)} tiles for view: {view.ref}",
                    "info"
                )

            except Exception as e:
                await job_service.add_log(job_id, f"Failed to generate tiles for {view.ref}: {e}", "error")

        await db.commit()
        await job_service.update_progress(job_id, 95, "Finalizing...")

        job_result = {
            "building_ref": building.ref,
            "views_processed": len(all_tiles_metadata),
            "total_tile_count": total_tile_count,
            "views": all_tiles_metadata,
            "built_at": datetime.utcnow().isoformat(),
        }

        await job_service.complete_job(job_id, job_result)
        return job_result

    except Exception as e:
        await job_service.fail_job(job_id, str(e))
        raise


async def _generate_tiles_for_view(
    job_service: JobService,
    job_id: UUID,
    db: AsyncSession,
    view: BuildingView,
    building_ref: str,
    build_path: str,
    progress_base: int,
    progress_range: int,
) -> Dict[str, Any]:
    """
    Generate tiles for a single building view.

    Handles different view types:
    - elevation: Tall images (e.g., 2048x4096)
    - rotation: Square images (e.g., 2048x2048)
    - floor_plan: Wide images (e.g., 4096x2048)
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download source image
        source_ext = Path(view.asset_path).suffix or ".png"
        source_path = temp_path / f"source{source_ext}"
        await _download_from_storage(view.asset_path, source_path)

        # Generate tiles
        tiles_dir = temp_path / "tiles"

        result = tile_service.generate_tiles(
            source_path=str(source_path),
            output_dir=str(tiles_dir),
        )

        # Store viewBox from generated image dimensions
        view.view_box = f"0 0 {result['width']} {result['height']}"

        # Upload tiles
        tiles_key_prefix = f"{build_path}/tiles/buildings/{building_ref}/{view.ref}/"
        tile_files = list(tiles_dir.rglob(f"*.{result['format']}"))
        total_tiles = len(tile_files)

        uploaded_count = 0
        upload_lock = threading.Lock()
        content_type = f"image/{result['format']}"

        def upload_single_tile(tile_file: Path) -> bool:
            nonlocal uploaded_count
            relative_path = tile_file.relative_to(tiles_dir)
            key = f"{tiles_key_prefix}{relative_path}"

            with open(tile_file, "rb") as f:
                storage_service.storage.client.put_object(
                    Bucket=storage_service.storage.bucket,
                    Key=key,
                    Body=f.read(),
                    ContentType=content_type,
                )

            with upload_lock:
                uploaded_count += 1
            return True

        with ThreadPoolExecutor(max_workers=UPLOAD_WORKERS) as executor:
            futures = {executor.submit(upload_single_tile, tf): tf for tf in tile_files}

            for future in as_completed(futures):
                try:
                    future.result()
                except Exception as e:
                    tile_file = futures[future]
                    await job_service.add_log(job_id, f"Failed to upload {tile_file}: {e}", "error")

                with upload_lock:
                    current = uploaded_count
                if current % 50 == 0 or current == total_tiles:
                    progress = progress_base + int((current / total_tiles) * progress_range * 0.8)
                    await job_service.update_progress(
                        job_id,
                        min(progress_base + progress_range, progress),
                        f"Uploading tiles for {view.ref}... ({current}/{total_tiles})"
                    )

        return {
            "tiles_path": tiles_key_prefix,
            "view_type": view.view_type,
            "view_ref": view.ref,
            "width": result["width"],
            "height": result["height"],
            "levels": result["levels"],
            "tile_count": uploaded_count,
            "tile_size": result["tile_size"],
            "format": result["format"],
            "view_box": view.view_box,
        }


async def _download_from_storage(key: str, local_path: Path) -> None:
    """Download file from storage to local path."""
    url = await storage_service.storage.get_presigned_download_url(key)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        local_path.write_bytes(response.content)
