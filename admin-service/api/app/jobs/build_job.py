"""
Build Job

Background job that generates tiles for all base map assets and creates a preview build.
"""
import tempfile
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.services.job_service import JobService
from app.services.release_service import ReleaseService, generate_release_id
from app.services.storage_service import storage_service
from app.services.tile_service import tile_service


async def run_build_job(
    db: AsyncSession,
    job_id: UUID,
    project_slug: str,
    version_number: int,
    user_email: str,
    user_id: UUID,
) -> dict:
    """
    Background job to build tiles and generate preview manifest.

    Steps:
    1. Validate version is ready for build
    2. Generate build ID
    3. Find all base_map assets for the project
    4. Generate tiles for each base_map (grouped by level)
    5. Upload tiles to staging area
    6. Generate and upload release manifest
    7. Return build_id for preview

    Args:
        db: Database session
        job_id: Job ID for progress tracking
        project_slug: Project slug
        version_number: Version number being built
        user_email: User's email for manifest
        user_id: User's ID

    Returns:
        dict with build_id, preview_url, tiles_metadata
    """
    job_service = JobService(db)
    release_service = ReleaseService(db)

    try:
        # Start job
        await job_service.start_job(job_id)
        await job_service.update_progress(job_id, 2, "Validating version...")

        # Validate version exists and is draft
        result = await release_service.get_version(project_slug, version_number)
        if not result:
            await job_service.fail_job(job_id, "Project or version not found")
            return {"error": "Project or version not found"}

        project, version = result

        if version.status != "draft":
            await job_service.fail_job(job_id, f"Cannot build version with status: {version.status}")
            return {"error": f"Cannot build version with status: {version.status}"}

        await job_service.update_progress(job_id, 5, "Finding base map assets...")

        # Find all base_map assets for this project
        asset_result = await db.execute(
            select(Asset).where(
                Asset.project_id == project.id,
                Asset.asset_type == "base_map"
            ).order_by(Asset.level)
        )
        base_maps = list(asset_result.scalars().all())

        if not base_maps:
            await job_service.add_log(job_id, "No base map assets found, skipping tile generation", "warn")

        await job_service.update_progress(job_id, 8, "Generating build ID...")

        # Generate build ID (same format as release ID but with 'bld' prefix)
        build_id = generate_release_id().replace("rel_", "bld_")
        build_path = f"mp/{project_slug}/builds/{build_id}"

        await job_service.add_log(job_id, f"Build ID: {build_id}", "info")

        # Track all tile metadata by level
        all_tiles_metadata: Dict[str, Dict[str, Any]] = {}
        total_tile_count = 0

        # Process each base_map asset
        if base_maps:
            total_maps = len(base_maps)
            await job_service.add_log(job_id, f"Found {total_maps} base map(s) to process", "info")

            for idx, asset in enumerate(base_maps):
                level = asset.level or "project"
                map_progress_base = 10 + int((idx / total_maps) * 60)

                await job_service.update_progress(
                    job_id,
                    map_progress_base,
                    f"Processing base map: {level} ({idx + 1}/{total_maps})..."
                )

                try:
                    tiles_metadata = await _generate_tiles_for_asset(
                        job_service=job_service,
                        job_id=job_id,
                        asset=asset,
                        build_path=build_path,
                        level=level,
                        progress_base=map_progress_base,
                        progress_range=int(60 / total_maps),
                    )

                    all_tiles_metadata[level] = tiles_metadata
                    total_tile_count += tiles_metadata.get("tile_count", 0)

                    await job_service.add_log(
                        job_id,
                        f"Generated {tiles_metadata.get('tile_count', 0)} tiles for level: {level}",
                        "info"
                    )

                except Exception as e:
                    await job_service.add_log(job_id, f"Failed to generate tiles for {level}: {e}", "error")
                    # Continue with other assets instead of failing completely

        await job_service.update_progress(job_id, 75, "Generating build manifest...")

        # Build release manifest (same format as publish, but for preview)
        # Use the project-level tiles metadata if available
        primary_tiles = all_tiles_metadata.get("project", list(all_tiles_metadata.values())[0] if all_tiles_metadata else None)

        manifest = await release_service.build_manifest(
            project_slug=project_slug,
            version_number=version_number,
            release_id=build_id,
            user_email=user_email,
            tiles_metadata=primary_tiles,
        )

        if not manifest:
            await job_service.fail_job(job_id, "Failed to build manifest")
            return {"error": "Failed to build manifest"}

        await job_service.update_progress(job_id, 85, "Uploading manifest...")

        # Upload manifest
        manifest_json = manifest.model_dump_json(indent=2)
        manifest_key = f"{build_path}/release.json"

        await storage_service.storage.upload_file(
            key=manifest_key,
            body=manifest_json.encode(),
            content_type="application/json",
        )

        # Get preview URL
        preview_url = storage_service.storage.get_public_url(manifest_key)

        await job_service.add_log(job_id, f"Preview URL: {preview_url}", "info")
        await job_service.update_progress(job_id, 95, "Finalizing...")

        # Build result
        job_result = {
            "build_id": build_id,
            "build_path": build_path,
            "preview_url": preview_url,
            "overlay_count": len(manifest.overlays),
            "checksum": manifest.checksum,
            "tiles": {
                "levels": list(all_tiles_metadata.keys()),
                "total_count": total_tile_count,
                "metadata": all_tiles_metadata,
            },
            "built_at": datetime.utcnow().isoformat(),
        }

        await job_service.complete_job(job_id, job_result)
        return job_result

    except Exception as e:
        await job_service.fail_job(job_id, str(e))
        raise


async def _generate_tiles_for_asset(
    job_service: JobService,
    job_id: UUID,
    asset: Asset,
    build_path: str,
    level: str,
    progress_base: int,
    progress_range: int,
) -> Dict[str, Any]:
    """
    Generate tiles for a single base_map asset.

    Args:
        job_service: Job service for progress updates
        job_id: Job ID
        asset: Base map asset
        build_path: Base path for this build
        level: Level name (project, zone-a, etc.)
        progress_base: Starting progress percentage
        progress_range: Progress range for this asset

    Returns:
        Tile metadata dict
    """
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # Download source image
        source_path = temp_path / f"source_{level}.png"
        await _download_from_storage(asset.storage_path, source_path)

        # Generate tiles
        tiles_dir = temp_path / "tiles"

        result = tile_service.generate_tiles(
            source_path=str(source_path),
            output_dir=str(tiles_dir),
        )

        # Upload tiles to build folder
        tiles_key_prefix = f"{build_path}/tiles/{level}/"
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
            if tile_count % 50 == 0:
                progress = progress_base + int((tile_count / result["tile_count"]) * progress_range * 0.8)
                await job_service.update_progress(
                    job_id,
                    min(progress_base + progress_range, progress),
                    f"Uploading tiles for {level}... ({tile_count}/{result['tile_count']})"
                )

        return {
            "tiles_path": tiles_key_prefix,
            "width": result["width"],
            "height": result["height"],
            "levels": result["levels"],
            "tile_count": tile_count,
            "tile_size": result["tile_size"],
            "format": result["format"],
            "level": level,
        }


async def _download_from_storage(key: str, local_path: Path) -> None:
    """Download file from storage to local path."""
    url = await storage_service.storage.get_presigned_download_url(key)

    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        response.raise_for_status()
        local_path.write_bytes(response.content)
