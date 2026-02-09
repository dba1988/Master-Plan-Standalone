"""
Storage Service

High-level storage operations with project/asset-aware paths.
Wraps the R2 adapter with business logic for Master Plan assets.
"""
import uuid
from typing import Any, Dict, List, Optional

from app.infra.r2_storage import r2_storage
from app.lib.config import settings


class StorageService:
    """
    Project-aware storage service.

    Path conventions:
    - Uploads: mp/{slug}/uploads/{asset_type}/{filename}
    - Releases: mp/{slug}/releases/{release_id}/{filename}
    - Tiles: mp/{slug}/releases/{release_id}/tiles/{z}/{x}_{y}.png
    """

    def __init__(self):
        self.storage = r2_storage
        self.base_prefix = "mp"

    # --- Path Generation ---

    def get_upload_path(
        self,
        project_slug: str,
        asset_type: str,
        filename: str,
    ) -> str:
        """Generate storage path for uploads."""
        return f"{self.base_prefix}/{project_slug}/uploads/{asset_type}/{filename}"

    def get_release_path(
        self,
        project_slug: str,
        release_id: str,
        filename: str,
    ) -> str:
        """Generate storage path for release assets."""
        return f"{self.base_prefix}/{project_slug}/releases/{release_id}/{filename}"

    def get_tile_path(
        self,
        project_slug: str,
        release_id: str,
        z: int,
        x: int,
        y: int,
        extension: str = "png",
    ) -> str:
        """Generate storage path for tile images."""
        return f"{self.base_prefix}/{project_slug}/releases/{release_id}/tiles/{z}/{x}_{y}.{extension}"

    # --- Upload Operations ---

    async def create_upload_url(
        self,
        project_slug: str,
        asset_type: str,
        filename: str,
        content_type: str,
        expires_in: int = 300,
    ) -> Dict[str, Any]:
        """
        Generate presigned URL for client-side upload.

        Returns:
            {
                'upload_url': presigned URL for PUT request,
                'storage_path': where the file will be stored,
                'expires_in': seconds until URL expires
            }
        """
        # Generate unique filename to avoid collisions
        ext = filename.rsplit('.', 1)[-1] if '.' in filename else ''
        unique_filename = f"{uuid.uuid4().hex[:12]}_{filename}"

        storage_path = self.get_upload_path(project_slug, asset_type, unique_filename)

        upload_url = await self.storage.get_presigned_upload_url(
            key=storage_path,
            content_type=content_type,
            expires_in=expires_in,
        )

        return {
            'upload_url': upload_url,
            'storage_path': storage_path,
            'expires_in': expires_in,
        }

    async def confirm_upload(self, storage_path: str) -> Dict[str, Any]:
        """
        Verify upload completed and get file metadata.

        Returns:
            {
                'size': file size in bytes,
                'content_type': MIME type,
                'etag': file hash
            }
        """
        return await self.storage.get_file_metadata(storage_path)

    async def upload_file(
        self,
        project_slug: str,
        asset_type: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> Dict[str, Any]:
        """
        Upload file directly (for server-side uploads).

        Returns:
            {
                'storage_path': where the file is stored,
                'size': file size,
                'content_type': MIME type
            }
        """
        storage_path = self.get_upload_path(project_slug, asset_type, filename)

        result = await self.storage.upload_file(
            key=storage_path,
            body=content,
            content_type=content_type,
        )

        return {
            'storage_path': storage_path,
            'size': result['size'],
            'content_type': content_type,
        }

    # --- Download Operations ---

    async def get_download_url(
        self,
        storage_path: str,
        public: bool = False,
        expires_in: int = 300,
    ) -> str:
        """
        Get download URL for a file.

        Args:
            storage_path: Full storage path
            public: If True, returns CDN URL (for viewer access)
                   If False, returns presigned URL (for admin access)
            expires_in: URL expiry for presigned URLs

        Returns:
            Download URL
        """
        if public and settings.use_cdn:
            return self.storage.get_public_url(storage_path)

        return await self.storage.get_presigned_download_url(
            key=storage_path,
            expires_in=expires_in,
        )

    async def read_file(self, storage_path: str) -> bytes:
        """Download and return file content."""
        return await self.storage.download_file(storage_path)

    # --- File Management ---

    async def delete_asset(self, storage_path: str) -> bool:
        """Delete file from storage."""
        return await self.storage.delete_file(storage_path)

    async def file_exists(self, storage_path: str) -> bool:
        """Check if file exists."""
        return await self.storage.file_exists(storage_path)

    async def list_uploads(
        self,
        project_slug: str,
        asset_type: Optional[str] = None,
    ) -> List[str]:
        """List uploaded files for a project."""
        if asset_type:
            prefix = f"{self.base_prefix}/{project_slug}/uploads/{asset_type}/"
        else:
            prefix = f"{self.base_prefix}/{project_slug}/uploads/"

        return await self.storage.list_files(prefix)

    async def list_uploads_with_metadata(
        self,
        project_slug: str,
        asset_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """List uploaded files with metadata."""
        if asset_type:
            prefix = f"{self.base_prefix}/{project_slug}/uploads/{asset_type}/"
        else:
            prefix = f"{self.base_prefix}/{project_slug}/uploads/"

        return await self.storage.list_files_with_metadata(prefix)

    # --- Release Operations ---

    async def copy_to_release(
        self,
        source_path: str,
        project_slug: str,
        release_id: str,
        dest_filename: str,
    ) -> str:
        """
        Copy an upload to the immutable release folder.

        Returns:
            New storage path in release folder
        """
        dest_path = self.get_release_path(project_slug, release_id, dest_filename)

        await self.storage.copy_file(source_path, dest_path)

        return dest_path

    async def upload_release_file(
        self,
        project_slug: str,
        release_id: str,
        filename: str,
        content: bytes,
        content_type: str,
    ) -> str:
        """
        Upload file directly to release folder.

        Returns:
            Storage path
        """
        storage_path = self.get_release_path(project_slug, release_id, filename)

        await self.storage.upload_file(
            key=storage_path,
            body=content,
            content_type=content_type,
        )

        return storage_path

    async def upload_tile(
        self,
        project_slug: str,
        release_id: str,
        z: int,
        x: int,
        y: int,
        content: bytes,
        content_type: str = "image/png",
    ) -> str:
        """
        Upload tile image to release folder.

        Returns:
            Storage path
        """
        extension = "png" if "png" in content_type else "jpg"
        storage_path = self.get_tile_path(project_slug, release_id, z, x, y, extension)

        await self.storage.upload_file(
            key=storage_path,
            body=content,
            content_type=content_type,
        )

        return storage_path

    async def list_release_files(
        self,
        project_slug: str,
        release_id: str,
    ) -> List[str]:
        """List all files in a release."""
        prefix = f"{self.base_prefix}/{project_slug}/releases/{release_id}/"
        return await self.storage.list_files(prefix)


# Singleton instance
storage_service = StorageService()


async def get_storage() -> StorageService:
    """FastAPI dependency for storage service."""
    return storage_service
