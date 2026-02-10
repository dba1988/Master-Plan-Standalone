"""
Integration Config endpoints.

Manages client API integration:
- API connection settings
- Authentication (bearer, api_key, basic)
- Status mapping (5-status taxonomy)
- Connection testing
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.user import User
from app.schemas.integration import (
    ConnectionTestRequest,
    ConnectionTestResponse,
    IntegrationConfigResponse,
    IntegrationConfigUpdate,
    DEFAULT_STATUS_MAPPING,
)
from app.services.integration_service import IntegrationService

router = APIRouter(tags=["Integration"])


def _build_response(config, service: IntegrationService) -> IntegrationConfigResponse:
    """Build response with has_credentials flag."""
    return IntegrationConfigResponse(
        id=config.id,
        project_id=config.project_id,
        api_base_url=config.api_base_url,
        auth_type=config.auth_type,
        status_endpoint=config.status_endpoint,
        status_mapping=config.status_mapping or DEFAULT_STATUS_MAPPING,
        update_method=config.update_method,
        polling_interval_seconds=config.polling_interval_seconds,
        timeout_seconds=config.timeout_seconds,
        retry_count=config.retry_count,
        has_credentials=service.config_has_credentials(config),
        last_sync_at=config.last_sync_at,
        sync_status=config.sync_status,
        sync_error=config.sync_error,
        created_at=config.created_at,
        updated_at=config.updated_at,
    )


@router.get(
    "/projects/{slug}/integration",
    response_model=IntegrationConfigResponse,
)
async def get_integration_config(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get integration configuration for a project.

    Creates default config if it doesn't exist.
    Credentials are never exposed in the response.
    """
    service = IntegrationService(db)
    config = await service.get_or_create_config(slug)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return _build_response(config, service)


@router.put(
    "/projects/{slug}/integration",
    response_model=IntegrationConfigResponse,
)
async def update_integration_config(
    slug: str,
    data: IntegrationConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Update integration configuration.

    Credentials are encrypted before storage.
    Only admins and editors can update.
    """
    service = IntegrationService(db)
    config = await service.update_config(slug, data)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )

    return _build_response(config, service)


@router.delete(
    "/projects/{slug}/integration/credentials",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_credentials(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Delete stored credentials.

    Useful when rotating credentials or disabling integration.
    """
    service = IntegrationService(db)
    deleted = await service.delete_credentials(slug)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or integration config not found"
        )


@router.post(
    "/projects/{slug}/integration/test",
    response_model=ConnectionTestResponse,
)
async def test_connection(
    slug: str,
    data: ConnectionTestRequest = None,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Test connection to the client API.

    Uses stored config unless overrides are provided.
    Returns response time and sample data on success.
    """
    service = IntegrationService(db)

    override_url = data.api_base_url if data else None
    override_endpoint = data.status_endpoint if data else None

    result = await service.test_connection(
        project_slug=slug,
        override_url=override_url,
        override_endpoint=override_endpoint,
    )

    return ConnectionTestResponse(**result)


@router.post(
    "/projects/{slug}/integration/map-status",
)
async def map_status(
    slug: str,
    client_status: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Map a client status value to canonical 5-status taxonomy.

    Useful for testing status mapping configuration.
    """
    service = IntegrationService(db)
    config = await service.get_config(slug)

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or integration config not found"
        )

    canonical, matched = service.map_status(config, client_status)

    return {
        "original_status": client_status,
        "canonical_status": canonical,
        "matched": matched,
    }
