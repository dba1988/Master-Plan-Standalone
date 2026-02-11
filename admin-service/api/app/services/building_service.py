"""
Building Service

Handles building CRUD operations including views, stacks, units, and overlay mappings.
"""
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.building import Building
from app.models.building_view import BuildingView
from app.models.building_stack import BuildingStack
from app.models.building_unit import BuildingUnit
from app.models.view_overlay_mapping import ViewOverlayMapping
from app.models.project import Project
from app.models.version import ProjectVersion
from app.schemas.building import (
    BuildingCreate,
    BuildingUpdate,
    BuildingViewCreate,
    BuildingViewUpdate,
    StackCreate,
    StackUpdate,
    BuildingUnitCreate,
    BuildingUnitUpdate,
    OverlayMappingCreate,
    BulkStackItem,
    BulkOverlayMappingItem,
    ViewType,
)


class BuildingService:
    """Service for managing buildings and related entities."""

    def __init__(self, db: AsyncSession):
        self.db = db

    # ============================================
    # HELPER METHODS
    # ============================================

    async def get_project_by_slug(self, project_slug: str) -> Optional[Project]:
        """Get project by slug."""
        result = await self.db.execute(
            select(Project).where(
                Project.slug == project_slug,
                Project.is_active == True
            )
        )
        return result.scalar_one_or_none()

    async def has_draft_version(self, project_id: UUID) -> bool:
        """Check if project has a draft version (allows modifications)."""
        result = await self.db.execute(
            select(ProjectVersion).where(
                ProjectVersion.project_id == project_id,
                ProjectVersion.status == "draft"
            ).limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def get_building_by_ref(
        self,
        project_id: UUID,
        ref: str,
    ) -> Optional[Building]:
        """Get building by project and ref."""
        result = await self.db.execute(
            select(Building).where(
                Building.project_id == project_id,
                Building.ref == ref
            )
        )
        return result.scalar_one_or_none()

    # ============================================
    # BUILDING CRUD
    # ============================================

    async def list_buildings(
        self,
        project_slug: str,
    ) -> Optional[Tuple[List[Building], int]]:
        """
        List all buildings for a project.
        Returns None if project not found.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        query = select(Building).where(
            Building.project_id == project.id,
            Building.is_active == True
        ).order_by(Building.sort_order, Building.ref)

        count_result = await self.db.execute(
            select(func.count(Building.id)).where(
                Building.project_id == project.id,
                Building.is_active == True
            )
        )
        total = count_result.scalar_one()

        result = await self.db.execute(query)
        buildings = list(result.scalars().all())

        return buildings, total

    async def get_building(
        self,
        project_slug: str,
        building_id: UUID,
    ) -> Optional[Building]:
        """Get a specific building by ID."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        result = await self.db.execute(
            select(Building).where(
                Building.id == building_id,
                Building.project_id == project.id
            )
        )
        return result.scalar_one_or_none()

    async def create_building(
        self,
        project_slug: str,
        data: BuildingCreate,
    ) -> Optional[Building]:
        """Create a new building."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness
        existing = await self.get_building_by_ref(project.id, data.ref)
        if existing:
            return None

        building = Building(
            project_id=project.id,
            ref=data.ref,
            name=data.name,
            floors_count=data.floors_count,
            floors_start=data.floors_start,
            skip_floors=data.skip_floors or [],
            metadata_=data.metadata or {},
            sort_order=data.sort_order,
        )

        self.db.add(building)
        await self.db.commit()
        await self.db.refresh(building)

        return building

    async def update_building(
        self,
        project_slug: str,
        building_id: UUID,
        data: BuildingUpdate,
    ) -> Optional[Building]:
        """Update an existing building."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness if changing
        if data.ref and data.ref != building.ref:
            existing = await self.get_building_by_ref(project.id, data.ref)
            if existing and existing.id != building.id:
                return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "metadata":
                setattr(building, "metadata_", value)
            else:
                setattr(building, field, value)

        await self.db.commit()
        await self.db.refresh(building)

        return building

    async def delete_building(
        self,
        project_slug: str,
        building_id: UUID,
    ) -> bool:
        """Delete a building (cascades to views, stacks, units)."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return False

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return False

        await self.db.delete(building)
        await self.db.commit()

        return True

    # ============================================
    # BUILDING VIEW CRUD
    # ============================================

    async def list_views(
        self,
        project_slug: str,
        building_id: UUID,
        view_type: Optional[ViewType] = None,
    ) -> Optional[Tuple[List[BuildingView], int]]:
        """List all views for a building."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        query = select(BuildingView).where(
            BuildingView.building_id == building_id,
            BuildingView.is_active == True
        )

        if view_type:
            query = query.where(BuildingView.view_type == view_type.value)

        query = query.order_by(BuildingView.sort_order, BuildingView.ref)

        count_query = select(func.count(BuildingView.id)).where(
            BuildingView.building_id == building_id,
            BuildingView.is_active == True
        )
        if view_type:
            count_query = count_query.where(BuildingView.view_type == view_type.value)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        result = await self.db.execute(query)
        views = list(result.scalars().all())

        return views, total

    async def get_view(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
    ) -> Optional[BuildingView]:
        """Get a specific view by ID."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        result = await self.db.execute(
            select(BuildingView).where(
                BuildingView.id == view_id,
                BuildingView.building_id == building_id
            )
        )
        return result.scalar_one_or_none()

    async def get_view_by_ref(
        self,
        building_id: UUID,
        ref: str,
    ) -> Optional[BuildingView]:
        """Get view by building and ref."""
        result = await self.db.execute(
            select(BuildingView).where(
                BuildingView.building_id == building_id,
                BuildingView.ref == ref
            )
        )
        return result.scalar_one_or_none()

    async def create_view(
        self,
        project_slug: str,
        building_id: UUID,
        data: BuildingViewCreate,
    ) -> Optional[BuildingView]:
        """Create a new building view."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness
        existing = await self.get_view_by_ref(building_id, data.ref)
        if existing:
            return None

        view = BuildingView(
            building_id=building_id,
            view_type=data.view_type.value,
            ref=data.ref,
            label=data.label,
            angle=data.angle,
            floor_number=data.floor_number,
            view_box=data.view_box,
            asset_path=data.asset_path,
            sort_order=data.sort_order,
        )

        self.db.add(view)
        await self.db.commit()
        await self.db.refresh(view)

        return view

    async def update_view(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
        data: BuildingViewUpdate,
    ) -> Optional[BuildingView]:
        """Update an existing view."""
        view = await self.get_view(project_slug, building_id, view_id)
        if not view:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness if changing
        if data.ref and data.ref != view.ref:
            existing = await self.get_view_by_ref(building_id, data.ref)
            if existing and existing.id != view.id:
                return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "view_type" and value is not None:
                setattr(view, field, value.value)
            else:
                setattr(view, field, value)

        await self.db.commit()
        await self.db.refresh(view)

        return view

    async def delete_view(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
    ) -> bool:
        """Delete a view."""
        view = await self.get_view(project_slug, building_id, view_id)
        if not view:
            return False

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return False

        await self.db.delete(view)
        await self.db.commit()

        return True

    # ============================================
    # STACK CRUD
    # ============================================

    async def list_stacks(
        self,
        project_slug: str,
        building_id: UUID,
    ) -> Optional[Tuple[List[BuildingStack], int]]:
        """List all stacks for a building."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        query = select(BuildingStack).where(
            BuildingStack.building_id == building_id
        ).order_by(BuildingStack.sort_order, BuildingStack.ref)

        count_result = await self.db.execute(
            select(func.count(BuildingStack.id)).where(
                BuildingStack.building_id == building_id
            )
        )
        total = count_result.scalar_one()

        result = await self.db.execute(query)
        stacks = list(result.scalars().all())

        return stacks, total

    async def get_stack(
        self,
        project_slug: str,
        building_id: UUID,
        stack_id: UUID,
    ) -> Optional[BuildingStack]:
        """Get a specific stack by ID."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        result = await self.db.execute(
            select(BuildingStack).where(
                BuildingStack.id == stack_id,
                BuildingStack.building_id == building_id
            )
        )
        return result.scalar_one_or_none()

    async def get_stack_by_ref(
        self,
        building_id: UUID,
        ref: str,
    ) -> Optional[BuildingStack]:
        """Get stack by building and ref."""
        result = await self.db.execute(
            select(BuildingStack).where(
                BuildingStack.building_id == building_id,
                BuildingStack.ref == ref
            )
        )
        return result.scalar_one_or_none()

    async def create_stack(
        self,
        project_slug: str,
        building_id: UUID,
        data: StackCreate,
    ) -> Optional[BuildingStack]:
        """Create a new stack."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness
        existing = await self.get_stack_by_ref(building_id, data.ref)
        if existing:
            return None

        stack = BuildingStack(
            building_id=building_id,
            ref=data.ref,
            label=data.label,
            floor_start=data.floor_start,
            floor_end=data.floor_end,
            unit_type=data.unit_type,
            facing=data.facing,
            metadata_=data.metadata or {},
            sort_order=data.sort_order,
        )

        self.db.add(stack)
        await self.db.commit()
        await self.db.refresh(stack)

        return stack

    async def bulk_upsert_stacks(
        self,
        project_slug: str,
        building_id: UUID,
        stacks: List[BulkStackItem],
    ) -> Optional[Tuple[int, int, List[Dict[str, Any]]]]:
        """Bulk upsert stacks."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        created = 0
        updated = 0
        errors = []

        for idx, item in enumerate(stacks):
            try:
                existing = await self.get_stack_by_ref(building_id, item.ref)

                if existing:
                    existing.label = item.label
                    existing.floor_start = item.floor_start
                    existing.floor_end = item.floor_end
                    existing.unit_type = item.unit_type
                    existing.facing = item.facing
                    existing.metadata_ = item.metadata or {}
                    existing.sort_order = item.sort_order
                    updated += 1
                else:
                    stack = BuildingStack(
                        building_id=building_id,
                        ref=item.ref,
                        label=item.label,
                        floor_start=item.floor_start,
                        floor_end=item.floor_end,
                        unit_type=item.unit_type,
                        facing=item.facing,
                        metadata_=item.metadata or {},
                        sort_order=item.sort_order,
                    )
                    self.db.add(stack)
                    created += 1

            except Exception as e:
                errors.append({
                    "index": idx,
                    "ref": item.ref,
                    "error": str(e)
                })

        await self.db.commit()

        return created, updated, errors

    async def delete_stack(
        self,
        project_slug: str,
        building_id: UUID,
        stack_id: UUID,
    ) -> bool:
        """Delete a stack."""
        stack = await self.get_stack(project_slug, building_id, stack_id)
        if not stack:
            return False

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return False

        await self.db.delete(stack)
        await self.db.commit()

        return True

    # ============================================
    # BUILDING UNIT CRUD
    # ============================================

    async def list_units(
        self,
        project_slug: str,
        building_id: UUID,
        floor_number: Optional[int] = None,
        stack_id: Optional[UUID] = None,
    ) -> Optional[Tuple[List[BuildingUnit], int]]:
        """List units for a building with optional filters."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        query = select(BuildingUnit).where(
            BuildingUnit.building_id == building_id
        )
        count_query = select(func.count(BuildingUnit.id)).where(
            BuildingUnit.building_id == building_id
        )

        if floor_number is not None:
            query = query.where(BuildingUnit.floor_number == floor_number)
            count_query = count_query.where(BuildingUnit.floor_number == floor_number)

        if stack_id:
            query = query.where(BuildingUnit.stack_id == stack_id)
            count_query = count_query.where(BuildingUnit.stack_id == stack_id)

        query = query.order_by(BuildingUnit.floor_number, BuildingUnit.unit_number)

        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        result = await self.db.execute(query)
        units = list(result.scalars().all())

        return units, total

    async def get_unit(
        self,
        project_slug: str,
        building_id: UUID,
        unit_id: UUID,
    ) -> Optional[BuildingUnit]:
        """Get a specific unit by ID."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        result = await self.db.execute(
            select(BuildingUnit).where(
                BuildingUnit.id == unit_id,
                BuildingUnit.building_id == building_id
            )
        )
        return result.scalar_one_or_none()

    async def get_unit_by_ref(
        self,
        building_id: UUID,
        ref: str,
    ) -> Optional[BuildingUnit]:
        """Get unit by building and ref."""
        result = await self.db.execute(
            select(BuildingUnit).where(
                BuildingUnit.building_id == building_id,
                BuildingUnit.ref == ref
            )
        )
        return result.scalar_one_or_none()

    async def create_unit(
        self,
        project_slug: str,
        building_id: UUID,
        data: BuildingUnitCreate,
    ) -> Optional[BuildingUnit]:
        """Create a new unit."""
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness
        existing = await self.get_unit_by_ref(building_id, data.ref)
        if existing:
            return None

        unit = BuildingUnit(
            building_id=building_id,
            stack_id=data.stack_id,
            ref=data.ref,
            floor_number=data.floor_number,
            unit_number=data.unit_number,
            unit_type=data.unit_type,
            area_sqm=data.area_sqm,
            area_sqft=data.area_sqft,
            status=data.status.value,
            price=data.price,
            props=data.props or {},
        )

        self.db.add(unit)
        await self.db.commit()
        await self.db.refresh(unit)

        return unit

    async def update_unit(
        self,
        project_slug: str,
        building_id: UUID,
        unit_id: UUID,
        data: BuildingUnitUpdate,
    ) -> Optional[BuildingUnit]:
        """Update an existing unit."""
        unit = await self.get_unit(project_slug, building_id, unit_id)
        if not unit:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Check ref uniqueness if changing
        if data.ref and data.ref != unit.ref:
            existing = await self.get_unit_by_ref(building_id, data.ref)
            if existing and existing.id != unit.id:
                return None

        update_data = data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            if field == "status" and value is not None:
                setattr(unit, field, value.value)
            else:
                setattr(unit, field, value)

        await self.db.commit()
        await self.db.refresh(unit)

        return unit

    async def generate_units_from_stacks(
        self,
        project_slug: str,
        building_id: UUID,
        stack_ids: Optional[List[UUID]] = None,
        skip_floors: Optional[List[int]] = None,
    ) -> Optional[Tuple[int, int]]:
        """
        Auto-generate units from stacks.

        For each stack, creates a unit for each floor in the stack's range,
        skipping specified floors and the building's skip_floors.

        Returns (created, skipped) counts.
        """
        building = await self.get_building(project_slug, building_id)
        if not building:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        # Get stacks to process
        query = select(BuildingStack).where(
            BuildingStack.building_id == building_id
        )
        if stack_ids:
            query = query.where(BuildingStack.id.in_(stack_ids))

        result = await self.db.execute(query)
        stacks = list(result.scalars().all())

        # Combine skip floors
        all_skip_floors = set(building.skip_floors or [])
        if skip_floors:
            all_skip_floors.update(skip_floors)

        created = 0
        skipped = 0

        for stack in stacks:
            for floor in range(stack.floor_start, stack.floor_end + 1):
                if floor in all_skip_floors:
                    skipped += 1
                    continue

                # Generate unit ref: BUILDING-FLOOR-STACK
                # e.g., "A-15-01" for Tower A, Floor 15, Stack 01
                building_prefix = building.ref.replace("tower-", "").replace("building-", "").upper()
                unit_ref = f"{building_prefix}-{floor:02d}-{stack.ref}"

                # Check if already exists
                existing = await self.get_unit_by_ref(building_id, unit_ref)
                if existing:
                    skipped += 1
                    continue

                unit = BuildingUnit(
                    building_id=building_id,
                    stack_id=stack.id,
                    ref=unit_ref,
                    floor_number=floor,
                    unit_number=stack.ref,
                    unit_type=stack.unit_type,
                    status="available",
                    props={},
                )

                self.db.add(unit)
                created += 1

        await self.db.commit()

        return created, skipped

    async def delete_unit(
        self,
        project_slug: str,
        building_id: UUID,
        unit_id: UUID,
    ) -> bool:
        """Delete a unit."""
        unit = await self.get_unit(project_slug, building_id, unit_id)
        if not unit:
            return False

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return False

        await self.db.delete(unit)
        await self.db.commit()

        return True

    # ============================================
    # VIEW OVERLAY MAPPING CRUD
    # ============================================

    async def list_overlay_mappings(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
    ) -> Optional[Tuple[List[ViewOverlayMapping], int]]:
        """List overlay mappings for a view."""
        view = await self.get_view(project_slug, building_id, view_id)
        if not view:
            return None

        query = select(ViewOverlayMapping).where(
            ViewOverlayMapping.view_id == view_id
        ).order_by(ViewOverlayMapping.sort_order)

        count_result = await self.db.execute(
            select(func.count(ViewOverlayMapping.id)).where(
                ViewOverlayMapping.view_id == view_id
            )
        )
        total = count_result.scalar_one()

        result = await self.db.execute(query)
        mappings = list(result.scalars().all())

        return mappings, total

    async def create_overlay_mapping(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
        data: OverlayMappingCreate,
    ) -> Optional[ViewOverlayMapping]:
        """Create a new overlay mapping."""
        view = await self.get_view(project_slug, building_id, view_id)
        if not view:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        mapping = ViewOverlayMapping(
            view_id=view_id,
            target_type=data.target_type,
            stack_id=data.stack_id,
            unit_id=data.unit_id,
            geometry=data.geometry,
            label_position=data.label_position,
            sort_order=data.sort_order,
        )

        self.db.add(mapping)
        await self.db.commit()
        await self.db.refresh(mapping)

        return mapping

    async def bulk_upsert_overlay_mappings(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
        mappings: List[BulkOverlayMappingItem],
    ) -> Optional[Tuple[int, int, List[Dict[str, Any]]]]:
        """
        Bulk upsert overlay mappings.

        Resolves target_ref to stack_id or unit_id based on target_type.
        """
        view = await self.get_view(project_slug, building_id, view_id)
        if not view:
            return None

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return None

        created = 0
        updated = 0
        errors = []

        for idx, item in enumerate(mappings):
            try:
                # Resolve target ref to ID
                stack_id = None
                unit_id = None

                if item.target_type == "stack":
                    stack = await self.get_stack_by_ref(building_id, item.target_ref)
                    if not stack:
                        errors.append({
                            "index": idx,
                            "ref": item.target_ref,
                            "error": f"Stack '{item.target_ref}' not found"
                        })
                        continue
                    stack_id = stack.id
                else:  # unit
                    unit = await self.get_unit_by_ref(building_id, item.target_ref)
                    if not unit:
                        errors.append({
                            "index": idx,
                            "ref": item.target_ref,
                            "error": f"Unit '{item.target_ref}' not found"
                        })
                        continue
                    unit_id = unit.id

                # Check for existing mapping
                existing_query = select(ViewOverlayMapping).where(
                    ViewOverlayMapping.view_id == view_id,
                    ViewOverlayMapping.target_type == item.target_type
                )
                if stack_id:
                    existing_query = existing_query.where(
                        ViewOverlayMapping.stack_id == stack_id
                    )
                if unit_id:
                    existing_query = existing_query.where(
                        ViewOverlayMapping.unit_id == unit_id
                    )

                existing_result = await self.db.execute(existing_query)
                existing = existing_result.scalar_one_or_none()

                if existing:
                    existing.geometry = item.geometry
                    existing.label_position = item.label_position
                    existing.sort_order = item.sort_order
                    updated += 1
                else:
                    mapping = ViewOverlayMapping(
                        view_id=view_id,
                        target_type=item.target_type,
                        stack_id=stack_id,
                        unit_id=unit_id,
                        geometry=item.geometry,
                        label_position=item.label_position,
                        sort_order=item.sort_order,
                    )
                    self.db.add(mapping)
                    created += 1

            except Exception as e:
                errors.append({
                    "index": idx,
                    "ref": item.target_ref,
                    "error": str(e)
                })

        await self.db.commit()

        return created, updated, errors

    async def delete_overlay_mapping(
        self,
        project_slug: str,
        building_id: UUID,
        view_id: UUID,
        mapping_id: UUID,
    ) -> bool:
        """Delete an overlay mapping."""
        view = await self.get_view(project_slug, building_id, view_id)
        if not view:
            return False

        project = await self.get_project_by_slug(project_slug)
        if not await self.has_draft_version(project.id):
            return False

        result = await self.db.execute(
            select(ViewOverlayMapping).where(
                ViewOverlayMapping.id == mapping_id,
                ViewOverlayMapping.view_id == view_id
            )
        )
        mapping = result.scalar_one_or_none()

        if not mapping:
            return False

        await self.db.delete(mapping)
        await self.db.commit()

        return True
