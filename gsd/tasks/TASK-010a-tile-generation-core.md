# TASK-010a: Tile Generation Core

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-027 (R2 storage)
**Blocks**: TASK-010b (tile job integration)
**Estimated Time**: 3-4 hours

## Objective

Implement the core tile generation service that creates DZI tiles from base map images using libvips/pyvips.

## Scope

This task covers ONLY the tile generation logic. Job integration is in TASK-010b.

## Files to Create

```
admin-service/api/app/
└── services/
    └── tile_service.py
```

## Implementation

```python
# app/services/tile_service.py
import os
import tempfile
import shutil
from pathlib import Path
from typing import Optional
import pyvips

class TileService:
    """
    Generate DZI (Deep Zoom Image) tiles from base map images.

    Uses libvips for efficient large image processing.
    Output: tiles in {level}/{x}_{y}.{format} structure.
    """

    def __init__(
        self,
        tile_size: int = 256,
        overlap: int = 1,
        format: str = "png",
        quality: int = 85,
    ):
        self.tile_size = tile_size
        self.overlap = overlap
        self.format = format
        self.quality = quality

    def generate_tiles(
        self,
        source_path: str,
        output_dir: str,
        progress_callback: Optional[callable] = None,
    ) -> dict:
        """
        Generate DZI tiles from source image.

        Args:
            source_path: Path to source image (PNG, JPEG, WebP)
            output_dir: Directory to write tiles to
            progress_callback: Optional callback(percent: int)

        Returns:
            dict with tile metadata (width, height, levels, tile_count)
        """
        # Load image
        image = pyvips.Image.new_from_file(source_path, access="sequential")
        width = image.width
        height = image.height

        # Calculate number of levels
        max_dim = max(width, height)
        levels = 1
        while max_dim > self.tile_size:
            max_dim //= 2
            levels += 1

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate tiles at each level
        tile_count = 0
        for level in range(levels):
            level_dir = Path(output_dir) / str(level)
            level_dir.mkdir(exist_ok=True)

            # Scale factor for this level
            scale = 2 ** (levels - level - 1)
            level_width = width // scale
            level_height = height // scale

            # Resize image for this level
            if scale > 1:
                level_image = image.resize(1 / scale)
            else:
                level_image = image

            # Calculate tile grid
            cols = (level_width + self.tile_size - 1) // self.tile_size
            rows = (level_height + self.tile_size - 1) // self.tile_size

            # Extract and save tiles
            for y in range(rows):
                for x in range(cols):
                    # Calculate tile bounds
                    left = x * self.tile_size
                    top = y * self.tile_size
                    tile_width = min(self.tile_size, level_width - left)
                    tile_height = min(self.tile_size, level_height - top)

                    # Extract tile
                    tile = level_image.crop(left, top, tile_width, tile_height)

                    # Save tile
                    tile_path = level_dir / f"{x}_{y}.{self.format}"
                    if self.format == "png":
                        tile.write_to_file(str(tile_path))
                    else:
                        tile.write_to_file(str(tile_path), Q=self.quality)

                    tile_count += 1

            # Progress callback
            if progress_callback:
                percent = int((level + 1) / levels * 100)
                progress_callback(percent)

        return {
            "width": width,
            "height": height,
            "tile_size": self.tile_size,
            "overlap": self.overlap,
            "levels": levels,
            "format": self.format,
            "tile_count": tile_count,
        }

    def generate_dzi_xml(
        self,
        width: int,
        height: int,
        output_path: str,
    ) -> None:
        """
        Generate DZI XML descriptor file.

        Not required for our implementation (we use release.json),
        but useful for standalone DZI viewers.
        """
        xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Image xmlns="http://schemas.microsoft.com/deepzoom/2008"
    Format="{self.format}"
    Overlap="{self.overlap}"
    TileSize="{self.tile_size}">
    <Size Width="{width}" Height="{height}"/>
</Image>"""

        with open(output_path, "w") as f:
            f.write(xml)


# Singleton instance
tile_service = TileService()
```

## Dependencies

```txt
# requirements.txt (add)
pyvips>=2.2.1
```

Note: libvips must be installed on the system:
```bash
# Ubuntu/Debian
apt-get install libvips-dev

# macOS
brew install vips

# Alpine (Docker)
apk add vips-dev
```

## Update Dockerfile

```dockerfile
# admin-service/api/Dockerfile (add to Stage 1)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    libvips-dev \  # Add this
    curl \
    && rm -rf /var/lib/apt/lists/*
```

## Unit Tests

```python
# tests/test_tile_service.py
import pytest
import tempfile
from pathlib import Path
from PIL import Image
from app.services.tile_service import tile_service

@pytest.fixture
def sample_image():
    """Create a sample 1024x1024 image."""
    with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
        img = Image.new("RGB", (1024, 1024), color="blue")
        img.save(f.name)
        yield f.name
        Path(f.name).unlink()

def test_generate_tiles(sample_image):
    with tempfile.TemporaryDirectory() as output_dir:
        result = tile_service.generate_tiles(
            source_path=sample_image,
            output_dir=output_dir,
        )

        assert result["width"] == 1024
        assert result["height"] == 1024
        assert result["levels"] >= 1
        assert result["tile_count"] > 0

        # Check tiles exist
        assert (Path(output_dir) / "0" / "0_0.png").exists()

def test_progress_callback(sample_image):
    progress_values = []

    def callback(percent):
        progress_values.append(percent)

    with tempfile.TemporaryDirectory() as output_dir:
        tile_service.generate_tiles(
            source_path=sample_image,
            output_dir=output_dir,
            progress_callback=callback,
        )

    assert len(progress_values) > 0
    assert progress_values[-1] == 100
```

## Acceptance Criteria

- [ ] Tile generation works for PNG, JPEG, WebP inputs
- [ ] Output structure is `{level}/{x}_{y}.{format}`
- [ ] Handles large images (8K+) without memory issues
- [ ] Progress callback fires at each level
- [ ] Returns correct metadata (width, height, levels, tile_count)
- [ ] libvips installed in Docker image
- [ ] Unit tests pass
