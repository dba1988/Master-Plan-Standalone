#!/bin/bash
# Upload All Assets Script
# Uploads all project resources with hierarchy metadata

set -e

API_URL="http://localhost:8000"
RESOURCE_DIR="/Users/nishajamaludin/Documents/GitHub/Master-Plan-Standalone/resource/sedra-3"
PROJECT_SLUG="sedra-3"
VERSION_NUMBER="${1:-2}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo "================================================"
echo "  Upload All Assets to $PROJECT_SLUG v$VERSION_NUMBER"
echo "================================================"
echo ""

# Login
echo -e "${YELLOW}Logging in...${NC}"
ACCESS_TOKEN=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}' | \
  python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))")

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}Login failed${NC}"
  exit 1
fi
echo -e "${GREEN}✓ Logged in${NC}"

auth_curl() {
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$@"
}

# Function to upload an asset
upload_asset() {
  local filename="$1"
  local asset_type="$2"
  local content_type="$3"
  local level="$4"
  local filepath="$RESOURCE_DIR/$filename"

  if [ ! -f "$filepath" ]; then
    echo -e "${RED}✗ File not found: $filename${NC}"
    return 1
  fi

  echo -e "${YELLOW}Uploading $filename ($asset_type, level: $level)...${NC}"

  # Get upload URL
  UPLOAD_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects/$PROJECT_SLUG/versions/$VERSION_NUMBER/assets/upload-url" \
    -H "Content-Type: application/json" \
    -d "{
      \"filename\": \"$filename\",
      \"asset_type\": \"$asset_type\",
      \"content_type\": \"$content_type\"
    }")

  UPLOAD_URL=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('upload_url', ''))" 2>/dev/null)
  STORAGE_PATH=$(echo "$UPLOAD_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('storage_path', ''))" 2>/dev/null)

  if [ -z "$UPLOAD_URL" ] || [ "$UPLOAD_URL" == "null" ]; then
    echo -e "${RED}✗ Failed to get upload URL for $filename${NC}"
    echo "$UPLOAD_RESPONSE"
    return 1
  fi

  # Upload to storage
  curl -s -X PUT "$UPLOAD_URL" \
    -H "Content-Type: $content_type" \
    --data-binary "@$filepath" > /dev/null

  # Confirm upload with metadata
  FILE_SIZE=$(stat -f%z "$filepath" 2>/dev/null || stat -c%s "$filepath" 2>/dev/null)

  CONFIRM_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects/$PROJECT_SLUG/versions/$VERSION_NUMBER/assets/confirm" \
    -H "Content-Type: application/json" \
    -d "{
      \"storage_path\": \"$STORAGE_PATH\",
      \"asset_type\": \"$asset_type\",
      \"filename\": \"$filename\",
      \"file_size\": $FILE_SIZE,
      \"level\": \"$level\"
    }")

  ASSET_ID=$(echo "$CONFIRM_RESPONSE" | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

  if [ -z "$ASSET_ID" ] || [ "$ASSET_ID" == "null" ]; then
    echo -e "${RED}✗ Failed to confirm $filename${NC}"
    echo "$CONFIRM_RESPONSE"
    return 1
  fi

  echo -e "${GREEN}✓ Uploaded $filename (ID: $ASSET_ID)${NC}"
  return 0
}

echo ""
echo "=== Project Level ==="
upload_asset "project-view-map.webp" "base_map" "image/webp" "project"
upload_asset "project-view-overlay.svg" "overlay_svg" "image/svg+xml" "project"

echo ""
echo "=== Zone GC Level ==="
upload_asset "zone-gc-map.webp" "base_map" "image/webp" "zone-gc"
# zone-gc-overlay.svg already uploaded

echo ""
echo "=== Zone A Level ==="
upload_asset "zone-a-map.webp" "base_map" "image/webp" "zone-a"
upload_asset "zone-a-overlay.svg" "overlay_svg" "image/svg+xml" "zone-a"

echo ""
echo "=== Zone H Level ==="
upload_asset "zone-h-map.webp" "base_map" "image/webp" "zone-h"
upload_asset "zone-h-overlay.svg" "overlay_svg" "image/svg+xml" "zone-h"

echo ""
echo "================================================"
echo -e "${GREEN}  Asset Upload Complete!${NC}"
echo "================================================"
echo ""

# List all assets
echo "Listing all assets:"
auth_curl "$API_URL/api/projects/$PROJECT_SLUG/versions/$VERSION_NUMBER/assets" | \
  python3 -c "
import sys, json
data = json.load(sys.stdin)
assets = data.get('assets', [])
print(f'Total: {len(assets)} assets')
print()
for a in assets:
    print(f\"  - {a['filename']} ({a['asset_type']})\")
"
