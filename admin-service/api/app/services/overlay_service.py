"""
Overlay Service

Handles overlay CRUD operations with bulk upsert support.
"""
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.overlay import Overlay
from app.models.project import Project
from app.models.version import ProjectVersion
from app.schemas.overlay import (
    BulkOverlayItem,
    BulkUpsertError,
    OverlayCreate,
    OverlayType,
    OverlayUpdate,
)


class OverlayService:
    """Service for managing overlays."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_version_by_project_and_number(
        self,
        project_slug: str,
        version_number: int,
    ) -> Optional[Tuple[Project, ProjectVersion]]:
        """Get project and version by slug and version number."""
        # Get the project
        project_result = await self.db.execute(
            select(Project).where(
                Project.slug == project_slug,
                Project.is_active == True
            )
        )
        project = project_result.scalar_one_or_none()
        if not project:
            return None

        # Get the version
        version_result = await self.db.execute(
            select(ProjectVersion).where(
                ProjectVersion.project_id == project.id,
                ProjectVersion.version_number == version_number
            )
        )
        version = version_result.scalar_one_or_none()
        if not version:
            return None

        return project, version

    async def list_overlays(
        self,
        project_slug: str,
        version_number: int,
        overlay_type: Optional[OverlayType] = None,
        layer_id: Optional[UUID] = None,
    ) -> Optional[Tuple[List[Overlay], int]]:
        """
        List overlays for a project version with optional filters.

        Returns None if project/version not found.
        Returns tuple of (overlays, total_count).
        """
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return None

        project, version = result

        # Build query
        query = select(Overlay).where(Overlay.version_id == version.id)
        count_query = select(func.count(Overlay.id)).where(Overlay.version_id == version.id)

        if overlay_type:
            query = query.where(Overlay.overlay_type == overlay_type.value)
            count_query = count_query.where(Overlay.overlay_type == overlay_type.value)

        if layer_id:
            query = query.where(Overlay.layer_id == layer_id)
            count_query = count_query.where(Overlay.layer_id == layer_id)

        # Get count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Get overlays ordered by sort_order then ref
        query = query.order_by(Overlay.sort_order, Overlay.ref)
        overlays_result = await self.db.execute(query)
        overlays = overlays_result.scalars().all()

        return list(overlays), total

    async def get_overlay(
        self,
        project_slug: str,
        version_number: int,
        overlay_id: UUID,
    ) -> Optional[Overlay]:
        """Get a specific overlay by ID."""
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return None

        project, version = result

        overlay_result = await self.db.execute(
            select(Overlay).where(
                Overlay.id == overlay_id,
                Overlay.version_id == version.id
            )
        )
        return overlay_result.scalar_one_or_none()

    async def get_overlay_by_ref(
        self,
        version_id: UUID,
        overlay_type: str,
        ref: str,
    ) -> Optional[Overlay]:
        """Get overlay by type and reference."""
        result = await self.db.execute(
            select(Overlay).where(
                Overlay.version_id == version_id,
                Overlay.overlay_type == overlay_type,
                Overlay.ref == ref
            )
        )
        return result.scalar_one_or_none()

    async def create_overlay(
        self,
        project_slug: str,
        version_number: int,
        data: OverlayCreate,
    ) -> Optional[Overlay]:
        """
        Create a new overlay.

        Returns None if project/version not found or version is not draft.
        """
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return None

        project, version = result

        # Only allow modifications to draft versions
        if version.status != "draft":
            return None

        # Check if ref already exists for this type
        existing = await self.get_overlay_by_ref(
            version.id, data.overlay_type.value, data.ref
        )
        if existing:
            return None  # Duplicate ref

        overlay = Overlay(
            version_id=version.id,
            overlay_type=data.overlay_type.value,
            ref=data.ref,
            geometry=data.geometry,
            view_box=data.view_box,
            label=data.label,
            label_position=data.label_position,
            props=data.props or {},
            style_override=data.style_override,
            sort_order=data.sort_order or 0,
            is_visible=data.is_visible if data.is_visible is not None else True,
            layer_id=data.layer_id,
        )

        self.db.add(overlay)
        await self.db.commit()
        await self.db.refresh(overlay)

        return overlay

    async def update_overlay(
        self,
        project_slug: str,
        version_number: int,
        overlay_id: UUID,
        data: OverlayUpdate,
    ) -> Optional[Overlay]:
        """
        Update an existing overlay.

        Returns None if not found or version is not draft.
        """
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return None

        project, version = result

        # Only allow modifications to draft versions
        if version.status != "draft":
            return None

        # Get overlay
        overlay = await self.get_overlay(project_slug, version_number, overlay_id)
        if not overlay:
            return None

        # Check ref uniqueness if being changed
        if data.ref and data.ref != overlay.ref:
            existing = await self.get_overlay_by_ref(
                version.id,
                data.overlay_type.value if data.overlay_type else overlay.overlay_type,
                data.ref
            )
            if existing and existing.id != overlay.id:
                return None  # Duplicate ref

        # Update fields
        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "overlay_type" and value is not None:
                setattr(overlay, field, value.value)
            else:
                setattr(overlay, field, value)

        await self.db.commit()
        await self.db.refresh(overlay)

        return overlay

    async def delete_overlay(
        self,
        project_slug: str,
        version_number: int,
        overlay_id: UUID,
    ) -> bool:
        """
        Delete an overlay.

        Returns True if deleted, False if not found or version is not draft.
        """
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return False

        project, version = result

        # Only allow modifications to draft versions
        if version.status != "draft":
            return False

        # Get overlay
        overlay_result = await self.db.execute(
            select(Overlay).where(
                Overlay.id == overlay_id,
                Overlay.version_id == version.id
            )
        )
        overlay = overlay_result.scalar_one_or_none()

        if not overlay:
            return False

        await self.db.delete(overlay)
        await self.db.commit()

        return True

    async def bulk_upsert(
        self,
        project_slug: str,
        version_number: int,
        overlays: List[BulkOverlayItem],
    ) -> Optional[Tuple[int, int, List[BulkUpsertError]]]:
        """
        Bulk create or update overlays.

        Matches by (version_id, overlay_type, ref).
        Returns None if project/version not found or version is not draft.
        Returns tuple of (created_count, updated_count, errors).
        """
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return None

        project, version = result

        # Only allow modifications to draft versions
        if version.status != "draft":
            return None

        created = 0
        updated = 0
        errors: List[BulkUpsertError] = []

        for idx, item in enumerate(overlays):
            try:
                # Check if exists
                existing = await self.get_overlay_by_ref(
                    version.id, item.overlay_type.value, item.ref
                )

                if existing:
                    # Update existing
                    existing.geometry = item.geometry
                    existing.view_box = item.view_box
                    existing.label = item.label
                    existing.label_position = item.label_position
                    existing.props = item.props or {}
                    existing.style_override = item.style_override
                    existing.sort_order = item.sort_order or 0
                    existing.is_visible = item.is_visible if item.is_visible is not None else True
                    existing.layer_id = item.layer_id
                    updated += 1
                else:
                    # Create new
                    overlay = Overlay(
                        version_id=version.id,
                        overlay_type=item.overlay_type.value,
                        ref=item.ref,
                        geometry=item.geometry,
                        view_box=item.view_box,
                        label=item.label,
                        label_position=item.label_position,
                        props=item.props or {},
                        style_override=item.style_override,
                        sort_order=item.sort_order or 0,
                        is_visible=item.is_visible if item.is_visible is not None else True,
                        layer_id=item.layer_id,
                    )
                    self.db.add(overlay)
                    created += 1

            except Exception as e:
                errors.append(BulkUpsertError(
                    index=idx,
                    ref=item.ref,
                    error=str(e)
                ))

        await self.db.commit()

        return created, updated, errors

    async def delete_by_type(
        self,
        project_slug: str,
        version_number: int,
        overlay_type: OverlayType,
    ) -> Optional[int]:
        """
        Delete all overlays of a specific type.

        Returns None if project/version not found or version is not draft.
        Returns count of deleted overlays.
        """
        result = await self.get_version_by_project_and_number(
            project_slug, version_number
        )
        if not result:
            return None

        project, version = result

        # Only allow modifications to draft versions
        if version.status != "draft":
            return None

        # Get all overlays of this type
        overlays_result = await self.db.execute(
            select(Overlay).where(
                Overlay.version_id == version.id,
                Overlay.overlay_type == overlay_type.value
            )
        )
        overlays = overlays_result.scalars().all()

        count = len(overlays)
        for overlay in overlays:
            await self.db.delete(overlay)

        await self.db.commit()

        return count
