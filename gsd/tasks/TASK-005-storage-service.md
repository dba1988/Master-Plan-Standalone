# TASK-005: Storage Service

**Phase**: 2 - Storage + Assets
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-001

## Objective

Create a unified storage abstraction that works with both S3 and GCS.

## Description

Implement a storage service that:
- Abstracts S3/GCS operations
- Generates signed URLs for direct uploads
- Handles file downloads
- Lists files by prefix
- Deletes files

## Files to Create

```
admin-api/app/
├── core/
│   └── config.py (add storage settings)
└── services/
    └── storage_service.py
```

## Implementation Steps

### Step 1: Add Storage Config
```python
# app/core/config.py (add to existing)
class Settings(BaseSettings):
    # ... existing settings ...

    # Storage
    storage_type: str = "local"  # local, s3, gcs
    storage_bucket: str = ""
    storage_region: str = "us-east-1"
    storage_endpoint: Optional[str] = None  # For MinIO/LocalStack

    # AWS (S3)
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None

    # GCP (GCS)
    gcp_project_id: Optional[str] = None
    gcp_credentials_path: Optional[str] = None

    # Local storage path (for local mode)
    local_storage_path: str = "./storage"
```

### Step 2: Storage Service
```python
# app/services/storage_service.py
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional, List, BinaryIO
from datetime import timedelta
import mimetypes

class StorageBackend(ABC):
    @abstractmethod
    async def upload_file(self, file: BinaryIO, path: str, content_type: str) -> str:
        """Upload file and return public URL"""
        pass

    @abstractmethod
    async def download_file(self, path: str) -> bytes:
        """Download file content"""
        pass

    @abstractmethod
    async def delete_file(self, path: str) -> bool:
        """Delete file"""
        pass

    @abstractmethod
    async def list_files(self, prefix: str) -> List[str]:
        """List files with prefix"""
        pass

    @abstractmethod
    async def generate_upload_url(
        self,
        path: str,
        content_type: str,
        expires_in: timedelta = timedelta(minutes=5)
    ) -> str:
        """Generate signed URL for direct upload"""
        pass

    @abstractmethod
    async def file_exists(self, path: str) -> bool:
        """Check if file exists"""
        pass


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def upload_file(self, file: BinaryIO, path: str, content_type: str) -> str:
        file_path = self.base_path / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(file.read())
        return f"/storage/{path}"

    async def download_file(self, path: str) -> bytes:
        file_path = self.base_path / path
        return file_path.read_bytes()

    async def delete_file(self, path: str) -> bool:
        file_path = self.base_path / path
        if file_path.exists():
            file_path.unlink()
            return True
        return False

    async def list_files(self, prefix: str) -> List[str]:
        prefix_path = self.base_path / prefix
        if not prefix_path.exists():
            return []
        return [str(p.relative_to(self.base_path)) for p in prefix_path.rglob("*") if p.is_file()]

    async def generate_upload_url(
        self,
        path: str,
        content_type: str,
        expires_in: timedelta = timedelta(minutes=5)
    ) -> str:
        # For local, return direct upload endpoint
        return f"/api/assets/upload-direct?path={path}"

    async def file_exists(self, path: str) -> bool:
        return (self.base_path / path).exists()


class S3StorageBackend(StorageBackend):
    def __init__(
        self,
        bucket: str,
        region: str,
        access_key: str,
        secret_key: str,
        endpoint: Optional[str] = None
    ):
        import boto3
        self.bucket = bucket
        self.s3 = boto3.client(
            's3',
            region_name=region,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            endpoint_url=endpoint
        )

    async def upload_file(self, file: BinaryIO, path: str, content_type: str) -> str:
        self.s3.upload_fileobj(
            file, self.bucket, path,
            ExtraArgs={'ContentType': content_type}
        )
        return f"https://{self.bucket}.s3.amazonaws.com/{path}"

    async def download_file(self, path: str) -> bytes:
        import io
        buffer = io.BytesIO()
        self.s3.download_fileobj(self.bucket, path, buffer)
        buffer.seek(0)
        return buffer.read()

    async def delete_file(self, path: str) -> bool:
        self.s3.delete_object(Bucket=self.bucket, Key=path)
        return True

    async def list_files(self, prefix: str) -> List[str]:
        response = self.s3.list_objects_v2(Bucket=self.bucket, Prefix=prefix)
        return [obj['Key'] for obj in response.get('Contents', [])]

    async def generate_upload_url(
        self,
        path: str,
        content_type: str,
        expires_in: timedelta = timedelta(minutes=5)
    ) -> str:
        return self.s3.generate_presigned_url(
            'put_object',
            Params={
                'Bucket': self.bucket,
                'Key': path,
                'ContentType': content_type
            },
            ExpiresIn=int(expires_in.total_seconds())
        )

    async def file_exists(self, path: str) -> bool:
        try:
            self.s3.head_object(Bucket=self.bucket, Key=path)
            return True
        except:
            return False


class GCSStorageBackend(StorageBackend):
    def __init__(self, bucket: str, project_id: str, credentials_path: Optional[str] = None):
        from google.cloud import storage
        if credentials_path:
            self.client = storage.Client.from_service_account_json(credentials_path)
        else:
            self.client = storage.Client(project=project_id)
        self.bucket = self.client.bucket(bucket)

    async def upload_file(self, file: BinaryIO, path: str, content_type: str) -> str:
        blob = self.bucket.blob(path)
        blob.upload_from_file(file, content_type=content_type)
        return f"https://storage.googleapis.com/{self.bucket.name}/{path}"

    async def download_file(self, path: str) -> bytes:
        blob = self.bucket.blob(path)
        return blob.download_as_bytes()

    async def delete_file(self, path: str) -> bool:
        blob = self.bucket.blob(path)
        blob.delete()
        return True

    async def list_files(self, prefix: str) -> List[str]:
        return [blob.name for blob in self.bucket.list_blobs(prefix=prefix)]

    async def generate_upload_url(
        self,
        path: str,
        content_type: str,
        expires_in: timedelta = timedelta(minutes=5)
    ) -> str:
        from datetime import datetime, timezone
        blob = self.bucket.blob(path)
        return blob.generate_signed_url(
            version="v4",
            expiration=expires_in,
            method="PUT",
            content_type=content_type
        )

    async def file_exists(self, path: str) -> bool:
        blob = self.bucket.blob(path)
        return blob.exists()


def get_storage_backend() -> StorageBackend:
    from app.core.config import settings

    if settings.storage_type == "s3":
        return S3StorageBackend(
            bucket=settings.storage_bucket,
            region=settings.storage_region,
            access_key=settings.aws_access_key_id,
            secret_key=settings.aws_secret_access_key,
            endpoint=settings.storage_endpoint
        )
    elif settings.storage_type == "gcs":
        return GCSStorageBackend(
            bucket=settings.storage_bucket,
            project_id=settings.gcp_project_id,
            credentials_path=settings.gcp_credentials_path
        )
    else:
        return LocalStorageBackend(settings.local_storage_path)


# Dependency for FastAPI
async def get_storage() -> StorageBackend:
    return get_storage_backend()
```

### Step 3: Add Requirements
```
# requirements.txt (add)
boto3==1.34.0
google-cloud-storage==2.14.0
```

## Acceptance Criteria

- [ ] LocalStorageBackend works for development
- [ ] S3StorageBackend connects to AWS/MinIO
- [ ] GCSStorageBackend connects to GCS
- [ ] Signed URLs generated correctly
- [ ] Files can be uploaded and downloaded
- [ ] Files can be listed by prefix
- [ ] Files can be deleted

## Testing

```python
# Test with local storage
storage = LocalStorageBackend("./test-storage")
await storage.upload_file(open("test.png", "rb"), "test/image.png", "image/png")
assert await storage.file_exists("test/image.png")
url = await storage.generate_upload_url("test/upload.png", "image/png")
print(f"Upload URL: {url}")
```
