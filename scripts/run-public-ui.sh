#!/bin/bash
# Start the Public Viewer locally

set -e

cd "$(dirname "$0")/../public-service/viewer"

# Create .env from example if it doesn't exist
if [ ! -f ".env" ]; then
  echo "Creating .env from .env.example..."
  cp .env.example .env
fi

# Install dependencies if needed
if [ ! -d "node_modules" ]; then
  echo "Installing dependencies..."
  npm install
fi

echo "Starting Public Viewer on http://localhost:3000"
echo "Open: http://localhost:3000?project=project-marina"
echo ""

npm run dev
