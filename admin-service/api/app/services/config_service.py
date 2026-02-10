"""
Config Service

Handles project configuration management.

Config belongs to projects (not versions) - versions are just release tags.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.config import ProjectConfig
from app.models.project import Project
from app.models.version import ProjectVersion
from app.schemas.config import (
    DEFAULT_INTERACTION_COLORS,
    DEFAULT_MAP_SETTINGS,
    DEFAULT_STATUS_COLORS,
    DEFAULT_THEME,
    ProjectConfigUpdate,
)


class ConfigService:
    """Service for managing project configurations."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_by_slug(self, project_slug: str) -> Optional[Project]:
        """Get project by slug."""
        result = await self.db.execute(
            select(Project).where(
                Project.slug == project_slug,
                Project.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def has_draft_version(self, project_id: UUID) -> bool:
        """Check if project has a draft version (allows modifications)."""
        result = await self.db.execute(
            select(ProjectVersion).where(
                ProjectVersion.project_id == project_id,
                ProjectVersion.status == "draft"
            )
        )
        return result.scalar_one_or_none() is not None

    async def get_config(self, project_slug: str) -> Optional[ProjectConfig]:
        """Get config for a project."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        config_result = await self.db.execute(
            select(ProjectConfig).where(ProjectConfig.project_id == project.id)
        )
        return config_result.scalar_one_or_none()

    async def get_or_create_config(self, project_slug: str) -> Optional[ProjectConfig]:
        """
        Get config for a project, creating with defaults if it doesn't exist.

        Returns None if project not found.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        # Check if config exists
        config_result = await self.db.execute(
            select(ProjectConfig).where(ProjectConfig.project_id == project.id)
        )
        config = config_result.scalar_one_or_none()

        if config:
            return config

        # Create default config
        config = ProjectConfig(
            project_id=project.id,
            theme=DEFAULT_THEME.copy(),
            map_settings=DEFAULT_MAP_SETTINGS.copy(),
            status_colors=DEFAULT_STATUS_COLORS.copy(),
            popup_config={
                "enabled": True,
                "showPrice": True,
                "showArea": True,
                "showStatus": True,
                "fields": []
            },
            filter_config={
                "enableStatusFilter": True,
                "enableTypeFilter": False,
                "enableLayerFilter": False,
                "defaultStatuses": ["available", "reserved", "sold", "unreleased"]
            }
        )

        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def update_config(
        self,
        project_slug: str,
        data: ProjectConfigUpdate,
    ) -> Optional[ProjectConfig]:
        """
        Update config for a project.

        Returns None if project not found or no draft version exists.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        # Only allow modifications if there's a draft version
        if not await self.has_draft_version(project.id):
            return None

        # Get or create config
        config = await self.get_or_create_config(project_slug)
        if not config:
            return None

        # Update fields - merge JSONB fields
        update_data = data.model_dump(exclude_unset=True)

        for field, value in update_data.items():
            if value is not None:
                current_value = getattr(config, field)
                if isinstance(current_value, dict) and isinstance(value, dict):
                    # Merge dictionaries
                    merged = {**current_value, **value}
                    setattr(config, field, merged)
                else:
                    setattr(config, field, value)

        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def reset_config(self, project_slug: str) -> Optional[ProjectConfig]:
        """
        Reset config to defaults.

        Returns None if project not found or no draft version exists.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        # Only allow modifications if there's a draft version
        if not await self.has_draft_version(project.id):
            return None

        # Get config
        config_result = await self.db.execute(
            select(ProjectConfig).where(ProjectConfig.project_id == project.id)
        )
        config = config_result.scalar_one_or_none()

        if not config:
            # Create with defaults
            return await self.get_or_create_config(project_slug)

        # Reset to defaults
        config.theme = DEFAULT_THEME.copy()
        config.map_settings = DEFAULT_MAP_SETTINGS.copy()
        config.status_colors = DEFAULT_STATUS_COLORS.copy()
        config.popup_config = {
            "enabled": True,
            "showPrice": True,
            "showArea": True,
            "showStatus": True,
            "fields": []
        }
        config.filter_config = {
            "enableStatusFilter": True,
            "enableTypeFilter": False,
            "enableLayerFilter": False,
            "defaultStatuses": ["available", "reserved", "sold", "unreleased"]
        }

        await self.db.commit()
        await self.db.refresh(config)

        return config

    def get_config_with_defaults(self, config: ProjectConfig) -> Dict[str, Any]:
        """
        Get config with all defaults applied for missing fields.

        Returns a complete config object with no missing values.
        """
        # Merge with defaults
        theme = {**DEFAULT_THEME, **(config.theme or {})}
        map_settings = {**DEFAULT_MAP_SETTINGS, **(config.map_settings or {})}
        status_colors = {**DEFAULT_STATUS_COLORS, **(config.status_colors or {})}

        return {
            "id": str(config.id),
            "project_id": str(config.project_id),
            "theme": theme,
            "map_settings": map_settings,
            "status_colors": status_colors,
            "interaction_colors": DEFAULT_INTERACTION_COLORS,
            "popup_config": config.popup_config or {},
            "filter_config": config.filter_config or {},
            "created_at": config.created_at,
            "updated_at": config.updated_at,
        }
