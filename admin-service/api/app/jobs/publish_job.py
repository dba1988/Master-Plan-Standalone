"""
Publish Job

Background job that creates an immutable release from a build.
"""
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# Workers for parallel copy operations (using threads for true parallelism)
COPY_WORKERS = 20

from app.models.job import Job
from app.schemas.release import ZoneManifestInfo
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

        # Find the build job (either specified or latest)
        build_path = None
        tiles_metadata = None
        build_job = None

        if build_id:
            # Find the specified build job
            build_job_result = await db.execute(
                select(Job).where(
                    Job.project_id == project.id,
                    Job.job_type == "build",
                    Job.status == "completed",
                ).order_by(Job.completed_at.desc())
            )
            # Find the one matching the build_id
            for job in build_job_result.scalars().all():
                if job.result and job.result.get("build_id") == build_id:
                    build_job = job
                    break

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
                await job_service.add_log(job_id, f"Using latest build: {build_id}", "info")
            else:
                await job_service.add_log(job_id, "No build found, will check staging area", "warn")

        # Extract tiles metadata from build job
        if build_job and build_job.result:
            tiles_info = build_job.result.get("tiles", {})
            tiles_metadata = tiles_info.get("metadata", {}).get("project")

        await job_service.update_progress(job_id, 10, "Generating release ID...")

        # Generate release ID
        release_id = generate_release_id()
        release_path = f"mp/{project_slug}/releases/{release_id}"

        await job_service.add_log(job_id, f"Release ID: {release_id}", "info")

        # Copy tiles from build or staging to release folder
        await job_service.update_progress(job_id, 20, "Copying tiles to release folder...")

        total_copied = 0
        try:
            # Helper for parallel copy with progress tracking using threads
            def copy_tiles_parallel_threaded(tiles_list, src_prefix, dest_prefix, source_name):
                if not tiles_list:
                    return 0

                total_tiles = len(tiles_list)
                copied_count = 0
                copy_lock = threading.Lock()

                def copy_one(tile_key):
                    """Copy a single tile (runs in thread)."""
                    nonlocal copied_count
                    relative_path = tile_key.replace(src_prefix, "")
                    dest_key = f"{dest_prefix}{relative_path}"

                    # Synchronous copy in thread - true parallelism
                    storage_service.storage.client.copy_object(
                        Bucket=storage_service.storage.bucket,
                        CopySource={
                            'Bucket': storage_service.storage.bucket,
                            'Key': tile_key
                        },
                        Key=dest_key,
                    )

                    with copy_lock:
                        copied_count += 1
                    return True

                # Use ThreadPoolExecutor for true parallelism
                with ThreadPoolExecutor(max_workers=COPY_WORKERS) as executor:
                    futures = {executor.submit(copy_one, tk): tk for tk in tiles_list}

                    for future in as_completed(futures):
                        try:
                            future.result()
                        except Exception as e:
                            tile_key = futures[future]
                            # Log error but continue with other tiles
                            print(f"Failed to copy {tile_key}: {e}")

                return copied_count

            # Try to copy from build folder first
            if build_path:
                build_tiles_prefix = f"{build_path}/tiles/"
                build_tiles = await storage_service.storage.list_files(build_tiles_prefix)

                if not build_tiles:
                    await job_service.add_log(job_id, "No tiles in build", "warn")
                else:
                    await job_service.add_log(job_id, f"Copying {len(build_tiles)} tiles from build...", "info")
                    total_copied = copy_tiles_parallel_threaded(
                        build_tiles, build_tiles_prefix, f"{release_path}/tiles/", "build"
                    )
                    await job_service.add_log(job_id, f"Copied {total_copied} tiles from build", "info")
            else:
                # Fallback to legacy staging area
                staging_tiles_prefix = f"mp/{project_slug}/uploads/tiles/"
                staging_tiles = await storage_service.storage.list_files(staging_tiles_prefix)

                if not staging_tiles:
                    await job_service.add_log(job_id, "No tiles in staging", "warn")
                else:
                    await job_service.add_log(job_id, f"Copying {len(staging_tiles)} tiles from staging...", "info")
                    total_copied = copy_tiles_parallel_threaded(
                        staging_tiles, staging_tiles_prefix, f"{release_path}/tiles/", "staging"
                    )
                    await job_service.add_log(job_id, f"Copied {total_copied} tiles from staging", "info")

        except Exception as e:
            await job_service.add_log(job_id, f"Tile copy warning: {e}", "warn")

        await job_service.update_progress(job_id, 60, "Generating release manifests...")

        # Get all tile metadata from build (keyed by level)
        all_tiles_metadata = {}
        if build_job and build_job.result:
            all_tiles_metadata = build_job.result.get("tiles", {}).get("metadata", {})

        # Build project-level manifest (zones only)
        project_tiles_metadata = all_tiles_metadata.get("project", tiles_metadata)
        manifest = await release_service.build_manifest(
            project_slug=project_slug,
            version_number=version_number,
            release_id=release_id,
            user_email=user_email,
            tiles_metadata=project_tiles_metadata,
            level="project",
        )

        if not manifest:
            await job_service.fail_job(job_id, "Failed to build release manifest")
            return {"error": "Failed to build manifest"}

        await job_service.update_progress(job_id, 70, "Uploading project manifest...")

        # Upload main release.json (project level)
        manifest_json = manifest.model_dump_json(indent=2)
        manifest_key = f"{release_path}/release.json"

        await storage_service.storage.upload_file(
            key=manifest_key,
            body=manifest_json.encode(),
            content_type="application/json",
        )

        await job_service.add_log(job_id, f"Uploaded project manifest with {len(manifest.overlays)} zones", "info")

        # Get zone levels that have content
        zone_levels = await release_service.get_zone_levels(project_slug)
        zone_manifests_uploaded = 0

        # Build zone manifests and collect zone info for project manifest
        zone_info_list: list[ZoneManifestInfo] = []

        if zone_levels:
            await job_service.update_progress(job_id, 75, f"Generating {len(zone_levels)} zone manifests...")
            await job_service.add_log(job_id, f"Found {len(zone_levels)} zones with content: {zone_levels}", "info")

            for zone_level in zone_levels:
                # Get tiles metadata for this zone
                zone_tiles_metadata = all_tiles_metadata.get(zone_level)

                zone_manifest = await release_service.build_manifest(
                    project_slug=project_slug,
                    version_number=version_number,
                    release_id=release_id,
                    user_email=user_email,
                    tiles_metadata=zone_tiles_metadata,
                    level=zone_level,
                )

                if zone_manifest and zone_manifest.overlays:
                    # Upload zone manifest to /zones/{zone-level}.json
                    zone_manifest_json = zone_manifest.model_dump_json(indent=2)
                    zone_manifest_key = f"{release_path}/zones/{zone_level}.json"

                    await storage_service.storage.upload_file(
                        key=zone_manifest_key,
                        body=zone_manifest_json.encode(),
                        content_type="application/json",
                    )

                    # Find the zone overlay that corresponds to this level
                    # Zone level "zone-a" corresponds to zone with ref pattern
                    zone_overlay = None
                    for overlay in manifest.overlays:
                        if overlay.overlay_type == "zone":
                            # Check if this zone's layer matches the level
                            # or if level contains the zone ref (zone-a contains "a")
                            if overlay.layer == zone_level or zone_level.endswith(f"-{overlay.ref}") or zone_level == overlay.ref:
                                zone_overlay = overlay
                                break

                    zone_info_list.append(ZoneManifestInfo(
                        zone_ref=zone_overlay.ref if zone_overlay else zone_level,
                        level=zone_level,
                        manifest_path=f"zones/{zone_level}.json",
                        label=zone_overlay.label if zone_overlay else None,
                    ))

                    zone_manifests_uploaded += 1
                    await job_service.add_log(
                        job_id,
                        f"Uploaded {zone_level} manifest with {len(zone_manifest.overlays)} overlays",
                        "info"
                    )

        # Add zone info to project manifest and re-upload
        if zone_info_list:
            manifest.zones = zone_info_list
            manifest_json = manifest.model_dump_json(indent=2)
            await storage_service.storage.upload_file(
                key=manifest_key,
                body=manifest_json.encode(),
                content_type="application/json",
            )
            await job_service.add_log(job_id, f"Updated project manifest with {len(zone_info_list)} zone references", "info")

        await job_service.update_progress(job_id, 85, "Finalizing manifests...")

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
            "zone_count": len(manifest.overlays),  # Project manifest contains zones
            "zone_levels": zone_levels,
            "zone_manifests_uploaded": zone_manifests_uploaded,
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
