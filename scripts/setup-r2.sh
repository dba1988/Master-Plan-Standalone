#!/bin/bash
# Setup and verify Cloudflare R2 buckets using Wrangler
# This script creates the R2 buckets and tests connectivity
#
# Prerequisites:
#   1. Install wrangler: npm install -g wrangler
#   2. Authenticate: wrangler login (opens browser for OAuth)

set -e

cd "$(dirname "$0")/.."

# Configuration
BUCKETS=("masterplan-dev" "masterplan-prod")

echo "Cloudflare R2 Setup"
echo "==================="
echo ""

# Check for wrangler
if ! command -v wrangler &> /dev/null; then
    echo "ERROR: Wrangler CLI is not installed."
    echo "Install it with: npm install -g wrangler"
    exit 1
fi

# Check authentication
echo "Checking wrangler authentication..."
if ! wrangler whoami > /dev/null 2>&1; then
    echo ""
    echo "ERROR: Not authenticated with Cloudflare."
    echo ""
    echo "Please run this command first:"
    echo "  wrangler login"
    echo ""
    echo "This will open a browser to authenticate with your Cloudflare account."
    exit 1
fi
echo "Authenticated!"

echo ""
echo "Current R2 buckets:"
wrangler r2 bucket list

echo ""
# Create buckets
for bucket in "${BUCKETS[@]}"; do
    echo "Checking bucket: $bucket"
    if wrangler r2 bucket list 2>/dev/null | grep -q "$bucket"; then
        echo "  Bucket already exists"
    else
        echo "  Creating bucket..."
        wrangler r2 bucket create "$bucket"
        echo "  Bucket created"
    fi
done

echo ""
echo "Testing upload/download with masterplan-dev..."
TEST_FILE="/tmp/r2-test-$$"
echo "R2 connectivity test - $(date)" > "$TEST_FILE"

# Upload test file
wrangler r2 object put "masterplan-dev/test.txt" --file="$TEST_FILE" --content-type="text/plain"

# Download and verify
wrangler r2 object get "masterplan-dev/test.txt" --file="${TEST_FILE}-downloaded"

if diff "$TEST_FILE" "${TEST_FILE}-downloaded" > /dev/null; then
    echo "Upload/download test passed!"
else
    echo "ERROR: Upload/download test failed!"
    rm -f "$TEST_FILE" "${TEST_FILE}-downloaded"
    exit 1
fi

# Cleanup
wrangler r2 object delete "masterplan-dev/test.txt"
rm -f "$TEST_FILE" "${TEST_FILE}-downloaded"

echo ""
echo "R2 Setup Complete!"
echo "=================="
echo ""
echo "Buckets available:"
for bucket in "${BUCKETS[@]}"; do
    echo "  - $bucket"
done
echo ""
echo "Next steps:"
echo "  1. Enable public access via Cloudflare Dashboard:"
echo "     - Go to R2 > masterplan-dev > Settings > Public access"
echo "     - Enable 'R2.dev subdomain'"
echo "     - Copy the public URL (e.g., https://pub-xxxxx.r2.dev)"
echo ""
echo "  2. Update your .env files with the public URL:"
echo "     - admin-service/api/.env: CDN_BASE_URL=<public-url>"
echo "     - public-service/api/.env: CDN_BASE_URL=<public-url>"
echo "     - public-service/viewer/.env: VITE_CDN_BASE_URL=<public-url>"
