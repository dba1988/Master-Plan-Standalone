"""
SVG Parser Service

Parses SVG files to extract overlay geometry and calculate label positions.
Used for importing overlays from SVG designs.
"""
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple


@dataclass
class ParsedOverlay:
    """Parsed overlay from SVG."""
    id: str
    path_data: str  # SVG d attribute
    centroid: Tuple[float, float]
    bounds: Tuple[float, float, float, float]  # minX, minY, maxX, maxY


class SVGParserService:
    """
    Parse SVG files and extract overlay geometry.

    Supports:
    - Path elements with d attribute
    - Groups (g elements) for layer organization
    - ViewBox extraction
    - Centroid calculation for label placement
    """

    SVG_NS = "http://www.w3.org/2000/svg"

    def __init__(self):
        # Register SVG namespace
        ET.register_namespace("", self.SVG_NS)
        ET.register_namespace("xlink", "http://www.w3.org/1999/xlink")

    def parse_svg(
        self,
        svg_content: str,
        id_pattern: Optional[str] = None,
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
        paths = self._find_all_paths(root)

        for path in paths:
            path_id = path.get("id", "")
            path_data = path.get("d", "")

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
                bounds=bounds,
            ))

        return overlays

    def parse_svg_with_groups(
        self,
        svg_content: str,
    ) -> Dict[str, List[ParsedOverlay]]:
        """
        Parse SVG and group paths by parent group ID.

        Returns:
            Dict mapping group ID to list of overlays
        """
        root = ET.fromstring(svg_content)
        result = {}

        # Find all groups
        groups = self._find_all_groups(root)

        for group in groups:
            group_id = group.get("id", "default")
            paths = []

            # Find paths directly in this group
            for path in group.findall(f"./{{{self.SVG_NS}}}path"):
                self._process_path(path, paths)
            for path in group.findall("./path"):
                self._process_path(path, paths)

            if paths:
                result[group_id] = paths

        # Also get root-level paths
        root_paths = []
        for path in root.findall(f"./{{{self.SVG_NS}}}path"):
            self._process_path(path, root_paths)
        for path in root.findall("./path"):
            self._process_path(path, root_paths)

        if root_paths:
            result["root"] = root_paths

        return result

    def get_viewbox(self, svg_content: str) -> Optional[str]:
        """Extract viewBox from SVG (case-insensitive)."""
        root = ET.fromstring(svg_content)
        # Try standard camelCase first
        viewbox = root.get("viewBox")
        if viewbox:
            return viewbox
        # Try lowercase (also valid in SVG)
        viewbox = root.get("viewbox")
        if viewbox:
            return viewbox
        # Try checking all attributes case-insensitively
        for attr, value in root.attrib.items():
            if attr.lower() == "viewbox":
                return value
        return None

    def get_dimensions(self, svg_content: str) -> Tuple[Optional[float], Optional[float]]:
        """Extract width and height from SVG."""
        root = ET.fromstring(svg_content)

        width = self._parse_dimension(root.get("width"))
        height = self._parse_dimension(root.get("height"))

        # Fall back to viewBox if dimensions not set
        if (width is None or height is None) and root.get("viewBox"):
            parts = root.get("viewBox").split()
            if len(parts) == 4:
                width = width or float(parts[2])
                height = height or float(parts[3])

        return width, height

    def convert_to_overlays(
        self,
        parsed: List[ParsedOverlay],
        overlay_type: str = "unit",
        layer: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Convert parsed overlays to bulk upsert format.

        Args:
            parsed: List of ParsedOverlay
            overlay_type: "zone", "unit", or "poi"
            layer: Optional layer name

        Returns:
            List of overlay dicts for bulk upsert
        """
        return [
            {
                "overlay_type": overlay_type,
                "ref": p.id,
                "layer": layer,
                "geometry": {
                    "type": "path",
                    "d": p.path_data,
                },
                "label": {
                    "en": self._extract_label(p.id),
                },
                "label_position": list(p.centroid),
                "props": {},
                "style_override": None,
            }
            for p in parsed
        ]

    def _find_all_paths(self, root: ET.Element) -> List[ET.Element]:
        """Find all path elements in SVG."""
        paths = []
        paths.extend(root.findall(f".//{{{self.SVG_NS}}}path"))
        paths.extend(root.findall(".//path"))
        return paths

    def _find_all_groups(self, root: ET.Element) -> List[ET.Element]:
        """Find all group elements in SVG."""
        groups = []
        groups.extend(root.findall(f".//{{{self.SVG_NS}}}g"))
        groups.extend(root.findall(".//g"))
        return groups

    def _process_path(
        self,
        path: ET.Element,
        paths: List[ParsedOverlay],
    ) -> None:
        """Process a single path element."""
        path_id = path.get("id", "")
        path_data = path.get("d", "")

        if not path_data:
            return

        bounds = self._calculate_bounds(path_data)
        centroid = self._calculate_centroid(path_data, bounds)

        paths.append(ParsedOverlay(
            id=path_id or f"path-{len(paths)}",
            path_data=path_data,
            centroid=centroid,
            bounds=bounds,
        ))

    def _calculate_bounds(
        self,
        path_data: str,
    ) -> Tuple[float, float, float, float]:
        """Calculate bounding box from path data."""
        coords = self._extract_coordinates(path_data)

        if not coords:
            return (0, 0, 0, 0)

        xs = [c[0] for c in coords]
        ys = [c[1] for c in coords]

        return (min(xs), min(ys), max(xs), max(ys))

    def _extract_coordinates(
        self,
        path_data: str,
    ) -> List[Tuple[float, float]]:
        """
        Extract coordinate pairs from path data.

        Handles M, L, H, V, C, S, Q, T, A commands (absolute only for now).
        """
        # Remove commands to get just numbers
        # Match number patterns including negatives and decimals
        numbers = re.findall(r"-?\d+\.?\d*", path_data)
        coords = []

        i = 0
        while i < len(numbers) - 1:
            try:
                x = float(numbers[i])
                y = float(numbers[i + 1])
                coords.append((x, y))
                i += 2
            except (ValueError, IndexError):
                i += 1

        return coords

    def _calculate_centroid(
        self,
        path_data: str,
        bounds: Tuple[float, float, float, float],
    ) -> Tuple[float, float]:
        """
        Calculate centroid for label placement.

        Uses polylabel for complex polygons if available,
        falls back to bounding box center.
        """
        coords = self._extract_coordinates(path_data)

        if len(coords) < 3:
            # For simple shapes, use bounding box center
            return (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
            )

        try:
            from polylabel import polylabel

            # Convert to polygon format
            polygon = [coords]
            center = polylabel(polygon, precision=1.0)
            return (center[0], center[1])

        except ImportError:
            # Fallback to simple centroid
            avg_x = sum(c[0] for c in coords) / len(coords)
            avg_y = sum(c[1] for c in coords) / len(coords)
            return (avg_x, avg_y)

        except Exception:
            # Fallback to bounding box center
            return (
                (bounds[0] + bounds[2]) / 2,
                (bounds[1] + bounds[3]) / 2,
            )

    def _extract_label(self, path_id: str) -> str:
        """Extract display label from path ID."""
        # Remove common prefixes
        label = re.sub(r"^(unit|zone|poi|path)-?", "", path_id, flags=re.IGNORECASE)
        # Replace underscores/hyphens with spaces
        label = re.sub(r"[_-]+", " ", label)
        # Title case
        return label.strip() or path_id

    def _parse_dimension(self, value: Optional[str]) -> Optional[float]:
        """Parse dimension value (e.g., '100px', '50%')."""
        if not value:
            return None

        # Remove units
        match = re.match(r"^(\d+\.?\d*)", value)
        if match:
            return float(match.group(1))
        return None


# Singleton instance
svg_parser = SVGParserService()
