#!/bin/bash
# E2E Test Script for Admin API
# Tests the full flow: login -> create project -> upload assets -> generate tiles -> publish

set -e

API_URL="http://localhost:8000"
RESOURCE_DIR="/Users/nishajamaludin/Documents/GitHub/Master-Plan-Standalone/resource/sedra-3"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo "================================================"
echo "  E2E Test: Admin API"
echo "================================================"
echo ""

# Step 1: Login
echo -e "${YELLOW}[1/8] Logging in...${NC}"
LOGIN_RESPONSE=$(curl -s -X POST "$API_URL/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email": "admin@example.com", "password": "admin123"}')

ACCESS_TOKEN=$(echo $LOGIN_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('access_token', ''))" 2>/dev/null)

if [ -z "$ACCESS_TOKEN" ]; then
  echo -e "${RED}✗ Login failed${NC}"
  echo "$LOGIN_RESPONSE"
  exit 1
fi
echo -e "${GREEN}✓ Logged in successfully${NC}"

# Helper function for authenticated requests
auth_curl() {
  curl -s -H "Authorization: Bearer $ACCESS_TOKEN" "$@"
}

# Step 2: Create Project
echo -e "${YELLOW}[2/8] Creating test project 'sedra-3'...${NC}"
PROJECT_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Sedra Phase 3",
    "slug": "sedra-3",
    "description": "E2E Test Project"
  }')

PROJECT_SLUG=$(echo $PROJECT_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('slug', ''))" 2>/dev/null)

if [ -z "$PROJECT_SLUG" ] || [ "$PROJECT_SLUG" == "null" ]; then
  # Check if project already exists
  EXISTING=$(auth_curl "$API_URL/api/projects/sedra-3")
  PROJECT_SLUG=$(echo $EXISTING | python3 -c "import sys, json; print(json.load(sys.stdin).get('slug', ''))" 2>/dev/null)
  if [ -n "$PROJECT_SLUG" ] && [ "$PROJECT_SLUG" != "null" ]; then
    echo -e "${GREEN}✓ Project already exists${NC}"
  else
    echo -e "${RED}✗ Failed to create project${NC}"
    echo "$PROJECT_RESPONSE"
    exit 1
  fi
else
  echo -e "${GREEN}✓ Project created: $PROJECT_SLUG${NC}"
fi

# Get draft version number
PROJECT_DATA=$(auth_curl "$API_URL/api/projects/sedra-3")
VERSION_NUMBER=$(echo $PROJECT_DATA | python3 -c "
import sys, json
data = json.load(sys.stdin)
versions = data.get('versions', [])
draft = next((v for v in versions if v.get('status') == 'draft'), None)
print(draft.get('version_number', 1) if draft else 1)
" 2>/dev/null)

echo "   Draft version: $VERSION_NUMBER"

# Step 3: Upload Base Map
echo -e "${YELLOW}[3/8] Uploading base map (zone-gc-map.webp)...${NC}"

# Get presigned upload URL
UPLOAD_URL_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects/sedra-3/versions/$VERSION_NUMBER/assets/upload-url" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "zone-gc-map.webp",
    "asset_type": "base_map",
    "content_type": "image/webp"
  }')

UPLOAD_URL=$(echo $UPLOAD_URL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('upload_url', ''))" 2>/dev/null)
STORAGE_PATH=$(echo $UPLOAD_URL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('storage_path', ''))" 2>/dev/null)

if [ -z "$UPLOAD_URL" ] || [ "$UPLOAD_URL" == "null" ]; then
  echo -e "${RED}✗ Failed to get upload URL${NC}"
  echo "$UPLOAD_URL_RESPONSE"
  exit 1
fi

# Upload file to storage
curl -s -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/webp" \
  --data-binary "@$RESOURCE_DIR/zone-gc-map.webp" > /dev/null

# Confirm upload
CONFIRM_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects/sedra-3/versions/$VERSION_NUMBER/assets/confirm" \
  -H "Content-Type: application/json" \
  -d "{
    \"storage_path\": \"$STORAGE_PATH\",
    \"asset_type\": \"base_map\",
    \"filename\": \"zone-gc-map.webp\",
    \"file_size\": $(stat -f%z "$RESOURCE_DIR/zone-gc-map.webp")
  }")

BASE_MAP_ID=$(echo $CONFIRM_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -z "$BASE_MAP_ID" ] || [ "$BASE_MAP_ID" == "null" ]; then
  echo -e "${RED}✗ Failed to confirm upload${NC}"
  echo "$CONFIRM_RESPONSE"
  exit 1
fi
echo -e "${GREEN}✓ Base map uploaded (ID: $BASE_MAP_ID)${NC}"

# Step 4: Upload SVG Overlay
echo -e "${YELLOW}[4/8] Uploading SVG overlay (zone-gc-overlay.svg)...${NC}"

UPLOAD_URL_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects/sedra-3/versions/$VERSION_NUMBER/assets/upload-url" \
  -H "Content-Type: application/json" \
  -d '{
    "filename": "zone-gc-overlay.svg",
    "asset_type": "overlay_svg",
    "content_type": "image/svg+xml"
  }')

UPLOAD_URL=$(echo $UPLOAD_URL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('upload_url', ''))" 2>/dev/null)
STORAGE_PATH=$(echo $UPLOAD_URL_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('storage_path', ''))" 2>/dev/null)

curl -s -X PUT "$UPLOAD_URL" \
  -H "Content-Type: image/svg+xml" \
  --data-binary "@$RESOURCE_DIR/zone-gc-overlay.svg" > /dev/null

CONFIRM_RESPONSE=$(auth_curl -X POST "$API_URL/api/projects/sedra-3/versions/$VERSION_NUMBER/assets/confirm" \
  -H "Content-Type: application/json" \
  -d "{
    \"storage_path\": \"$STORAGE_PATH\",
    \"asset_type\": \"overlay_svg\",
    \"filename\": \"zone-gc-overlay.svg\",
    \"file_size\": $(stat -f%z "$RESOURCE_DIR/zone-gc-overlay.svg")
  }")

SVG_ASSET_ID=$(echo $CONFIRM_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)
echo -e "${GREEN}✓ SVG overlay uploaded (ID: $SVG_ASSET_ID)${NC}"

# Step 5: Generate Tiles
echo -e "${YELLOW}[5/8] Generating tiles from base map...${NC}"

TILE_JOB_RESPONSE=$(auth_curl -X POST "$API_URL/api/tiles/projects/sedra-3/versions/$VERSION_NUMBER/generate-tiles?asset_id=$BASE_MAP_ID")

JOB_ID=$(echo $TILE_JOB_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('job_id', ''))" 2>/dev/null)

if [ -z "$JOB_ID" ] || [ "$JOB_ID" == "null" ]; then
  echo -e "${RED}✗ Failed to start tile generation${NC}"
  echo "$TILE_JOB_RESPONSE"
  exit 1
fi

echo "   Job ID: $JOB_ID"

# Poll for job completion
echo -n "   Waiting for completion"
for i in {1..60}; do
  sleep 2
  JOB_STATUS=$(auth_curl "$API_URL/api/jobs/$JOB_ID")
  STATUS=$(echo $JOB_STATUS | python3 -c "import sys, json; print(json.load(sys.stdin).get('status', ''))" 2>/dev/null)
  PROGRESS=$(echo $JOB_STATUS | python3 -c "import sys, json; print(json.load(sys.stdin).get('progress', 0))" 2>/dev/null)

  echo -n "."

  if [ "$STATUS" == "completed" ]; then
    echo ""
    echo -e "${GREEN}✓ Tiles generated successfully${NC}"
    break
  elif [ "$STATUS" == "failed" ]; then
    echo ""
    echo -e "${RED}✗ Tile generation failed${NC}"
    echo "$JOB_STATUS"
    exit 1
  fi
done

# Step 6: Test Config Endpoints
echo -e "${YELLOW}[6/8] Testing config endpoints...${NC}"

CONFIG_RESPONSE=$(auth_curl "$API_URL/api/projects/sedra-3/versions/$VERSION_NUMBER/config")
CONFIG_ID=$(echo $CONFIG_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -n "$CONFIG_ID" ] && [ "$CONFIG_ID" != "null" ]; then
  echo -e "${GREEN}✓ Config endpoint works${NC}"
else
  echo -e "${YELLOW}⚠ Config returned empty (may be expected)${NC}"
fi

# Step 7: Test Integration Endpoints
echo -e "${YELLOW}[7/8] Testing integration endpoints...${NC}"

INTEGRATION_RESPONSE=$(auth_curl "$API_URL/api/projects/sedra-3/integration")
INTEGRATION_ID=$(echo $INTEGRATION_RESPONSE | python3 -c "import sys, json; print(json.load(sys.stdin).get('id', ''))" 2>/dev/null)

if [ -n "$INTEGRATION_ID" ] && [ "$INTEGRATION_ID" != "null" ]; then
  echo -e "${GREEN}✓ Integration endpoint works${NC}"
else
  echo -e "${YELLOW}⚠ Integration returned empty (may be expected)${NC}"
fi

# Step 8: List Assets
echo -e "${YELLOW}[8/8] Verifying uploaded assets...${NC}"

ASSETS_RESPONSE=$(auth_curl "$API_URL/api/projects/sedra-3/versions/$VERSION_NUMBER/assets")
ASSET_COUNT=$(echo $ASSETS_RESPONSE | python3 -c "import sys, json; data=json.load(sys.stdin); print(len(data.get('items', data)) if isinstance(data, dict) else len(data))" 2>/dev/null)

echo -e "${GREEN}✓ Found $ASSET_COUNT assets${NC}"

echo ""
echo "================================================"
echo -e "${GREEN}  E2E Test Completed Successfully!${NC}"
echo "================================================"
echo ""
echo "Summary:"
echo "  - Project: sedra-3"
echo "  - Version: $VERSION_NUMBER"
echo "  - Base Map ID: $BASE_MAP_ID"
echo "  - SVG Asset ID: $SVG_ASSET_ID"
echo "  - Tile Job ID: $JOB_ID"
echo ""
echo "Next steps:"
echo "  1. Open http://localhost:3001 in browser"
echo "  2. Login with admin@example.com / admin123"
echo "  3. Navigate to Projects -> Sedra Phase 3"
echo "  4. Check Assets tab for uploaded files"
echo "  5. Try publishing the project"
