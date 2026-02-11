from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.project import Project
from app.models.version import ProjectVersion
from app.models.config import ProjectConfig
from app.schemas.project import ProjectCreate, ProjectUpdate, VersionCreate


class ProjectService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def list_projects(
        self, skip: int = 0, limit: int = 20
    ) -> Tuple[List[Project], int]:
        """List active projects with pagination."""
        # Get total count
        count_result = await self.db.execute(
            select(func.count(Project.id)).where(Project.is_active == True)
        )
        total = count_result.scalar_one()

        # Get projects
        result = await self.db.execute(
            select(Project)
            .where(Project.is_active == True)
            .order_by(Project.created_at.desc())
            .offset(skip)
            .limit(limit)
        )
        projects = result.scalars().all()

        return list(projects), total

    async def get_project_by_slug(self, slug: str) -> Optional[Project]:
        """Get project by slug with versions loaded."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.versions))
            .where(Project.slug == slug, Project.is_active == True)
        )
        return result.scalar_one_or_none()

    async def get_project_by_id(self, project_id: UUID) -> Optional[Project]:
        """Get project by ID."""
        result = await self.db.execute(
            select(Project)
            .options(selectinload(Project.versions))
            .where(Project.id == project_id)
        )
        return result.scalar_one_or_none()

    async def slug_exists(self, slug: str) -> bool:
        """Check if slug already exists."""
        result = await self.db.execute(
            select(func.count(Project.id)).where(Project.slug == slug)
        )
        return result.scalar_one() > 0

    async def create_project(
        self, data: ProjectCreate, user_id: UUID
    ) -> Project:
        """Create project with initial draft version."""
        # Create project
        project = Project(
            slug=data.slug,
            name=data.name,
            name_ar=data.name_ar,
            description=data.description,
            created_by=user_id,
            is_active=True,
        )
        self.db.add(project)
        await self.db.flush()

        # Create initial version (v1 draft)
        version = ProjectVersion(
            project_id=project.id,
            version_number=1,
            status="draft",
        )
        self.db.add(version)
        await self.db.flush()

        # Create default config for the project
        config = ProjectConfig(
            project_id=project.id,
            theme={},
            map_settings={},
            status_colors={
                "available": "#52c41a",
                "reserved": "#faad14",
                "sold": "#ff4d4f",
                "hidden": "#8c8c8c",
                "unreleased": "#d9d9d9"
            },
            popup_config={},
            filter_config={},
        )
        self.db.add(config)

        await self.db.commit()
        await self.db.refresh(project)

        # Reload with versions
        return await self.get_project_by_id(project.id)

    async def update_project(
        self, slug: str, data: ProjectUpdate
    ) -> Optional[Project]:
        """Update project fields."""
        project = await self.get_project_by_slug(slug)
        if not project:
            return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(project, field, value)

        await self.db.commit()
        await self.db.refresh(project)
        return project

    async def delete_project(self, slug: str) -> bool:
        """Soft delete project (set is_active=False)."""
        result = await self.db.execute(
            select(Project).where(Project.slug == slug, Project.is_active == True)
        )
        project = result.scalar_one_or_none()

        if not project:
            return False

        project.is_active = False
        await self.db.commit()
        return True

    async def create_version(
        self, project_id: UUID, data: VersionCreate
    ) -> Optional[ProjectVersion]:
        """
        Create new version for a project.

        Versions are just release tags (like git tags).
        Assets, overlays, and config belong to the project directly.

        Only one draft version allowed at a time.
        """
        project = await self.get_project_by_id(project_id)
        if not project:
            return None

        # Check if there's already a draft version
        draft_result = await self.db.execute(
            select(ProjectVersion).where(
                ProjectVersion.project_id == project_id,
                ProjectVersion.status == "draft"
            ).limit(1)
        )
        existing_draft = draft_result.scalar_one_or_none()
        if existing_draft:
            raise ValueError(
                f"Cannot create new version: draft version {existing_draft.version_number} already exists. "
                "Publish or delete the existing draft first."
            )

        # Get next version number
        result = await self.db.execute(
            select(func.max(ProjectVersion.version_number))
            .where(ProjectVersion.project_id == project_id)
        )
        max_version = result.scalar_one() or 0
        new_version_number = max_version + 1

        # Create new version (just a release tag)
        version = ProjectVersion(
            project_id=project_id,
            version_number=new_version_number,
            status="draft",
        )
        self.db.add(version)

        # Ensure project has a config (create default if not exists)
        config_result = await self.db.execute(
            select(ProjectConfig).where(ProjectConfig.project_id == project_id)
        )
        existing_config = config_result.scalar_one_or_none()

        if not existing_config:
            # Create default config for the project
            config = ProjectConfig(
                project_id=project_id,
                theme={},
                map_settings={},
                status_colors={
                    "available": "#52c41a",
                    "reserved": "#faad14",
                    "sold": "#ff4d4f",
                    "hidden": "#d9d9d9",
                    "unreleased": "#bfbfbf",
                },
                popup_config={},
                filter_config={},
            )
            self.db.add(config)

        await self.db.commit()
        await self.db.refresh(version)

        return version

    async def get_version(
        self, project_id: UUID, version_number: int
    ) -> Optional[ProjectVersion]:
        """Get specific version of a project."""
        result = await self.db.execute(
            select(ProjectVersion)
            .where(
                ProjectVersion.project_id == project_id,
                ProjectVersion.version_number == version_number
            )
        )
        return result.scalar_one_or_none()

    async def delete_version(
        self, project_id: UUID, version_number: int
    ) -> bool:
        """
        Delete a draft version.

        Only draft versions can be deleted. Published versions are immutable.
        """
        version = await self.get_version(project_id, version_number)
        if not version:
            return False

        if version.status != "draft":
            raise ValueError(
                f"Cannot delete version {version_number}: only draft versions can be deleted. "
                f"This version has status '{version.status}'."
            )

        await self.db.delete(version)
        await self.db.commit()
        return True
