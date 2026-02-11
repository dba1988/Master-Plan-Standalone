import re
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ProjectCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None

    @field_validator('slug')
    @classmethod
    def validate_slug(cls, v: str) -> str:
        v = v.lower()
        if not re.match(r'^[a-z][a-z0-9-]*$', v):
            raise ValueError('Slug must start with a letter and contain only lowercase letters, numbers, and hyphens')
        return v


class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    name_ar: Optional[str] = Field(None, max_length=255)
    description: Optional[str] = None
    is_active: Optional[bool] = None


class VersionInfo(BaseModel):
    id: UUID
    version_number: int
    status: str
    release_id: Optional[str] = None
    release_url: Optional[str] = None
    created_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ProjectResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    name_ar: Optional[str] = None
    description: Optional[str] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class ProjectDetailResponse(ProjectResponse):
    versions: List[VersionInfo] = []
    current_draft: Optional[int] = None
    published_version: Optional[int] = None


class ProjectListResponse(BaseModel):
    items: List[ProjectResponse]
    total: int
    skip: int
    limit: int


class VersionCreate(BaseModel):
    base_version: Optional[int] = Field(None, description="Clone from existing version number")


class VersionResponse(BaseModel):
    id: UUID
    project_id: UUID
    version_number: int
    status: str
    release_id: Optional[str] = None
    release_url: Optional[str] = None
    created_at: datetime
    published_at: Optional[datetime] = None

    class Config:
        from_attributes = True
