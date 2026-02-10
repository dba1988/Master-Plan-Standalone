#!/bin/bash
# Start the Admin API locally

set -e

cd "$(dirname "$0")/../admin-service/api"

# Activate venv if it exists
if [ -d "venv" ]; then
  source venv/bin/activate
fi

echo "Starting Admin API on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
echo ""

uvicorn app.main:app --reload --port 8000
