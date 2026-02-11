#!/bin/bash
# Start the Public API locally

set -e

cd "$(dirname "$0")/../public-service/api"

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

echo "Starting Public API on http://localhost:8001"
echo ""

npm run dev
