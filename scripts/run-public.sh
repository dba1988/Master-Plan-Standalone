#!/bin/bash
# Start both Public API and Viewer for local development

set -e

cd "$(dirname "$0")/.."

echo "Starting Public API and Viewer..."
echo ""

# Create .env files if they don't exist
if [ ! -f "public-service/api/.env" ]; then
  cp public-service/api/.env.example public-service/api/.env
fi
if [ ! -f "public-service/viewer/.env" ]; then
  cp public-service/viewer/.env.example public-service/viewer/.env
fi

# Install dependencies if needed
if [ ! -d "public-service/api/node_modules" ]; then
  echo "Installing Public API dependencies..."
  (cd public-service/api && npm install)
fi
if [ ! -d "public-service/viewer/node_modules" ]; then
  echo "Installing Viewer dependencies..."
  (cd public-service/viewer && npm install)
fi

# Start API in background
(cd public-service/api && npm run dev) &
API_PID=$!

# Give API a moment to start
sleep 2

# Start Viewer in background
(cd public-service/viewer && npm run dev) &
UI_PID=$!

echo ""
echo "Services starting:"
echo "  - Public API: http://localhost:8001"
echo "  - Viewer:     http://localhost:3000"
echo ""
echo "Open: http://localhost:3000?project=project-marina"
echo ""
echo "Press Ctrl+C to stop both services"

# Handle Ctrl+C to kill both processes
trap "echo ''; echo 'Stopping services...'; kill $API_PID $UI_PID 2>/dev/null; exit 0" INT

# Wait for both processes
wait
