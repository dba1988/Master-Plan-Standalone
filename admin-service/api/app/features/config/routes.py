"""
Project Config endpoints.

Manages per-project configuration:
- Theme settings
- Map settings (zoom, viewBox)
- Status colors (5-status taxonomy)
- Popup/tooltip config
- Filter config

Config belongs to projects (not versions) - versions are just release tags.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.user import User
from app.schemas.config import (
    ProjectConfigResponse,
    ProjectConfigUpdate,
    ProjectConfigWithDefaultsResponse,
)
from app.services.config_service import ConfigService

router = APIRouter(tags=["Project Config"])


@router.get(
    "/projects/{slug}/config",
    response_model=ProjectConfigResponse,
)
async def get_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get configuration for a project.

    Creates default config if it doesn't exist.
    """
    service = ConfigService(db)
    config = await service.get_or_create_config(project_slug=slug)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return ProjectConfigResponse.model_validate(config)


@router.get(
    "/projects/{slug}/config/full",
    response_model=ProjectConfigWithDefaultsResponse,
)
async def get_config_with_defaults(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get configuration with all defaults applied.

    Returns a complete config object with no missing values.
    Useful for the viewer which needs all config values.
    """
    service = ConfigService(db)
    config = await service.get_or_create_config(project_slug=slug)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    full_config = service.get_config_with_defaults(config)
    return ProjectConfigWithDefaultsResponse(**full_config)


@router.put(
    "/projects/{slug}/config",
    response_model=ProjectConfigResponse,
)
async def update_config(
    slug: str,
    data: ProjectConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Update configuration for a project.

    Only works if project has a draft version.
    Fields are merged with existing values (partial update).
    """
    service = ConfigService(db)
    config = await service.update_config(
        project_slug=slug,
        data=data,
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not found or no draft version exists"
        )

    return ProjectConfigResponse.model_validate(config)


@router.post(
    "/projects/{slug}/config/reset",
    response_model=ProjectConfigResponse,
)
async def reset_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Reset configuration to defaults.

    Only works if project has a draft version.
    """
    service = ConfigService(db)
    config = await service.reset_config(project_slug=slug)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project not found or no draft version exists"
        )

    return ProjectConfigResponse.model_validate(config)
