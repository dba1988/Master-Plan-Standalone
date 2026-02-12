"""
Building Release Service

Generates building manifests and overlay files for release publishing.
"""
import json
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.building import Building
from app.models.building_view import BuildingView
from app.models.building_stack import BuildingStack
from app.models.building_unit import BuildingUnit
from app.models.view_overlay_mapping import ViewOverlayMapping
from app.models.project import Project
from app.schemas.building_release import (
    BuildingManifest,
    BuildingManifestInfo,
    BuildingViews,
    BuildingConfig,
    BuildingStackSummary,
    ElevationView,
    RotationView,
    RotationConfig,
    FloorPlanConfig,
    ViewOverlayFile,
    StackOverlay,
    FloorPlanOverlayFile,
    UnitOverlay,
)


class BuildingReleaseService:
    """Service for generating building release artifacts."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_project_buildings(
        self,
        project_slug: str,
    ) -> List[Building]:
        """Get all active buildings for a project."""
        result = await self.db.execute(
            select(Project).where(
                Project.slug == project_slug,
                Project.is_active == True
            )
        )
        project = result.scalar_one_or_none()
        if not project:
            return []

        buildings_result = await self.db.execute(
            select(Building).where(
                Building.project_id == project.id,
                Building.is_active == True
            ).order_by(Building.sort_order, Building.ref)
        )
        return list(buildings_result.scalars().all())

    async def build_building_manifest_info(
        self,
        building: Building,
    ) -> BuildingManifestInfo:
        """Build manifest info for project-level manifest."""
        return BuildingManifestInfo(
            ref=building.ref,
            name=building.name,
            manifest_path=f"buildings/{building.ref}.json",
        )

    async def build_building_manifest(
        self,
        building: Building,
        release_path: str,
    ) -> BuildingManifest:
        """
        Build complete building manifest.

        Args:
            building: Building model instance
            release_path: Base path for release artifacts

        Returns:
            BuildingManifest ready for serialization
        """
        # Get all views for this building
        views_result = await self.db.execute(
            select(BuildingView).where(
                BuildingView.building_id == building.id,
                BuildingView.is_active == True
            ).order_by(BuildingView.sort_order)
        )
        views = list(views_result.scalars().all())

        # Get all stacks
        stacks_result = await self.db.execute(
            select(BuildingStack).where(
                BuildingStack.building_id == building.id
            ).order_by(BuildingStack.sort_order)
        )
        stacks = list(stacks_result.scalars().all())

        # Build views section
        elevations = []
        rotations = []
        floor_plans_available = []
        rotation_angles = []

        for view in views:
            if view.view_type == "elevation":
                elevations.append(ElevationView(
                    ref=view.ref,
                    label=view.label,
                    tiles_url=f"tiles/buildings/{building.ref}/{view.ref}",
                    view_box=view.view_box or "0 0 2048 4096",
                    overlays_url=f"overlays/{building.ref}/{view.ref}-stacks.json",
                ))
            elif view.view_type == "rotation":
                rotations.append(RotationView(
                    angle=view.angle or 0,
                    tiles_url=f"tiles/buildings/{building.ref}/{view.ref}",
                    view_box=view.view_box,
                    overlays_url=f"overlays/{building.ref}/{view.ref}-stacks.json",
                ))
                rotation_angles.append(view.angle or 0)
            elif view.view_type == "floor_plan":
                floor_plans_available.append(view.floor_number)

        # Calculate rotation config if we have rotations
        rotation_config = None
        if rotation_angles:
            rotation_angles.sort()
            angle_step = 15  # Default
            if len(rotation_angles) > 1:
                # Calculate step from consecutive angles
                steps = [rotation_angles[i+1] - rotation_angles[i]
                         for i in range(len(rotation_angles)-1)]
                if steps:
                    angle_step = min(steps)

            rotation_config = RotationConfig(
                total_angles=len(rotation_angles),
                angle_step=angle_step,
                default_angle=rotation_angles[0] if rotation_angles else 0,
            )

        # Build stacks summary
        stack_summaries = []
        for stack in stacks:
            stack_summaries.append(BuildingStackSummary(
                ref=stack.ref,
                label=stack.label,
                unit_type=stack.unit_type,
                facing=stack.facing,
                floors=[stack.floor_start, stack.floor_end],
            ))

        # Determine default view
        default_view = "front"
        if elevations:
            default_view = elevations[0].ref

        return BuildingManifest(
            version=1,
            building_ref=building.ref,
            name=building.name,
            floors_count=building.floors_count,
            floors_start=building.floors_start,
            skip_floors=building.skip_floors or [],
            views=BuildingViews(
                elevations=elevations,
                rotations=rotations,
                rotation_config=rotation_config,
            ),
            floor_plans=FloorPlanConfig(
                available_floors=sorted(floor_plans_available),
            ),
            stacks=stack_summaries,
            config=BuildingConfig(
                default_view=default_view,
            ),
        )

    async def build_view_overlay_file(
        self,
        view: BuildingView,
        building: Building,
    ) -> ViewOverlayFile:
        """
        Build overlay file for a specific view.

        Contains all stack overlays with geometry and summary stats.
        """
        # Get overlay mappings for this view
        mappings_result = await self.db.execute(
            select(ViewOverlayMapping).where(
                ViewOverlayMapping.view_id == view.id,
                ViewOverlayMapping.target_type == "stack"
            ).order_by(ViewOverlayMapping.sort_order)
        )
        mappings = list(mappings_result.scalars().all())

        stack_overlays = []
        for mapping in mappings:
            if not mapping.stack_id:
                continue

            # Get stack info
            stack_result = await self.db.execute(
                select(BuildingStack).where(BuildingStack.id == mapping.stack_id)
            )
            stack = stack_result.scalar_one_or_none()
            if not stack:
                continue

            # Count units by status
            status_counts = await self._count_units_by_status(stack.id, building.id)

            stack_overlays.append(StackOverlay(
                ref=stack.ref,
                geometry=mapping.geometry,
                label_position=mapping.label_position,
                unit_type=stack.unit_type,
                floors_visible=[stack.floor_start, stack.floor_end],
                units_count=status_counts.get("total", 0),
                available_count=status_counts.get("available", 0),
                reserved_count=status_counts.get("reserved", 0),
                sold_count=status_counts.get("sold", 0),
            ))

        return ViewOverlayFile(
            view_ref=view.ref,
            view_box=view.view_box or "0 0 2048 4096",
            stacks=stack_overlays,
        )

    async def build_floor_overlay_file(
        self,
        view: BuildingView,
        building: Building,
    ) -> FloorPlanOverlayFile:
        """
        Build overlay file for a floor plan view.

        Contains all unit overlays for the floor.
        """
        # Get overlay mappings for this view (units)
        mappings_result = await self.db.execute(
            select(ViewOverlayMapping).where(
                ViewOverlayMapping.view_id == view.id,
                ViewOverlayMapping.target_type == "unit"
            ).order_by(ViewOverlayMapping.sort_order)
        )
        mappings = list(mappings_result.scalars().all())

        unit_overlays = []
        for mapping in mappings:
            if not mapping.unit_id:
                continue

            # Get unit info
            unit_result = await self.db.execute(
                select(BuildingUnit).where(BuildingUnit.id == mapping.unit_id)
            )
            unit = unit_result.scalar_one_or_none()
            if not unit:
                continue

            # Get stack ref if available
            stack_ref = None
            if unit.stack_id:
                stack_result = await self.db.execute(
                    select(BuildingStack.ref).where(BuildingStack.id == unit.stack_id)
                )
                stack_ref = stack_result.scalar_one_or_none()

            unit_overlays.append(UnitOverlay(
                ref=unit.ref,
                unit_number=unit.unit_number,
                geometry=mapping.geometry,
                label_position=mapping.label_position,
                unit_type=unit.unit_type,
                status=unit.status,
                stack_ref=stack_ref,
            ))

        return FloorPlanOverlayFile(
            floor_number=view.floor_number or 0,
            view_box=view.view_box or "0 0 4096 2048",
            units=unit_overlays,
        )

    async def _count_units_by_status(
        self,
        stack_id: UUID,
        building_id: UUID,
    ) -> Dict[str, int]:
        """Count units by status for a stack."""
        result = await self.db.execute(
            select(
                BuildingUnit.status,
                func.count(BuildingUnit.id)
            ).where(
                BuildingUnit.stack_id == stack_id,
                BuildingUnit.building_id == building_id
            ).group_by(BuildingUnit.status)
        )

        counts = {"total": 0, "available": 0, "reserved": 0, "sold": 0, "hidden": 0}
        for row in result.all():
            status, count = row
            counts[status] = count
            counts["total"] += count

        return counts

    async def get_all_building_views(
        self,
        building_id: UUID,
    ) -> List[BuildingView]:
        """Get all views for a building."""
        result = await self.db.execute(
            select(BuildingView).where(
                BuildingView.building_id == building_id,
                BuildingView.is_active == True
            ).order_by(BuildingView.sort_order)
        )
        return list(result.scalars().all())

    async def generate_building_artifacts(
        self,
        building: Building,
        release_path: str,
    ) -> Dict[str, Any]:
        """
        Generate all artifacts for a building.

        Returns dict mapping file paths to content.
        """
        artifacts = {}

        # 1. Building manifest
        manifest = await self.build_building_manifest(building, release_path)
        artifacts[f"buildings/{building.ref}.json"] = manifest.model_dump_json(indent=2)

        # 2. View overlay files
        views = await self.get_all_building_views(building.id)
        for view in views:
            if view.view_type in ("elevation", "rotation"):
                overlay_file = await self.build_view_overlay_file(view, building)
                path = f"overlays/{building.ref}/{view.ref}-stacks.json"
                artifacts[path] = overlay_file.model_dump_json(indent=2)
            elif view.view_type == "floor_plan":
                floor_file = await self.build_floor_overlay_file(view, building)
                path = f"overlays/{building.ref}/floor-{view.floor_number}.json"
                artifacts[path] = floor_file.model_dump_json(indent=2)

        return artifacts
