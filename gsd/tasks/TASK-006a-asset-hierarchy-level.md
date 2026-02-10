# TASK-006a: Asset Hierarchy Level

**Status**: Complete
**Duration**: 30 minutes
**Depends On**: TASK-006

## Objective

Add `level` field to Asset model to support project hierarchy (project → zone-a, zone-gc, etc.) enabling drill-down navigation.

## Background

Projects have a hierarchical structure:
- **Project level**: Shows zones (base map + overlay SVG with zone paths)
- **Zone level**: Shows units within a zone (base map + overlay SVG with unit paths)

Each level has 2 files:
1. Base map image (webp/jpeg)
2. Overlay SVG (with clickable paths)

## Implementation

### 1. Model Changes
```python
# app/models/asset.py
class Asset(Base):
    # ... existing fields ...
    level = Column(String(100), nullable=True)  # "project", "zone-a", "zone-gc", etc.
```

### 2. Schema Changes
```python
# app/schemas/asset.py
class UploadConfirmRequest(BaseModel):
    # ... existing fields ...
    level: Optional[str] = Field(None, description="Hierarchy level")

class AssetResponse(BaseModel):
    # ... existing fields ...
    level: Optional[str] = None
```

### 3. API Endpoint Update
```
GET /api/projects/{slug}/versions/{version}/assets?level=zone-a
```
Returns only assets for that hierarchy level.

### 4. Database Migration
```
alembic upgrade head  # Creates level column + index
```

## Usage Example

```bash
# Upload asset with level
curl -X POST ".../assets/confirm" -d '{
  "storage_path": "...",
  "asset_type": "base_map",
  "filename": "zone-a-map.webp",
  "level": "zone-a"
}'

# Query by level
curl ".../assets?level=project"  # Returns project-level assets
curl ".../assets?level=zone-a"   # Returns zone-a assets
```

## Files Changed

- `app/models/asset.py` - Added level column and index
- `app/schemas/asset.py` - Added level to request/response schemas
- `app/services/asset_service.py` - Handle level in confirm_upload and list_assets
- `app/features/assets/routes.py` - Added level query parameter
- `alembic/versions/acda00a0a4a6_add_level_to_assets.py` - Migration

## Testing

```bash
# List all assets
GET /api/projects/sedra-3/versions/2/assets
# Returns: project-view-map.webp, project-view-overlay.svg, zone-a-*, zone-gc-*, zone-h-*

# Filter by level
GET /api/projects/sedra-3/versions/2/assets?level=project
# Returns: project-view-map.webp, project-view-overlay.svg (2 assets)

GET /api/projects/sedra-3/versions/2/assets?level=zone-a
# Returns: zone-a-map.webp, zone-a-overlay.svg (2 assets)
```

## Notes

- Level is optional - existing assets without level still work
- Convention: "project" for top level, "zone-{id}" for zone levels
- Viewer SDK should use level to determine which base map to load when drilling down
