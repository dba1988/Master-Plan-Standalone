# Code Style: Admin Service

> **Applies to**: `admin-service/api/` and `admin-service/ui/`
> **Last Updated**: 2026-02-09

---

## 1. General Principles

| Principle | Rule |
|-----------|------|
| **No shared code with public-service** | Duplication is acceptable |
| **Feature-first organization** | Code lives in `features/<name>/` |
| **Single responsibility** | One file = one job |
| **Explicit over implicit** | No magic, clear data flow |
| **Validate at boundaries** | API layer validates, inner layers trust |

---

## 2. Python (FastAPI Backend)

### 2.1 File Naming

```
<action>_<entity>.py           # Services: create_project.py
<entity>_repo.py               # Repositories: project_repo.py
<entity>_routes.py             # Routes: project_routes.py (or just routes.py)
types.py                       # Domain types per feature
```

### 2.2 Function/Class Naming

```python
# Services: verb_noun
async def create_project(db: AsyncSession, data: CreateProjectDTO) -> Project:
async def publish_version(db: AsyncSession, version_id: UUID) -> Release:

# Repositories: verb_noun or get_by_*
async def get_project_by_slug(db: AsyncSession, slug: str) -> Project | None:
async def list_overlays_for_version(db: AsyncSession, version_id: UUID) -> list[Overlay]:

# Route handlers: match HTTP semantics
@router.post("/projects")
async def create_project(...):

@router.get("/projects/{slug}")
async def get_project(...):
```

### 2.3 Layer Responsibilities

```python
# Routes: Parse input, call service, return response
@router.post("/projects/{slug}/versions/{version}/publish")
async def publish_version(
    slug: str,
    version: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    # Validate input (done by Pydantic)
    # Call service
    job = await publish_service.start_publish(db, slug, version, user.id)
    # Return response
    return {"job_id": job.id, "status": "queued"}


# Services: Business logic, orchestration
class PublishService:
    async def start_publish(
        self, db: AsyncSession, slug: str, version: int, user_id: UUID
    ) -> Job:
        project = await project_repo.get_by_slug(db, slug)
        if not project:
            raise NotFoundError("Project not found")

        version_obj = await version_repo.get_by_number(db, project.id, version)
        if version_obj.status != "draft":
            raise ValidationError("Only draft versions can be published")

        job = await job_repo.create(db, job_type="publish", ...)
        return job


# Repositories: Data access only, no business logic
class ProjectRepo:
    async def get_by_slug(self, db: AsyncSession, slug: str) -> Project | None:
        result = await db.execute(
            select(Project).where(Project.slug == slug)
        )
        return result.scalar_one_or_none()
```

### 2.4 Error Handling

```python
# Define in lib/exceptions.py
class AppError(Exception):
    def __init__(self, message: str, code: str = "ERROR"):
        self.message = message
        self.code = code

class NotFoundError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "NOT_FOUND")

class ValidationError(AppError):
    def __init__(self, message: str):
        super().__init__(message, "VALIDATION_ERROR")


# Handle in main.py
@app.exception_handler(NotFoundError)
async def not_found_handler(request: Request, exc: NotFoundError):
    return JSONResponse(status_code=404, content={"error": exc.message})
```

### 2.5 Type Definitions

```python
# features/projects/domain/types.py
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from enum import Enum

class VersionStatus(str, Enum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"

class CreateProjectDTO(BaseModel):
    name: str
    slug: str
    description: str | None = None

class ProjectResponse(BaseModel):
    id: UUID
    name: str
    slug: str
    created_at: datetime

    class Config:
        from_attributes = True
```

### 2.6 Imports Order

```python
# 1. Standard library
from datetime import datetime
from uuid import UUID
from typing import Optional

# 2. Third-party
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel

# 3. Local - lib/infra
from app.lib.database import get_db
from app.lib.exceptions import NotFoundError
from app.infra.r2_client import r2_storage

# 4. Local - same feature
from .types import CreateProjectDTO, ProjectResponse
from .project_repo import project_repo
```

---

## 3. TypeScript/React (Admin UI)

### 3.1 File Naming

```
<ComponentName>.tsx            # Components: ProjectCard.tsx
<hookName>.ts                  # Hooks: useProjects.ts
<featureName>Api.ts            # API: projectsApi.ts
types.ts                       # Types per feature
```

### 3.2 Component Structure

```tsx
// features/projects/ui/ProjectCard.tsx
import { type Project } from '../types';
import { Card, Button } from '@/components';
import styles from './ProjectCard.module.css';

interface ProjectCardProps {
  project: Project;
  onSelect: (id: string) => void;
}

export function ProjectCard({ project, onSelect }: ProjectCardProps) {
  return (
    <Card className={styles.card}>
      <h3>{project.name}</h3>
      <p>{project.description}</p>
      <Button onClick={() => onSelect(project.id)}>Open</Button>
    </Card>
  );
}
```

### 3.3 Hook Structure

```tsx
// features/projects/hooks/useProjects.ts
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { projectsApi } from '../api/projectsApi';
import { type Project, type CreateProjectDTO } from '../types';

export function useProjects() {
  return useQuery({
    queryKey: ['projects'],
    queryFn: projectsApi.list,
  });
}

export function useCreateProject() {
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: (data: CreateProjectDTO) => projectsApi.create(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects'] });
    },
  });
}
```

### 3.4 API Layer

```tsx
// features/projects/api/projectsApi.ts
import { apiClient } from '@/lib/api-client';
import { type Project, type CreateProjectDTO } from '../types';

export const projectsApi = {
  list: async (): Promise<Project[]> => {
    const response = await apiClient.get('/projects');
    return response.data;
  },

  get: async (slug: string): Promise<Project> => {
    const response = await apiClient.get(`/projects/${slug}`);
    return response.data;
  },

  create: async (data: CreateProjectDTO): Promise<Project> => {
    const response = await apiClient.post('/projects', data);
    return response.data;
  },
};
```

### 3.5 Type Definitions

```tsx
// features/projects/types.ts
export interface Project {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  createdAt: string;
  currentReleaseId: string | null;
}

export interface CreateProjectDTO {
  name: string;
  slug: string;
  description?: string;
}

export interface Version {
  id: string;
  versionNumber: number;
  status: 'draft' | 'published' | 'archived';
  createdAt: string;
}
```

### 3.6 Imports Order

```tsx
// 1. React
import { useState, useEffect } from 'react';

// 2. Third-party
import { useQuery } from '@tanstack/react-query';
import { Button, Modal } from 'antd';

// 3. Local - lib/components
import { Card } from '@/components';
import { apiClient } from '@/lib/api-client';

// 4. Local - same feature
import { type Project } from '../types';
import { useProjects } from '../hooks/useProjects';

// 5. Styles (last)
import styles from './ProjectsPage.module.css';
```

---

## 4. Testing

### 4.1 Python Tests

```python
# features/publish/__tests__/test_release_builder.py
import pytest
from app.features.publish.application.release_builder import build_release

def test_build_release_includes_all_overlays():
    # Arrange
    version_data = {...}
    overlays = [...]

    # Act
    release = build_release(version_data, overlays)

    # Assert
    assert len(release["overlays"]) == len(overlays)
    assert release["version"] == 3


def test_build_release_excludes_hidden_overlays():
    overlays = [
        {"ref": "A", "is_visible": True},
        {"ref": "B", "is_visible": False},
    ]

    release = build_release({}, overlays)

    assert len(release["overlays"]) == 1
    assert release["overlays"][0]["ref"] == "A"
```

### 4.2 TypeScript Tests

```tsx
// features/projects/__tests__/useProjects.test.ts
import { renderHook, waitFor } from '@testing-library/react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { useProjects } from '../hooks/useProjects';

describe('useProjects', () => {
  it('fetches projects list', async () => {
    const { result } = renderHook(() => useProjects(), {
      wrapper: createWrapper(),
    });

    await waitFor(() => expect(result.current.isSuccess).toBe(true));

    expect(result.current.data).toHaveLength(2);
  });
});
```

---

## 5. What NOT to Do

```python
# ❌ God utils file
# utils.py with 50 unrelated functions

# ✓ Small focused modules
# lib/slug.py - slug generation
# lib/datetime.py - date formatting


# ❌ Business logic in routes
@router.post("/projects/{slug}/publish")
async def publish(slug: str, db: AsyncSession = Depends(get_db)):
    project = await db.execute(select(Project).where(...))
    if project.status != "draft":
        raise HTTPException(400, "...")
    # 100 more lines of business logic...

# ✓ Routes call services
@router.post("/projects/{slug}/publish")
async def publish(slug: str, db: AsyncSession = Depends(get_db)):
    return await publish_service.publish(db, slug)


# ❌ Importing from public-service
from public_service.api.src.lib.sse import SSEManager

# ✓ Own copy in admin-service
from app.lib.sse import SSEManager


# ❌ Barrel files re-exporting everything
# features/index.ts
export * from './auth';
export * from './projects';
export * from './overlays';

# ✓ Explicit imports
import { useProjects } from '@/features/projects/hooks/useProjects';
```

---

## 6. Checklist for New Features

- [ ] Create feature folder: `features/<name>/`
- [ ] Add subfolders: `api/`, `domain/`, `application/`, `data/`, `__tests__/`
- [ ] Define types in `domain/types.py` (or `types.ts`)
- [ ] Repository handles data access only
- [ ] Service handles business logic
- [ ] Routes handle HTTP concerns only
- [ ] Tests cover critical business logic
- [ ] No imports from other features (use lib/infra)
- [ ] No imports from public-service
