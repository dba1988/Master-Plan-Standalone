# TASK-027: R2 Storage Adapter

**Phase**: 2 - Storage + Assets
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001 (project scaffold)
**Blocks**: TASK-005 (storage service), TASK-006 (asset upload)
**Estimated Time**: 3-4 hours

## Objective

Create a Cloudflare R2 storage adapter using AWS S3 SDK (R2 is S3-compatible). This replaces local/GCS storage with R2 for all asset operations.

## Pattern Reference

| Source File | Pattern to Reuse | DO NOT Reuse |
|-------------|------------------|--------------|
| `carjom-platform/web-app/backend/src/common/services/r2-storage.service.ts` | S3Client init, presigned URLs, public vs secure paths, HMAC signing | Bucket name `carjom-*`, CDN domain `cdn.*.carjom.com` |
| `carjom-platform/web-app/backend/src/common/modules/storage.module.ts` | Module structure | - |

## Environment Variables

```bash
# Cloudflare R2 (S3-compatible)
CF_ACCOUNT_ID=<cloudflare-account-id>
R2_ACCESS_KEY_ID=<r2-access-key>
R2_SECRET_ACCESS_KEY=<r2-secret-key>
R2_BUCKET=masterplan-uat  # or masterplan-prod

# CDN
CDN_BASE=https://cdn.uat.mp.example.com
CDN_HMAC_SECRET=<hmac-secret-for-signed-urls>
```

## Files to Create

```
admin-service/api/app/
├── core/
│   └── r2_client.py
└── services/
    └── r2_storage_service.py
```

## Implementation

### R2 Client Configuration

```python
# app/core/r2_client.py
import boto3
from botocore.config import Config
from app.core.config import settings

def get_r2_client():
    """
    Initialize S3-compatible client for Cloudflare R2.

    R2 endpoint format: https://{account_id}.r2.cloudflarestorage.com
    """
    return boto3.client(
        's3',
        endpoint_url=f"https://{settings.cf_account_id}.r2.cloudflarestorage.com",
        aws_access_key_id=settings.r2_access_key_id,
        aws_secret_access_key=settings.r2_secret_access_key,
        region_name='auto',  # R2 uses 'auto' for region
        config=Config(
            signature_version='s3v4',
            retries={'max_attempts': 3}
        )
    )

# Singleton instance
r2_client = get_r2_client()
```

### R2 Storage Service

```python
# app/services/r2_storage_service.py
import hashlib
import hmac
import time
from typing import Optional
from botocore.exceptions import ClientError

from app.core.r2_client import r2_client
from app.core.config import settings

class R2StorageService:
    """
    Cloudflare R2 storage service.

    Supports:
    - Public uploads (tiles, release.json) - served via CDN
    - Secure uploads (admin assets) - requires signed URL
    - Presigned upload URLs for client-side uploads
    """

    def __init__(self):
        self.client = r2_client
        self.bucket = settings.r2_bucket
        self.cdn_base = settings.cdn_base.rstrip('/')
        self.hmac_secret = settings.cdn_hmac_secret

    async def upload_file(
        self,
        key: str,
        body: bytes,
        content_type: str,
        metadata: Optional[dict] = None,
        public: bool = False
    ) -> dict:
        """Upload file to R2."""
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

            # Generate appropriate URL
            if public:
                url = self.get_public_url(key)
            else:
                url = self.generate_signed_url(key)

            return {
                'key': key,
                'size': len(body),
                'url': url,
                'public': public,
            }
        except ClientError as e:
            raise Exception(f"R2 upload failed: {e}")

    async def get_presigned_upload_url(
        self,
        key: str,
        content_type: str,
        expires_in: int = 300
    ) -> str:
        """Generate presigned URL for client-side upload."""
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
        expires_in: int = 300
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
        Generate public CDN URL (no signing required).
        Used for: tiles, release.json
        """
        return f"{self.cdn_base}/public/{key}"

    def generate_signed_url(
        self,
        key: str,
        expires_in: int = 300,
        download: bool = False
    ) -> str:
        """
        Generate HMAC-signed URL for secure content.
        Used for: admin uploads, private assets

        Signature format matches Cloudflare Worker validation.
        """
        exp = int(time.time()) + expires_in
        payload = f"{key}|{exp}||"
        sig = hmac.new(
            self.hmac_secret.encode(),
            payload.encode(),
            hashlib.sha256
        ).hexdigest()

        url = f"{self.cdn_base}/secure/{key}?exp={exp}&sig={sig}"
        if download:
            url += "&download=true"
        return url

    async def delete_file(self, key: str) -> None:
        """Delete file from R2."""
        try:
            self.client.delete_object(
                Bucket=self.bucket,
                Key=key,
            )
        except ClientError as e:
            raise Exception(f"R2 delete failed: {e}")

    async def file_exists(self, key: str) -> bool:
        """Check if file exists in R2."""
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

    async def copy_file(self, source_key: str, dest_key: str) -> None:
        """Copy file within R2 bucket."""
        try:
            self.client.copy_object(
                Bucket=self.bucket,
                CopySource={'Bucket': self.bucket, 'Key': source_key},
                Key=dest_key,
            )
        except ClientError as e:
            raise Exception(f"R2 copy failed: {e}")

    async def list_files(self, prefix: str) -> list:
        """List files with given prefix."""
        try:
            response = self.client.list_objects_v2(
                Bucket=self.bucket,
                Prefix=prefix,
            )
            return [obj['Key'] for obj in response.get('Contents', [])]
        except ClientError as e:
            raise Exception(f"R2 list failed: {e}")


# Singleton instance
r2_storage = R2StorageService()
```

### Settings Update

```python
# app/core/config.py (add to Settings class)

class Settings(BaseSettings):
    # ... existing settings ...

    # Cloudflare R2
    cf_account_id: str = Field(..., env='CF_ACCOUNT_ID')
    r2_access_key_id: str = Field(..., env='R2_ACCESS_KEY_ID')
    r2_secret_access_key: str = Field(..., env='R2_SECRET_ACCESS_KEY')
    r2_bucket: str = Field(..., env='R2_BUCKET')

    # CDN
    cdn_base: str = Field(..., env='CDN_BASE')
    cdn_hmac_secret: str = Field(..., env='CDN_HMAC_SECRET')
```

## Key Path Patterns

```
# Admin uploads (staging)
mp/{project}/uploads/{asset_id}/{filename}

# Published releases (immutable)
mp/{project}/releases/{release_id}/release.json
mp/{project}/releases/{release_id}/tiles/{z}/{x}_{y}.png

# Public access pattern
https://cdn.mp.example.com/public/mp/{project}/releases/{release_id}/...
```

## Testing

```python
# tests/test_r2_storage.py
import pytest
from app.services.r2_storage_service import r2_storage

@pytest.mark.asyncio
async def test_upload_and_download():
    key = "test/example.txt"
    content = b"Hello, R2!"

    # Upload
    result = await r2_storage.upload_file(
        key=key,
        body=content,
        content_type="text/plain",
        public=True,
    )
    assert result['key'] == key

    # Check exists
    exists = await r2_storage.file_exists(key)
    assert exists

    # Cleanup
    await r2_storage.delete_file(key)

@pytest.mark.asyncio
async def test_presigned_upload_url():
    key = "test/upload.png"
    url = await r2_storage.get_presigned_upload_url(
        key=key,
        content_type="image/png",
    )
    assert "X-Amz-Signature" in url
```

## Acceptance Criteria

- [ ] R2 client initializes with env vars
- [ ] File upload works (public and secure)
- [ ] Presigned upload URLs generate correctly
- [ ] Signed download URLs validate on CDN worker
- [ ] File delete works
- [ ] File existence check works
- [ ] File copy works (for publish)
- [ ] List files with prefix works
- [ ] No CarJom-specific naming in code
