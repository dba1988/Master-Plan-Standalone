"""
Publish Job

Background job that creates an immutable release from a draft version.
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.job_service import JobService
from app.services.release_service import ReleaseService, generate_release_id
from app.services.storage_service import storage_service


async def run_publish_job(
    db: AsyncSession,
    job_id: UUID,
    project_slug: str,
    version_number: int,
    user_email: str,
    user_id: UUID,
    tiles_metadata: Optional[Dict[str, Any]] = None,
) -> dict:
    """
    Background job to publish a version as an immutable release.

    Steps:
    1. Validate version is ready for publish
    2. Generate release ID
    3. Copy tiles from staging to release folder
    4. Generate release.json manifest
    5. Upload release.json
    6. Update database records
    7. Return release_id

    Args:
        db: Database session
        job_id: Job ID for progress tracking
        project_slug: Project slug
        version_number: Version number to publish
        user_email: Publishing user's email
        user_id: Publishing user's ID
        tiles_metadata: Optional tile generation result

    Returns:
        dict with release_id and release_url
    """
    job_service = JobService(db)
    release_service = ReleaseService(db)

    try:
        # Start job
        await job_service.start_job(job_id)
        await job_service.update_progress(job_id, 5, "Validating version...")

        # Validate
        is_valid, errors, warnings = await release_service.validate_for_publish(
            project_slug, version_number
        )

        if not is_valid:
            await job_service.fail_job(job_id, f"Validation failed: {', '.join(errors)}")
            return {"error": errors}

        # Log warnings
        for warning in warnings:
            await job_service.add_log(job_id, f"Warning: {warning}", "warn")

        await job_service.update_progress(job_id, 10, "Generating release ID...")

        # Generate release ID
        release_id = generate_release_id()
        release_path = f"mp/{project_slug}/releases/{release_id}"

        await job_service.add_log(job_id, f"Release ID: {release_id}", "info")

        # Copy tiles from staging to release folder
        staging_tiles_prefix = f"mp/{project_slug}/uploads/tiles/"
        release_tiles_prefix = f"{release_path}/tiles/"

        await job_service.update_progress(job_id, 20, "Copying tiles to release folder...")

        try:
            staging_tiles = await storage_service.storage.list_files(staging_tiles_prefix)
            total_tiles = len(staging_tiles)

            if total_tiles > 0:
                copied = 0
                for tile_key in staging_tiles:
                    # Calculate relative path and destination
                    relative_path = tile_key.replace(staging_tiles_prefix, "")
                    dest_key = f"{release_tiles_prefix}{relative_path}"

                    await storage_service.storage.copy_file(tile_key, dest_key)
                    copied += 1

                    # Update progress every 100 tiles
                    if copied % 100 == 0 or copied == total_tiles:
                        progress = 20 + int((copied / total_tiles) * 40)
                        await job_service.update_progress(
                            job_id,
                            min(60, progress),
                            f"Copying tiles... ({copied}/{total_tiles})"
                        )

                await job_service.add_log(job_id, f"Copied {copied} tiles", "info")
            else:
                await job_service.add_log(job_id, "No tiles to copy", "warn")

        except Exception as e:
            await job_service.add_log(job_id, f"Tile copy warning: {e}", "warn")

        await job_service.update_progress(job_id, 60, "Generating release manifest...")

        # Build release manifest
        manifest = await release_service.build_manifest(
            project_slug=project_slug,
            version_number=version_number,
            release_id=release_id,
            user_email=user_email,
            tiles_metadata=tiles_metadata,
        )

        if not manifest:
            await job_service.fail_job(job_id, "Failed to build release manifest")
            return {"error": "Failed to build manifest"}

        await job_service.update_progress(job_id, 80, "Uploading release manifest...")

        # Upload release.json
        manifest_json = manifest.model_dump_json(indent=2)
        manifest_key = f"{release_path}/release.json"

        await storage_service.storage.upload_file(
            key=manifest_key,
            body=manifest_json.encode(),
            content_type="application/json",
        )

        # Get release URL
        release_url = storage_service.storage.get_public_url(manifest_key)

        await job_service.add_log(job_id, f"Release URL: {release_url}", "info")
        await job_service.update_progress(job_id, 90, "Updating database...")

        # Get version for update
        result = await release_service.get_version(project_slug, version_number)
        if result:
            project, version = result

            # Update version record
            await release_service.mark_version_published(
                version_id=version.id,
                release_id=release_id,
                release_url=release_url,
                user_id=user_id,
            )

            # Update project current release
            await release_service.update_project_current_release(
                project_id=project.id,
                release_id=release_id,
            )

        await job_service.update_progress(job_id, 95, "Finalizing...")

        # Build result
        job_result = {
            "release_id": release_id,
            "release_url": release_url,
            "overlay_count": len(manifest.overlays),
            "checksum": manifest.checksum,
            "published_at": datetime.utcnow().isoformat(),
        }

        await job_service.complete_job(job_id, job_result)
        return job_result

    except Exception as e:
        await job_service.fail_job(job_id, str(e))
        raise
