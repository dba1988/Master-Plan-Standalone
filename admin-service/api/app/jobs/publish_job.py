"""
Publish Job

Background job that creates an immutable release from a build.
"""
import json
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.job import Job
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
    build_id: Optional[str] = None,
) -> dict:
    """
    Background job to publish a version as an immutable release.

    Steps:
    1. Validate version is ready for publish
    2. Find the latest build (or use specified build_id)
    3. Generate release ID
    4. Copy tiles from build folder to release folder
    5. Generate release.json manifest
    6. Upload release.json
    7. Update database records
    8. Return release_id

    Args:
        db: Database session
        job_id: Job ID for progress tracking
        project_slug: Project slug
        version_number: Version number to publish
        user_email: Publishing user's email
        user_id: Publishing user's ID
        build_id: Optional specific build ID to publish (uses latest if not provided)

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

        await job_service.update_progress(job_id, 8, "Finding build artifacts...")

        # Get project and version for looking up builds
        result = await release_service.get_version(project_slug, version_number)
        if not result:
            await job_service.fail_job(job_id, "Project or version not found")
            return {"error": "Project or version not found"}

        project, version = result

        # Find the latest successful build job if no specific build_id provided
        build_path = None
        tiles_metadata = None

        if build_id:
            build_path = f"mp/{project_slug}/builds/{build_id}"
            await job_service.add_log(job_id, f"Using specified build: {build_id}", "info")
        else:
            # Find latest completed build job for this version
            build_job_result = await db.execute(
                select(Job).where(
                    Job.project_id == project.id,
                    Job.version_id == version.id,
                    Job.job_type == "build",
                    Job.status == "completed"
                ).order_by(Job.completed_at.desc()).limit(1)
            )
            build_job = build_job_result.scalar_one_or_none()

            if build_job and build_job.result:
                build_id = build_job.result.get("build_id")
                build_path = build_job.result.get("build_path")
                tiles_info = build_job.result.get("tiles", {})
                # Get metadata for the primary (project) level
                tiles_metadata = tiles_info.get("metadata", {}).get("project")
                await job_service.add_log(job_id, f"Using latest build: {build_id}", "info")
            else:
                await job_service.add_log(job_id, "No build found, will check staging area", "warn")

        await job_service.update_progress(job_id, 10, "Generating release ID...")

        # Generate release ID
        release_id = generate_release_id()
        release_path = f"mp/{project_slug}/releases/{release_id}"

        await job_service.add_log(job_id, f"Release ID: {release_id}", "info")

        # Copy tiles from build or staging to release folder
        await job_service.update_progress(job_id, 20, "Copying tiles to release folder...")

        total_copied = 0
        try:
            # Try to copy from build folder first
            if build_path:
                build_tiles_prefix = f"{build_path}/tiles/"
                build_tiles = await storage_service.storage.list_files(build_tiles_prefix)

                if build_tiles:
                    total_tiles = len(build_tiles)
                    for tile_key in build_tiles:
                        relative_path = tile_key.replace(build_tiles_prefix, "")
                        dest_key = f"{release_path}/tiles/{relative_path}"

                        await storage_service.storage.copy_file(tile_key, dest_key)
                        total_copied += 1

                        if total_copied % 100 == 0 or total_copied == total_tiles:
                            progress = 20 + int((total_copied / total_tiles) * 40)
                            await job_service.update_progress(
                                job_id,
                                min(60, progress),
                                f"Copying tiles... ({total_copied}/{total_tiles})"
                            )

                    await job_service.add_log(job_id, f"Copied {total_copied} tiles from build", "info")
                else:
                    await job_service.add_log(job_id, "No tiles in build folder", "warn")
            else:
                # Fallback to legacy staging area
                staging_tiles_prefix = f"mp/{project_slug}/uploads/tiles/"
                staging_tiles = await storage_service.storage.list_files(staging_tiles_prefix)

                if staging_tiles:
                    total_tiles = len(staging_tiles)
                    for tile_key in staging_tiles:
                        relative_path = tile_key.replace(staging_tiles_prefix, "")
                        dest_key = f"{release_path}/tiles/{relative_path}"

                        await storage_service.storage.copy_file(tile_key, dest_key)
                        total_copied += 1

                        if total_copied % 100 == 0 or total_copied == total_tiles:
                            progress = 20 + int((total_copied / total_tiles) * 40)
                            await job_service.update_progress(
                                job_id,
                                min(60, progress),
                                f"Copying tiles... ({total_copied}/{total_tiles})"
                            )

                    await job_service.add_log(job_id, f"Copied {total_copied} tiles from staging", "info")
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
            "build_id": build_id,
            "tiles_copied": total_copied,
            "published_at": datetime.utcnow().isoformat(),
        }

        await job_service.complete_job(job_id, job_result)
        return job_result

    except Exception as e:
        await job_service.fail_job(job_id, str(e))
        raise
