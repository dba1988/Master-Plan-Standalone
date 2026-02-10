"""
Project Config endpoints.

Manages per-version configuration:
- Theme settings
- Map settings (zoom, viewBox)
- Status colors (5-status taxonomy)
- Popup/tooltip config
- Filter config
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
    "/projects/{slug}/versions/{version_number}/config",
    response_model=ProjectConfigResponse,
)
async def get_config(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get configuration for a project version.

    Creates default config if it doesn't exist.
    """
    service = ConfigService(db)
    config = await service.get_or_create_config(
        project_slug=slug,
        version_number=version_number,
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or version not found"
        )

    return ProjectConfigResponse.model_validate(config)


@router.get(
    "/projects/{slug}/versions/{version_number}/config/full",
    response_model=ProjectConfigWithDefaultsResponse,
)
async def get_config_with_defaults(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get configuration with all defaults applied.

    Returns a complete config object with no missing values.
    Useful for the viewer which needs all config values.
    """
    service = ConfigService(db)
    config = await service.get_or_create_config(
        project_slug=slug,
        version_number=version_number,
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or version not found"
        )

    full_config = service.get_config_with_defaults(config)
    return ProjectConfigWithDefaultsResponse(**full_config)


@router.put(
    "/projects/{slug}/versions/{version_number}/config",
    response_model=ProjectConfigResponse,
)
async def update_config(
    slug: str,
    version_number: int,
    data: ProjectConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Update configuration for a project version.

    Only works for draft versions.
    Fields are merged with existing values (partial update).
    """
    service = ConfigService(db)
    config = await service.update_config(
        project_slug=slug,
        version_number=version_number,
        data=data,
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project/version not found or version is not a draft"
        )

    return ProjectConfigResponse.model_validate(config)


@router.post(
    "/projects/{slug}/versions/{version_number}/config/reset",
    response_model=ProjectConfigResponse,
)
async def reset_config(
    slug: str,
    version_number: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Reset configuration to defaults.

    Only works for draft versions.
    """
    service = ConfigService(db)
    config = await service.reset_config(
        project_slug=slug,
        version_number=version_number,
    )

    if not config:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Project/version not found or version is not a draft"
        )

    return ProjectConfigResponse.model_validate(config)
