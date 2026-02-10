"""
Tile Generation Service

Generates DZI (Deep Zoom Image) tiles from base map images using libvips.
"""
import math
from pathlib import Path
from typing import Callable, Dict, Optional

import pyvips


class TileService:
    """
    Generate DZI tiles from base map images.

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
        # Load image with sequential access for memory efficiency
        image = pyvips.Image.new_from_file(source_path, access="sequential")
        width = image.width
        height = image.height

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
                level_image = image.resize(1 / scale)
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
                    tile_width = min(self.tile_size, level_width - left)
                    tile_height = min(self.tile_size, level_height - top)

                    if tile_width <= 0 or tile_height <= 0:
                        continue

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
