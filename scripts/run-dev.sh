#!/bin/bash
# Start both Admin API and UI for local development

set -e

cd "$(dirname "$0")/.."

echo "Starting Admin API and UI..."
echo ""

# Start API in background
(cd admin-service/api && source venv/bin/activate && uvicorn app.main:app --reload --port 8000) &
API_PID=$!

# Start UI in background
(cd admin-service/ui && npm run dev) &
UI_PID=$!

echo "Services starting:"
echo "  - API: http://localhost:8000 (docs: http://localhost:8000/docs)"
echo "  - UI:  http://localhost:3001"
echo ""
echo "Press Ctrl+C to stop both services"

# Handle Ctrl+C to kill both processes
trap "echo ''; echo 'Stopping services...'; kill $API_PID $UI_PID 2>/dev/null; exit 0" INT

# Wait for both processes
wait
