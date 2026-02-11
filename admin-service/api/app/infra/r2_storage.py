"""
Cloudflare R2 Storage Adapter

Provides low-level S3-compatible storage operations for Cloudflare R2.
"""
import hashlib
import hmac
import time
from typing import Any, Dict, List, Optional

import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

from app.lib.config import settings


def get_s3_client():
    """Initialize S3-compatible client for Cloudflare R2."""
    return boto3.client(
        's3',
        endpoint_url=settings.r2_endpoint,
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name=settings.r2_region,
        config=Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )
    )


class R2StorageAdapter:
    """
    Low-level R2/S3 storage adapter.

    Provides:
    - File upload/download
    - Presigned URLs for client-side uploads
    - File metadata and existence checks
    - File copy and delete operations
    - Listing files by prefix
    """

    def __init__(self):
        self.client = get_s3_client()
        self.bucket = settings.r2_bucket
        self.cdn_base = settings.cdn_base_url.rstrip('/') if settings.cdn_base_url else None
        self.hmac_secret = settings.cdn_hmac_secret

    def _ensure_bucket_exists(self) -> None:
        """Verify bucket exists. Buckets should be pre-created via setup-r2.sh."""
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code in ('404', 'NoSuchBucket'):
                raise Exception(
                    f"Bucket '{self.bucket}' does not exist. "
                    "Run scripts/setup-r2.sh to create R2 buckets."
                )
            else:
                raise

    async def upload_file(
        self,
        key: str,
        body: bytes,
        content_type: str,
        metadata: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Upload file to storage."""
        self._ensure_bucket_exists()

        try:
            params = {
                'Bucket': self.bucket,
                'Key': key,
                'Body': body,
                'ContentType': content_type,
            }
            if metadata:
                params['Metadata'] = metadata

            self.client.put_object(**params)

            return {
                'key': key,
                'size': len(body),
                'content_type': content_type,
            }
        except ClientError as e:
            raise Exception(f"Upload failed: {e}")

    async def download_file(self, key: str) -> bytes:
        """Download file content."""
        try:
            response = self.client.get_object(
                Bucket=self.bucket,
                Key=key,
            )
            return response['Body'].read()
        except ClientError as e:
            if e.response['Error']['Code'] == 'NoSuchKey':
                raise FileNotFoundError(f"File not found: {key}")
            raise Exception(f"Download failed: {e}")

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 300,
    ) -> str:
        """Generate presigned URL for client-side upload."""
        self._ensure_bucket_exists()

        try:
            url = self.client.generate_presigned_url(
                'put_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key,
                    'ContentType': content_type,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate upload URL: {e}")

    async def get_presigned_download_url(
        self,
        key: str,
        expires_in: int = 300,
    ) -> str:
        """Generate presigned URL for download."""
        try:
            url = self.client.generate_presigned_url(
                'get_object',
                Params={
                    'Bucket': self.bucket,
                    'Key': key,
                },
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise Exception(f"Failed to generate download URL: {e}")

    def get_public_url(self, key: str) -> str:
        """
        Generate public URL.
        Uses CDN if configured, otherwise presigned URL.
        """
        if self.cdn_base:
            return f"{self.cdn_base}/{key}"
        # Fallback to endpoint-based URL for local dev
        return f"{settings.r2_endpoint}/{self.bucket}/{key}"

    def generate_signed_cdn_url(
        self,
        key: str,
        expires_in: int = 300,
    ) -> str:
        """
        Generate HMAC-signed CDN URL for secure content.
        Used when CDN requires signed URLs for private content.
        """
        if not self.cdn_base:
            # Fallback to presigned S3 URL
            return self.client.generate_presigned_url(
                'get_object',
                Params={'Bucket': self.bucket, 'Key': key},
                ExpiresIn=expires_in,
            )

        exp = int(time.time()) + expires_in
        payload = f"{key}|{exp}"
        sig = hmac.new(
            self.hmac_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        return f"{self.cdn_base}/{key}?exp={exp}&sig={sig}"

    async def get_file_metadata(self, key: str) -> Dict[str, Any]:
        """Get file metadata (size, content type, etag)."""
        try:
            response = self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
            return {
                'size': response['ContentLength'],
                'content_type': response.get('ContentType', 'application/octet-stream'),
                'etag': response.get('ETag', '').strip('"'),
                'last_modified': response.get('LastModified'),
            }
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                raise FileNotFoundError(f"File not found: {key}")
            raise Exception(f"Failed to get metadata: {e}")

    async def file_exists(self, key: str) -> bool:
        """Check if file exists."""
        try:
            self.client.head_object(
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == '404':
                return False
            raise

    async def delete_file(self, key: str) -> bool:
        """Delete file from storage."""
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key,
            )
            return True
        except ClientError as e:
            raise Exception(f"Delete failed: {e}")

    async def copy_file(self, source_key: str, dest_key: str) -> Dict[str, Any]:
        """Copy file within bucket."""
        try:
            self.client.copy_object(
                Bucket=self.bucket,
                CopySource={'Bucket': self.bucket, 'Key': source_key},
                Key=dest_key,
            )
            return {'source': source_key, 'destination': dest_key}
        except ClientError as e:
            raise Exception(f"Copy failed: {e}")

    async def list_files(self, prefix: str, max_keys: int = 1000) -> List[str]:
        """List files with given prefix."""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            raise Exception(f"List failed: {e}")

    async def list_files_with_metadata(
        self, prefix: str, max_keys: int = 1000
    ) -> List[Dict[str, Any]]:
        """List files with metadata."""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
                MaxKeys=max_keys,
            )
            return [
                {
                    'key': obj['Key'],
                    'size': obj['Size'],
                    'last_modified': obj['LastModified'],
                    'etag': obj.get('ETag', '').strip('"'),
                }
                for obj in response.get('Contents', [])
            ]
        except ClientError as e:
            raise Exception(f"List failed: {e}")


# Singleton instance
r2_storage = R2StorageAdapter()
