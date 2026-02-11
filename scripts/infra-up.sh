#!/bin/bash
# Start infrastructure services (PostgreSQL)
# Run this once, then use run-api.sh and run-ui.sh for local dev

set -e

cd "$(dirname "$0")/.."

echo "Starting infrastructure (PostgreSQL)..."
docker-compose up -d postgres

echo "Waiting for PostgreSQL to be ready..."
until docker-compose exec -T postgres pg_isready -U masterplan > /dev/null 2>&1; do
  sleep 1
done

echo ""
echo "Infrastructure is running:"
echo "  - PostgreSQL: localhost:5433"
echo ""
echo "Storage is handled by Cloudflare R2."
echo "Run scripts/setup-r2.sh to verify R2 connection."
echo ""
echo "Next steps:"
echo "  1. Run migrations: cd admin-service/api && alembic upgrade head"
echo "  2. Start API:      ./scripts/run-api.sh"
echo "  3. Start UI:       ./scripts/run-ui.sh"
