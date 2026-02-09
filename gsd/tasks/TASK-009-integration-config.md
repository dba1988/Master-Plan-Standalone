# TASK-009: Integration Config

**Phase**: 3 - Overlays + Config
**Status**: [ ] Not Started
**Priority**: P1 - High
**Depends On**: TASK-008, TASK-000 (parity harness for status mapping)

## Objective

Implement client API integration configuration with encrypted credentials.

## Description

Create endpoints for configuring integration with client APIs:
- API base URL and authentication
- Status endpoint mapping
- Update method (polling/SSE/webhook)
- Test connection endpoint

## Files to Create

```
admin-api/app/
├── core/
│   └── crypto.py
├── schemas/
│   └── integration.py
├── api/
│   └── integration.py
└── services/
    └── integration_service.py
```

## Implementation Steps

### Step 1: Crypto Utilities
```python
# app/core/crypto.py
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib

def get_fernet_key() -> bytes:
    """Derive Fernet key from secret"""
    key = hashlib.sha256(settings.secret_key.encode()).digest()
    return base64.urlsafe_b64encode(key)

def encrypt_value(value: str) -> str:
    """Encrypt a string value"""
    if not value:
        return value
    f = Fernet(get_fernet_key())
    return f.encrypt(value.encode()).decode()

def decrypt_value(encrypted: str) -> str:
    """Decrypt a string value"""
    if not encrypted:
        return encrypted
    f = Fernet(get_fernet_key())
    return f.decrypt(encrypted.encode()).decode()
```

### Step 2: Integration Schemas
```python
# app/schemas/integration.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, List
from uuid import UUID
from datetime import datetime
from enum import Enum

class AuthType(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    BASIC = "basic"

class UpdateMethod(str, Enum):
    POLLING = "polling"
    SSE = "sse"
    WEBHOOK = "webhook"

class AuthCredentials(BaseModel):
    """Auth credentials (sent to API, stored encrypted)"""
    token: Optional[str] = None  # For bearer
    api_key: Optional[str] = None  # For api_key
    api_key_header: Optional[str] = "X-API-Key"  # Header name for api_key
    username: Optional[str] = None  # For basic
    password: Optional[str] = None  # For basic

class StatusMapping(BaseModel):
    """Map client status values to canonical 7 statuses (per STATUS-TAXONOMY.md)"""
    available: List[str] = ["Available", "AVAILABLE", "available", "Open", "OPEN"]
    reserved: List[str] = ["Reserved", "RESERVED", "reserved"]
    hold: List[str] = ["Hold", "HOLD", "OnHold", "ON_HOLD", "on_hold", "Pending"]
    sold: List[str] = ["Sold", "SOLD", "sold", "Purchased", "PURCHASED"]
    unreleased: List[str] = ["Unreleased", "UNRELEASED", "unreleased", "Future"]
    unavailable: List[str] = ["Unavailable", "UNAVAILABLE", "unavailable", "NotForSale"]
    coming_soon: List[str] = ["ComingSoon", "COMING_SOON", "coming_soon", "Announced"]

class IntegrationConfigBase(BaseModel):
    api_base_url: Optional[str] = None
    auth_type: AuthType = AuthType.NONE
    status_endpoint: Optional[str] = None  # e.g., "/api/units/status"
    status_mapping: Optional[StatusMapping] = None
    update_method: UpdateMethod = UpdateMethod.POLLING
    polling_interval_seconds: int = Field(default=30, ge=5, le=300)
    timeout_seconds: int = Field(default=10, ge=1, le=60)
    retry_count: int = Field(default=3, ge=0, le=10)

class IntegrationConfigCreate(IntegrationConfigBase):
    auth_credentials: Optional[AuthCredentials] = None

class IntegrationConfigUpdate(IntegrationConfigBase):
    auth_credentials: Optional[AuthCredentials] = None

class IntegrationConfigResponse(IntegrationConfigBase):
    id: UUID
    project_id: UUID
    has_credentials: bool  # Don't expose actual credentials
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class TestConnectionRequest(BaseModel):
    pass  # Uses saved config

class TestConnectionResponse(BaseModel):
    success: bool
    status_code: Optional[int] = None
    response_time_ms: Optional[int] = None
    error: Optional[str] = None
    sample_data: Optional[Dict] = None
```

### Step 3: Integration Service
```python
# app/services/integration_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Optional
from uuid import UUID
import httpx
import time
from app.models.integration import IntegrationConfig
from app.schemas.integration import IntegrationConfigUpdate, AuthType
from app.core.crypto import encrypt_value, decrypt_value

class IntegrationService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_config(self, project_id: UUID) -> Optional[IntegrationConfig]:
        result = await self.db.execute(
            select(IntegrationConfig).where(
                IntegrationConfig.project_id == project_id
            )
        )
        return result.scalar_one_or_none()

    async def update_config(
        self,
        project_id: UUID,
        data: IntegrationConfigUpdate
    ) -> IntegrationConfig:
        config = await self.get_config(project_id)

        if not config:
            config = IntegrationConfig(project_id=project_id)
            self.db.add(config)

        # Update fields
        update_data = data.dict(exclude={'auth_credentials'}, exclude_unset=True)
        for key, value in update_data.items():
            if value is not None:
                setattr(config, key, value)

        # Handle credentials encryption
        if data.auth_credentials:
            encrypted_creds = {}
            creds = data.auth_credentials.dict(exclude_unset=True)
            for key, value in creds.items():
                if value:
                    encrypted_creds[key] = encrypt_value(value)
            config.auth_config = encrypted_creds

        await self.db.commit()
        await self.db.refresh(config)
        return config

    async def test_connection(self, project_id: UUID) -> dict:
        config = await self.get_config(project_id)

        if not config or not config.api_base_url:
            return {
                "success": False,
                "error": "Integration not configured"
            }

        url = config.api_base_url
        if config.status_endpoint:
            url = f"{config.api_base_url.rstrip('/')}/{config.status_endpoint.lstrip('/')}"

        headers = {}

        # Add auth headers
        if config.auth_type == AuthType.BEARER.value and config.auth_config:
            token = decrypt_value(config.auth_config.get("token", ""))
            if token:
                headers["Authorization"] = f"Bearer {token}"

        elif config.auth_type == AuthType.API_KEY.value and config.auth_config:
            api_key = decrypt_value(config.auth_config.get("api_key", ""))
            header_name = config.auth_config.get("api_key_header", "X-API-Key")
            if api_key:
                headers[header_name] = api_key

        try:
            start_time = time.time()
            async with httpx.AsyncClient(timeout=config.timeout_seconds) as client:
                response = await client.get(url, headers=headers)
            elapsed_ms = int((time.time() - start_time) * 1000)

            sample_data = None
            if response.status_code == 200:
                try:
                    sample_data = response.json()
                    if isinstance(sample_data, list) and len(sample_data) > 3:
                        sample_data = sample_data[:3]  # Limit sample
                except:
                    pass

            return {
                "success": response.status_code == 200,
                "status_code": response.status_code,
                "response_time_ms": elapsed_ms,
                "sample_data": sample_data
            }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": "Connection timeout"
            }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }

    def map_status(self, config: IntegrationConfig, client_status: str) -> str:
        """Map client status to standard status"""
        if not config.status_mapping:
            return client_status.lower()

        mapping = config.status_mapping
        for standard_status, client_values in mapping.items():
            if client_status in client_values:
                return standard_status

        return "unavailable"  # Default
```

### Step 4: Integration Endpoints
```python
# app/api/integration.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user
from app.models.user import User
from app.services.integration_service import IntegrationService
from app.services.project_service import ProjectService
from app.schemas.integration import (
    IntegrationConfigUpdate, IntegrationConfigResponse,
    TestConnectionResponse
)

router = APIRouter(tags=["Integration"])

async def get_project_or_404(db, slug: str):
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

@router.get(
    "/projects/{slug}/integration",
    response_model=IntegrationConfigResponse
)
async def get_integration(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await get_project_or_404(db, slug)
    service = IntegrationService(db)

    config = await service.get_config(project.id)

    if not config:
        # Return empty config
        return IntegrationConfigResponse(
            id=None,
            project_id=project.id,
            has_credentials=False,
            created_at=None,
            updated_at=None
        )

    return IntegrationConfigResponse(
        id=config.id,
        project_id=config.project_id,
        api_base_url=config.api_base_url,
        auth_type=config.auth_type,
        status_endpoint=config.status_endpoint,
        status_mapping=config.status_mapping,
        update_method=config.update_method,
        polling_interval_seconds=config.polling_interval_seconds,
        timeout_seconds=config.timeout_seconds,
        retry_count=config.retry_count,
        has_credentials=bool(config.auth_config),
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.put(
    "/projects/{slug}/integration",
    response_model=IntegrationConfigResponse
)
async def update_integration(
    slug: str,
    data: IntegrationConfigUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await get_project_or_404(db, slug)
    service = IntegrationService(db)

    config = await service.update_config(project.id, data)

    return IntegrationConfigResponse(
        id=config.id,
        project_id=config.project_id,
        api_base_url=config.api_base_url,
        auth_type=config.auth_type,
        status_endpoint=config.status_endpoint,
        status_mapping=config.status_mapping,
        update_method=config.update_method,
        polling_interval_seconds=config.polling_interval_seconds,
        timeout_seconds=config.timeout_seconds,
        retry_count=config.retry_count,
        has_credentials=bool(config.auth_config),
        created_at=config.created_at,
        updated_at=config.updated_at
    )

@router.post(
    "/projects/{slug}/integration/test",
    response_model=TestConnectionResponse
)
async def test_integration(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    project = await get_project_or_404(db, slug)
    service = IntegrationService(db)

    result = await service.test_connection(project.id)

    return TestConnectionResponse(**result)
```

## Acceptance Criteria

- [ ] Can save integration config
- [ ] Credentials encrypted in database
- [ ] Can test connection to client API
- [ ] Status mapping works correctly
- [ ] Different auth types supported
- [ ] Credentials never exposed in responses
