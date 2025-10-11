#!/usr/bin/env bash

# =============================================================================
# Nova Europa - Docker Entrypoint (Production)
# =============================================================================
# This script runs BEFORE the main container process starts
# It handles:
# - Database migrations
# - Cache warming
# - Configuration optimization
# - Health checks
# =============================================================================

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[ENTRYPOINT]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[ENTRYPOINT]${NC} $1"
}

log_error() {
    echo -e "${RED}[ENTRYPOINT]${NC} $1"
}

log_step() {
    echo -e "${BLUE}[ENTRYPOINT]${NC} $1"
}

# =============================================================================
# Wait for Database to be Ready
# =============================================================================
wait_for_database() {
    log_step "Waiting for database connection..."

    until php artisan db:show > /dev/null 2>&1; do
        log_info "Database is unavailable - sleeping 2s"
        sleep 2
    done

    log_info "Database is ready!"
}

# =============================================================================
# Main Initialization
# =============================================================================
main() {
    log_step "==================================================================="
    log_step "Nova Europa - Production Container Initialization"
    log_step "==================================================================="

    # Only run initialization for the main app container
    # Skip for queue, scheduler, etc.
    if [ "${CONTAINER_ROLE:-app}" != "app" ]; then
        log_info "Container role is '${CONTAINER_ROLE}', skipping app initialization"
        exec "$@"
        return
    fi

    log_step "Environment: ${APP_ENV:-production}"
    log_step "Debug mode: ${APP_DEBUG:-false}"

    # =============================================================================
    # 1. Wait for Database
    # =============================================================================
    if [ "${DB_CONNECTION:-mysql}" != "sqlite" ]; then
        wait_for_database
    fi

    # =============================================================================
    # 2. Run Database Migrations
    # =============================================================================
    log_step "Running database migrations..."

    if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
        php artisan migrate --force --no-interaction
        log_info "Migrations completed successfully"
    else
        log_warn "Migrations skipped (RUN_MIGRATIONS=false)"
    fi

    # =============================================================================
    # 3. Optimize Configuration for Production
    # =============================================================================
    log_step "Optimizing application configuration..."

    # Clear all caches first
    php artisan config:clear
    php artisan route:clear
    php artisan view:clear
    php artisan cache:clear

    # Cache configuration and routes
    php artisan config:cache
    php artisan route:cache
    php artisan view:cache

    log_info "Application optimized for production"

    # =============================================================================
    # 4. Storage Link (if not exists)
    # =============================================================================
    if [ ! -L /var/www/html/public/storage ]; then
        log_step "Creating storage symlink..."
        php artisan storage:link
    fi

    # =============================================================================
    # 5. Warm Up Cache (Optional)
    # =============================================================================
    if [ "${WARM_CACHE:-false}" = "true" ]; then
        log_step "Warming up application cache..."
        # Add custom cache warming commands here
        # php artisan cache:warm
        log_info "Cache warming completed"
    fi

    # =============================================================================
    # 6. Final Checks
    # =============================================================================
    log_step "Running final health checks..."

    # Check if APP_KEY is set (via environment variable)
    # NOTE: This is a warning, not a blocker. Laravel will fail gracefully if needed.
    if [ -z "$APP_KEY" ]; then
        log_warn "APP_KEY environment variable is not set!"
        log_warn "The application may not work correctly without it."
        log_warn "Generate one with: php artisan key:generate"
    else
        log_info "APP_KEY is configured"
    fi

    log_info "All health checks passed"

    # =============================================================================
    # 7. Start Application
    # =============================================================================
    log_step "==================================================================="
    log_step "Initialization complete. Starting application..."
    log_step "==================================================================="

    exec "$@"
}

# Run main function with all arguments
main "$@"
