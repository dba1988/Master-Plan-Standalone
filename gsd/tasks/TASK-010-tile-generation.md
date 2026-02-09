# TASK-010: Tile Generation Service

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-005

## Objective

Implement DZI tile generation from source images using pyvips.

## Description

Create a service that:
- Converts PNG/WEBP images to DZI format
- Generates tile pyramid for OpenSeadragon
- Runs as background job (can take minutes)
- Uploads tiles to storage

## Files to Create

```
admin-api/app/services/
└── tile_service.py
```

## Implementation Steps

### Step 1: Install pyvips
```bash
# macOS
brew install vips

# Ubuntu
apt-get install libvips-dev

# Python package
pip install pyvips
```

### Step 2: Tile Service
```python
# app/services/tile_service.py
import pyvips
import os
import shutil
import tempfile
from pathlib import Path
from typing import Optional
from uuid import UUID
from app.services.storage_service import StorageBackend

class TileService:
    def __init__(self, storage: StorageBackend):
        self.storage = storage

    async def generate_tiles(
        self,
        source_path: str,
        output_prefix: str,
        tile_size: int = 256,
        overlap: int = 1,
        quality: int = 85
    ) -> dict:
        """
        Generate DZI tiles from source image.

        Args:
            source_path: Path in storage to source image
            output_prefix: Storage prefix for output tiles
            tile_size: Tile size in pixels (default 256)
            overlap: Tile overlap in pixels (default 1)
            quality: JPEG quality (default 85)

        Returns:
            dict with dzi_path and tile_count
        """
        # Create temp directory for processing
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)

            # Download source image
            source_file = temp_dir / "source.png"
            source_bytes = await self.storage.download_file(source_path)
            source_file.write_bytes(source_bytes)

            # Output paths
            output_dir = temp_dir / "tiles"
            output_dir.mkdir()
            dzi_name = "image"

            # Generate DZI using pyvips
            image = pyvips.Image.new_from_file(str(source_file))

            # Save as DZI (creates .dzi file and _files directory)
            dzi_path = output_dir / f"{dzi_name}.dzi"
            image.dzsave(
                str(output_dir / dzi_name),
                tile_size=tile_size,
                overlap=overlap,
                suffix=".jpg",
                Q=quality
            )

            # Count tiles generated
            tile_count = 0
            files_dir = output_dir / f"{dzi_name}_files"

            # Upload all generated files
            for file_path in files_dir.rglob("*"):
                if file_path.is_file():
                    tile_count += 1
                    relative_path = file_path.relative_to(output_dir)
                    storage_path = f"{output_prefix}/{relative_path}"

                    with open(file_path, "rb") as f:
                        content_type = "image/jpeg" if file_path.suffix == ".jpg" else "application/xml"
                        await self.storage.upload_file(f, storage_path, content_type)

            # Upload DZI file
            with open(dzi_path, "rb") as f:
                await self.storage.upload_file(
                    f,
                    f"{output_prefix}/{dzi_name}.dzi",
                    "application/xml"
                )

            return {
                "dzi_path": f"{output_prefix}/{dzi_name}.dzi",
                "tile_count": tile_count,
                "width": image.width,
                "height": image.height
            }

    async def generate_tiles_from_bytes(
        self,
        image_bytes: bytes,
        output_prefix: str,
        tile_size: int = 256
    ) -> dict:
        """Generate tiles from in-memory image bytes"""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_dir = Path(temp_dir)
            source_file = temp_dir / "source.png"
            source_file.write_bytes(image_bytes)

            return await self._process_image(source_file, output_prefix, tile_size)

    def get_optimal_tile_size(self, image_width: int, image_height: int) -> int:
        """Calculate optimal tile size based on image dimensions"""
        max_dim = max(image_width, image_height)

        if max_dim <= 2048:
            return 256
        elif max_dim <= 8192:
            return 512
        else:
            return 1024

    async def check_tiles_exist(self, dzi_path: str) -> bool:
        """Check if tiles already exist for a DZI"""
        return await self.storage.file_exists(dzi_path)
```

### Step 3: Add to Requirements
```
# requirements.txt (add)
pyvips==2.2.2
```

### Step 4: Background Job Integration
```python
# app/services/build_service.py (excerpt)
from app.services.tile_service import TileService

class BuildService:
    async def build_tiles(self, version_id: UUID, asset: Asset) -> dict:
        """Build tiles for a base map asset"""
        tile_service = TileService(self.storage)

        output_prefix = f"tiles/{asset.version_id}"

        result = await tile_service.generate_tiles(
            source_path=asset.storage_path,
            output_prefix=output_prefix
        )

        return result
```

## DZI Output Structure

```
tiles/
└── {version_id}/
    ├── image.dzi           # DZI manifest
    └── image_files/
        ├── 0/              # Lowest zoom level
        │   └── 0_0.jpg
        ├── 1/
        │   ├── 0_0.jpg
        │   └── 0_1.jpg
        ├── ...
        └── 12/             # Highest zoom level
            ├── 0_0.jpg
            ├── 0_1.jpg
            └── ...
```

## DZI Format Example

```xml
<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
       Format="jpg"
       Overlap="1"
       TileSize="256">
    <Size Width="4096" Height="4096"/>
</Image>
```

## Acceptance Criteria

- [ ] Can generate DZI from PNG/WEBP
- [ ] Tiles uploaded to storage correctly
- [ ] DZI manifest generated properly
- [ ] Works with large images (8K+)
- [ ] Progress can be tracked
- [ ] Handles errors gracefully

## Performance Notes

- pyvips is memory-efficient (streaming)
- Use appropriate tile size (256-512 for most cases)
- Consider parallel upload for many tiles
- Large images may take 1-5 minutes
