#!/usr/bin/env python3
"""Test script for storage service with R2."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.storage_service import storage_service


async def test_storage():
    """Test basic storage operations."""
    print("Testing storage service with R2...\n")

    project_slug = "test-project"
    test_content = b"Hello, R2!"

    # 1. Test presigned upload URL
    print("1. Testing presigned upload URL generation...")
    result = await storage_service.create_upload_url(
        project_slug=project_slug,
        asset_type="test",
        filename="test.txt",
        content_type="text/plain",
    )
    print(f"   Upload URL: {result['upload_url'][:80]}...")
    print(f"   Storage path: {result['storage_path']}")
    print("   ✓ Presigned URL generated\n")

    # 2. Test direct upload
    print("2. Testing direct file upload...")
    upload_result = await storage_service.upload_file(
        project_slug=project_slug,
        asset_type="test",
        filename="direct-upload.txt",
        content=test_content,
        content_type="text/plain",
    )
    storage_path = upload_result['storage_path']
    print(f"   Uploaded to: {storage_path}")
    print(f"   Size: {upload_result['size']} bytes")
    print("   ✓ File uploaded\n")

    # 3. Test file exists
    print("3. Testing file existence check...")
    exists = await storage_service.file_exists(storage_path)
    print(f"   File exists: {exists}")
    assert exists, "File should exist"
    print("   ✓ File exists check passed\n")

    # 4. Test download URL
    print("4. Testing download URL generation...")
    download_url = await storage_service.get_download_url(storage_path)
    print(f"   Download URL: {download_url[:80]}...")
    print("   ✓ Download URL generated\n")

    # 5. Test read file
    print("5. Testing file read...")
    content = await storage_service.read_file(storage_path)
    print(f"   Content: {content.decode()}")
    assert content == test_content, "Content should match"
    print("   ✓ File read successfully\n")

    # 6. Test list files
    print("6. Testing list files...")
    files = await storage_service.list_uploads(project_slug, asset_type="test")
    print(f"   Found {len(files)} file(s)")
    for f in files:
        print(f"   - {f}")
    print("   ✓ Files listed\n")

    # 7. Test copy to release
    print("7. Testing copy to release...")
    release_path = await storage_service.copy_to_release(
        source_path=storage_path,
        project_slug=project_slug,
        release_id="rel_test_001",
        dest_filename="copied.txt",
    )
    print(f"   Copied to: {release_path}")
    print("   ✓ File copied to release\n")

    # 8. Test delete
    print("8. Testing file deletion...")
    deleted = await storage_service.delete_asset(storage_path)
    print(f"   Deleted: {deleted}")
    exists_after = await storage_service.file_exists(storage_path)
    assert not exists_after, "File should be deleted"
    print("   ✓ File deleted\n")

    # Cleanup release file
    await storage_service.delete_asset(release_path)

    print("=" * 50)
    print("All storage tests passed! ✓")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(test_storage())
