"""
Asset Service

Handles asset upload workflow:
1. Generate signed upload URL
2. Confirm upload and create DB record
3. List/delete assets

Assets belong to projects (not versions) - versions are just release tags.
"""
import mimetypes
from typing import Dict, List, Optional, Tuple
from uuid import UUID

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.asset import Asset
from app.models.overlay import Overlay
from app.models.project import Project
from app.models.version import ProjectVersion
from app.schemas.asset import AssetType, UploadConfirmRequest
from app.services.storage_service import StorageService, storage_service


class AssetService:
    """Service for managing asset uploads and records."""

    def __init__(self, db: AsyncSession, storage: StorageService = None):
        self.db = db
        self.storage = storage or storage_service

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
            )
        )
        return result.scalar_one_or_none() is not None

    async def generate_upload_url(
        self,
        project_slug: str,
        filename: str,
        asset_type: AssetType,
        content_type: str,
        expires_in: int = 300,
    ) -> Optional[Dict]:
        """
        Generate signed URL for direct upload to storage.

        Returns None if project not found or no draft version exists.
        Returns dict with upload_url, storage_path, expires_in_seconds.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        # Only allow uploads if there's a draft version
        if not await self.has_draft_version(project.id):
            return None

        # Generate upload URL via storage service
        upload_data = await self.storage.create_upload_url(
            project_slug=project_slug,
            asset_type=asset_type.value,
            filename=filename,
            content_type=content_type,
            expires_in=expires_in,
        )

        return {
            "upload_url": upload_data["upload_url"],
            "storage_path": upload_data["storage_path"],
            "expires_in_seconds": upload_data["expires_in"],
        }

    async def confirm_upload(
        self,
        project_slug: str,
        data: UploadConfirmRequest,
        user_id: UUID,
    ) -> Optional[Asset]:
        """
        Confirm upload completed and create/update asset record.

        Returns None if project not found or file doesn't exist.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        # Only allow uploads if there's a draft version
        if not await self.has_draft_version(project.id):
            return None

        # Verify file exists in storage
        exists = await self.storage.file_exists(data.storage_path)
        if not exists:
            return None

        # Detect MIME type from filename if not provided in metadata
        mime_type = mimetypes.guess_type(data.filename)[0] or "application/octet-stream"

        # Extract image dimensions from metadata if provided
        width = None
        height = None
        if data.metadata:
            width = data.metadata.get("width")
            height = data.metadata.get("height")

        # Check if asset with same (project, level, asset_type) exists
        # Each level should only have one base_map and one overlay_svg
        existing_result = await self.db.execute(
            select(Asset).where(
                Asset.project_id == project.id,
                Asset.level == data.level,
                Asset.asset_type == data.asset_type.value
            )
        )
        existing_asset = existing_result.scalar_one_or_none()

        if existing_asset:
            # Delete old asset from storage
            try:
                await self.storage.delete_asset(existing_asset.storage_path)
            except Exception:
                pass  # Ignore storage deletion errors

            # Update existing asset record with new file
            existing_asset.filename = data.filename
            existing_asset.original_filename = data.filename
            existing_asset.file_size = data.file_size
            existing_asset.mime_type = mime_type
            existing_asset.storage_path = data.storage_path
            existing_asset.width = width
            existing_asset.height = height
            existing_asset.processing_status = "completed"

            await self.db.commit()
            await self.db.refresh(existing_asset)
            return existing_asset
        else:
            # Create new asset record
            asset = Asset(
                project_id=project.id,
                asset_type=data.asset_type.value,
                level=data.level,
                filename=data.filename,
                original_filename=data.filename,
                mime_type=mime_type,
                file_size=data.file_size,
                storage_path=data.storage_path,
                width=width,
                height=height,
                processing_status="completed",
            )

            self.db.add(asset)
            await self.db.commit()
            await self.db.refresh(asset)

            return asset

    async def list_assets(
        self,
        project_slug: str,
        asset_type: Optional[AssetType] = None,
        level: Optional[str] = None,
    ) -> Optional[Tuple[List[Asset], int]]:
        """
        List assets for a project.

        Returns None if project not found.
        Returns tuple of (assets, total_count).
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        # Build query
        query = select(Asset).where(Asset.project_id == project.id)
        count_query = select(func.count(Asset.id)).where(Asset.project_id == project.id)

        if asset_type:
            query = query.where(Asset.asset_type == asset_type.value)
            count_query = count_query.where(Asset.asset_type == asset_type.value)

        if level:
            query = query.where(Asset.level == level)
            count_query = count_query.where(Asset.level == level)

        # Get count
        count_result = await self.db.execute(count_query)
        total = count_result.scalar_one()

        # Get assets
        query = query.order_by(Asset.created_at.desc())
        assets_result = await self.db.execute(query)
        assets = assets_result.scalars().all()

        return list(assets), total

    async def get_asset(
        self,
        project_slug: str,
        asset_id: UUID,
    ) -> Optional[Asset]:
        """Get a specific asset by ID."""
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return None

        asset_result = await self.db.execute(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.project_id == project.id
            )
        )
        return asset_result.scalar_one_or_none()

    async def delete_asset(
        self,
        project_slug: str,
        asset_id: UUID,
    ) -> bool:
        """
        Delete asset from database and storage.

        Returns True if deleted, False if not found or no draft version.
        """
        project = await self.get_project_by_slug(project_slug)
        if not project:
            return False

        # Only allow deletion if there's a draft version
        if not await self.has_draft_version(project.id):
            return False

        # Get asset
        asset_result = await self.db.execute(
            select(Asset).where(
                Asset.id == asset_id,
                Asset.project_id == project.id
            )
        )
        asset = asset_result.scalar_one_or_none()

        if not asset:
            return False

        # Delete from storage
        try:
            await self.storage.delete_asset(asset.storage_path)
        except Exception:
            # Log error but continue with DB deletion
            pass

        # If this is an overlay_svg, delete associated overlays by source_level
        if asset.asset_type == "overlay_svg" and asset.level:
            await self.db.execute(
                delete(Overlay).where(
                    Overlay.project_id == project.id,
                    Overlay.source_level == asset.level
                )
            )

        # Delete from database
        await self.db.delete(asset)
        await self.db.commit()

        return True

    async def get_download_url(
        self,
        project_slug: str,
        asset_id: UUID,
        expires_in: int = 300,
    ) -> Optional[str]:
        """Get download URL for an asset."""
        asset = await self.get_asset(project_slug, asset_id)
        if not asset:
            return None

        return await self.storage.get_download_url(
            storage_path=asset.storage_path,
            public=False,
            expires_in=expires_in,
        )

    async def read_asset(self, asset: Asset) -> bytes:
        """Read asset content from storage."""
        return await self.storage.read_file(asset.storage_path)
