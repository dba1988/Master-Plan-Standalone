"""
Release Service

Handles release ID generation, manifest building, and publish operations.
"""
import hashlib
import json
import secrets
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import ProjectConfig
from app.models.overlay import Overlay
from app.models.project import Project
from app.models.version import ProjectVersion
from app.schemas.config import DEFAULT_INTERACTION_COLORS, DEFAULT_STATUS_COLORS
from app.schemas.release import (
    ReleaseConfig,
    ReleaseManifest,
    ReleaseOverlay,
    TileConfig,
    ZoomConfig,
)


def generate_release_id() -> str:
    """
    Generate a unique, sortable release ID.

    Format: rel_{YYYYMMDDHHMMSS}_{random_hex}
    Example: rel_20240115100000_a1b2c3d4
    """
    timestamp = time.strftime("%Y%m%d%H%M%S")
    random_suffix = secrets.token_hex(4)
    return f"rel_{timestamp}_{random_suffix}"


class ReleaseService:
    """Service for managing releases and publish workflow."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_by_slug(self, slug: str) -> Optional[Project]:
        """Get project by slug."""
        result = await self.db.execute(
            select(Project).where(
                Project.slug == slug,
                Project.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def get_version(
        self,
        project_slug: str,
        version_number: int,
    ) -> Optional[Tuple[Project, ProjectVersion]]:
        """Get project and version."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        result = await self.db.execute(
            select(ProjectVersion).where(
                ProjectVersion.project_id == project.id,
                ProjectVersion.version_number == version_number
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            return None

        return project, version

    async def validate_for_publish(
        self,
        project_slug: str,
        version_number: int,
    ) -> Tuple[bool, List[str], List[str]]:
        """
        Validate version is ready for publish.

        Returns: (is_valid, errors, warnings)
        """
        errors = []
        warnings = []

        result = await self.get_version(project_slug, version_number)
        if not result:
            errors.append("Project or version not found")
            return False, errors, warnings

        project, version = result

        # Check status
        if version.status != "draft":
            errors.append("Only draft versions can be published")

        # Check config exists
        config_result = await self.db.execute(
            select(ProjectConfig).where(
                ProjectConfig.project_id == project.id
            )
        )
        config = config_result.scalar_one_or_none()
        if not config:
            warnings.append("No configuration defined, will use defaults")

        # Check overlays exist
        overlay_result = await self.db.execute(
            select(Overlay).where(
                Overlay.project_id == project.id
            ).limit(1)
        )
        has_overlays = overlay_result.scalar_one_or_none() is not None
        if not has_overlays:
            warnings.append("No overlays defined")

        # Check if there's a successful build for this version
        from app.models.job import Job
        build_job_result = await self.db.execute(
            select(Job).where(
                Job.project_id == project.id,
                Job.version_id == version.id,
                Job.job_type == "build",
                Job.status == "completed"
            ).limit(1)
        )
        has_build = build_job_result.scalar_one_or_none() is not None
        if not has_build:
            warnings.append("No build found - consider running build first to generate tiles")

        is_valid = len(errors) == 0
        return is_valid, errors, warnings

    async def build_manifest(
        self,
        project_slug: str,
        version_number: int,
        release_id: str,
        user_email: str,
        tiles_metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ReleaseManifest]:
        """
        Build the release.json manifest.

        Args:
            project_slug: Project slug
            version_number: Version number
            release_id: Generated release ID
            user_email: Publishing user's email
            tiles_metadata: Optional tile generation result

        Returns:
            ReleaseManifest or None if project/version not found
        """
        result = await self.get_version(project_slug, version_number)
        if not result:
            return None

        project, version = result

        # Get config
        config_result = await self.db.execute(
            select(ProjectConfig).where(
                ProjectConfig.project_id == project.id
            )
        )
        config = config_result.scalar_one_or_none()

        # Build config section - extract from JSONB fields
        map_settings = (config.map_settings or {}) if config else {}
        theme = (config.theme or {}) if config else {}
        zoom_settings = map_settings.get("zoom", {})

        release_config = ReleaseConfig(
            default_view_box=map_settings.get("defaultViewBox", "0 0 4096 4096"),
            default_zoom=ZoomConfig(
                min=zoom_settings.get("min", 0.5),
                max=zoom_settings.get("max", 4.0),
                default=zoom_settings.get("default", 1.0),
            ),
            default_locale=theme.get("defaultLocale", "en"),
            supported_locales=theme.get("supportedLocales", ["en"]),
            status_styles=config.status_colors if config else DEFAULT_STATUS_COLORS,
            interaction_styles=DEFAULT_INTERACTION_COLORS,
        )

        # Get overlays
        overlay_result = await self.db.execute(
            select(Overlay)
            .where(Overlay.project_id == project.id)
            .order_by(Overlay.sort_order, Overlay.ref)
        )
        overlays = list(overlay_result.scalars().all())

        release_overlays = [
            ReleaseOverlay(
                ref=o.ref,
                overlay_type=o.overlay_type,
                geometry=o.geometry,
                label=o.label,
                label_position=o.label_position,
                props=o.props or {},
                layer=o.layer,
                sort_order=o.sort_order or 0,
            )
            for o in overlays
        ]

        # Build tiles section if metadata provided
        tiles = None
        if tiles_metadata:
            tiles = TileConfig(
                base_url="tiles",
                format="dzi",
                tile_size=tiles_metadata.get("tile_size", 256),
                overlap=tiles_metadata.get("overlap", 1),
                levels=tiles_metadata.get("levels", 1),
                width=tiles_metadata.get("width", 4096),
                height=tiles_metadata.get("height", 4096),
            )

        # Calculate checksum of overlay data
        overlay_data = [o.model_dump() for o in release_overlays]
        checksum = self._calculate_checksum(overlay_data)

        return ReleaseManifest(
            version=3,
            release_id=release_id,
            project_slug=project_slug,
            published_at=datetime.utcnow(),
            published_by=user_email,
            config=release_config,
            tiles=tiles,
            overlays=release_overlays,
            checksum=checksum,
        )

    def _calculate_checksum(self, data: List[Dict]) -> str:
        """Calculate SHA256 checksum of data."""
        json_str = json.dumps(data, sort_keys=True, default=str)
        hash_obj = hashlib.sha256(json_str.encode())
        return f"sha256:{hash_obj.hexdigest()}"

    async def mark_version_published(
        self,
        version_id: UUID,
        release_id: str,
        release_url: str,
        user_id: UUID,
    ) -> None:
        """Update version record after successful publish."""
        result = await self.db.execute(
            select(ProjectVersion).where(ProjectVersion.id == version_id)
        )
        version = result.scalar_one_or_none()

        if version:
            version.status = "published"
            version.release_id = release_id
            version.release_url = release_url
            version.published_at = datetime.utcnow()
            version.published_by = user_id
            await self.db.commit()

    async def update_project_current_release(
        self,
        project_id: UUID,
        release_id: str,
    ) -> None:
        """Update project's current release pointer."""
        result = await self.db.execute(
            select(Project).where(Project.id == project_id)
        )
        project = result.scalar_one_or_none()

        if project:
            project.current_release_id = release_id
            await self.db.commit()


# Singleton for release ID generation
def get_release_id() -> str:
    """Get a new release ID."""
    return generate_release_id()
