"""
Integration Service

Handles client API integration configuration with encrypted credentials.
"""
import time
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.crypto import decrypt_credentials, encrypt_credentials, has_credentials
from app.models.integration import IntegrationConfig
from app.models.project import Project
from app.schemas.integration import (
    DEFAULT_STATUS_MAPPING,
    IntegrationConfigUpdate,
)


class IntegrationService:
    """Service for managing client API integrations."""

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

    async def get_config(self, project_slug: str) -> Optional[IntegrationConfig]:
        """Get integration config for a project."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        result = await self.db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.project_id == project.id
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create_config(self, project_slug: str) -> Optional[IntegrationConfig]:
        """Get or create integration config for a project."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        result = await self.db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.project_id == project.id
            )
        )
        config = result.scalar_one_or_none()

        if config:
            return config

        # Create default config
        config = IntegrationConfig(
            project_id=project.id,
            auth_type="none",
            status_mapping=DEFAULT_STATUS_MAPPING,
            update_method="polling",
            polling_interval_seconds=30,
            timeout_seconds=10,
            retry_count=3,
        )

        self.db.add(config)
        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def update_config(
        self,
        project_slug: str,
        data: IntegrationConfigUpdate,
    ) -> Optional[IntegrationConfig]:
        """Update integration configuration."""
        config = await self.get_or_create_config(project_slug)
        if not config:
            return None

        update_data = data.model_dump(exclude_unset=True)

        # Handle credentials encryption
        if 'auth_credentials' in update_data:
            creds = update_data.pop('auth_credentials')
            if creds:
                config.auth_credentials = encrypt_credentials(creds)
            else:
                config.auth_credentials = None

        # Handle auth_type enum
        if 'auth_type' in update_data and update_data['auth_type']:
            update_data['auth_type'] = update_data['auth_type'].value

        # Handle update_method enum
        if 'update_method' in update_data and update_data['update_method']:
            update_data['update_method'] = update_data['update_method'].value

        # Update other fields
        for field, value in update_data.items():
            if value is not None:
                setattr(config, field, value)

        await self.db.commit()
        await self.db.refresh(config)

        return config

    async def delete_credentials(self, project_slug: str) -> bool:
        """Delete stored credentials."""
        config = await self.get_config(project_slug)
        if not config:
            return False

        config.auth_credentials = None
        await self.db.commit()

        return True

    async def test_connection(
        self,
        project_slug: str,
        override_url: Optional[str] = None,
        override_endpoint: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Test connection to the client API.

        Returns success status, response time, and sample data.
        """
        config = await self.get_config(project_slug)
        if not config:
            return {"success": False, "error": "Integration config not found"}

        # Use overrides or stored values
        base_url = override_url or config.api_base_url
        endpoint = override_endpoint or config.status_endpoint

        if not base_url:
            return {"success": False, "error": "No API base URL configured"}

        if not endpoint:
            return {"success": False, "error": "No status endpoint configured"}

        # Build full URL
        url = f"{base_url.rstrip('/')}{endpoint}"

        # Build headers
        headers = await self._build_auth_headers(config)

        # Make request
        start_time = time.time()
        try:
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.get(url, headers=headers)

            response_time_ms = int((time.time() - start_time) * 1000)

            if response.status_code == 200:
                try:
                    data = response.json()
                    # Extract sample (first 5 items if list)
                    sample = data[:5] if isinstance(data, list) else [data]
                except Exception:
                    sample = None

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "response_time_ms": response_time_ms,
                    "sample_data": sample,
                }
            else:
                return {
                    "success": False,
                    "status_code": response.status_code,
                    "response_time_ms": response_time_ms,
                    "error": f"HTTP {response.status_code}: {response.text[:200]}",
                }

        except httpx.TimeoutException:
            return {"success": False, "error": "Connection timeout"}
        except httpx.ConnectError as e:
            return {"success": False, "error": f"Connection error: {str(e)}"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _build_auth_headers(self, config: IntegrationConfig) -> Dict[str, str]:
        """Build authentication headers based on config."""
        headers = {}

        if config.auth_type == "none" or not config.auth_credentials:
            return headers

        creds = decrypt_credentials(config.auth_credentials)
        if not creds:
            return headers

        if config.auth_type == "bearer":
            token = creds.get("token")
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif config.auth_type == "api_key":
            api_key = creds.get("api_key")
            header_name = creds.get("api_key_header", "X-API-Key")
            if api_key:
                headers[header_name] = api_key

        elif config.auth_type == "basic":
            import base64
            username = creds.get("username", "")
            password = creds.get("password", "")
            credentials = base64.b64encode(f"{username}:{password}".encode()).decode()
            headers["Authorization"] = f"Basic {credentials}"

        return headers

    def map_status(self, config: IntegrationConfig, client_status: str) -> Tuple[str, bool]:
        """
        Map a client status to canonical 5-status taxonomy.

        Returns (canonical_status, matched) where matched indicates
        if the status was found in the mapping.
        """
        mapping = config.status_mapping or DEFAULT_STATUS_MAPPING

        for canonical, client_values in mapping.items():
            if client_status in client_values:
                return canonical, True

        # Default to hidden if not found
        return "hidden", False

    def config_has_credentials(self, config: IntegrationConfig) -> bool:
        """Check if config has valid credentials."""
        return has_credentials(config.auth_credentials)
