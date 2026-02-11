"""
Tile Generation Service

Generates DZI (Deep Zoom Image) tiles from base map images.
Uses Pillow for image processing.
"""
import math
from pathlib import Path
from typing import Callable, Dict, Optional

from PIL import Image


class TileService:
    """
    Generate DZI tiles from base map images.

    Uses Pillow for image processing.
    Output: tiles in {level}/{x}_{y}.{format} structure.
    Default format is WebP for ~30% smaller file sizes than PNG.
    """

    def __init__(
        self,
        tile_size: int = 256,
        overlap: int = 1,
        format: str = "webp",
        quality: int = 85,
    ):
        self.tile_size = tile_size
        self.overlap = overlap
        self.format = format
        self.quality = quality  # Used for webp and jpeg

    def generate_tiles(
        self,
        source_path: str,
        output_dir: str,
        progress_callback: Optional[Callable[[int], None]] = None,
    ) -> Dict:
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
        image = Image.open(source_path)
        width, height = image.size

        # Convert to RGB if necessary (handles RGBA, palette, etc.)
        if image.mode not in ("RGB", "RGBA"):
            image = image.convert("RGB")

        # Calculate number of levels
        max_dim = max(width, height)
        levels = 1
        temp = max_dim
        while temp > self.tile_size:
            temp //= 2
            levels += 1

        # Create output directory
        Path(output_dir).mkdir(parents=True, exist_ok=True)

        # Generate tiles at each level
        tile_count = 0
        for level in range(levels):
            level_dir = Path(output_dir) / str(level)
            level_dir.mkdir(exist_ok=True)

            # Scale factor for this level (0 = smallest, levels-1 = full size)
            scale = 2 ** (levels - level - 1)
            level_width = max(1, width // scale)
            level_height = max(1, height // scale)

            # Resize image for this level
            if scale > 1:
                level_image = image.resize(
                    (level_width, level_height),
                    Image.Resampling.LANCZOS
                )
            else:
                level_image = image

            # Calculate tile grid
            cols = math.ceil(level_width / self.tile_size)
            rows = math.ceil(level_height / self.tile_size)

            # Extract and save tiles
            for y in range(rows):
                for x in range(cols):
                    # Calculate tile bounds
                    left = x * self.tile_size
                    top = y * self.tile_size
                    right = min(left + self.tile_size, level_width)
                    bottom = min(top + self.tile_size, level_height)

                    if right <= left or bottom <= top:
                        continue

                    # Extract tile
                    tile = level_image.crop((left, top, right, bottom))

                    # Save tile
                    tile_path = level_dir / f"{x}_{y}.{self.format}"
                    if self.format == "png":
                        tile.save(str(tile_path), "PNG", optimize=True)
                    elif self.format == "webp":
                        tile.save(str(tile_path), "WEBP", quality=self.quality, method=4)
                    else:
                        tile.save(str(tile_path), "JPEG", quality=self.quality, optimize=True)

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

    def get_optimal_tile_size(
        self,
        image_width: int,
        image_height: int,
    ) -> int:
        """Calculate optimal tile size based on image dimensions."""
        max_dim = max(image_width, image_height)

        if max_dim <= 2048:
            return 256
        elif max_dim <= 8192:
            return 512
        else:
            return 1024


# Default singleton instance
tile_service = TileService()
