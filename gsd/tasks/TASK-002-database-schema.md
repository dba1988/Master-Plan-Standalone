# TASK-002: Database Schema + Migrations

**Phase**: 1 - Foundation
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001

## Objective

Implement the complete database schema using SQLAlchemy models and Alembic migrations.

## Description

Create all database tables required for the MVP:
- Users and refresh tokens (auth)
- Projects and versions
- Project config
- Assets
- Layers and overlays
- Integration config
- Published releases

## Files to Create/Modify

```
admin-service/api/
├── alembic/
│   ├── env.py (modify for async)
│   └── versions/
│       └── 001_initial_schema.py
└── app/
    ├── core/
    │   └── database.py
    └── models/
        ├── __init__.py
        ├── user.py
        ├── project.py
        ├── version.py
        ├── config.py
        ├── asset.py
        ├── layer.py
        ├── overlay.py
        ├── integration.py
        └── release.py
```

## Implementation Steps

### Step 1: Configure Database Connection
```python
# app/core/database.py
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=settings.debug)

AsyncSessionLocal = sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

Base = declarative_base()

async def get_db():
    async with AsyncSessionLocal() as session:
        yield session
```

### Step 2: Create User Model
```python
# app/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime
from sqlalchemy.dialects.postgresql import UUID
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)
    role = Column(String(50), default="editor")  # admin, editor, viewer
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class RefreshToken(Base):
    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"))
    token_hash = Column(String(255), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    revoked_at = Column(DateTime, nullable=True)
```

### Step 3: Create Project Models
```python
# app/models/project.py
import uuid
from datetime import datetime
from sqlalchemy import Column, String, Boolean, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.core.database import Base

class Project(Base):
    __tablename__ = "projects"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug = Column(String(100), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    name_ar = Column(String(255), nullable=True)
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)
    created_by = Column(UUID(as_uuid=True), ForeignKey("users.id"))
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    versions = relationship("ProjectVersion", back_populates="project")
    integration_config = relationship("IntegrationConfig", back_populates="project", uselist=False)
```

### Step 4: Create Version Model
```python
# app/models/version.py
class ProjectVersion(Base):
    __tablename__ = "project_versions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    project_id = Column(UUID(as_uuid=True), ForeignKey("projects.id", ondelete="CASCADE"))
    version_number = Column(Integer, nullable=False)
    status = Column(String(20), default="draft")  # draft, published, archived
    published_at = Column(DateTime, nullable=True)
    published_by = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    project = relationship("Project", back_populates="versions")
    config = relationship("ProjectConfig", back_populates="version", uselist=False)
    assets = relationship("Asset", back_populates="version")
    layers = relationship("Layer", back_populates="version")
    overlays = relationship("Overlay", back_populates="version")

    __table_args__ = (
        UniqueConstraint('project_id', 'version_number', name='uq_project_version'),
    )
```

### Step 5: Create Overlay Model
```python
# app/models/overlay.py
from sqlalchemy.dialects.postgresql import JSONB

class Overlay(Base):
    __tablename__ = "overlays"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    version_id = Column(UUID(as_uuid=True), ForeignKey("project_versions.id", ondelete="CASCADE"))
    layer_id = Column(UUID(as_uuid=True), ForeignKey("layers.id", ondelete="SET NULL"), nullable=True)

    overlay_type = Column(String(20), nullable=False)  # zone, unit, poi
    ref = Column(String(255), nullable=False)  # External reference

    geometry = Column(JSONB, nullable=False)  # { type: "path", d: "M..." }
    view_box = Column(String(100), nullable=True)

    label = Column(JSONB, nullable=True)  # { en: "Zone A", ar: "..." }
    label_position = Column(JSONB, nullable=True)  # [x, y]

    props = Column(JSONB, default=dict)
    style_override = Column(JSONB, nullable=True)

    sort_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    version = relationship("ProjectVersion", back_populates="overlays")
    layer = relationship("Layer", back_populates="overlays")

    __table_args__ = (
        UniqueConstraint('version_id', 'overlay_type', 'ref', name='uq_overlay_ref'),
        Index('ix_overlays_version', 'version_id'),
        Index('ix_overlays_type', 'overlay_type'),
        Index('ix_overlays_ref', 'ref'),
    )
```

### Step 6: Create Migration
```bash
cd admin-service/api
alembic revision --autogenerate -m "Initial schema"
alembic upgrade head
```

### Step 7: Create Seed Script
```python
# scripts/seed_dev_user.py
import asyncio
from app.core.database import AsyncSessionLocal
from app.models.user import User
from app.core.security import get_password_hash

async def seed():
    async with AsyncSessionLocal() as session:
        user = User(
            email="admin@example.com",
            password_hash=get_password_hash("admin123"),
            name="Admin User",
            role="admin"
        )
        session.add(user)
        await session.commit()
        print(f"Created user: {user.email}")

if __name__ == "__main__":
    asyncio.run(seed())
```

## Acceptance Criteria

- [ ] All models defined with correct relationships
- [ ] Migration runs successfully
- [ ] Tables created in PostgreSQL
- [ ] Indexes created for query performance
- [ ] Seed script creates dev user
- [ ] Can connect to DB from FastAPI

## Notes

- Use UUID primary keys for better distribution
- JSONB for flexible schema fields
- Proper foreign key constraints with cascade
- Index frequently queried columns
