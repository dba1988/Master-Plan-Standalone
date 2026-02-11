#!/bin/bash

# Master Plan - Service Management Script
# Manages all services: database, admin API/UI, and public API/viewer

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_ROOT"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Log files
ADMIN_API_LOG="/tmp/admin-api.log"
ADMIN_UI_LOG="/tmp/admin-ui.log"
PUBLIC_API_LOG="/tmp/public-api.log"
PUBLIC_VIEWER_LOG="/tmp/public-viewer.log"

# -----------------------------------------------------------------------------
# Helper Functions
# -----------------------------------------------------------------------------

print_header() {
    echo ""
    echo -e "${BLUE}========================================${NC}"
    echo -e "${BLUE}   Master Plan - $1${NC}"
    echo -e "${BLUE}========================================${NC}"
    echo ""
}

print_success() {
    echo -e "${GREEN}✓ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}! $1${NC}"
}

print_error() {
    echo -e "${RED}✗ $1${NC}"
}

print_info() {
    echo -e "${BLUE}→ $1${NC}"
}

# -----------------------------------------------------------------------------
# Service Control Functions
# -----------------------------------------------------------------------------

stop_processes() {
    print_info "Stopping application processes..."
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "node" 2>/dev/null || true
    pkill -f "tsx" 2>/dev/null || true
    pkill -f "vite" 2>/dev/null || true
    sleep 2
    print_success "Application processes stopped"
}

stop_database() {
    print_info "Stopping database containers..."
    docker compose down 2>/dev/null || true
    print_success "Database containers stopped"
}

start_database() {
    print_info "Starting database (Postgres)..."
    docker compose up -d postgres
    sleep 3
    print_success "Database container started"
}

start_admin_api() {
    print_info "Starting Admin API (port 8000)..."
    cd "$PROJECT_ROOT/admin-service/api"
    source venv/bin/activate
    # Load .env file explicitly for R2 config
    set -a && source .env && set +a
    nohup python -m uvicorn app.main:app --reload --port 8000 > "$ADMIN_API_LOG" 2>&1 &
    sleep 3
    local retries=30
    while ! curl -s http://localhost:8000/health > /dev/null 2>&1; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            print_error "Admin API failed to start. Check $ADMIN_API_LOG"
            return 1
        fi
        sleep 1
    done
    print_success "Admin API ready on http://localhost:8000"
}

start_admin_ui() {
    print_info "Starting Admin UI (port 3001)..."
    cd "$PROJECT_ROOT/admin-service/ui"
    nohup npm run dev -- --port 3001 > "$ADMIN_UI_LOG" 2>&1 &
    sleep 3
    local retries=30
    while ! curl -s http://localhost:3001 > /dev/null 2>&1; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            print_error "Admin UI failed to start. Check $ADMIN_UI_LOG"
            return 1
        fi
        sleep 1
    done
    print_success "Admin UI ready on http://localhost:3001"
}

start_public_api() {
    print_info "Starting Public API (port 8001)..."
    cd "$PROJECT_ROOT/public-service/api"
    nohup npm run dev > "$PUBLIC_API_LOG" 2>&1 &
    sleep 3
    local retries=30
    while ! curl -s http://localhost:8001/health > /dev/null 2>&1; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            print_error "Public API failed to start. Check $PUBLIC_API_LOG"
            return 1
        fi
        sleep 1
    done
    print_success "Public API ready on http://localhost:8001"
}

start_public_viewer() {
    print_info "Starting Public Viewer (port 3000)..."
    cd "$PROJECT_ROOT/public-service/viewer"
    nohup npm run dev -- --port 3000 > "$PUBLIC_VIEWER_LOG" 2>&1 &
    sleep 3
    local retries=30
    while ! curl -s http://localhost:3000 > /dev/null 2>&1; do
        retries=$((retries - 1))
        if [ $retries -le 0 ]; then
            print_error "Public Viewer failed to start. Check $PUBLIC_VIEWER_LOG"
            return 1
        fi
        sleep 1
    done
    print_success "Public Viewer ready on http://localhost:3000"
}

start_all_services() {
    start_database
    start_admin_api
    start_admin_ui
    start_public_api
    start_public_viewer
}

print_status() {
    echo ""
    echo "Service Status:"
    echo "---------------"

    # Check Postgres
    if docker compose ps postgres 2>/dev/null | grep -q "running"; then
        print_success "Postgres:       Running"
    else
        print_error "Postgres:       Not running"
    fi

    # Check Admin API
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        print_success "Admin API:      Running (http://localhost:8000)"
    else
        print_error "Admin API:      Not running"
    fi

    # Check Admin UI
    if curl -s http://localhost:3001 > /dev/null 2>&1; then
        print_success "Admin UI:       Running (http://localhost:3001)"
    else
        print_error "Admin UI:       Not running"
    fi

    # Check Public API
    if curl -s http://localhost:8001/health > /dev/null 2>&1; then
        print_success "Public API:     Running (http://localhost:8001)"
    else
        print_error "Public API:     Not running"
    fi

    # Check Public Viewer
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        print_success "Public Viewer:  Running (http://localhost:3000)"
    else
        print_error "Public Viewer:  Not running"
    fi
    echo ""
}

print_summary() {
    echo ""
    echo "Services:"
    echo "  Admin API:      http://localhost:8000"
    echo "  Admin UI:       http://localhost:3001"
    echo "  Public API:     http://localhost:8001"
    echo "  Public Viewer:  http://localhost:3000?project=sedra-3"
    echo ""
    echo "Logs:"
    echo "  $ADMIN_API_LOG"
    echo "  $ADMIN_UI_LOG"
    echo "  $PUBLIC_API_LOG"
    echo "  $PUBLIC_VIEWER_LOG"
    echo ""
}

show_logs() {
    local service="${1:-all}"
    case "$service" in
        admin-api)
            tail -f "$ADMIN_API_LOG"
            ;;
        admin-ui)
            tail -f "$ADMIN_UI_LOG"
            ;;
        public-api)
            tail -f "$PUBLIC_API_LOG"
            ;;
        public-viewer)
            tail -f "$PUBLIC_VIEWER_LOG"
            ;;
        all)
            tail -f "$ADMIN_API_LOG" "$ADMIN_UI_LOG" "$PUBLIC_API_LOG" "$PUBLIC_VIEWER_LOG"
            ;;
        *)
            print_error "Unknown service: $service"
            echo "Available: admin-api, admin-ui, public-api, public-viewer, all"
            exit 1
            ;;
    esac
}

# -----------------------------------------------------------------------------
# Command Handlers
# -----------------------------------------------------------------------------

cmd_start() {
    print_header "Starting All Services"
    stop_processes
    start_all_services
    print_header "All Services Started!"
    print_summary
}

cmd_stop() {
    print_header "Stopping Services"
    stop_processes
    print_success "All application services stopped"
    echo ""
    print_warning "Database is still running. Use 'shutdown' to stop everything."
    echo ""
}

cmd_up() {
    print_header "Starting All Services"
    start_database
    start_admin_api
    start_admin_ui
    start_public_api
    start_public_viewer
    print_header "All Services Started!"
    print_summary
}

cmd_down() {
    print_header "Stopping All Services"
    stop_processes
    stop_database
    print_success "All services stopped"
    echo ""
}

cmd_restart() {
    print_header "Restarting All Services"
    stop_processes
    echo ""
    start_all_services
    print_header "All Services Restarted!"
    print_summary
}

cmd_shutdown() {
    print_header "Shutting Down Everything"
    stop_processes
    stop_database
    print_success "Complete shutdown finished"
    echo ""
}

cmd_status() {
    print_header "Service Status"
    print_status
}

cmd_logs() {
    show_logs "${1:-all}"
}

cmd_help() {
    echo ""
    echo "Master Plan - Service Management Script"
    echo ""
    echo "Usage: $0 <command> [options]"
    echo ""
    echo "Commands:"
    echo "  start       Stop processes, then start all services (default)"
    echo "  stop        Stop application processes (keeps database running)"
    echo "  up          Start all services without stopping first"
    echo "  down        Stop all services including database"
    echo "  restart     Restart all application services"
    echo "  shutdown    Complete shutdown of all services and containers"
    echo "  status      Show status of all services"
    echo "  logs [svc]  Tail logs (admin-api|admin-ui|public-api|public-viewer|all)"
    echo "  help        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 start              # Start all services"
    echo "  $0 restart            # Restart all services"
    echo "  $0 status             # Check service status"
    echo "  $0 logs admin-api     # Tail admin API logs"
    echo "  $0 shutdown           # Stop everything"
    echo ""
}

# -----------------------------------------------------------------------------
# Main Entry Point
# -----------------------------------------------------------------------------

COMMAND="${1:-start}"
shift 2>/dev/null || true

case "$COMMAND" in
    start)
        cmd_start
        ;;
    stop)
        cmd_stop
        ;;
    up)
        cmd_up
        ;;
    down)
        cmd_down
        ;;
    restart)
        cmd_restart
        ;;
    shutdown)
        cmd_shutdown
        ;;
    status)
        cmd_status
        ;;
    logs)
        cmd_logs "$1"
        ;;
    help|--help|-h)
        cmd_help
        ;;
    *)
        print_error "Unknown command: $COMMAND"
        cmd_help
        exit 1
        ;;
esac
