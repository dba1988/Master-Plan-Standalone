# TASK-011: SVG Parser Service

**Phase**: 4 - Build Pipeline
**Status**: [ ] Not Started
**Priority**: P0 - Critical
**Depends On**: TASK-007

## Objective

Parse SVG overlays to extract geometry and calculate label positions.

## Description

Create a service that:
- Parses SVG files to extract path data
- Calculates optimal label positions using polylabel
- Handles SVG groups and transforms
- Generates overlay data for bulk import

## Files to Create

```
admin-service/api/app/services/
└── svg_parser.py
```

## Implementation Steps

### Step 1: Install Dependencies
```bash
pip install svgelements polylabel-py
```

### Step 2: SVG Parser Service
```python
# app/services/svg_parser.py
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass
import re
import math

@dataclass
class ParsedOverlay:
    id: str
    path_data: str  # SVG d attribute
    centroid: Tuple[float, float]
    bounds: Tuple[float, float, float, float]  # minX, minY, maxX, maxY

class SVGParserService:
    """Parse SVG files and extract overlay geometry"""

    def __init__(self):
        self.ns = {
            'svg': 'http://www.w3.org/2000/svg'
        }

    def parse_svg(
        self,
        svg_content: str,
        id_pattern: Optional[str] = None
    ) -> List[ParsedOverlay]:
        """
        Parse SVG content and extract all paths.

        Args:
            svg_content: SVG file content as string
            id_pattern: Optional regex to filter paths by ID

        Returns:
            List of ParsedOverlay objects
        """
        root = ET.fromstring(svg_content)
        overlays = []

        # Find all path elements (with or without namespace)
        paths = root.findall('.//{http://www.w3.org/2000/svg}path')
        paths.extend(root.findall('.//path'))

        for path in paths:
            path_id = path.get('id', '')
            path_data = path.get('d', '')

            if not path_data:
                continue

            # Filter by pattern if provided
            if id_pattern and not re.match(id_pattern, path_id):
                continue

            # Calculate bounds and centroid
            bounds = self._calculate_bounds(path_data)
            centroid = self._calculate_centroid(path_data, bounds)

            overlays.append(ParsedOverlay(
                id=path_id or f"path-{len(overlays)}",
                path_data=path_data,
                centroid=centroid,
                bounds=bounds
            ))

        return overlays

    def parse_svg_with_groups(
        self,
        svg_content: str
    ) -> Dict[str, List[ParsedOverlay]]:
        """
        Parse SVG and group paths by parent group ID.

        Returns:
            Dict mapping group ID to list of overlays
        """
        root = ET.fromstring(svg_content)
        result = {}

        # Find all groups
        groups = root.findall('.//{http://www.w3.org/2000/svg}g')
        groups.extend(root.findall('.//g'))

        for group in groups:
            group_id = group.get('id', 'default')
            paths = []

            for path in group.findall('./{http://www.w3.org/2000/svg}path'):
                self._process_path(path, paths)

            for path in group.findall('./path'):
                self._process_path(path, paths)

            if paths:
                result[group_id] = paths

        return result

    def _process_path(self, path, paths: List[ParsedOverlay]):
        """Process a single path element"""
        path_id = path.get('id', '')
        path_data = path.get('d', '')

        if not path_data:
            return

        bounds = self._calculate_bounds(path_data)
        centroid = self._calculate_centroid(path_data, bounds)

        paths.append(ParsedOverlay(
            id=path_id or f"path-{len(paths)}",
            path_data=path_data,
            centroid=centroid,
            bounds=bounds
        ))

    def _calculate_bounds(self, path_data: str) -> Tuple[float, float, float, float]:
        """Calculate bounding box from path data"""
        coords = self._extract_coordinates(path_data)

        if not coords:
            return (0, 0, 0, 0)

        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]

        return (min(xs), min(ys), max(xs), max(ys))

    def _extract_coordinates(self, path_data: str) -> List[Tuple[float, float]]:
        """Extract coordinate pairs from path data"""
        # Find all numbers in the path
        numbers = re.findall(r'-?\d+\.?\d*', path_data)
        coords = []

        for i in range(0, len(numbers) - 1, 2):
            try:
                x = float(numbers[i])
                y = float(numbers[i + 1])
                coords.append((x, y))
            except (ValueError, IndexError):
                continue

        return coords

    def _calculate_centroid(
        self,
        path_data: str,
        bounds: Tuple[float, float, float, float]
    ) -> Tuple[float, float]:
        """
        Calculate centroid for label placement.
        Uses polylabel for concave polygons, falls back to center.
        """
        coords = self._extract_coordinates(path_data)

        if len(coords) < 3:
            # For simple shapes, use bounding box center
            return (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2
            )

        try:
            from polylabel import polylabel

            # Convert to polygon format
            polygon = [coords]
            center = polylabel(polygon, precision=1.0)
            return (center[0], center[1])

        except Exception:
            # Fallback to simple centroid
            avg_x = sum(c[0] for c in coords) / len(coords)
            avg_y = sum(c[1] for c in coords) / len(coords)
            return (avg_x, avg_y)

    def get_viewbox(self, svg_content: str) -> Optional[str]:
        """Extract viewBox from SVG"""
        root = ET.fromstring(svg_content)
        return root.get('viewBox')

    def convert_to_overlays(
        self,
        parsed: List[ParsedOverlay],
        overlay_type: str = "unit"
    ) -> List[Dict[str, Any]]:
        """
        Convert parsed overlays to bulk upsert format.

        Args:
            parsed: List of ParsedOverlay
            overlay_type: "zone", "unit", or "poi"

        Returns:
            List of overlay dicts for bulk upsert
        """
        return [
            {
                "overlay_type": overlay_type,
                "ref": p.id,
                "geometry": {
                    "type": "path",
                    "d": p.path_data
                },
                "label": {"en": p.id.split("-")[-1]},  # Use last part of ID as label
                "label_position": list(p.centroid),
                "props": {},
                "style_override": None
            }
            for p in parsed
        ]
```

### Step 3: Integration with Asset Upload
```python
# app/services/build_service.py (excerpt)
from app.services.svg_parser import SVGParserService
from app.services.overlay_service import OverlayService

class BuildService:
    async def import_svg_overlays(
        self,
        version_id: UUID,
        svg_path: str,
        overlay_type: str
    ) -> dict:
        """Import overlays from SVG file"""
        # Download SVG
        svg_bytes = await self.storage.download_file(svg_path)
        svg_content = svg_bytes.decode('utf-8')

        # Parse SVG
        parser = SVGParserService()
        parsed = parser.parse_svg(svg_content)

        # Convert to overlay format
        overlays = parser.convert_to_overlays(parsed, overlay_type)

        # Bulk upsert
        overlay_service = OverlayService(self.db)
        created, updated, errors = await overlay_service.bulk_upsert(
            version_id,
            overlays
        )

        # Get viewBox for config
        view_box = parser.get_viewbox(svg_content)

        return {
            "parsed_count": len(parsed),
            "created": created,
            "updated": updated,
            "errors": errors,
            "view_box": view_box
        }
```

## Polylabel Algorithm

The polylabel algorithm finds the "pole of inaccessibility" - the point inside a polygon that is farthest from any edge. This is ideal for label placement in irregular shapes.

```
       ┌─────────────────────────┐
       │                         │
       │     ┌─────────────┐     │
       │     │             │     │
       │     │      ●      │     │  ← Pole of inaccessibility
       │     │             │     │    (optimal label position)
       │     └─────────────┘     │
       │                         │
       └─────────────────────────┘
```

## Acceptance Criteria

- [ ] Can parse SVG and extract all paths
- [ ] IDs extracted correctly
- [ ] Path data preserved exactly
- [ ] Centroid calculated for label placement
- [ ] ViewBox extracted from SVG
- [ ] Handles groups and transforms
- [ ] Converts to bulk upsert format
