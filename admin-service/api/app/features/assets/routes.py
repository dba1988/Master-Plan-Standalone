"""
Asset upload endpoints.

Upload flow:
1. Client requests signed upload URL via POST .../upload-url
2. Client uploads directly to storage using signed URL
3. Client confirms upload via POST .../confirm
4. API creates asset record in database
"""
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.lib.database import get_db
from app.lib.deps import get_current_user, require_editor
from app.models.user import User
from app.schemas.asset import (
    AssetDownloadResponse,
    AssetListResponse,
    AssetResponse,
    AssetType,
    UploadConfirmRequest,
    UploadUrlRequest,
    UploadUrlResponse,
)
from app.services.asset_service import AssetService

router = APIRouter(tags=["Assets"])


@router.post(
    "/projects/{slug}/versions/{version_number}/assets/upload-url",
    response_model=UploadUrlResponse,
)
async def request_upload_url(
    slug: str,
    version_number: int,
    data: UploadUrlRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Request a signed URL for direct upload to storage.

    The client should use this URL to upload the file directly,
    then call the confirm endpoint.
    """
    service = AssetService(db)
    result = await service.generate_upload_url(
        project_slug=slug,
        version_number=version_number,
        filename=data.filename,
        asset_type=data.asset_type,
        content_type=data.content_type,
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or version not found, or version is not a draft"
        )

    return UploadUrlResponse(
        upload_url=result["upload_url"],
        storage_path=result["storage_path"],
        expires_in_seconds=result["expires_in_seconds"],
    )


@router.post(
    "/projects/{slug}/versions/{version_number}/assets/confirm",
    response_model=AssetResponse,
    status_code=status.HTTP_201_CREATED,
)
async def confirm_upload(
    slug: str,
    version_number: int,
    data: UploadConfirmRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Confirm upload and create asset record.

    Call this after successfully uploading the file using the signed URL.
    The API will verify the file exists and create a database record.
    """
    service = AssetService(db)
    asset = await service.confirm_upload(
        project_slug=slug,
        version_number=version_number,
        data=data,
        user_id=current_user.id,
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Upload confirmation failed. Project/version not found, version is not a draft, or file does not exist in storage."
        )

    return AssetResponse.model_validate(asset)


@router.get(
    "/projects/{slug}/versions/{version_number}/assets",
    response_model=AssetListResponse,
)
async def list_assets(
    slug: str,
    version_number: int,
    asset_type: Optional[AssetType] = Query(None, description="Filter by asset type"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    List all assets for a project version.

    Optionally filter by asset type.
    """
    service = AssetService(db)
    result = await service.list_assets(
        project_slug=slug,
        version_number=version_number,
        asset_type=asset_type,
    )

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project or version not found"
        )

    assets, total = result
    return AssetListResponse(
        assets=[AssetResponse.model_validate(a) for a in assets],
        total=total,
    )


@router.get(
    "/projects/{slug}/versions/{version_number}/assets/{asset_id}",
    response_model=AssetResponse,
)
async def get_asset(
    slug: str,
    version_number: int,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a specific asset by ID.
    """
    service = AssetService(db)
    asset = await service.get_asset(
        project_slug=slug,
        version_number=version_number,
        asset_id=asset_id,
    )

    if not asset:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    return AssetResponse.model_validate(asset)


@router.get(
    "/projects/{slug}/versions/{version_number}/assets/{asset_id}/download",
    response_model=AssetDownloadResponse,
)
async def get_download_url(
    slug: str,
    version_number: int,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get a signed download URL for an asset.

    The URL expires after 5 minutes.
    """
    service = AssetService(db)
    download_url = await service.get_download_url(
        project_slug=slug,
        version_number=version_number,
        asset_id=asset_id,
    )

    if not download_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found"
        )

    return AssetDownloadResponse(
        download_url=download_url,
        expires_in_seconds=300,
    )


@router.delete(
    "/projects/{slug}/versions/{version_number}/assets/{asset_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_asset(
    slug: str,
    version_number: int,
    asset_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_editor),
):
    """
    Delete an asset from both database and storage.

    Only works for draft versions.
    """
    service = AssetService(db)
    deleted = await service.delete_asset(
        project_slug=slug,
        version_number=version_number,
        asset_id=asset_id,
    )

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Asset not found or version is not a draft"
        )
