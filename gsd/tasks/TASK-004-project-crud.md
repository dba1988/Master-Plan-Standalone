# TASK-004: Project CRUD

**Phase**: 1 - Foundation
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-003

## Objective

Implement project management endpoints with version support.

## Description

Create CRUD operations for projects:
- List all projects
- Create new project
- Get project details
- Update project
- Delete project
- Create new version

## Files to Create/Modify

```
admin-api/app/
├── schemas/
│   └── project.py
├── api/
│   └── projects.py
└── services/
    └── project_service.py
```

## Implementation Steps

### Step 1: Project Schemas
```python
# app/schemas/project.py
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
import re

def validate_slug(v: str) -> str:
    if not re.match(r'^[a-z][a-z0-9-]*$', v):
        raise ValueError('Slug must be lowercase, start with letter, contain only letters, numbers, hyphens')
    return v

class ProjectCreate(BaseModel):
    slug: str = Field(..., min_length=2, max_length=100)
    name: str = Field(..., min_length=1, max_length=255)
    name_ar: Optional[str] = None
    description: Optional[str] = None

    @validator('slug')
    def validate_slug(cls, v):
        return validate_slug(v)

class ProjectUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    name_ar: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class VersionInfo(BaseModel):
    version_number: int
    status: str
    created_at: datetime
    published_at: Optional[datetime] = None

class ProjectResponse(BaseModel):
    id: UUID
    slug: str
    name: str
    name_ar: Optional[str]
    description: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

class ProjectDetailResponse(ProjectResponse):
    versions: List[VersionInfo]
    current_draft: Optional[int] = None
    published_version: Optional[int] = None

class ProjectListResponse(BaseModel):
    projects: List[ProjectResponse]
    total: int

class VersionCreate(BaseModel):
    base_version: Optional[int] = None  # Clone from existing version
```

### Step 2: Project Service
```python
# app/services/project_service.py
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from typing import Optional, List
from uuid import UUID
from app.models.project import Project
from app.models.version import ProjectVersion
from app.schemas.project import ProjectCreate, ProjectUpdate

class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(self, skip: int = 0, limit: int = 100) -> tuple[List[Project], int]:
        # Get total count
        count_result = await self.db.execute(select(func.count(Project.id)))
        total = count_result.scalar()

        # Get projects
        result = await self.db.execute(
            select(Project)
            .where(Project.is_active == True)
            .order_by(Project.updated_at.desc())
            .offset(skip)
            .limit(limit)
        )
        projects = result.scalars().all()

        return projects, total

    async def get_project_by_slug(self, slug: str) -> Optional[Project]:
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.versions))
            .where(Project.slug == slug)
        )
        return result.scalar_one_or_none()

    async def create_project(self, data: ProjectCreate, user_id: UUID) -> Project:
        # Check slug uniqueness
        existing = await self.get_project_by_slug(data.slug)
        if existing:
            raise ValueError(f"Project with slug '{data.slug}' already exists")

        project = Project(
            slug=data.slug,
            name=data.name,
            name_ar=data.name_ar,
            description=data.description,
            created_by=user_id
        )
        self.db.add(project)
        await self.db.commit()
        await self.db.refresh(project)

        # Create initial draft version
        await self.create_version(project.id)

        return project

    async def update_project(self, slug: str, data: ProjectUpdate) -> Optional[Project]:
        project = await self.get_project_by_slug(slug)
        if not project:
            return None

        update_data = data.dict(exclude_unset=True)
        for key, value in update_data.items():
            setattr(project, key, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, slug: str) -> bool:
        project = await self.get_project_by_slug(slug)
        if not project:
            return False

        # Soft delete
        project.is_active = False
        await self.db.commit()
        return True

    async def create_version(
        self,
        project_id: UUID,
        base_version: Optional[int] = None
    ) -> ProjectVersion:
        # Get next version number
        result = await self.db.execute(
            select(func.max(ProjectVersion.version_number))
            .where(ProjectVersion.project_id == project_id)
        )
        max_version = result.scalar() or 0
        new_version_number = max_version + 1

        version = ProjectVersion(
            project_id=project_id,
            version_number=new_version_number,
            status="draft"
        )
        self.db.add(version)
        await self.db.commit()
        await self.db.refresh(version)

        # TODO: If base_version provided, clone config/overlays
        if base_version:
            await self._clone_version_data(project_id, base_version, version.id)

        return version

    async def _clone_version_data(
        self,
        project_id: UUID,
        source_version: int,
        target_version_id: UUID
    ):
        # Implementation for cloning overlays and config
        pass
```

### Step 3: Project Endpoints
```python
# app/api/projects.py
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_db
from app.api.deps import get_current_user, require_role
from app.models.user import User
from app.schemas.project import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectDetailResponse, ProjectListResponse, VersionCreate, VersionInfo
)
from app.services.project_service import ProjectService

router = APIRouter(prefix="/projects", tags=["Projects"])

@router.get("", response_model=ProjectListResponse)
async def list_projects(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ProjectService(db)
    projects, total = await service.list_projects(skip, limit)

    return ProjectListResponse(
        projects=[ProjectResponse.from_orm(p) for p in projects],
        total=total
    )

@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    data: ProjectCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    service = ProjectService(db)
    try:
        project = await service.create_project(data, current_user.id)
        return ProjectResponse.from_orm(project)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

@router.get("/{slug}", response_model=ProjectDetailResponse)
async def get_project(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    versions = [
        VersionInfo(
            version_number=v.version_number,
            status=v.status,
            created_at=v.created_at,
            published_at=v.published_at
        )
        for v in sorted(project.versions, key=lambda v: v.version_number, reverse=True)
    ]

    current_draft = next(
        (v.version_number for v in project.versions if v.status == "draft"),
        None
    )
    published_version = next(
        (v.version_number for v in project.versions if v.status == "published"),
        None
    )

    return ProjectDetailResponse(
        **ProjectResponse.from_orm(project).dict(),
        versions=versions,
        current_draft=current_draft,
        published_version=published_version
    )

@router.put("/{slug}", response_model=ProjectResponse)
async def update_project(
    slug: str,
    data: ProjectUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "editor"]))
):
    service = ProjectService(db)
    project = await service.update_project(slug, data)

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    return ProjectResponse.from_orm(project)

@router.delete("/{slug}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    slug: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"]))
):
    service = ProjectService(db)
    deleted = await service.delete_project(slug)

    if not deleted:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

@router.post("/{slug}/versions", response_model=VersionInfo, status_code=status.HTTP_201_CREATED)
async def create_version(
    slug: str,
    data: VersionCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin", "editor"]))
):
    service = ProjectService(db)
    project = await service.get_project_by_slug(slug)

    if not project:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")

    version = await service.create_version(project.id, data.base_version)

    return VersionInfo(
        version_number=version.version_number,
        status=version.status,
        created_at=version.created_at,
        published_at=version.published_at
    )
```

### Step 4: Register Router
```python
# app/main.py (add to existing)
from app.api import auth, projects

app.include_router(auth.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
```

## Acceptance Criteria

- [ ] Can list all projects (paginated)
- [ ] Can create project with unique slug
- [ ] Slug validation (lowercase, alphanumeric, hyphens)
- [ ] Initial version created automatically
- [ ] Can get project details with versions
- [ ] Can update project name/description
- [ ] Can soft delete project
- [ ] Can create new version
- [ ] Role-based access (admin for create/delete)

## API Reference

| Method | Endpoint | Auth | Description |
|--------|----------|------|-------------|
| GET | /api/projects | Any | List projects |
| POST | /api/projects | Admin | Create project |
| GET | /api/projects/{slug} | Any | Get project details |
| PUT | /api/projects/{slug} | Admin/Editor | Update project |
| DELETE | /api/projects/{slug} | Admin | Delete project |
| POST | /api/projects/{slug}/versions | Admin/Editor | Create version |
