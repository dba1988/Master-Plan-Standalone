#!/bin/bash
# Start the Admin UI locally

set -e

cd "$(dirname "$0")/../admin-service/ui"

echo "Starting Admin UI on http://localhost:3001"
echo ""

npm run dev
